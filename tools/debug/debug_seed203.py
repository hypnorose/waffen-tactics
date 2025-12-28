import sys, os, random
from collections import defaultdict

sys.path.insert(0, os.path.join(os.getcwd(), 'waffen-tactics/src'))
sys.path.insert(0, os.path.join(os.getcwd(), 'waffen-tactics-web/backend'))

from waffen_tactics.services.combat_shared import CombatUnit
from waffen_tactics.services.data_loader import load_game_data
from services.combat_service import run_combat_simulation
from services.combat_event_reconstructor import CombatEventReconstructor

game_data = load_game_data()
all_unit_ids = [u.id for u in game_data.units]

def make_team_from_ids(ids):
    team = []
    for idx, unit_id in enumerate(ids):
        unit = next(u for u in game_data.units if u.id == unit_id)
        team.append(CombatUnit(
            id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
            defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
            position='front' if idx < 5 else 'back', stats=unit.stats, skill=unit.skill,
            max_mana=unit.stats.max_mana
        ))
    return team

seed = 203
random.seed(seed)
sample_20 = random.sample(all_unit_ids, 20)
player_ids = sample_20[:10]
opponent_ids = sample_20[10:]

print('Player IDs:', player_ids)
print('Opponent IDs:', opponent_ids)

player_units = make_team_from_ids(player_ids)
opponent_units = make_team_from_ids(opponent_ids)

result = run_combat_simulation(player_units, opponent_units)
events = result['events']
events.sort(key=lambda x: (x[1].get('seq', 0), x[1].get('timestamp', 0)))

state_snapshots = [e for e in events if e[0] == 'state_snapshot']
reconstructor = CombatEventReconstructor()
reconstructor.initialize_from_snapshot(state_snapshots[0][1])

hp_events = []
for et, ed in events:
    if et in ('unit_attack', 'unit_heal', 'heal', 'hp_regen', 'damage_over_time_tick', 'unit_died', 'stat_buff', 'skill_cast'):
        hp_events.append((et, ed))
    reconstructor.process_event(et, ed)

reconstructed_player_units, reconstructed_opponent_units = reconstructor.get_reconstructed_state()

mismatches = []
print('\nMismatches:')
for u in player_units:
    recon_hp = reconstructed_player_units[u.id]['hp']
    recon_max = reconstructed_player_units[u.id]['max_hp']
    recon_mana = reconstructed_player_units[u.id]['current_mana']
    if u.hp != recon_hp or u.max_hp != recon_max or getattr(u, 'mana', None) != recon_mana:
        mismatches.append(('player', u.id, u.name, u.hp, recon_hp, u.max_hp, recon_max, getattr(u, 'mana', None), recon_mana))
        print(f'  Player {u.name} ({u.id}): sim_hp={u.hp}, recon_hp={recon_hp}, sim_max={u.max_hp}, recon_max={recon_max}, sim_mana={getattr(u, "mana", None)}, recon_mana={recon_mana}')

for u in opponent_units:
    recon_hp = reconstructed_opponent_units[u.id]['hp']
    recon_max = reconstructed_opponent_units[u.id]['max_hp']
    recon_mana = reconstructed_opponent_units[u.id]['current_mana']
    if u.hp != recon_hp or u.max_hp != recon_max or getattr(u, 'mana', None) != recon_mana:
        mismatches.append(('opponent', u.id, u.name, u.hp, recon_hp, u.max_hp, recon_max, getattr(u, 'mana', None), recon_mana))
        print(f'  Opponent {u.name} ({u.id}): sim_hp={u.hp}, recon_hp={recon_hp}, sim_max={u.max_hp}, recon_max={recon_max}, sim_mana={getattr(u, "mana", None)}, recon_mana={recon_mana}')

if mismatches:
    # Collect last N hp-related events per mismatched unit for debugging
    per_unit_events = defaultdict(list)
    for et, ed in hp_events:
        uid = ed.get('unit_id') or ed.get('target_id') or ed.get('id') or ed.get('unit') or ed.get('caster_id')
        if uid:
            per_unit_events[uid].append((et, ed))

    # Also collect mana_update and skill_cast events
    mana_events = defaultdict(list)
    skill_cast_events = defaultdict(list)
    for et, ed in events:
        if et == 'mana_update':
            uid = ed.get('unit_id')
            if uid:
                mana_events[uid].append((et, ed))
        elif et == 'skill_cast':
            uid = ed.get('caster_id')
            if uid:
                skill_cast_events[uid].append((et, ed))

    print("\nDetailed events for mismatched units:")
    for m in mismatches:
        side, uid, name, sim_hp, recon_hp, sim_max, recon_max, sim_mana, recon_mana = m
        print(f"\n  {side} {name} ({uid}):")
        
        # HP events
        hp_unit_events = per_unit_events.get(uid, [])
        print(f"    HP events ({len(hp_unit_events)}):")
        for et, ed in hp_unit_events[-10:]:  # Last 10
            print(f"      {et}: {ed}")
        
        # Mana events
        mana_unit_events = mana_events.get(uid, [])
        print(f"    Mana events ({len(mana_unit_events)}):")
        for et, ed in mana_unit_events[-10:]:  # Last 10
            print(f"      {et}: {ed}")
        
        # Skill cast events
        skill_unit_events = skill_cast_events.get(uid, [])
        print(f"    Skill cast events ({len(skill_unit_events)}):")
        for et, ed in skill_unit_events[-5:]:  # Last 5
            print(f"      {et}: {ed}")