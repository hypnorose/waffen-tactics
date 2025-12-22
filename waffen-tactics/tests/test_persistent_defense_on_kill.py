import pytest

from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.services.combat_effect_processor import CombatEffectProcessor
from waffen_tactics.services.modular_effect_processor import ModularEffectProcessor
from waffen_tactics.services.trait_converter import TraitConverter


def test_on_enemy_death_grants_persistent_defense():
    """When an enemy dies, units with kill_buff(defense) gain permanent defense and it's recorded."""
    # Create modular effect processor and register the effect
    converter = TraitConverter()
    modular_processor = converter.get_processor()
    
    # Create a mock trait effect for the killer
    test_trait = {
        'name': 'Test Kill Buff',
        'type': 'trait',
        'thresholds': [1],
        'effects': [
            {
                'type': 'on_enemy_death',
                'actions': [
                    {
                        'type': 'kill_buff',
                        'stat': 'defense',
                        'value': 10,
                        'is_percentage': False
                    }
                ]
            }
        ]
    }
    
    # Register the trait effect for the killer unit
    killer = CombatUnit(
        id="killer",
        name="Killer",
        hp=100,
        attack=25,
        defense=15,
        attack_speed=1.0,
        effects=[]  # Effects will be handled by modular processor
    )
    
    converter.register_trait_effects_for_unit(killer, test_trait, 1, killer.id)

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
        side="team_a",
    )

    # After processing, killer should have permanent_buffs_applied with defense
    assert hasattr(killer, 'permanent_buffs_applied'), "permanent_buffs_applied should be initialized"
    assert 'defense' in killer.permanent_buffs_applied, "defense key should be present in permanent_buffs_applied"

    # The permanent buff value should match the added defense (10)
    assert killer.permanent_buffs_applied['defense'] == 10

    # And the killer's defense should have increased by that amount
    assert killer.defense >= 25
