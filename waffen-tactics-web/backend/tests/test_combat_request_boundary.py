import pytest

import routes.game_combat as game_combat


@pytest.mark.parametrize('payload', [[{'token': 'x'}], 'not-an-object', 7])
def test_start_combat_rejects_non_object_json_without_attribute_error(flask_app, payload):
    with flask_app.test_request_context(
        '/game/combat',
        method='POST',
        json=payload,
    ):
        response, status = game_combat.start_combat()

    assert status == 401
    assert response.get_json() == {'error': 'Missing token'}


def test_start_combat_rejects_non_json_body_with_existing_missing_token_contract(flask_app):
    with flask_app.test_request_context(
        '/game/combat',
        method='POST',
        data='not-json',
        content_type='text/plain',
    ):
        response, status = game_combat.start_combat()

    assert status == 401
    assert response.get_json() == {'error': 'Missing token'}
