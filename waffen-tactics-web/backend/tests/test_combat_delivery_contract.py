import types

import routes.game_combat as game_combat


def test_combat_endpoint_explicitly_advertises_batch_replay(flask_app, monkeypatch):
    player = types.SimpleNamespace(
        round_number=3,
        hp=100,
        board=[object()],
    )
    cached_action = {
        'player': player,
        'result': {'winner': 'team_a'},
        'result_id': 'cached-result',
    }
    responses = iter([player, cached_action])

    def fake_run_async(coro):
        # start_combat creates the production coroutine before handing it to
        # the lifecycle helper; close it here because the test bypasses I/O.
        coro.close()
        return next(responses)

    monkeypatch.setattr(game_combat, 'verify_token', lambda token: {'user_id': '42'})
    monkeypatch.setattr(game_combat, 'run_async', fake_run_async)
    monkeypatch.setattr(game_combat, 'enrich_player_state', lambda value: {'round_number': 3})
    monkeypatch.setattr(game_combat.db_manager, '_serialize_player', lambda value: '{}')

    with flask_app.test_request_context(
        '/game/combat',
        method='POST',
        json={'token': 'test-token', 'idempotency_key': 'retry-1'},
    ):
        response = game_combat.start_combat()

    assert response.mimetype == 'text/event-stream'
    assert response.headers['X-Combat-Delivery-Mode'] == 'batch_replay'
    assert response.headers['X-Combat-Live-Stream'] == 'false'
    assert '"delivery_mode": "batch_replay"' in response.get_data(as_text=True)


def test_cached_combat_enrichment_failure_is_not_returned_as_success(flask_app, monkeypatch):
    player = types.SimpleNamespace(round_number=3, hp=100, board=[object()])
    cached_action = {
        'player': player,
        'result': {'winner': 'team_a'},
        'result_id': 'cached-result',
    }

    def fake_run_async(coro):
        coro.close()
        return cached_action

    def raise_sentinel(value):
        raise RuntimeError('secret enrichment failure')

    monkeypatch.setattr(game_combat, 'verify_token', lambda token: {'user_id': '42'})
    monkeypatch.setattr(game_combat, 'run_async', fake_run_async)
    monkeypatch.setattr(game_combat, 'enrich_player_state', raise_sentinel)
    monkeypatch.setattr(game_combat.db_manager, '_serialize_player', lambda value: '{}')

    with flask_app.test_request_context(
        '/game/combat',
        method='POST',
        json={'token': 'test-token', 'idempotency_key': 'retry-1'},
    ):
        response = game_combat.start_combat()

    body = response.get_data(as_text=True)
    assert response.mimetype == 'text/event-stream'
    assert 'combat_request_failed' in body
    assert 'secret enrichment failure' not in body
