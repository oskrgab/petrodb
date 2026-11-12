"""The guard the deploy runs over the built Landing before publishing it (issue #54).

The Cloudflare deploy tree is the SvelteKit build output. Before it ships, every
data URL in it must name the deploying branch's Hugging Face base (ADR-0005,
issue #42), and it must carry no parquet bytes and no ``_files.json`` manifest
(ADR-0005: those live on Hugging Face only).
"""

from pathlib import Path

import pytest

from scripts.deploy import check_deploy_tree as guard

MAIN_BASE = "https://huggingface.co/datasets/oskrgab/petrodb/resolve/main"
STAGE_BASE = "https://huggingface.co/datasets/oskrgab/petrodb/resolve/stage"
DEV_HOST = "https://dev-petrodb.ocortez.com"


def _write(root: Path, rel: str, text: str = "") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_tree_whose_data_urls_all_name_the_deploy_base_passes(tmp_path: Path) -> None:
    _write(tmp_path, "index.html", f"FROM '{STAGE_BASE}/volve/daily_production.parquet'")
    _write(tmp_path, "argentina/index.html", f"FROM '{STAGE_BASE}/argentina/wells.parquet'")
    _write(tmp_path, "argentina/schema.md", "| `idpozo` | INTEGER |")

    assert guard.problems([tmp_path], other_base=MAIN_BASE) == []


def test_a_page_naming_the_other_branch_base_fails(tmp_path: Path) -> None:
    _write(tmp_path, "index.html", f"FROM '{STAGE_BASE}/volve/daily_production.parquet'")
    page = _write(
        tmp_path, "argentina/index.html", f"FROM '{MAIN_BASE}/argentina/wells.parquet'"
    )

    found = guard.problems([tmp_path], other_base=MAIN_BASE)

    assert len(found) == 1
    assert str(page) in found[0]
    assert MAIN_BASE in found[0]


def test_a_page_naming_the_dev_caddy_host_fails(tmp_path: Path) -> None:
    page = _write(tmp_path, "petrobras_3w/README.md", f"See {DEV_HOST}/petrobras_3w/")

    found = guard.problems([tmp_path], other_base=MAIN_BASE)

    assert len(found) == 1
    assert str(page) in found[0]
    assert "dev-petrodb.ocortez.com" in found[0]


def test_a_single_file_argument_is_checked_too(tmp_path: Path) -> None:
    # The HF dataset card sits outside the deploy tree but ships the same URLs.
    card = _write(tmp_path, "hf/README.md", f"{MAIN_BASE}/volve/wells.parquet")

    assert guard.problems([card], other_base=MAIN_BASE) != []


@pytest.mark.parametrize(
    "rel",
    ["volve/daily_production.parquet", "argentina/monthly_production/_files.json"],
)
def test_data_files_in_the_tree_fail(tmp_path: Path, rel: str) -> None:
    # ADR-0005: parquet bytes and manifests are served from Hugging Face only.
    _write(tmp_path, rel)

    found = guard.problems([tmp_path], other_base=MAIN_BASE)

    assert len(found) == 1
    assert rel.split("/")[-1] in found[0]


def test_binary_assets_do_not_break_the_scan(tmp_path: Path) -> None:
    # The build ships fonts; they are not UTF-8 and carry no data URLs.
    (tmp_path / "font.woff2").write_bytes(b"\xff\xfe\x00\x81wOF2")

    assert guard.problems([tmp_path], other_base=MAIN_BASE) == []


def test_main_exits_nonzero_when_the_tree_has_problems(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "index.html", f"{MAIN_BASE}/volve/wells.parquet")
    monkeypatch.setenv("OTHER_BASE", MAIN_BASE)

    with pytest.raises(SystemExit) as exit_:
        guard.main([str(tmp_path)])

    assert exit_.value.code == 1


def test_main_passes_on_a_clean_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "index.html", f"{STAGE_BASE}/volve/wells.parquet")
    monkeypatch.setenv("OTHER_BASE", MAIN_BASE)

    guard.main([str(tmp_path)])
