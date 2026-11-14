"""The Landing host guard in the deploy's verify step (issue #47).

Before the main/stage deploy publishes ``site/build``, the step asserts that the
tree is staged where the Landing says it lives: ``index.html`` at the tree's
root, and its ``canonical`` (and ``og:url``, when present) naming the host in
``PUBLIC_LANDING_URL``. The tests run the step's own ``run`` script with bash,
as the runner does, against small trees.
"""

import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github" / "workflows" / "deploy-cloudflare-pages.yml"
STEP = "Verify no off-branch data host in the built output"

LANDING = "https://petrodb.ocortez.com"
MAIN_BASE = "https://huggingface.co/datasets/oskrgab/petrodb/resolve/main"
STAGE_BASE = "https://huggingface.co/datasets/oskrgab/petrodb/resolve/stage"


def _workflow_lines() -> list[str]:
    return WORKFLOW.read_text().splitlines()


def _step_script() -> str:
    """The verify step's ``run: |`` block, dedented, read without a YAML parser."""
    lines = _workflow_lines()
    start = next(i for i, line in enumerate(lines) if line.strip() == f"- name: {STEP}")
    run = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == "run: |")
    key_indent = len(lines[run]) - len(lines[run].lstrip())
    body: list[str] = []
    for line in lines[run + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= key_indent:
            break
        body.append(line)
    indent = min(len(b) - len(b.lstrip()) for b in body if b.strip())
    return "\n".join(b[indent:] for b in body) + "\n"


def _page(canonical: str | None = f"{LANDING}/", og_url: str | None = None) -> str:
    head = ['<meta charset="utf-8">']
    if canonical is not None:
        head.append(f'<link rel="canonical" href="{canonical}">')
    if og_url is not None:
        head.append(f'<meta property="og:url" content="{og_url}">')
    return (
        "<!doctype html><html><head>"
        + "".join(head)
        + f"</head><body>FROM '{STAGE_BASE}/volve/wells.parquet'</body></html>"
    )


def _stage(root: Path, rel: str = "index.html", page: str | None = None) -> None:
    """A stage-deploy checkout: the built tree and the HF dataset card."""
    path = root / "site" / "build" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_page() if page is None else page)
    card = root / "hf" / "README.md"
    card.parent.mkdir(parents=True, exist_ok=True)
    card.write_text(f"{STAGE_BASE}/volve/wells.parquet")


def _run(root: Path, landing: str | None = LANDING) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "PUBLIC_LANDING_URL"}
    env |= {"OTHER_BASE": MAIN_BASE, "PYTHONPATH": str(REPO)}
    if landing is not None:
        env["PUBLIC_LANDING_URL"] = landing
    # GitHub runs `run:` blocks as `bash --noprofile --norc -eo pipefail {0}`.
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", _step_script()],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )


def test_a_tree_staged_at_the_landing_host_passes(tmp_path: Path) -> None:
    _stage(tmp_path)

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("landing", [None, ""])
def test_an_unset_or_empty_landing_url_fails(
    tmp_path: Path, landing: str | None
) -> None:
    _stage(tmp_path)

    result = _run(tmp_path, landing=landing)

    assert result.returncode != 0
    assert "PUBLIC_LANDING_URL is empty or unset" in result.stdout


def test_a_root_page_staged_one_directory_deep_fails(tmp_path: Path) -> None:
    # Commit 5bd0271's layout: the Landing under site/build/petrodb/.
    _stage(tmp_path, rel="petrodb/index.html")

    result = _run(tmp_path)

    assert result.returncode != 0
    assert "no index.html at the root of site/build" in result.stdout


def test_a_canonical_naming_another_host_fails(tmp_path: Path) -> None:
    # Commit 5bd0271's canonical.
    _stage(tmp_path, page=_page(canonical="https://sumpalabs.com/petrodb/"))

    result = _run(tmp_path)

    assert result.returncode != 0
    assert "canonical names https://sumpalabs.com/petrodb/" in result.stdout
    assert LANDING in result.stdout


def test_an_og_url_naming_another_host_fails(tmp_path: Path) -> None:
    _stage(tmp_path, page=_page(og_url="https://petrodb.pages.dev/"))

    result = _run(tmp_path)

    assert result.returncode != 0
    assert "og:url names https://petrodb.pages.dev/" in result.stdout


def test_an_og_url_at_the_landing_host_passes(tmp_path: Path) -> None:
    _stage(tmp_path, page=_page(og_url=LANDING))

    assert _run(tmp_path).returncode == 0


@pytest.mark.parametrize("landing", [LANDING, f"{LANDING}/"])
def test_a_trailing_slash_on_either_side_is_tolerated(
    tmp_path: Path, landing: str
) -> None:
    _stage(tmp_path, page=_page(canonical=LANDING))

    assert _run(tmp_path, landing=landing).returncode == 0


def test_another_scheme_fails(tmp_path: Path) -> None:
    _stage(tmp_path, page=_page(canonical="http://petrodb.ocortez.com/"))

    assert _run(tmp_path).returncode != 0


def test_a_root_page_without_a_canonical_fails(tmp_path: Path) -> None:
    _stage(tmp_path, page=_page(canonical=None))

    result = _run(tmp_path)

    assert result.returncode != 0
    assert "no canonical link" in result.stdout


def test_the_data_host_check_still_runs_beside_the_host_guard(tmp_path: Path) -> None:
    _stage(tmp_path, rel="petrodb/index.html")
    (tmp_path / "site" / "build" / "volve.parquet").write_bytes(b"PAR1")

    result = _run(tmp_path)

    # Both guards report before the step fails.
    assert "data file in the deploy tree" in result.stdout
    assert "no index.html at the root of site/build" in result.stdout


def test_the_deploy_job_sets_the_landing_url_as_a_literal() -> None:
    lines = [line.strip() for line in _workflow_lines()]

    assert f"PUBLIC_LANDING_URL: {LANDING}" in lines
