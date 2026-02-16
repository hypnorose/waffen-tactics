"""Discord bot for Waffen Tactics leaderboard only"""
import discord
from discord import app_commands
import os
import asyncio
from typing import Optional
import sys
from pathlib import Path
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

# Load environment variables from .env file
load_dotenv()

# Enhanced logging setup with rotation
log_formatter = logging.Formatter(
    '[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Main log file with rotation (10MB max, keep 5 backups)
main_handler = RotatingFileHandler(
    'bot.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
main_handler.setFormatter(log_formatter)
main_handler.setLevel(logging.DEBUG)

# Error log file with rotation
error_handler = RotatingFileHandler(
    'bot_errors.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
error_handler.setFormatter(log_formatter)
error_handler.setLevel(logging.ERROR)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

# Setup root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(main_handler)
root_logger.addHandler(error_handler)
root_logger.addHandler(console_handler)

# Import database after logging setup
from .services.database import DatabaseManager

class WaffenTacticsBot(discord.Client):
    """Main bot class for leaderboard only"""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)
        self.db = DatabaseManager()

        # Setup commands
        self.setup_commands()

    def setup_commands(self):
        @self.tree.command(name="ranking", description="Zobacz topkę graczy")
        async def ranking_command(interaction: discord.Interaction):
            leaderboard = await self.db.get_leaderboard(10)

            embed = discord.Embed(
                title="🏆 Ranking Graczy - Top 10",
                description="Najlepsi gracze według liczby wygranych",
                color=discord.Color.gold()
            )

            if not leaderboard:
                embed.add_field(
                    name="Brak wpisów",
                    value="Nikt jeszcze nie ukończył gry!",
                    inline=False
                )
            else:
                for i, (nickname, wins, losses, level, round_num, created_at) in enumerate(leaderboard, 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
                    winrate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
                    embed.add_field(
                        name=f"{medal} {nickname}",
                        value=f"🏆 {wins}W-{losses}L ({winrate:.0f}%)\n📊 Lvl {level} | 🔄 Runda {round_num}",
                        inline=True
                    )

            embed.set_footer(text="🎮 Gra dostępna na stronie internetowej!")
            await interaction.response.send_message(embed=embed, ephemeral=False)

    async def on_ready(self):
        logging.info(f'Bot logged in as {self.user}')
        try:
            synced = await self.tree.sync()
            logging.info(f'Synced {len(synced)} commands')
        except Exception as e:
            logging.error(f'Failed to sync commands: {e}')

    async def on_error(self, event, *args, **kwargs):
        logging.error(f'Error in {event}: {args} {kwargs}')


async def main():
    """Main entry point"""
    bot = WaffenTacticsBot()

    # Initialize database
    await bot.db.initialize()

    # Start bot
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logging.error('DISCORD_BOT_TOKEN not found in environment variables')
        return

    try:
        await bot.start(token)
    except KeyboardInterrupt:
        logging.info('Bot stopped by user')
    except Exception as e:
        logging.error(f'Bot crashed: {e}')
    finally:
        await bot.db.close()


if __name__ == '__main__':
    asyncio.run(main())