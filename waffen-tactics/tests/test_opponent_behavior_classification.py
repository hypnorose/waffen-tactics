from types import SimpleNamespace

import pytest

from tools.balance_audit import _classify_opponent_behavior


@pytest.mark.parametrize(
    ("seed", "role", "attacks", "skill_casts", "final_hp", "timeout", "team_alive", "expected"),
    [
        (157001, "fighter", [{}, {}], [], 100, False, True, "repeated_basic_attack"),
        (157003, "fighter", [], [], 0, False, True, "combat_ended_before_action"),
        (157004, "defender", [], [], 100, True, True, "intentional_defensive_identity"),
        (157005, "fighter", [], [], 100, False, False, "no_legal_action"),
        (157006, "fighter", [], [], 100, False, True, "runtime_defect_candidate"),
        (157007, "fighter", [{"target_id": "target"}], [], 100, False, True, "targeted_action"),
    ],
)
def test_seeded_opponent_behavior_categories(
    seed, role, attacks, skill_casts, final_hp, timeout, team_alive, expected
):
    result = _classify_opponent_behavior(
        unit=SimpleNamespace(role=role, passive={}),
        attacks=attacks,
        skill_casts=skill_casts,
        final_hp=final_hp,
        timeout=timeout,
        opponent_team_alive=team_alive,
    )

    assert result[0] == expected, f"seed {seed} classified incorrectly"
