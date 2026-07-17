from waffen_tactics.services.data_loader import load_game_data


def test_role_mana_profiles_are_consistent_for_all_units():
    expected = {
        "mage": (40, 10, 8),
        "duelist": (60, 7, 6),
        "fighter": (80, 5, 5),
        "defender": (100, 4, 4),
    }

    units = load_game_data().units

    assert len(units) == 52
    for unit in units:
        max_mana, mana_on_attack, mana_regen = expected[unit.role]
        assert (unit.stats.max_mana, unit.stats.mana_on_attack, unit.stats.mana_regen) == (
            max_mana,
            mana_on_attack,
            mana_regen,
        )
