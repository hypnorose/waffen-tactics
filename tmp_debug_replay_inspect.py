from waffen_tactics.services.combat_shared import CombatSimulator, CombatUnit

# Build teams like test_bosman_replay_full_stats
import json
from pathlib import Path


def _load_template(unit_id_or_name: str):
    path = Path(__file__).parent / 'waffen-tactics' / 'units.json'
    if not path.exists():
        path = Path(__file__).parent.parent / 'waffen-tactics' / 'units.json'
    if not path.exists():
        return None
    with open(path, 'r') as fh:
        data = json.load(fh)
    for u in data.get('units', []):
        if u.get('id') == unit_id_or_name or u.get('name') == unit_id_or_name:
            return u
    return None


def _make_from_template(template_id: str, instance_id: str = None):
    tpl = _load_template(template_id)
    if not tpl:
        return None
    cost = tpl.get('cost', 1)
    stats = tpl.get('stats') or {}
    hp = int(stats.get('hp', 80 + (cost * 40)))
    attack = int(stats.get('attack', 20 + (cost * 10)))
    defense = int(stats.get('defense', 5))
    attack_speed = float(stats.get('attack_speed', 1.0))

    class StatsObj:
        def __init__(self, hp_val, mana_on_attack=0):
            self.hp = hp_val
            self.mana_on_attack = mana_on_attack

    mana_on_attack = int(stats.get('mana_on_attack', 0))
    stats_obj = StatsObj(hp, mana_on_attack=mana_on_attack)
    from waffen_tactics.services.combat_shared import CombatUnit
    unit = CombatUnit(id=instance_id or tpl.get('id'), name=tpl.get('name'), hp=hp, attack=attack, defense=defense, attack_speed=attack_speed, stats=stats_obj)
    try:
        unit.max_mana = int(tpl.get('max_mana', 100))
    except Exception:
        pass
    return unit


def make(uid, name):
    u = _make_from_template(name)
    if u is None:
        class StatsObj:
            def __init__(self, hp_val, mana_on_attack=0):
                self.hp = hp_val
                self.mana_on_attack = mana_on_attack
        stats = StatsObj(600, 0)
        return CombatUnit(id=uid, name=name, hp=600, attack=50, defense=0, attack_speed=1.0, stats=stats)
    u.id = uid
    return u


wu = make('cb896ef5', 'Wu_hao')
turbo = make('turboglowica', 'Turboglowica')
beudzik = make('ad1614e4', 'Beudzik')
pepe = make('cd45bffd', 'Pepe')
un4 = make('un4given', 'Un4given')
team_a = [wu, turbo, beudzik, pepe, un4]

mrv = make('opp_0', 'Mrvlook')
bosman = make('opp_1', 'Bosman')
xnt = make('opp_2', 'xntentacion')
team_b = [mrv, bosman, xnt]

sim = CombatSimulator(dt=0.1, timeout=10)

events = []

def collector(et, data):
    events.append((et, dict(data)))

sim.simulate(team_a, team_b, collector)

for i, (et, payload) in enumerate(events):
    seq = payload.get('seq') if isinstance(payload, dict) else None
    ts = payload.get('timestamp') if isinstance(payload, dict) else None
    if et == 'unit_attack':
        print(f"{i:03d} SEQ={seq} TS={ts} EVENT={et} attacker={payload.get('attacker_id')} target={payload.get('target_id')} target_hp={payload.get('target_hp')}")
    elif et == 'unit_died':
        print(f"{i:03d} SEQ={seq} TS={ts} EVENT={et} unit={payload.get('unit_id')}")
    else:
        print(f"{i:03d} SEQ={seq} TS={ts} EVENT={et}")

# Print final snapshot for comparison
snapshots = [p for t,p in events if t == 'state_snapshot']
if snapshots:
    print('\nFINAL SNAPSHOT:')
    import json
    print(json.dumps(snapshots[-1], indent=2))
