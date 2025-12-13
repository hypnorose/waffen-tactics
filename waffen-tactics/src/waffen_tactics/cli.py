import sys
from pathlib import Path

# Allow running as a script by fixing sys.path when package context is missing
pkg_root = Path(__file__).resolve().parents[1]
if str(pkg_root) not in sys.path:
    sys.path.append(str(pkg_root))

from services.data_loader import load_game_data
from services.shop import ShopService
from services.synergy import SynergyEngine
from services.combat import CombatSimulator
from services.progression import ProgressionService
from models.player import PlayerProfile, TeamSnapshot

def demo_round():
    data = load_game_data()
    shop = ShopService(data.units)
    synergies = SynergyEngine(data.traits)
    combat = CombatSimulator()
    prog = ProgressionService()

    player = PlayerProfile(nickname="PlayerOne", level=3, gold=10)
    offer = shop.roll(player.level)
    team = offer[:3]
    opp_team = offer[3:5] if len(offer) >= 5 else offer[:2]

    print("Team A:")
    for u in team:
        print(f" - {u.name} (cost {u.cost}) [{', '.join(u.factions + u.classes)}] | atk_spd={u.stats.attack_speed:.2f} atk={u.stats.attack} def={u.stats.defense} hp={u.stats.hp}")
    print("Team B:")
    for u in opp_team:
        print(f" - {u.name} (cost {u.cost}) [{', '.join(u.factions + u.classes)}] | atk_spd={u.stats.attack_speed:.2f} atk={u.stats.attack} def={u.stats.defense} hp={u.stats.hp}")

    s = synergies.compute(team)
    print("Synergies:", s)

    result = combat.simulate(team, opp_team)
    print("Combat result:", result)
    print("Combat log (first 20 lines):")
    for line in result.get("log", [])[:20]:
        print(line)

    prog.award_post_combat(player, won=(result["winner"] == "A"))
    print("Post-combat:", player)

if __name__ == "__main__":
    demo_round()
