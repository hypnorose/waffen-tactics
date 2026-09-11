"""WFT-54 regression checks for economy audit alignment."""

from tools.balance_audit import economy_audit


def test_balance_audit_models_the_canonical_two_xp_post_combat_contract():
    rows = {row["path"]: row for row in economy_audit()["xp_paths"]}

    assert rows["all_losses"]["xp_per_loss"] == 2
    assert rows["all_wins"]["xp_per_win"] == 2
    assert rows["all_losses"]["level"] == rows["all_wins"]["level"]
    assert rows["all_losses"]["xp_remainder"] == rows["all_wins"]["xp_remainder"]
