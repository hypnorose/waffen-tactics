"""Fail-closed comparison of a public game-data API with local canonical data.

This is a read-only release check.  It deliberately compares IDs as well as
counts: a deployment containing the same number of records from a different
roster must still fail the gate.
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ContractProbeError(RuntimeError):
    """Raised when a local or public contract cannot be inspected safely."""


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractProbeError(f"cannot read JSON from {path}: {exc}") from exc


def _records(payload: Any, collection_key: str, source: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict) and isinstance(payload.get(collection_key), list):
        records = payload[collection_key]
    else:
        raise ContractProbeError(
            f"{source} must be a JSON array or an object containing "
            f"'{collection_key}' as an array"
        )

    normalized: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ContractProbeError(f"{source}[{index}] is not a JSON object")
        normalized.append(record)
    return normalized


def _item_records(payload: Any, source: str) -> list[dict[str, Any]]:
    """Return the approved WFT-139 base and combined item records."""

    if not isinstance(payload, dict):
        raise ContractProbeError(f"{source} must be a WFT-139 matrix object")
    if payload.get("matrix_id") != "WFT-139":
        raise ContractProbeError(f"{source} has an unexpected matrix identity")
    if payload.get("status") != "approved-runtime-contract":
        raise ContractProbeError(f"{source} is not approved for runtime")

    base_items = payload.get("base_items")
    recipes = payload.get("recipes")
    if not isinstance(base_items, list) or not isinstance(recipes, list):
        raise ContractProbeError(f"{source} must contain base_items and recipes lists")
    return _records([*base_items, *recipes], "items", source)


def _ids(records: Iterable[dict[str, Any]], source: str) -> list[str]:
    result: list[str] = []
    for index, record in enumerate(records):
        value = record.get("id")
        if not isinstance(value, str) or not value.strip():
            raise ContractProbeError(f"{source}[{index}] has no non-empty string id")
        result.append(value)

    duplicates = sorted({value for value in result if result.count(value) > 1})
    if duplicates:
        raise ContractProbeError(f"{source} contains duplicate ids: {duplicates}")
    return result


def _valid_public_ids(records: Iterable[dict[str, Any]], source: str) -> list[str]:
    """Collect valid public IDs while leaving malformed records reportable."""

    result: list[str] = []
    for record in records:
        value = record.get("id")
        if isinstance(value, str) and value.strip():
            result.append(value)

    duplicates = sorted({value for value in result if result.count(value) > 1})
    if duplicates:
        raise ContractProbeError(f"{source} contains duplicate ids: {duplicates}")
    return result


def _schema_errors(
    expected_records: list[dict[str, Any]],
    actual_records: list[dict[str, Any]],
    source: str,
) -> list[str]:
    """Report missing canonical fields without accepting malformed payloads."""

    if not expected_records:
        return []

    required_keys = set(expected_records[0])
    for record in expected_records[1:]:
        required_keys.intersection_update(record)

    errors: list[str] = []
    for index, record in enumerate(actual_records):
        missing = sorted(required_keys - set(record))
        if missing:
            errors.append(f"{source}[{index}] is missing required keys: {missing}")

        value = record.get("id")
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{source}[{index}] has no non-empty string id")
    return errors


def _tls_context() -> ssl.SSLContext:
    """Build a certificate-verifying context from the maintained CA bundle.

    Python installations on Windows can have an incomplete or stale OpenSSL
    default CA path even when the operating-system and server trust stores
    are healthy.  certifi supplies a maintained public CA bundle; using it
    still performs normal hostname and certificate-chain verification and
    never disables TLS verification.
    """

    try:
        import certifi
    except ImportError as exc:
        raise ContractProbeError(
            "certifi is required for the public HTTPS contract verifier"
        ) from exc

    return ssl.create_default_context(cafile=certifi.where())


def _fetch_json(url: str, timeout: float) -> Any:
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(
            request,
            context=_tls_context(),
            timeout=timeout,
        ) as response:  # nosec B310: URL is an explicit release target
            status = response.getcode()
            body = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise ContractProbeError(f"GET {url} failed: {exc}") from exc

    if status != 200:
        raise ContractProbeError(f"GET {url} returned HTTP {status}")
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise ContractProbeError(f"GET {url} returned invalid JSON: {exc}") from exc


def _compare(name: str, expected: list[str], actual: list[str]) -> dict[str, Any]:
    expected_set = set(expected)
    actual_set = set(actual)
    return {
        "name": name,
        "ok": expected_set == actual_set,
        "expected_count": len(expected),
        "actual_count": len(actual),
        "missing_ids": sorted(expected_set - actual_set),
        "unexpected_ids": sorted(actual_set - expected_set),
    }


def verify(base_url: str, repo_root: Path, timeout: float = 10.0) -> dict[str, Any]:
    base = base_url.rstrip("/")
    contracts = (
        ("units", "units.json", "/api/game/units"),
        ("traits", "traits.json", "/api/game/traits"),
        ("items", "item_recipe_matrix_wft139.json", "/api/game/items"),
    )
    results: list[dict[str, Any]] = []
    for name, filename, endpoint in contracts:
        local_payload = _load_json(repo_root / "waffen-tactics" / filename)
        if name == "items":
            local_records = _item_records(local_payload, f"local {filename}")
        else:
            local_records = _records(local_payload, name, f"local {filename}")
        local = _ids(local_records, name)
        public_payload = _fetch_json(f"{base}{endpoint}", timeout)
        public_records = _records(public_payload, name, f"public {endpoint}")
        if name in {"units", "traits"}:
            public = _valid_public_ids(public_records, endpoint)
            schema_errors = _schema_errors(local_records, public_records, endpoint)
        else:
            public = _ids(public_records, endpoint)
            schema_errors = []

        comparison = _compare(name, local, public)
        comparison["actual_count"] = len(public_records)
        comparison["schema_errors"] = schema_errors
        comparison["ok"] = comparison["ok"] and not schema_errors
        results.append(comparison)

    return {
        "ok": all(result["ok"] for result in results),
        "base_url": base,
        "contracts": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare public units, traits and item IDs with local canonical data."
    )
    parser.add_argument("--base-url", required=True, help="Public HTTPS origin to inspect")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root (defaults to the parent of tools/)",
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args(argv)

    try:
        report = verify(args.base_url, args.repo_root, args.timeout)
    except ContractProbeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
