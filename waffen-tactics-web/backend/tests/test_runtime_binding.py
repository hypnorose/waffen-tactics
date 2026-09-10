import api


def test_production_api_server_binds_to_loopback(monkeypatch):
    calls = []

    monkeypatch.setattr(
        api.app,
        'run',
        lambda **kwargs: calls.append(kwargs),
    )

    api.run_api_server()

    assert calls == [
        {
            'host': '127.0.0.1',
            'port': 8000,
            'debug': False,
        }
    ]
