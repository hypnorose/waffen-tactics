"""Production WSGI entrypoint for the Waffen Tactics API.

The development entrypoint in ``api.py`` performs the same initialization
before calling Flask's local server.  Gunicorn imports this module instead,
so keep initialization explicit and fail closed before serving requests.
"""

from api import app, db_manager, run_async
from routes.game_routes import init_sample_bots


def initialize_runtime() -> None:
    """Initialize shared runtime data before the WSGI server accepts traffic."""
    run_async(db_manager.initialize())
    run_async(init_sample_bots())
    print("[db] Database initialized")


initialize_runtime()

