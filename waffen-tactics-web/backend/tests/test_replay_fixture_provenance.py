import hashlib
import json
from collections import Counter
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
FIXTURE_PATH = BACKEND_DIR / "events_test_fresh.json"
MANIFEST_PATH = BACKEND_DIR / "events_test_fresh.provenance.json"
GENERATOR_PATH = BACKEND_DIR / "generate_fresh_test.py"


def test_approved_replay_fixture_matches_its_provenance_manifest():
    fixture_bytes = FIXTURE_PATH.read_bytes()
    events = json.loads(fixture_bytes.decode("utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    snapshot = manifest["fixture_snapshot"]

    assert manifest["fixture"] == FIXTURE_PATH.name
    assert hashlib.sha256(fixture_bytes).hexdigest() == snapshot["sha256"]
    assert len(fixture_bytes) == snapshot["bytes"]
    assert len(events) == snapshot["event_count"]

    sequences = [event["seq"] for event in events]
    assert sequences == list(
        range(snapshot["sequence"]["first"], snapshot["sequence"]["last"] + 1)
    )

    counts = Counter(event["type"] for event in events)
    assert dict(sorted(counts.items())) == snapshot["event_type_counts"]
    assert sorted(counts) == snapshot["event_types"]


def test_fixture_generator_is_seeded_and_never_replaces_approved_fixture_by_default():
    generator = GENERATOR_PATH.read_text(encoding="utf-8")

    assert "random.seed(args.seed)" in generator
    assert "default=Path('sim_events_dump.json')" in generator
    assert "events_test_fresh.json" not in generator
