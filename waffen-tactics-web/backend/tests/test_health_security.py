import api


def test_health_does_not_expose_database_path(client):
    response = client.get('/health')

    assert response.status_code == 200
    assert response.json == {'status': 'ok', 'db': 'configured'}
    body = response.get_data(as_text=True)
    assert api.DB_PATH not in body
    assert 'waffen_tactics_game.db' not in body
