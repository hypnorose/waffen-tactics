import os
import json
import asyncio
import warnings
from typing import Any

try:
    from waffen_tactics.engine.event_dispatcher import EventDispatcher
except Exception:
    EventDispatcher = None

# Path for JSONL dump. Can be overridden with env var WT_EVENT_DUMP
DUMP_PATH = os.environ.get('WT_EVENT_DUMP', 'pytest_events_dump.jsonl')


def pytest_sessionstart(session):
    """Prevent pytest-asyncio from preserving an implicit Windows event loop.

    On Python 3.11's Proactor policy, ``get_event_loop()`` can create a loop
    while pytest-asyncio is saving the previous policy state.  The plugin then
    restores that loop after its Runner closes, leaving its internal socketpair
    to be reported later as an unraisable ResourceWarning.  Start the test
    session with an explicit ``None`` current loop so the runner owns the only
    loop it creates and can close it deterministically.
    """
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', DeprecationWarning)
        try:
            current_loop = asyncio.get_event_loop()
        except RuntimeError:
            current_loop = None
    if current_loop is not None and not current_loop.is_closed():
        current_loop.close()
    asyncio.set_event_loop(None)


def pytest_configure(config):
    # clear previous dump
    try:
        if os.path.exists(DUMP_PATH):
            os.remove(DUMP_PATH)
    except Exception:
        pass

    if not EventDispatcher:
        return

    orig_wrap = EventDispatcher.wrap_callback

    def new_wrap(self, original_callback):
        wrapped = orig_wrap(self, original_callback)
        if wrapped is None:
            return None

        def wrapper(event_type: str, payload: Any):
            # write a JSON line with event type and payload
            try:
                rec = {'type': event_type, 'payload': payload}
                with open(DUMP_PATH, 'a') as f:
                    f.write(json.dumps(rec, default=str) + '\n')
            except Exception:
                pass
            return wrapped(event_type, payload)

        return wrapper

    EventDispatcher.wrap_callback = new_wrap
import shutil


def _ensure_sim_fixture():
    """Ensure `sim_with_skills.jsonl` exists at the repo root for tests that expect it.
    The file is generated/copied at test time and should be git-ignored.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    dest = os.path.join(repo_root, 'sim_with_skills.jsonl')
    if os.path.exists(dest):
        return
    src = os.path.join(repo_root, 'waffen-tactics-web', 'backend', 'test_fixtures', 'sim_with_skills.jsonl')
    try:
        if os.path.exists(src):
            shutil.copy(src, dest)
    except Exception:
        pass


_ensure_sim_fixture()
import os

# Ensure test runs are deterministic: enable deterministic targeting during pytest
# This keeps the existing tests stable while the runtime default remains random.
os.environ.setdefault('WAFFEN_DETERMINISTIC_TARGETING', '1')

def pytest_configure(config):
    # Make the env var visible to any subprocesses/tests
    os.environ['WAFFEN_DETERMINISTIC_TARGETING'] = os.environ.get('WAFFEN_DETERMINISTIC_TARGETING', '1')
