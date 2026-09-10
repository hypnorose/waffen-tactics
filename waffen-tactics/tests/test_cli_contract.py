from waffen_tactics.cli import is_player_side_win


def test_cli_uses_shared_team_winner_contract():
    assert is_player_side_win({"winner": "team_a"}) is True
    assert is_player_side_win({"winner": "team_b"}) is False


def test_cli_does_not_accept_legacy_or_malformed_winner_values():
    assert is_player_side_win({"winner": "A"}) is False
    assert is_player_side_win({"winner": None}) is False
    assert is_player_side_win(None) is False
