"""Fail-closed static verifier for the WFT-198 combat event contract."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "COMBAT_EVENT_CONTRACT.json"
VALID_POST_STATE_MODES = {
    "none",
    "snapshot_initialization",
    "snapshot_validation_only",
    "snapshot_final",
    "authoritative",
    "unchanged_authoritative",
}
VALID_ORDERING_MODES = {"control", "strict_seq"}
VALID_DEDUPE_MODES = {"type_seq", "event_id"}
VALID_PRESENTATION_MODES = {"control", "metadata", "animation", "combat_log"}


def _load_contract() -> dict[str, Any]:
    with CONTRACT_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8-sig")


def _contains_event(source: str, event_type: str) -> bool:
    literal = re.escape(event_type)
    return bool(
        re.search(rf"['\"]{literal}['\"]", source)
        or re.search(rf"\b{literal}\b", source)
    )


def _contains_frontend_case(source: str, event_type: str) -> bool:
    literal = re.escape(event_type)
    return bool(
        re.search(rf"case\s+['\"]{literal}['\"]", source)
        or re.search(rf"['\"]{literal}['\"]", source)
    )


def verify_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = contract or _load_contract()
    events = contract.get("events")
    if not isinstance(events, list) or not events:
        raise AssertionError("Combat event contract must contain events")

    event_names = [event.get("type") for event in events]
    if any(not isinstance(name, str) or not name for name in event_names):
        raise AssertionError("Combat event contract contains an invalid event type")
    if len(set(event_names)) != len(event_names):
        raise AssertionError("Combat event contract contains duplicate event types")

    layers = contract["layers"]
    sources = {name: _read(path) if isinstance(path, str) else "" for name, path in layers.items()}
    core_sources = [_read(path) for path in layers["core"]]
    control_events = set(contract["stream_rules"]["control_frames"])
    failures: list[str] = []

    every_frame_requires = set(contract["stream_rules"].get("every_frame_requires", []))
    non_control_requires = set(contract["stream_rules"].get("every_non_control_frame_requires", []))
    if every_frame_requires != {"type", "seq"}:
        failures.append("stream rules: every frame must require exactly type and seq")
    if non_control_requires != {"event_id"}:
        failures.append("stream rules: every non-control frame must require event_id")

    source_guards = contract["stream_rules"].get("source_guards", {})
    for layer_name, required_markers in source_guards.items():
        source = sources.get(layer_name)
        if source is None:
            failures.append(f"stream rules: source guard references unknown layer {layer_name}")
            continue
        for marker in required_markers:
            if marker not in source:
                failures.append(f"{layer_name}: required contract guard missing: {marker}")

    for event in events:
        event_type = event["type"]
        required_fields = event.get("required_fields")
        if not isinstance(required_fields, list) or any(
            not isinstance(field, str) or not field for field in required_fields
        ):
            failures.append(f"{event_type}: required_fields must be a non-empty string list")
            required_fields = []
        if len(set(required_fields)) != len(required_fields):
            failures.append(f"{event_type}: required_fields contains duplicates")
        if not every_frame_requires.issubset(required_fields):
            failures.append(f"{event_type}: required_fields must include type and seq")

        is_control = event_type in control_events
        if is_control and "event_id" in required_fields:
            failures.append(f"{event_type}: control frame must not require event_id")
        if not is_control and not non_control_requires.issubset(required_fields):
            failures.append(f"{event_type}: non-control frame must require event_id")

        post_state = event.get("post_state")
        if post_state not in VALID_POST_STATE_MODES:
            failures.append(f"{event_type}: invalid post_state mode {post_state!r}")
        ordering = event.get("ordering")
        expected_ordering = "control" if is_control else "strict_seq"
        if ordering not in VALID_ORDERING_MODES or ordering != expected_ordering:
            failures.append(f"{event_type}: ordering must be {expected_ordering}")
        dedupe = event.get("dedupe")
        expected_dedupe = "type_seq" if is_control else "event_id"
        if dedupe not in VALID_DEDUPE_MODES or dedupe != expected_dedupe:
            failures.append(f"{event_type}: dedupe must be {expected_dedupe}")
        if event.get("presentation") not in VALID_PRESENTATION_MODES:
            failures.append(f"{event_type}: invalid presentation mode")

        if event_type in control_events:
            if not _contains_event(sources["route"], event_type):
                failures.append(f"{event_type}: route control origin missing")
        elif event.get("origin") != "core_compatibility_alias" and not any(
            _contains_event(source, event_type) for source in core_sources
        ):
            failures.append(f"{event_type}: core origin missing")

        if event.get("mapper") == "map_branch" and not _contains_event(sources["mapper"], event_type):
            failures.append(f"{event_type}: SSE mapper branch missing")
        if event.get("reconstructor") in {"state", "explicit_noop"} and not _contains_event(
            sources["reconstructor"], event_type
        ):
            failures.append(f"{event_type}: backend reconstructor branch missing")
        if event.get("frontend") in {"case", "control"} and not _contains_frontend_case(
            sources["frontend"], event_type
        ):
            failures.append(f"{event_type}: frontend reducer branch missing")

    if not _contains_event(sources["sse_buffer"], "CONTROL_EVENT_TYPES"):
        failures.append("SSE buffer: control event registry missing")
    if failures:
        raise AssertionError("\n".join(failures))

    return {
        "contract_id": contract["contract_id"],
        "event_count": len(events),
        "event_types": event_names,
        "control_event_count": len(control_events),
        "status": "pass",
    }


def main() -> int:
    print(json.dumps(verify_contract(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
