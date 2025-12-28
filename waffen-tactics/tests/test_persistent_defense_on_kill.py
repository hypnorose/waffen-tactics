import pytest

from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.services.combat_effect_processor import CombatEffectProcessor
from waffen_tactics.services.modular_effect_processor import (
    ModularEffectProcessor,
    ModularEffect,
    TriggerType,
    EffectConditions,
    Reward,
    RewardType,
    ValueType,
    DurationType
)


def test_on_enemy_death_grants_persistent_defense():
    """When an enemy dies, units with kill_buff(defense) gain permanent defense and it's recorded."""
    # Create modular effect processor and register the effect
    modular_processor = ModularEffectProcessor()
    
    # Create the kill_buff effect directly
    kill_buff_effect = ModularEffect(
        trigger=TriggerType.ON_ENEMY_DEATH,
        conditions=EffectConditions(),
        rewards=[Reward(
            type=RewardType.STAT_BUFF,
            stat="defense",
            value=10,
            value_type=ValueType.FLAT,
            duration=DurationType.PERMANENT
        )]
    )
    
    # Register the effect
    modular_processor.register_effect("test_kill_buff", kill_buff_effect)
    
    # Create the killer unit
    killer = CombatUnit(
        id="killer",
        name="Killer",
        hp=100,
        attack=25,
        defense=15,
        attack_speed=1.0,
        effects=[]  # Effects will be handled by modular processor
    )

    # Victim that will be killed
    victim = CombatUnit(
        id="victim",
        name="Victim",
        hp=0,
        attack=5,
        defense=20,
        attack_speed=1.0,
        effects=[]
    )

    processor = CombatEffectProcessor(modular_processor)
    log = []

    # Simulate death processing: attacking_team contains the killer
    processor._process_unit_death(
        killer=killer,
        defending_team=[victim],
        defending_hp=[0],
        attacking_team=[killer],
        attacking_hp=[killer.hp],
        target_idx=0,
        time=1.0,
        log=log,
        event_callback=None,
        side="team_a"
    )

    # After processing, killer should have permanent_buffs_applied with defense
    assert hasattr(killer, 'permanent_buffs_applied'), "permanent_buffs_applied should be initialized"
    assert 'defense' in killer.permanent_buffs_applied, "defense key should be present in permanent_buffs_applied"

    # The permanent buff value should match the added defense (10)
    assert killer.permanent_buffs_applied['defense'] == 10

    # And the killer's defense should have increased by that amount
    assert killer.defense >= 25
