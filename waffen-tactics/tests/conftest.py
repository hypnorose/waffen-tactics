import os

# Ensure test runs are deterministic: enable deterministic targeting during pytest
# This keeps the existing tests stable while the runtime default remains random.
os.environ.setdefault('WAFFEN_DETERMINISTIC_TARGETING', '1')

def pytest_configure(config):
    # Make the env var visible to any subprocesses/tests
    os.environ['WAFFEN_DETERMINISTIC_TARGETING'] = os.environ.get('WAFFEN_DETERMINISTIC_TARGETING', '1')
