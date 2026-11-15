"""The Landing host guard in the deploy's verify step (issue #47).

Before the main/stage deploy publishes ``site/build``, the step asserts that the
tree is staged where the Landing says it lives: ``index.html`` at the tree's
root, and every ``canonical`` (and every ``og:url``) in it naming the host in
``PUBLIC_LANDING_URL``. The tests run the step's own ``run`` script with bash,
as the runner does, against small trees.
"""

import subprocess
from pathlib import Path

import pytest

from tests.deploy.support import LANDING, REPO_ROOT, env_value, run_step

STEP = "Verify no off-branch data host in the built output"

MAIN_BASE = "https://huggingface.co/datasets/oskrgab/petrodb/resolve/main"
STAGE_BASE = "https://huggingface.co/datasets/oskrgab/petrodb/resolve/stage"


def _page(
    canonical: str | None = f"{LANDING}/",
    og_url: str | None = None,
    extra_head: str = "",
) -> str:
    head = ['<meta charset="utf-8">']
    if canonical is not None:
        head.append(f'<link rel="canonical" href="{canonical}">')
    if og_url is not None:
        head.append(f'<meta property="og:url" content="{og_url}">')
    head.append(extra_head)
    return (
        "<!doctype html><html><head>"
        + "".join(head)
        + f"</head><body>FROM '{STAGE_BASE}/volve/wells.parquet'</body></html>"
    )


def _stage_branch_checkout(
    root: Path, rel: str = "index.html", page: str | None = None
) -> None:
    """A checkout as a `stage` branch deploy sees it: the built tree and the HF
    dataset card, both naming the `stage` data base."""
    path = root / "site" / "build" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_page() if page is None else page)
    card = root / "hf" / "README.md"
    card.parent.mkdir(parents=True, exist_ok=True)
    card.write_text(f"{STAGE_BASE}/volve/wells.parquet")


def _run(root: Path, landing: str | None = LANDING) -> subprocess.CompletedProcess[str]:
    env = {
        "OTHER_BASE": MAIN_BASE,
        "PYTHONPATH": str(REPO_ROOT),
        "PUBLIC_LANDING_URL": landing,
    }
    return run_step(STEP, env, cwd=root)


def test_a_tree_staged_at_the_landing_host_passes(tmp_path: Path) -> None:
    _stage_branch_checkout(tmp_path)

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("landing", [None, ""])
def test_an_unset_or_empty_landing_url_fails(
    tmp_path: Path, landing: str | None
) -> None:
    _stage_branch_checkout(tmp_path)

    result = _run(tmp_path, landing=landing)

    assert result.returncode != 0
    assert "PUBLIC_LANDING_URL is empty or unset" in result.stdout


def test_a_root_page_staged_one_directory_deep_fails(tmp_path: Path) -> None:
    # Commit 5bd0271's layout: the Landing under site/build/petrodb/.
    _stage_branch_checkout(tmp_path, rel="petrodb/index.html")

    result = _run(tmp_path)

    assert result.returncode != 0
    assert "no index.html at the root of site/build" in result.stdout


def test_a_canonical_naming_another_host_fails(tmp_path: Path) -> None:
    # Commit 5bd0271's canonical.
    _stage_branch_checkout(
        tmp_path, page=_page(canonical="https://sumpalabs.com/petrodb/")
    )

    result = _run(tmp_path)

    assert result.returncode != 0
    assert "canonical names https://sumpalabs.com/petrodb/" in result.stdout
    assert LANDING in result.stdout


def test_an_og_url_naming_another_host_fails(tmp_path: Path) -> None:
    _stage_branch_checkout(tmp_path, page=_page(og_url="https://petrodb.pages.dev/"))

    result = _run(tmp_path)

    assert result.returncode != 0
    assert "og:url names https://petrodb.pages.dev/" in result.stdout


def test_an_og_url_at_the_landing_host_passes(tmp_path: Path) -> None:
    _stage_branch_checkout(tmp_path, page=_page(og_url=LANDING))

    assert _run(tmp_path).returncode == 0


@pytest.mark.parametrize("landing", [LANDING, f"{LANDING}/"])
def test_a_trailing_slash_on_either_side_is_tolerated(
    tmp_path: Path, landing: str
) -> None:
    _stage_branch_checkout(tmp_path, page=_page(canonical=LANDING))

    assert _run(tmp_path, landing=landing).returncode == 0


def test_another_scheme_fails(tmp_path: Path) -> None:
    _stage_branch_checkout(
        tmp_path, page=_page(canonical="http://petrodb.ocortez.com/")
    )

    assert _run(tmp_path).returncode != 0


def test_the_canonical_is_read_from_its_href_attribute_only(tmp_path: Path) -> None:
    page = _page(canonical=None).replace(
        "<meta charset",
        '<link rel="canonical" data-href="https://petrodb.ocortez.com/"'
        ' href="https://sumpalabs.com/petrodb/"><meta charset',
    )
    _stage_branch_checkout(tmp_path, page=page)

    result = _run(tmp_path)

    assert result.returncode != 0
    assert "canonical names https://sumpalabs.com/petrodb/" in result.stdout


@pytest.mark.parametrize(
    "tag",
    [
        "<link rel=canonical href=https://sumpalabs.com/petrodb/>",
        '<link\n  rel="canonical"\n  href="https://sumpalabs.com/petrodb/"\n/>',
        '<LINK REL="Canonical" HREF="https://sumpalabs.com/petrodb/">',
    ],
    ids=["unquoted", "across-lines", "upper-case"],
)
def test_a_canonical_in_any_html_spelling_is_read(tmp_path: Path, tag: str) -> None:
    _stage_branch_checkout(tmp_path, page=_page(canonical=None, extra_head=tag))

    result = _run(tmp_path)

    assert result.returncode != 0
    assert "canonical names https://sumpalabs.com/petrodb/" in result.stdout


@pytest.mark.parametrize(
    "tag",
    [
        "<meta property=og:url content=https://sumpalabs.com/petrodb/>",
        '<meta\n  property="og:url"\n  content="https://sumpalabs.com/petrodb/"\n/>',
        '<meta name="og:url" content="https://sumpalabs.com/petrodb/">',
    ],
    ids=["unquoted", "across-lines", "name-attribute"],
)
def test_an_og_url_in_any_html_spelling_is_read(tmp_path: Path, tag: str) -> None:
    _stage_branch_checkout(tmp_path, page=_page(extra_head=tag))

    result = _run(tmp_path)

    assert result.returncode != 0
    assert "og:url names https://sumpalabs.com/petrodb/" in result.stdout


@pytest.mark.parametrize(
    ("tag", "message"),
    [
        ('<meta property="og:url">', "og:url tag has no readable content"),
        ('<meta property="og:url" content="">', "og:url tag has no readable content"),
        ('<link rel="canonical">', "canonical tag has no readable href"),
    ],
    ids=["og-url-no-content", "og-url-empty-content", "canonical-no-href"],
)
def test_a_tag_whose_url_cannot_be_read_fails(
    tmp_path: Path, tag: str, message: str
) -> None:
    _stage_branch_checkout(tmp_path, page=_page(extra_head=tag))

    result = _run(tmp_path)

    assert result.returncode != 0
    assert message in result.stdout
    assert tag in result.stdout


@pytest.mark.parametrize(
    "tag",
    [
        '<link rel="canonical" href="https://sumpalabs.com/petrodb/">',
        '<meta property="og:url" content="https://sumpalabs.com/petrodb/">',
    ],
    ids=["second-canonical", "second-og-url"],
)
def test_every_tag_is_checked_not_only_the_first(tmp_path: Path, tag: str) -> None:
    _stage_branch_checkout(
        tmp_path, page=_page(og_url=f"{LANDING}/", extra_head=tag)
    )

    result = _run(tmp_path)

    assert result.returncode != 0
    assert "names https://sumpalabs.com/petrodb/" in result.stdout


def test_a_root_page_without_a_canonical_fails(tmp_path: Path) -> None:
    _stage_branch_checkout(tmp_path, page=_page(canonical=None))

    result = _run(tmp_path)

    assert result.returncode != 0
    assert "no canonical link" in result.stdout


def test_the_data_host_check_still_runs_beside_the_host_guard(tmp_path: Path) -> None:
    _stage_branch_checkout(tmp_path, rel="petrodb/index.html")
    (tmp_path / "site" / "build" / "volve.parquet").write_bytes(b"PAR1")

    result = _run(tmp_path)

    # Both guards report before the step fails.
    assert "data file in the deploy tree" in result.stdout
    assert "no index.html at the root of site/build" in result.stdout


def test_the_deploy_job_sets_the_landing_url_as_a_literal() -> None:
    assert env_value("PUBLIC_LANDING_URL") == LANDING
