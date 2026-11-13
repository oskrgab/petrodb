"""The one-shot Argentina runner: transform, export, then the Landing's Glances."""

from unittest.mock import MagicMock

import pytest

from scripts.run_pipeline.argentina import __main__ as runner


def test_runner_regenerates_the_glances_last(monkeypatch: pytest.MonkeyPatch) -> None:
    steps = MagicMock()
    monkeypatch.setattr(runner.transform_orch, "run", steps.transform)
    monkeypatch.setattr(runner.export_orch, "run", steps.export)
    monkeypatch.setattr(runner.glances, "write", steps.glances)

    runner.main()

    assert [c[0] for c in steps.mock_calls] == ["transform", "export", "glances"]
    steps.glances.assert_called_once_with("argentina")
