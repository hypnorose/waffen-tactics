import sys
sys.path.insert(0, 'waffen-tactics/src')
sys.path.insert(0, 'waffen-tactics-web')

from waffen_tactics.models.player_state import PlayerState, UnitInstance
from waffen_tactics.models.unit import Unit, Stats, Skill
import backend.routes.game_state_utils as gsu

# Create units
def make_unit(uid, name, factions=None, classes=None, atk_speed=1.0):
    stats = Stats(attack=50, hp=500, defense=10, max_mana=100, attack_speed=atk_speed)
    skill = Skill(name="s", description="d", mana_cost=100, effect={})
    return Unit(id=uid, name=name, cost=1, factions=factions or [], classes=classes or [], stats=stats, skill=skill)

# Create player with 3 XN Waffen and 1 XN Jugend
player = PlayerState(user_id=1)
u1 = make_unit("xn1", "XN1", factions=["XN Waffen"])
u2 = make_unit("xn2", "XN2", factions=["XN Waffen"])
u3 = make_unit("xn3", "XN3", factions=["XN Waffen"])
u4 = make_unit("noname", "Noname", factions=["XN Jugend"])

ui1 = UnitInstance(unit_id="yossarian", star_level=1)
ui2 = UnitInstance(unit_id="szalwia", star_level=1)
ui3 = UnitInstance(unit_id="bosman", star_level=1)
ui4 = UnitInstance(unit_id="noname", star_level=1)  # XN Jugend

player.board = [ui1, ui2, ui3, ui4]

state = gsu.enrich_player_state(player)

print("Synergies:", state['synergies'])
for b in state['board']:
    iid = b['instance_id']
    buffed = b['buffed_stats']
    print(f"Unit {b['unit_id']}: attack {buffed['attack']}, attack_speed {buffed['attack_speed']}")
