"""The post-deploy public URL guard in the deploy workflow (issue #48).

After a ``main`` deploy, the last step polls ``PUBLIC_LANDING_URL`` until it
answers ``200`` with a body that carries the Landing's home-page marker, and
fails the job if the retry budget runs out. The tests run the step's own
``run`` script with bash, as the runner does, against a local HTTP server.
"""

import http.server
import os
import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github" / "workflows" / "deploy-cloudflare-pages.yml"
STEP = "Verify the Landing serves at its public URL"
DEPLOY_STEP = "Deploy to Cloudflare Pages"
HOME_PAGE_SOURCE = REPO / "site" / "src" / "routes" / "+page.svelte"


def _workflow_lines() -> list[str]:
    return WORKFLOW.read_text().splitlines()


def _step_block(name: str) -> list[str]:
    """The lines of the step named ``name``, up to the next step or the end."""
    lines = _workflow_lines()
    start = next(i for i, line in enumerate(lines) if line.strip() == f"- name: {name}")
    dash_indent = len(lines[start]) - len(lines[start].lstrip())
    block = [lines[start]]
    for line in lines[start + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= dash_indent:
            break
        block.append(line)
    return block


def _step_script() -> str:
    """The step's ``run: |`` block, dedented, read without a YAML parser."""
    block = _step_block(STEP)
    run = next(i for i, line in enumerate(block) if line.strip() == "run: |")
    key_indent = len(block[run]) - len(block[run].lstrip())
    body: list[str] = []
    for line in block[run + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= key_indent:
            break
        body.append(line)
    indent = min(len(b) - len(b.lstrip()) for b in body if b.strip())
    return "\n".join(b[indent:] for b in body) + "\n"


def _step_env(key: str) -> str:
    """The value of ``key`` in the step's ``env:`` map, unquoted."""
    for line in _step_block(STEP):
        stripped = line.strip()
        if stripped.startswith(f"{key}:"):
            value = stripped.split(":", 1)[1].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            return value
    raise AssertionError(f"{key} is not in the env of step {STEP!r}")


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


def _home_page() -> str:
    marker = _step_env("LANDING_MARKER")
    return f"<!doctype html><html><head>{marker}</head><body>Datasets</body></html>"


def _run(url: str | None, attempts: str = "3") -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "PUBLIC_LANDING_URL"}
    env |= {
        "LANDING_MARKER": _step_env("LANDING_MARKER"),
        "POLL_ATTEMPTS": attempts,
        "POLL_DELAY_SECONDS": "0",
    }
    if url is not None:
        env["PUBLIC_LANDING_URL"] = url
    # GitHub runs `run:` blocks as `bash --noprofile --norc -eo pipefail {0}`.
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", _step_script()],
        check=False,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_the_landing_answering_200_with_its_home_page_passes(server: _Server) -> None:
    server.answers = [(200, _home_page())]

    result = _run(server.url)

    assert result.returncode == 0, result.stdout + result.stderr
    assert server.requests == 1
    assert f"OK: {server.url} serves the Landing" in result.stdout


def _closed_port_url() -> str:
    """A local URL nothing listens on, so every request fails to connect."""
    srv = _Server()
    url = srv.url
    srv.close()
    return url


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
    marker = _step_env("LANDING_MARKER")

    assert marker == "<title>PetroDB: open petroleum datasets in Parquet</title>"
    assert marker in HOME_PAGE_SOURCE.read_text()


def test_the_budget_is_six_attempts_ten_seconds_apart() -> None:
    assert _step_env("POLL_ATTEMPTS") == "6"
    assert _step_env("POLL_DELAY_SECONDS") == "10"


def test_the_step_runs_on_main_only() -> None:
    block = [line.strip() for line in _step_block(STEP)]

    assert "if: github.ref_name == 'main'" in block


def test_the_step_is_the_last_one_and_comes_after_the_pages_deploy() -> None:
    names = [
        line.strip()
        for line in _workflow_lines()
        if line.strip().startswith("- name: ")
    ]

    assert names[-1] == f"- name: {STEP}"
    assert names.index(f"- name: {DEPLOY_STEP}") < names.index(f"- name: {STEP}")


def test_it_polls_the_deploy_jobs_public_landing_url() -> None:
    assert "${PUBLIC_LANDING_URL" in _step_script()
    assert "      PUBLIC_LANDING_URL: https://petrodb.ocortez.com" in _workflow_lines()
