"""The post-deploy public URL guard in the deploy workflow (issue #48).

After a ``main`` deploy, the last step polls ``PUBLIC_LANDING_URL`` until it
answers ``200`` with a body that carries the Landing's home-page marker, and
fails the job if the retry budget runs out. The tests run the step's own
``run`` script with bash, as the runner does, against a local HTTP server.
"""

import http.server
import subprocess
import threading
from collections.abc import Iterator

import pytest

from tests.deploy.support import (
    REPO_ROOT,
    env_value,
    run_step,
    step_block,
    step_script,
    workflow_lines,
)

STEP = "Verify the Landing serves at its public URL"
DEPLOY_STEP = "Deploy to Cloudflare Pages"
HOME_PAGE_SOURCE = REPO_ROOT / "site" / "src" / "routes" / "+page.svelte"
BUILT_HOME_PAGE = REPO_ROOT / "site" / "build" / "index.html"


def _marker() -> str:
    return env_value("LANDING_MARKER", step_block(STEP))


class _Server:
    """A local server answering GETs from a script of ``(status, body)``.

    Request *n* gets ``answers[n - 1]``; once the script runs out, the last
    answer repeats. A ``None`` status drops the connection without a reply.
    """

    def __init__(self) -> None:
        self.answers: list[tuple[int | None, str]] = [(200, "")]
        self.requests = 0
        server = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                server.requests += 1
                status, body = server.answers[
                    min(server.requests, len(server.answers)) - 1
                ]
                if status is None:
                    self.close_connection = True
                    return
                payload = body.encode()
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args: object) -> None:
                pass

        self._httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._httpd.server_port}"
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()


@pytest.fixture
def server() -> Iterator[_Server]:
    srv = _Server()
    yield srv
    srv.close()


def _closed_port_url() -> str:
    """A local URL nothing listens on, so every request fails to connect."""
    srv = _Server()
    url = srv.url
    srv.close()
    return url


def _home_page() -> str:
    return f"<!doctype html><html><head>{_marker()}</head><body>Datasets</body></html>"


def _run(url: str | None, attempts: str = "3") -> subprocess.CompletedProcess[str]:
    env = {
        "LANDING_MARKER": _marker(),
        "POLL_ATTEMPTS": attempts,
        "POLL_DELAY_SECONDS": "0",
        "PUBLIC_LANDING_URL": url,
    }
    return run_step(STEP, env)


def test_the_landing_answering_200_with_its_home_page_passes(server: _Server) -> None:
    server.answers = [(200, _home_page())]

    result = _run(server.url)

    assert result.returncode == 0, result.stdout + result.stderr
    assert server.requests == 1
    assert f"OK: {server.url} serves the Landing" in result.stdout


def test_it_retries_until_the_landing_serves(server: _Server) -> None:
    server.answers = [
        (522, "origin unreachable"),
        (404, "not found"),
        (200, _home_page()),
    ]

    result = _run(server.url, attempts="5")

    assert result.returncode == 0, result.stdout + result.stderr
    assert server.requests == 3


def test_a_200_without_the_home_page_fails(server: _Server) -> None:
    server.answers = [(200, "<html><title>Parked domain</title></html>")]

    result = _run(server.url, attempts="2")

    assert result.returncode != 0
    assert server.requests == 2
    assert "::error::" in result.stdout
    assert "last status 200, home page marker found: no" in result.stdout


def test_exhausting_the_budget_reports_the_last_status(server: _Server) -> None:
    server.answers = [(530, _home_page()), (530, "error"), (404, "not found")]

    result = _run(server.url, attempts="3")

    assert result.returncode != 0
    assert server.requests == 3
    assert "::error::" in result.stdout
    assert (
        "after 3 attempts (last status 404, home page marker found: no)"
        in result.stdout
    )


def test_a_host_that_never_answers_reports_status_000() -> None:
    result = _run(_closed_port_url(), attempts="2")

    assert result.returncode != 0
    assert (
        "after 2 attempts (last status 000, home page marker found: no)"
        in result.stdout
    )


def test_a_failed_connection_does_not_reuse_the_previous_body(server: _Server) -> None:
    # Attempt 1 gets the home page with a 503; attempt 2 gets no reply. The
    # report must not claim the marker was found on a request that got nothing.
    server.answers = [(503, _home_page()), (None, "")]

    result = _run(server.url, attempts="2")

    assert "Attempt 1 of 2: status 503, home page marker found: yes" in result.stdout
    assert "last status 000, home page marker found: no" in result.stdout


@pytest.mark.parametrize("url", [None, ""])
def test_an_unset_public_url_fails_with_an_error(url: str | None) -> None:
    result = _run(url)

    assert result.returncode != 0
    assert (
        "::error::Public URL guard: PUBLIC_LANDING_URL is empty or unset"
        in result.stdout
    )


def test_the_marker_is_the_home_page_title_in_the_site_source() -> None:
    marker = _marker()

    assert marker.startswith("<title>")
    assert marker in HOME_PAGE_SOURCE.read_text()


@pytest.mark.skipif(
    not BUILT_HOME_PAGE.exists(), reason="no site/build; build the Landing first"
)
def test_the_marker_is_in_the_built_home_page() -> None:
    assert _marker() in BUILT_HOME_PAGE.read_text()


def test_the_step_runs_on_main_only() -> None:
    block = [line.strip() for line in step_block(STEP)]

    assert "if: github.ref_name == 'main'" in block


def test_the_step_is_the_last_one_and_comes_after_the_pages_deploy() -> None:
    names = [
        line.strip()
        for line in workflow_lines()
        if line.strip().startswith("- name: ")
    ]

    assert names[-1] == f"- name: {STEP}"
    assert names.index(f"- name: {DEPLOY_STEP}") < names.index(f"- name: {STEP}")


def test_it_polls_the_deploy_jobs_public_landing_url() -> None:
    # The job's value, pinned by the Landing host guard's tests; the step
    # must read it and never set its own.
    assert "${PUBLIC_LANDING_URL" in step_script(STEP)
    assert not any(
        line.strip().startswith("PUBLIC_LANDING_URL:") for line in step_block(STEP)
    )
