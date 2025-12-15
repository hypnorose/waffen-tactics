import sys
import argparse
import asyncio
from pathlib import Path

# Allow running as a script by fixing sys.path when package context is missing
pkg_root = Path(__file__).resolve().parents[1]
if str(pkg_root) not in sys.path:
    sys.path.append(str(pkg_root))

from waffen_tactics.services.data_loader import load_game_data
from waffen_tactics.services.shop import ShopService
from waffen_tactics.services.synergy import SynergyEngine
from waffen_tactics.services.combat import CombatSimulator
from waffen_tactics.services.progression import ProgressionService
from waffen_tactics.services.database import DatabaseManager
from waffen_tactics.models.player import PlayerProfile, TeamSnapshot

async def reset_leaderboard(db_path: str):
    """Reset the leaderboard"""
    db = DatabaseManager(db_path)
    await db.initialize()
    await db.reset_leaderboard()
    print("Leaderboard reset successfully!")

async def reset_opponents(db_path: str):
    """Reset opponent teams"""
    db = DatabaseManager(db_path)
    await db.initialize()
    await db.reset_opponent_teams()
    print("Opponent teams reset successfully!")

async def load_bots(db_path: str):
    """Load sample bot teams"""
    db = DatabaseManager(db_path)
    await db.initialize()
    data = load_game_data()
    await db.add_sample_teams(data.units)
    print("Sample bots loaded successfully!")

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

async def main():
    parser = argparse.ArgumentParser(description="Waffen Tactics CLI")
    # Use the same database path as the backend
    default_db_path = str(Path(__file__).resolve().parents[3] / 'waffen-tactics' / 'waffen_tactics_game.db')
    parser.add_argument('--db-path', default=default_db_path, help='Path to the database file')
    parser.add_argument('--reset-leaderboard', action='store_true', help='Reset the leaderboard')
    parser.add_argument('--reset-opponents', action='store_true', help='Reset opponent teams')
    parser.add_argument('--load-bots', action='store_true', help='Load sample bot teams')
    parser.add_argument('--demo', action='store_true', help='Run demo round')

    args = parser.parse_args()

    if args.reset_leaderboard:
        await reset_leaderboard(args.db_path)
    elif args.reset_opponents:
        await reset_opponents(args.db_path)
    elif args.load_bots:
        await load_bots(args.db_path)
    elif args.demo:
        demo_round()
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
