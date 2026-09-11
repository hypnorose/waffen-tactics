import json
from pathlib import Path

import pytest

from tools import verify_public_contract as verifier


class _Response:
    def __init__(self, payload, status=200):
        self._body = json.dumps(payload).encode("utf-8")
        self._status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def getcode(self):
        return self._status

    def read(self):
        return self._body


def test_compare_requires_exact_ids_and_reports_directional_differences():
    result = verifier._compare("units", ["a", "b"], ["b", "c"])

    assert result == {
        "name": "units",
        "ok": False,
        "expected_count": 2,
        "actual_count": 2,
        "missing_ids": ["a"],
        "unexpected_ids": ["c"],
    }


def test_compare_ignores_public_record_order():
    result = verifier._compare("traits", ["t1", "t2"], ["t2", "t1"])

    assert result["ok"] is True
    assert result["missing_ids"] == []
    assert result["unexpected_ids"] == []


def test_verify_accepts_array_and_wrapped_public_payloads(monkeypatch, tmp_path: Path):
    repo_root = tmp_path
    data_dir = repo_root / "waffen-tactics"
    data_dir.mkdir()
    (data_dir / "units.json").write_text(json.dumps({"units": [{"id": "u1"}]}), encoding="utf-8")
    (data_dir / "traits.json").write_text(json.dumps({"traits": [{"id": "t1"}]}), encoding="utf-8")

    payloads = {
        "/api/game/units": [{"id": "u1"}],
        "/api/game/traits": {"traits": [{"id": "t1"}]},
    }

    def fake_urlopen(request, timeout, context=None):
        for endpoint, payload in payloads.items():
            if request.full_url.endswith(endpoint):
                return _Response(payload)
        raise AssertionError(request.full_url)

    monkeypatch.setattr(verifier, "urlopen", fake_urlopen)
    report = verifier.verify("https://example.test", repo_root)

    assert report["ok"] is True
    assert all(contract["ok"] for contract in report["contracts"])


def test_verify_fails_closed_on_duplicate_public_ids(monkeypatch, tmp_path: Path):
    repo_root = tmp_path
    data_dir = repo_root / "waffen-tactics"
    data_dir.mkdir()
    (data_dir / "units.json").write_text(json.dumps({"units": [{"id": "u1"}]}), encoding="utf-8")
    (data_dir / "traits.json").write_text(json.dumps({"traits": [{"id": "t1"}]}), encoding="utf-8")

    def fake_urlopen(request, timeout, context=None):
        if request.full_url.endswith("/api/game/units"):
            return _Response([{"id": "u1"}, {"id": "u1"}])
        return _Response([{"id": "t1"}])

    monkeypatch.setattr(verifier, "urlopen", fake_urlopen)

    with pytest.raises(verifier.ContractProbeError, match="duplicate ids"):
        verifier.verify("https://example.test", repo_root)


def test_fetch_json_uses_certificate_verifying_context(monkeypatch):
    marker = object()
    seen = {}

    def fake_urlopen(request, timeout, context=None):
        seen["context"] = context
        return _Response({"ok": True})

    monkeypatch.setattr(verifier, "_tls_context", lambda: marker)
    monkeypatch.setattr(verifier, "urlopen", fake_urlopen)

    assert verifier._fetch_json("https://example.test/api", timeout=3) == {"ok": True}
    assert seen["context"] is marker
