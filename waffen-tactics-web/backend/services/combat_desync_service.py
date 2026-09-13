"""Validation helpers for client-reported combat replay desyncs."""

import json
import math
from typing import Any, Dict


MAX_REPORT_BYTES = 512 * 1024
MAX_EVENT_BYTES = 64 * 1024
MAX_EVENTS = 50
MAX_DIFF_KEYS = 64


class DesyncReportValidationError(ValueError):
    """Raised when a client desync report is outside the public contract."""


def _string_field(payload: dict, name: str, *, required: bool, max_length: int):
    value = payload.get(name)
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise DesyncReportValidationError(f"invalid {name}")
    return value.strip()


def _number_field(payload: dict, name: str, *, integer: bool = False):
    value = payload.get(name)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DesyncReportValidationError(f"invalid {name}")
    if not math.isfinite(float(value)):
        raise DesyncReportValidationError(f"invalid {name}")
    if integer and (not isinstance(value, int) or value < 0):
        raise DesyncReportValidationError(f"invalid {name}")
    return value


def _json_size(value: Any, *, max_bytes: int) -> str:
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    except (TypeError, ValueError) as exc:
        raise DesyncReportValidationError('report contains non-serializable values') from exc
    if len(encoded.encode('utf-8')) > max_bytes:
        raise DesyncReportValidationError('report section is too large')
    return encoded


def _events_field(payload: dict, name: str) -> list[dict]:
    value = payload.get(name, [])
    if not isinstance(value, list) or len(value) > MAX_EVENTS:
        raise DesyncReportValidationError(f"invalid {name}")
    for event in value:
        if not isinstance(event, dict):
            raise DesyncReportValidationError(f"invalid {name}")
        _json_size(event, max_bytes=MAX_EVENT_BYTES)
    _json_size(value, max_bytes=MAX_REPORT_BYTES)
    return value


def normalize_desync_report(payload: Any) -> Dict[str, Any]:
    """Validate and normalize the browser's diagnostic payload before storage."""
    if not isinstance(payload, dict):
        raise DesyncReportValidationError('report must be a JSON object')

    unit_id = _string_field(payload, 'unit_id', required=True, max_length=128)
    unit_name = _string_field(payload, 'unit_name', required=False, max_length=200)
    event_id = _string_field(payload, 'event_id', required=False, max_length=200)
    replay_session_id = _string_field(
        payload, 'replay_session_id', required=False, max_length=128
    )
    note = _string_field(payload, 'note', required=False, max_length=2000)
    seq = _number_field(payload, 'seq', integer=True)
    timestamp = _number_field(payload, 'timestamp')

    diff = payload.get('diff')
    if not isinstance(diff, dict) or len(diff) > MAX_DIFF_KEYS:
        raise DesyncReportValidationError('invalid diff')
    _json_size(diff, max_bytes=128 * 1024)

    normalized = {
        'unit_id': unit_id,
        'unit_name': unit_name,
        'seq': seq,
        'event_id': event_id,
        'timestamp': timestamp,
        'diff': diff,
        'pending_events': _events_field(payload, 'pending_events'),
        'recent_events': _events_field(payload, 'recent_events'),
        'note': note,
        'replay_session_id': replay_session_id,
    }
    _json_size(normalized, max_bytes=MAX_REPORT_BYTES)
    return normalized
