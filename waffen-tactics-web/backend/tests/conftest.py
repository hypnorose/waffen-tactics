"""
Test configuration for backend tests
"""
import os
import sys
import pytest
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'))
sys.path.insert(0, str(Path(__file__).parent.parent))

from api import app


@pytest.fixture(scope='session')
def flask_app():
    """Create and configure a test app instance."""
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_secret_key'
    return app


@pytest.fixture(scope='session')
def flask_app_context(flask_app):
    """Create a Flask app context for tests."""
    with flask_app.app_context():
        yield


@pytest.fixture
def client(flask_app):
    """A test client for the app."""
    return flask_app.test_client()