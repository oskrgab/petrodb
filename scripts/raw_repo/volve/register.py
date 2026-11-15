"""The wellbore register snapshot: the Norwegian Offshore Directorate's public CSV exports.

``fetch_register`` downloads the exports for development and exploration
wellbores into ``<raw dir>/register/`` and records the download date beside
them. The register is published under the Norwegian Licence for Open
Government Data (NLOD); its licence note is committed in
``hf/petrodb-raw-volve/register/LICENSE.md``.
"""

from __future__ import annotations

import datetime as dt
import urllib.request
from collections.abc import Callable
from pathlib import Path

REGISTER_DIR = "register"

_FACTPAGES_CSV = (
    "https://factpages.sodir.no/public?/Factpages/external/tableview/{table}"
    "&rs:Command=Render&rc:Toolbar=false&rc:Parameters=f&IpAddress=not_used"
    "&CultureCode=en&rs:Format=CSV&Top100=false"
)

# File name in the register folder -> the URL it is downloaded from.
EXPORTS = {
    f"{table}.csv": _FACTPAGES_CSV.format(table=table)
    for table in ("wellbore_development_all", "wellbore_exploration_all")
}

# ISO date (UTC) of the download, one line.
DATE_FILE = "download_date.txt"

SNAPSHOT_FILES = (*EXPORTS, DATE_FILE)


class RegisterError(Exception):
    """A download is not the register export it should be."""


def _http_get(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "petrodb-register-snapshot"}
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def fetch_register(
    raw_dir: Path,
    fetch: Callable[[str], bytes] = _http_get,
    today: dt.date | None = None,
) -> Path:
    """Download both register exports into ``raw_dir/register/`` and date them.

    Both exports are downloaded before anything is written, so a failed
    download leaves the previous snapshot as it was.
    """
    bodies = {name: fetch(url) for name, url in EXPORTS.items()}
    for name, body in bodies.items():
        first_line = body.split(b"\n", 1)[0]
        if b"wlbWellboreName" not in first_line:
            raise ValueError(
                f"{name}: the download is not a wellbore register CSV export"
            )

    folder = raw_dir / REGISTER_DIR
    folder.mkdir(parents=True, exist_ok=True)
    for name, body in bodies.items():
        (folder / name).write_bytes(body)
    date = today or dt.datetime.now(dt.UTC).date()
    (folder / DATE_FILE).write_text(f"{date.isoformat()}\n")
    return folder
