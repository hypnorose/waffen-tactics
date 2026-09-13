import importlib.util
from pathlib import Path

import api
import routes.game_routes as game_routes


def test_wsgi_entrypoint_initializes_runtime_before_exposing_app(monkeypatch):
    calls = []
    init_marker = object()
    bots_marker = object()

    class FakeDatabaseManager:
        def initialize(self):
            return init_marker

    monkeypatch.setattr(api, "db_manager", FakeDatabaseManager())
    monkeypatch.setattr(api, "run_async", lambda coroutine: calls.append(coroutine))
    monkeypatch.setattr(game_routes, "init_sample_bots", lambda: bots_marker)

    module_path = Path(__file__).parents[1] / "wsgi.py"
    spec = importlib.util.spec_from_file_location("wft_test_wsgi", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.app is api.app
    assert calls == [init_marker, bots_marker]
