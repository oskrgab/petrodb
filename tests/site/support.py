"""Shared by the Landing's tests: find a Glance, and run what a visitor copies.

A snippet is the SQL, Python or Polars code a page shows. ``variants`` gives
every language a page offers for one query, the way the site builds them, and
``run`` executes one and returns the tables it produced. Snippets that read
the published files on Hugging Face are opt-in: mark them ``needs_network``.
"""

from __future__ import annotations

import os
from typing import Any

import duckdb
import pytest

from scripts.site import glances
from scripts.site.glances import PUBLIC_BASE

# The repository root that `{repo}` stands for; `{base}` is its `main` revision.
REPO = PUBLIC_BASE.removesuffix("/resolve/main")

needs_network = pytest.mark.skipif(
    os.environ.get("PETRODB_NETWORK") != "1",
    reason="reads the published files; set PETRODB_NETWORK=1",
)


def find_glance(dataset: str, glance_id: str) -> glances.Glance:
    return next(g for g in glances.GLANCES if (g.dataset, g.id) == (dataset, glance_id))


def fill(code: str, base: str = PUBLIC_BASE) -> str:
    """Name ``base`` as the data host.

    Committed metadata writes ``{base}``; committed Glances arrive already
    written against the public host. Both become ``base``.
    """
    return code.replace("{base}", base).replace(PUBLIC_BASE, base).replace("{repo}", REPO)


def sql_to_python(sql: str) -> str:
    """The Python tab the site derives from a SQL snippet (`sqlToPython`)."""
    body = "\n".join(f"    {line}" if line else line for line in sql.rstrip().removesuffix(";").split("\n"))
    return f'import duckdb\n\ndf = duckdb.sql("""\n{body}\n""").df()'


def variants(item: dict[str, Any], base: str = PUBLIC_BASE) -> list[tuple[str, str]]:
    """(language, code) for every tab a page shows for one query, Glance or step."""
    sql = fill(item["sql"], base)
    out = [("sql", sql), ("python", fill(item["python"], base) if item.get("python") else sql_to_python(sql))]
    if item.get("polars"):
        out.append(("polars", fill(item["polars"], base)))
    return out


def run(lang: str, code: str) -> list[Any]:
    """Run one snippet; return the tables it produced (rows, or data frames)."""
    if lang == "sql":
        result = duckdb.connect().sql(code)
        return [] if result is None else [result.fetchall()]
    scope: dict[str, Any] = {}
    exec(compile(code, f"<{lang} snippet>", "exec"), scope)
    return [v for k, v in scope.items() if hasattr(v, "shape") and not k.startswith("_")]


def assert_returns_rows(lang: str, code: str) -> None:
    tables = run(lang, code)
    assert tables, "the snippet produced no table"
    assert all(len(t) for t in tables), "a table the snippet produced is empty"
