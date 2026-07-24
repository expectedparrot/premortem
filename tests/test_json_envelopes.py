from __future__ import annotations

import json
import sys

from typer.testing import CliRunner

from premortem.cli import app
from premortem.store import PremortemError, error_envelope, make_json_envelope


runner = CliRunner()


def test_success_envelope_contract(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["premortem", "docs", "list"])
    payload = make_json_envelope(
        "legacy command label",
        {"items": []},
        warnings=["example warning"],
        next_steps=["premortem status"],
    )

    assert payload["schema_version"] == "1.0"
    assert payload["ok"] is True
    assert payload["command"] == ["docs", "list"]
    assert payload["data"] == {"items": []}
    assert payload["warnings"] == ["example warning"]
    assert payload["next_actions"][0]["command"] == ["premortem", "status"]
    assert "error" not in payload


def test_error_envelope_contract(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["premortem", "docs", "show", "missing"])
    payload = error_envelope(
        "legacy command label",
        PremortemError("ID_NOT_FOUND", "Missing.", context="missing", hint="List topics."),
    )

    assert payload["schema_version"] == "1.0"
    assert payload["ok"] is False
    assert payload["command"] == ["docs", "show", "missing"]
    assert payload["error"] == {
        "code": "ID_NOT_FOUND",
        "message": "Missing.",
        "details": {"context": "missing", "hint": "List topics."},
    }
    assert "data" not in payload


def test_docs_list_emits_one_success_envelope(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["premortem", "docs", "list"])
    result = runner.invoke(app, ["docs", "list"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["schema_version"] == "1.0"
    assert payload["command"] == ["docs", "list"]
    assert isinstance(payload["data"], list)


def test_domain_failure_emits_one_error_envelope(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["premortem", "docs", "show", "missing"])
    result = runner.invoke(app, ["docs", "show", "missing"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "ID_NOT_FOUND"
    assert payload["next_actions"] == []
