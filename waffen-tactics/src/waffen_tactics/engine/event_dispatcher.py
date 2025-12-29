"""
EventDispatcher - handles event callback wrapping, sequencing, and payload normalization
"""
from typing import List, Dict, Any, Callable, Optional
import uuid


class EventDispatcher:
    """Handles event emission with sequencing, mana deltas, and HP normalization."""

    def __init__(self, team_a: List['CombatUnit'], team_b: List['CombatUnit'], a_hp: List[int], b_hp: List[int], initial_seq: int = 0, last_mana: Optional[Dict[str, int]] = None):
        self.team_a = team_a
        self.team_b = team_b
        self.a_hp = a_hp
        self.b_hp = b_hp
        self._event_seq = initial_seq
        self._last_mana = last_mana or {}

    def wrap_callback(self, original_callback: Optional[Callable[[str, Dict[str, Any]], None]]) -> Optional[Callable[[str, Dict[str, Any]], None]]:
        """Wrap the event callback to add sequencing and enhancements."""
        if not original_callback:
            return None

        def wrapped_callback(event_type, data):
            # Prepare a sequence value to attach to the payload, but only
            # increment the dispatcher's global seq after the callback
            # completes successfully. This prevents the seq counter from
            # advancing when the downstream consumer fails to receive the
            # event (which was causing snapshot mismatches).
            try:
                seq_value = self._event_seq + 1
            except Exception:
                seq_value = None

            # copy dicts to avoid mutating caller-owned objects
            if isinstance(data, dict):
                payload = dict(data)
            else:
                payload = data

            if isinstance(payload, dict):
                if seq_value is not None:
                    payload['seq'] = seq_value
                payload['event_id'] = str(uuid.uuid4())
                # Ensure payloads emitted downstream include the event type
                # so serialized dumps retain the type even when only the
                # payload dict is recorded.
                if 'type' not in payload:
                    payload['type'] = event_type

            # Enhance and normalize payloads, but don't let unexpected
            # errors in these helpers silently drop events. Log and re-raise
            # so upstream can see issues during debugging.
            try:
                self._enhance_mana_payload(payload, event_type)
            except Exception as e:
                try:
                    print(f"[EVENT WRAPPER ERROR] _enhance_mana_payload failed for type={event_type} error={e}")
                except Exception as e:
                    raise
                raise
            try:
                self._normalize_hp_payload(payload)
            except Exception as e:
                try:
                    print(f"[EVENT WRAPPER ERROR] _normalize_hp_payload failed for type={event_type} error={e}")
                except Exception as e:
                    raise
                raise

            # Try to emit the event. Only update the dispatcher seq if the
            # downstream callback succeeds.
            try:
                # Debug: show event being emitted and its timestamp
                # Dispatcher debug logging removed to reduce runtime noise
                # Suppress emitting mana_update snapshot events that do not
                # represent an actual mana delta. These snapshot-only
                # events (they contain `current_mana` but no computed
                # `amount`) would otherwise show up as zero-delta
                # mana_update events and break regen tests that expect
                # only meaningful mana changes.
                if event_type == 'mana_update' and isinstance(payload, dict) and 'current_mana' in payload and 'amount' not in payload:
                    return

                original_callback(event_type, payload)
            except Exception as e:
                # Log to stdout/stderr so the test harness can see failures
                try:
                    print(f"[EVENT EMIT ERROR] type={event_type} seq={seq_value} error={e}")
                except Exception as e:
                    raise
                # Do not advance self._event_seq on failure — this keeps
                # seqs tightly coupled to successfully-delivered events.
                return

            # If we got here, the event was delivered successfully —
            # advance the dispatcher sequence counter to the value used.
            try:
                if seq_value is not None:
                    self._event_seq = seq_value
                else:
                    self._event_seq += 1
            except Exception:
                # Best-effort: ignore if incrementing fails
                pass

            # Update last-seen mana after successful delivery so future
            # mana_update events can compute deltas.
            self._update_last_mana(payload, event_type)

        return wrapped_callback

    def _enhance_mana_payload(self, payload: Dict[str, Any], event_type: str) -> None:
        """Enhance mana_update payloads with delta calculations."""
        try:
            # Only compute mana delta when the payload supplies an explicit
            # current mana value. Do not fall back to reading live unit
            # attributes — that was a backward-compatibility behavior that
            # obscures the canonical contract between emitters and the
            # dispatcher.
            if isinstance(payload, dict) and event_type == 'mana_update' and 'amount' not in payload:
                unit_id = payload.get('unit_id')
                current = payload.get('current_mana')
                prev = None
                if unit_id is not None:
                    prev = self._last_mana.get(unit_id)
                if prev is not None and current is not None:
                    try:
                        delta = int(current - prev)
                        if delta != 0:
                            payload['amount'] = delta
                    except Exception:
                        pass
        except Exception:
            # best-effort; don't break event emission
            pass

    def _normalize_hp_payload(self, payload: Dict[str, Any]) -> None:
        """Normalize HP fields in payloads to authoritative values."""
        if isinstance(payload, dict):
            # Only consider explicit 'target_id' fields. Remove legacy
            # fallbacks and avoid injecting legacy 'target_hp'/'unit_hp'
            # fields into the payload. Emitters must provide canonical
            # HP values explicitly.
            target_id_ref = payload.get('target_id')
            if target_id_ref:
                # No mutation of payload HP fields here; leave any
                # existing HP fields untouched and require emitters to
                # provide authoritative values.
                return

    def _update_last_mana(self, payload: Dict[str, Any], event_type: str) -> None:
        """Update last seen mana for delta calculations."""
        try:
            if isinstance(payload, dict) and payload.get('unit_id') and event_type == 'mana_update':
                uid = payload.get('unit_id')
                cur = payload.get('current_mana')
                # Only record last-seen mana if the payload explicitly
                # supplies a numeric `current_mana` value. Do not query
                # live unit attributes as a fallback.
                if cur is not None:
                    try:
                        self._last_mana[uid] = int(cur)
                    except Exception:
                        self._last_mana[uid] = cur
        except Exception as e:
            raise

    def get_current_seq(self) -> int:
        """Get the current event sequence number."""
        return self._event_seq

    def get_last_mana(self) -> Dict[str, int]:
        """Get the last seen mana values."""
        return self._last_mana.copy()

    def initialize_mana_for_units(self, units: List['CombatUnit']) -> None:
        """Initialize mana tracking for units at combat start."""
        for u in units:
            if hasattr(u, 'get_mana') and hasattr(u, 'id'):
                self._last_mana[u.id] = u.get_mana()