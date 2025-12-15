"""Discord bot for Waffen Tactics game"""
import discord
from discord import app_commands
from discord.ui import Button, View, Select
import os
import asyncio
from typing import Optional, List
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

# Custom logger for our bot
bot_logger = logging.getLogger('waffen_tactics')
bot_logger.info('='*80)
bot_logger.info('🚀 Waffen Tactics Bot Starting...')
bot_logger.info('='*80)

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from waffen_tactics.models.player_state import PlayerState, UnitInstance
from waffen_tactics.services.database import DatabaseManager
from waffen_tactics.services.game_manager import GameManager
from waffen_tactics.services.data_loader import load_game_data


class OpponentPreviewView(View):
    """View for opponent preview with start combat button"""
    
    def __init__(self, bot_instance, user_id: int, opponent_data: dict, opponent_units: list):
        super().__init__(timeout=60)
        self.bot = bot_instance
        self.user_id = user_id
        self.opponent_data = opponent_data
        self.opponent_units = opponent_units
    
    @discord.ui.button(label="⚔️ ROZPOCZNIJ WALKĘ", style=discord.ButtonStyle.danger, row=0)
    async def start_combat_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        
        # Disable button and update message
        button.disabled = True
        await interaction.response.edit_message(view=self)
        
        # Start combat animation in new message
        player = await self.bot.db.load_player(interaction.user.id)
        combat_embed = discord.Embed(
            title="⚔️ WALKA W TOKU...",
            description="🎬 Obserwuj przebieg walki!",
            color=discord.Color.orange()
        )
        combat_msg = await interaction.followup.send(embed=combat_embed, ephemeral=True, wait=True)
        
        # Run combat with animation
        result = await self.bot.run_combat_with_animation(combat_msg, player, self.opponent_units, self.opponent_data)
        
        # Save player's team and update
        board_units = [{'unit_id': ui.unit_id, 'star_level': ui.star_level} for ui in player.board]
        bench_units = [{'unit_id': ui.unit_id, 'star_level': ui.star_level} for ui in player.bench]
        await self.bot.db.save_opponent_team(
            user_id=interaction.user.id,
            nickname=interaction.user.display_name,
            board_units=board_units,
            bench_units=bench_units,
            wins=player.wins,
            losses=player.losses,
            level=player.level
        )
        
        player.round_number += 1
        
        # Calculate interest: 1g per 10g, max 5g
        interest = min(5, player.gold // 10)
        base_income = 5
        total_income = base_income + interest
        player.gold += total_income
        
        self.bot.game_manager.generate_shop(player, force_new=True)
        await self.bot.db.save_player(player)
        
        # Show final result with game menu
        embed = self.bot.create_combat_result_embed(player, result, self.opponent_data, interest=interest)
        view = GameView(self.bot, interaction.user.id)
        await combat_msg.edit(embed=embed, view=view)


class GameView(View):
    """Main game UI with buttons"""
    
    def __init__(self, bot_instance, user_id: int):
        super().__init__(timeout=300)  # 5 min timeout
        self.bot = bot_instance
        self.user_id = user_id
    
    @discord.ui.button(label="🏪 Sklep", style=discord.ButtonStyle.primary, row=0)
    async def shop_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        await self.bot.show_shop(interaction)
    
    @discord.ui.button(label="📋 Ławka", style=discord.ButtonStyle.secondary, row=0)
    async def bench_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        await self.bot.show_bench(interaction)
    
    @discord.ui.button(label="⚔️ Plansza", style=discord.ButtonStyle.secondary, row=0)
    async def board_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        await self.bot.show_board(interaction)
    
    @discord.ui.button(label="🔄 Reroll (2g)", style=discord.ButtonStyle.danger, row=1)
    async def reroll_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        await self.bot.reroll_shop(interaction)
    
    @discord.ui.button(label="📈 Kup XP (4g)", style=discord.ButtonStyle.success, row=1)
    async def buy_xp_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        await self.bot.buy_xp(interaction)
    
    @discord.ui.button(label="⚔️ Walcz!", style=discord.ButtonStyle.danger, row=2)
    async def combat_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        
        await interaction.response.defer(ephemeral=True)
        await self.bot.start_combat(interaction)


class ShopView(View):
    """Shop interface with buy buttons"""
    
    def __init__(self, bot_instance, user_id: int, shop_units: List[str]):
        super().__init__(timeout=180)
        self.bot = bot_instance
        self.user_id = user_id
        self.shop_units = shop_units
        
        # Add buy buttons for each unit
        for i, unit_id in enumerate(shop_units):
            if unit_id:  # Skip empty slots
                unit = next((u for u in bot_instance.game_data.units if u.id == unit_id), None)
                if unit:
                    button = Button(
                        label=f"{unit.name} ({unit.cost}g)",
                        style=discord.ButtonStyle.success,
                        custom_id=f"buy_{i}_{unit_id}",  # Add index to make unique
                        row=i // 5
                    )
                    button.callback = self.make_buy_callback(unit_id)
                    self.add_item(button)
        
        # Action buttons
        reroll_btn = Button(label="🔄 Reroll (2g)", style=discord.ButtonStyle.danger, row=1)
        reroll_btn.callback = self.reroll_callback
        self.add_item(reroll_btn)
        
        xp_btn = Button(label="📈 Kup XP (4g)", style=discord.ButtonStyle.primary, row=1)
        xp_btn.callback = self.buy_xp_callback
        self.add_item(xp_btn)
        
        bench_btn = Button(label="📦 Ławka", style=discord.ButtonStyle.success, row=1)
        bench_btn.callback = self.bench_callback
        self.add_item(bench_btn)
        
        back_btn = Button(label="◀️ Powrót", style=discord.ButtonStyle.secondary, row=1)
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
    
    async def bench_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        await self.bot.show_bench(interaction)
    
    def make_buy_callback(self, unit_id: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.defer()
                return
            await self.bot.buy_unit(interaction, unit_id)
        return callback
    
    async def reroll_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        await self.bot.reroll_shop(interaction)
    
    async def buy_xp_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        await self.bot.buy_xp(interaction)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        await self.bot.show_main_menu(interaction)


class BenchView(View):
    """Bench interface with unit management"""
    
    def __init__(self, bot_instance, user_id: int, bench_units: List[UnitInstance]):
        super().__init__(timeout=180)
        self.bot = bot_instance
        self.user_id = user_id
        
        if bench_units:
            # Add select menu for units
            options = []
            for ui in bench_units[:25]:  # Discord limit
                unit = next((u for u in bot_instance.game_data.units if u.id == ui.unit_id), None)
                if unit:
                    stars = '⭐' * ui.star_level
                    options.append(discord.SelectOption(
                        label=f"{unit.name} {stars}",
                        value=ui.instance_id,
                        description=f"Cost: {unit.cost}g"
                    ))
            
            if options:
                select = Select(
                    placeholder="Wybierz jednostkę...",
                    options=options,
                    custom_id="select_bench_unit"
                )
                select.callback = self.select_unit_callback
                self.add_item(select)
        
        # Action buttons (work on selected unit)
        move_btn = Button(label="➡️ Na planszę", style=discord.ButtonStyle.primary, row=1)
        move_btn.callback = self.move_to_board_callback
        self.add_item(move_btn)
        
        sell_btn = Button(label="💰 Sprzedaj", style=discord.ButtonStyle.danger, row=1)
        sell_btn.callback = self.sell_callback
        self.add_item(sell_btn)
        
        board_btn = Button(label="🎯 Plansza", style=discord.ButtonStyle.success, row=1)
        board_btn.callback = self.board_callback
        self.add_item(board_btn)
        
        shop_btn = Button(label="🛒 Sklep", style=discord.ButtonStyle.success, row=1)
        shop_btn.callback = self.shop_callback
        self.add_item(shop_btn)
        
        back_btn = Button(label="◀️ Powrót", style=discord.ButtonStyle.secondary, row=1)
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
        
        self.selected_instance_id = None
    
    async def board_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        await interaction.response.defer()
        await self.bot.show_board(interaction)
    
    async def shop_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        await interaction.response.defer()
        await self.bot.show_shop(interaction)
    
    async def select_unit_callback(self, interaction: discord.Interaction):
        bot_logger = logging.getLogger('waffen_tactics')
        
        if interaction.user.id != self.user_id:
            bot_logger.warning(f"[SELECT_UNIT_BENCH] User mismatch! Expected {self.user_id}, got {interaction.user.id} - ignoring")
            await interaction.response.defer()
            return
        
        bot_logger.info(f"[SELECT_UNIT_BENCH] User {interaction.user.id} selecting unit")
        self.selected_instance_id = interaction.data['values'][0]
        bot_logger.info(f"[SELECT_UNIT_BENCH] Selected instance_id: {self.selected_instance_id}")
        await interaction.response.defer()
    
    async def move_to_board_callback(self, interaction: discord.Interaction):
        bot_logger = logging.getLogger('waffen_tactics')
        
        if interaction.user.id != self.user_id:
            bot_logger.warning(f"[MOVE_TO_BOARD] User mismatch! Expected {self.user_id}, got {interaction.user.id} - ignoring")
            await interaction.response.defer()
            return
        
        bot_logger.info(f"[MOVE_TO_BOARD] User {interaction.user.id} ({interaction.user.name}) triggered move_to_board")
        bot_logger.info(f"[MOVE_TO_BOARD] Selected instance_id: {self.selected_instance_id}")
        
        if not self.selected_instance_id:
            bot_logger.warning(f"[MOVE_TO_BOARD] No unit selected by user {interaction.user.id}")
            await interaction.response.send_message("Najpierw wybierz jednostkę z listy!", ephemeral=True)
            return
        
        bot_logger.info(f"[MOVE_TO_BOARD] Calling move_unit_to_board for instance {self.selected_instance_id}")
        await self.bot.move_unit_to_board(interaction, self.selected_instance_id)
    
    async def sell_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        
        if not self.selected_instance_id:
            await interaction.response.send_message("Najpierw wybierz jednostkę z listy!", ephemeral=True)
            return
        
        await self.bot.sell_unit(interaction, self.selected_instance_id)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        await interaction.response.defer()
        await self.bot.show_main_menu(interaction)


class BoardView(View):
    """Board interface"""
    
    def __init__(self, bot_instance, user_id: int, board_units: List[UnitInstance]):
        super().__init__(timeout=180)
        self.bot = bot_instance
        self.user_id = user_id
        
        if board_units:
            # Add select menu
            options = []
            for ui in board_units[:25]:
                unit = next((u for u in bot_instance.game_data.units if u.id == ui.unit_id), None)
                if unit:
                    stars = '⭐' * ui.star_level
                    options.append(discord.SelectOption(
                        label=f"{unit.name} {stars}",
                        value=ui.instance_id,
                        description=f"Cost: {unit.cost}g"
                    ))
            
            if options:
                select = Select(
                    placeholder="Wybierz jednostkę...",
                    options=options
                )
                select.callback = self.select_unit_callback
                self.add_item(select)
        
        # Move to bench button
        move_btn = Button(label="⬅️ Na ławkę", style=discord.ButtonStyle.primary, row=1)
        move_btn.callback = self.move_to_bench_callback
        self.add_item(move_btn)
        
        sell_btn = Button(label="💰 Sprzedaj", style=discord.ButtonStyle.danger, row=1)
        sell_btn.callback = self.sell_callback
        self.add_item(sell_btn)
        
        bench_btn = Button(label="📦 Ławka", style=discord.ButtonStyle.success, row=1)
        bench_btn.callback = self.bench_callback
        self.add_item(bench_btn)
        
        back_btn = Button(label="◀️ Powrót", style=discord.ButtonStyle.secondary, row=1)
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
        
        self.selected_instance_id = None
    
    async def bench_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        await interaction.response.defer()
        await self.bot.show_bench(interaction)
    
    async def select_unit_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        self.selected_instance_id = interaction.data['values'][0]
        await interaction.response.defer()
    
    async def move_to_bench_callback(self, interaction: discord.Interaction):
        bot_logger = logging.getLogger('waffen_tactics')
        bot_logger.info(f"[MOVE_TO_BENCH] User {interaction.user.id} ({interaction.user.name}) triggered move_to_bench")
        bot_logger.info(f"[MOVE_TO_BENCH] Expected user_id: {self.user_id}, Actual: {interaction.user.id}")
        bot_logger.info(f"[MOVE_TO_BENCH] Selected instance_id: {self.selected_instance_id}")
        
        if interaction.user.id != self.user_id:
            bot_logger.warning(f"[MOVE_TO_BENCH] User mismatch! Expected {self.user_id}, got {interaction.user.id}")
            await interaction.response.defer()
            return
        
        if not self.selected_instance_id:
            bot_logger.warning(f"[MOVE_TO_BENCH] No unit selected by user {interaction.user.id}")
            await interaction.response.send_message("Najpierw wybierz jednostkę!", ephemeral=True)
            return
        
        bot_logger.info(f"[MOVE_TO_BENCH] Calling move_unit_to_bench for instance {self.selected_instance_id}")
        await self.bot.move_unit_to_bench(interaction, self.selected_instance_id)
    
    async def sell_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        
        if not self.selected_instance_id:
            await interaction.response.send_message("Najpierw wybierz jednostkę!", ephemeral=True)
            return
        
        await self.bot.sell_unit_from_board(interaction, self.selected_instance_id)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        await interaction.response.defer()
        await self.bot.show_main_menu(interaction)


class WaffenTacticsBot:
    """Main bot class"""
    
    def __init__(self, token: str):
        intents = discord.Intents.default()
        intents.message_content = False  # Not needed for slash commands
        
        self.client = discord.Client(intents=intents)
        self.tree = app_commands.CommandTree(self.client)
        self.token = token
        
        self.db = DatabaseManager("waffen_tactics_game.db")
        self.game_manager = GameManager()
        self.game_data = load_game_data()
        
        # Track last simple messages per user to avoid spam
        self.last_simple_messages = {}  # user_id -> message
        
        self.setup_commands()
        self.setup_events()
    
    async def on_ready_handler(self):
        """Handler for on_ready event"""
        print("⏳ on_ready: rozpoczęto inicjalizację...", flush=True)
        await self.db.initialize()
        print("✅ on_ready: baza danych zainicjalizowana", flush=True)
        
        # Set bot status to online with activity
        activity = discord.Activity(type=discord.ActivityType.playing, name="Waffen Tactics | /graj")
        await self.client.change_presence(status=discord.Status.online, activity=activity)
        print("🟢 Status ustawiony na: Online", flush=True)
        
        # Add sample opponent teams if system bots don't exist
        has_bots = await self.db.has_system_opponents()
        print(f"🔍 on_ready: boty systemowe w bazie: {has_bots}", flush=True)
        if not has_bots:
            print("⚙️ Dodaję 20 botów systemowych...", flush=True)
            await self.db.add_sample_teams(self.game_data.units)
            print("✅ Dodano 20 botów (Tutorial Bot -> Master of War)!", flush=True)
        
        print(f'Bot zalogowany jako {self.client.user}', flush=True)
        try:
            print("🔄 Synchronizuję komendy...", flush=True)
            synced = await self.tree.sync()
            print(f"✅ Komendy zsynchronizowane! ({len(synced)} komend)", flush=True)
            for cmd in synced:
                print(f"  - /{cmd.name}: {cmd.description}", flush=True)
        except Exception as e:
            print(f"❌ Błąd synchronizacji komend: {e}", flush=True)
    
    def setup_events(self):
        @self.client.event
        async def on_ready():
            await self.on_ready_handler()
    
    def setup_commands(self):
        @self.tree.command(name="graj", description="Rozpocznij grę w Waffen Tactics!")
        async def play_command(interaction: discord.Interaction):
            # Send game to DM
            await interaction.response.send_message(
                "✅ Wysyłam grę na prywatną wiadomość...", 
                ephemeral=True
            )
            try:
                await self.start_game_dm(interaction.user)
            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ Nie mogę wysłać DM! Upewnij się, że masz włączone prywatne wiadomości od członków serwera.",
                    ephemeral=True
                )
        
        @self.tree.command(name="reset", description="Zresetuj swoją grę")
        async def reset_command(interaction: discord.Interaction):
            await self.db.delete_player(interaction.user.id)
            await interaction.response.send_message("✅ Twoja gra została zresetowana!", ephemeral=True)
        
        @self.tree.command(name="profil", description="Zobacz swój profil")
        async def profile_command(interaction: discord.Interaction):
            player = await self.db.load_player(interaction.user.id)
            if not player:
                await interaction.response.send_message("Nie masz jeszcze profilu! Użyj `/graj`", ephemeral=True)
                return
            
            embed = self.create_profile_embed(player)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
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
            
            embed.set_footer(text="🎮 Zagraj /graj aby dostać się na listę!")
            await interaction.response.send_message(embed=embed, ephemeral=False)
        
        @self.tree.command(name="readme", description="Kompletny przewodnik po grze")
        async def readme_command(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            
            # Read README.md file
            readme_path = Path(__file__).parent / "README.md"
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except FileNotFoundError:
                await interaction.followup.send("❌ README nie znaleziony!", ephemeral=True)
                return
            
            # Split content into chunks (Discord has 2000 char limit per message)
            # We'll send it as a file instead for better readability
            import io
            readme_file = discord.File(
                io.BytesIO(content.encode('utf-8')),
                filename="Waffen_Tactics_Przewodnik.md"
            )
            
            embed = discord.Embed(
                title="📖 Waffen Tactics - Kompletny Przewodnik",
                description="Pobierz pełny przewodnik z opisem wszystkich jednostek, traits i mechanik gry!",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📦 Zawartość",
                value="• 51 jednostek (1-7 cost)\n• 14 traits (frakcje + klasy)\n• Mechaniki gry\n• Porady strategiczne\n• System rankingu",
                inline=False
            )
            embed.set_footer(text="💡 Otwórz plik .md w edytorze tekstu lub przeglądarce")
            
            await interaction.followup.send(embed=embed, file=readme_file, ephemeral=True)
    
    async def start_game_dm(self, user: discord.User):
        """Start or resume game in DM"""
        player = await self.db.load_player(user.id)
        
        if not player:
            # New player
            player = self.game_manager.create_new_player(user.id)
            self.game_manager.generate_shop(player)
            await self.db.save_player(player)
            
            await user.send(
                "🎮 Witaj w **Waffen Tactics**!\n"
                "Kupuj jednostki, buduj drużynę i walcz!"
            )
        else:
            await user.send("Gra wznowiona!")
        
        # Show main menu in DM
        embed = self.create_game_state_embed(player)
        view = GameView(self, user.id)
        await user.send(embed=embed, view=view)
    
    async def start_game(self, interaction: discord.Interaction):
        """Start or resume game (legacy, used internally)"""
        player = await self.db.load_player(interaction.user.id)
        
        if not player:
            # New player
            player = self.game_manager.create_new_player(interaction.user.id)
            self.game_manager.generate_shop(player)
            await self.db.save_player(player)
            
            await interaction.response.send_message(
                "🎮 Witaj w **Waffen Tactics**!\n"
                "Kupuj jednostki, buduj drużynę i walcz!",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("Gra wznowiona!", ephemeral=True)
        
        # Show main menu
        await self.show_main_menu(interaction, edit=False)
    
    async def show_main_menu(self, interaction: discord.Interaction, edit: bool = True):
        """Show main game menu"""
        player = await self.db.load_player(interaction.user.id)
        if not player:
            # Check if this is a DM context
            if isinstance(interaction.channel, discord.DMChannel):
                if interaction.response.is_done():
                    await interaction.followup.send("Użyj `/graj` na serwerze aby rozpocząć!", ephemeral=True)
                else:
                    await interaction.response.send_message("Użyj `/graj` na serwerze aby rozpocząć!", ephemeral=True)
            else:
                if interaction.response.is_done():
                    await interaction.followup.send("Użyj `/graj` aby rozpocząć!", ephemeral=True)
                else:
                    await interaction.response.send_message("Użyj `/graj` aby rozpocząć!", ephemeral=True)
            return
        
        embed = self.create_game_state_embed(player)
        view = GameView(self, interaction.user.id)
        
        # Always use edit for button callbacks (response is already done)
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            # For slash commands or initial responses
            if edit:
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                # Check if we can send to DM
                try:
                    await interaction.user.send(embed=embed, view=view)
                    if not isinstance(interaction.channel, discord.DMChannel):
                        await interaction.followup.send("✅ Wysłałem menu gry na DM!", ephemeral=True)
                except (discord.Forbidden, AttributeError):
                    # Fallback to channel if DM fails
                    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    async def show_shop(self, interaction: discord.Interaction):
        """Show shop interface"""
        player = await self.db.load_player(interaction.user.id)
        if not player:
            return
        
        # Generate shop if needed
        if not player.last_shop:
            self.game_manager.generate_shop(player)
            await self.db.save_player(player)
        
        embed = self.create_shop_embed(player)
        view = ShopView(self, interaction.user.id, player.last_shop)
        
        # Use edit if interaction already responded (from button), otherwise send
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def show_bench(self, interaction: discord.Interaction):
        """Show bench interface"""
        player = await self.db.load_player(interaction.user.id)
        if not player:
            return
        
        embed = self.create_bench_embed(player)
        view = BenchView(self, interaction.user.id, player.bench)
        
        # Use edit if interaction already responded (from button), otherwise send
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    async def show_board(self, interaction: discord.Interaction):
        """Show board interface"""
        player = await self.db.load_player(interaction.user.id)
        if not player:
            return
        
        embed = self.create_board_embed(player)
        view = BoardView(self, interaction.user.id, player.board)
        
        # Use edit if interaction already responded (from button), otherwise send
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def send_or_edit_simple_message(self, interaction: discord.Interaction, content: str):
        """Send simple message or edit previous one to avoid spam"""
        user_id = interaction.user.id
        
        # Check if we have a previous simple message for this user
        if user_id in self.last_simple_messages:
            try:
                # Try to edit the previous message
                await self.last_simple_messages[user_id].edit(content=content)
                return
            except (discord.NotFound, discord.HTTPException):
                # Message was deleted or can't be edited, send new one
                pass
        
        # Send new message and store it
        msg = await interaction.followup.send(content, ephemeral=True, wait=True)
        self.last_simple_messages[user_id] = msg
    
    async def buy_unit(self, interaction: discord.Interaction, unit_id: str):
        """Handle unit purchase"""
        player = await self.db.load_player(interaction.user.id)
        if not player:
            return
        
        success, message = self.game_manager.buy_unit(player, unit_id)
        await self.db.save_player(player)
        
        # Refresh shop view with updated state
        embed = self.create_shop_embed(player)
        view = ShopView(self, interaction.user.id, player.last_shop)
        
        await interaction.response.edit_message(
            embed=embed, 
            view=view
        )
        
        # Send ephemeral feedback
        await self.send_or_edit_simple_message(interaction, f"{'✅' if success else '❌'} {message}")
    
    async def sell_unit(self, interaction: discord.Interaction, instance_id: str):
        """Handle unit sale from bench"""
        player = await self.db.load_player(interaction.user.id)
        if not player:
            return
        
        success, message = self.game_manager.sell_unit(player, instance_id)
        await self.db.save_player(player)
        
        # Stay in bench view
        embed = self.create_bench_embed(player)
        view = BenchView(self, interaction.user.id, player.bench)
        
        await interaction.response.edit_message(embed=embed, view=view)
        if not success:
            await self.send_or_edit_simple_message(interaction, f"❌ {message}")
    
    async def sell_unit_from_board(self, interaction: discord.Interaction, instance_id: str):
        """Handle unit sale from board"""
        player = await self.db.load_player(interaction.user.id)
        if not player:
            return
        
        success, message = self.game_manager.sell_unit(player, instance_id)
        await self.db.save_player(player)
        
        # Stay in board view
        embed = self.create_board_embed(player)
        view = BoardView(self, interaction.user.id, player.board)
        
        await interaction.response.edit_message(embed=embed, view=view)
        if not success:
            await self.send_or_edit_simple_message(interaction, f"❌ {message}")
    
    async def move_unit_to_board(self, interaction: discord.Interaction, instance_id: str):
        """Move unit from bench to board"""
        bot_logger = logging.getLogger('waffen_tactics')
        bot_logger.info(f"[MOVE_UNIT_TO_BOARD] Starting for user {interaction.user.id}, instance {instance_id}")
        
        player = await self.db.load_player(interaction.user.id)
        if not player:
            bot_logger.error(f"[MOVE_UNIT_TO_BOARD] Player not found for user {interaction.user.id}")
            return
        
        bot_logger.info(f"[MOVE_UNIT_TO_BOARD] Player state - Board: {len(player.board)}/{player.max_board_size}, Bench: {len(player.bench)}/{player.max_bench_size}")
        bot_logger.info(f"[MOVE_UNIT_TO_BOARD] Bench units: {[u.instance_id for u in player.bench]}")
        
        success, message = self.game_manager.move_to_board(player, instance_id)
        bot_logger.info(f"[MOVE_UNIT_TO_BOARD] Result - Success: {success}, Message: {message}")
        
        await self.db.save_player(player)
        bot_logger.info(f"[MOVE_UNIT_TO_BOARD] Player state saved")
        
        # Refresh bench view
        embed = self.create_bench_embed(player)
        view = BenchView(self, interaction.user.id, player.bench)
        
        await interaction.response.edit_message(embed=embed, view=view)
        if not success:
            bot_logger.warning(f"[MOVE_UNIT_TO_BOARD] Failed: {message}")
            await self.send_or_edit_simple_message(interaction, f"❌ {message}")
        else:
            bot_logger.info(f"[MOVE_UNIT_TO_BOARD] Success! New board size: {len(player.board)}")
    
    async def move_unit_to_bench(self, interaction: discord.Interaction, instance_id: str):
        """Move unit from board to bench"""
        bot_logger = logging.getLogger('waffen_tactics')
        bot_logger.info(f"[MOVE_UNIT_TO_BENCH] Starting for user {interaction.user.id}, instance {instance_id}")
        
        player = await self.db.load_player(interaction.user.id)
        if not player:
            bot_logger.error(f"[MOVE_UNIT_TO_BENCH] Player not found for user {interaction.user.id}")
            return
        
        bot_logger.info(f"[MOVE_UNIT_TO_BENCH] Player state - Board: {len(player.board)}/{player.max_board_size}, Bench: {len(player.bench)}/{player.max_bench_size}")
        bot_logger.info(f"[MOVE_UNIT_TO_BENCH] Board units: {[u.instance_id for u in player.board]}")
        
        success, message = self.game_manager.move_to_bench(player, instance_id)
        bot_logger.info(f"[MOVE_UNIT_TO_BENCH] Result - Success: {success}, Message: {message}")
        
        await self.db.save_player(player)
        bot_logger.info(f"[MOVE_UNIT_TO_BENCH] Player state saved")
        
        # Refresh board view
        embed = self.create_board_embed(player)
        view = BoardView(self, interaction.user.id, player.board)
        
        await interaction.response.edit_message(embed=embed, view=view)
        if not success:
            bot_logger.warning(f"[MOVE_UNIT_TO_BENCH] Failed: {message}")
            await self.send_or_edit_simple_message(interaction, f"❌ {message}")
        else:
            bot_logger.info(f"[MOVE_UNIT_TO_BENCH] Success! New bench size: {len(player.bench)}")
    
    async def reroll_shop(self, interaction: discord.Interaction):
        """Reroll shop"""
        player = await self.db.load_player(interaction.user.id)
        if not player:
            return
        
        success, message = self.game_manager.reroll_shop(player)
        await self.db.save_player(player)
        
        if success:
            # Refresh shop view
            embed = self.create_shop_embed(player)
            view = ShopView(self, interaction.user.id, player.last_shop)
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
    
    async def buy_xp(self, interaction: discord.Interaction):
        """Buy XP"""
        player = await self.db.load_player(interaction.user.id)
        if not player:
            return
        
        success, message = self.game_manager.buy_xp(player)
        await self.db.save_player(player)
        
        # Refresh main menu
        embed = self.create_game_state_embed(player)
        view = GameView(self, interaction.user.id)
        
        await interaction.response.edit_message(embed=embed, view=view)
        await self.send_or_edit_simple_message(interaction, f"{'✅' if success else '❌'} {message}")
    
    async def start_combat(self, interaction: discord.Interaction):
        """Start combat round"""
        player = await self.db.load_player(interaction.user.id)
        if not player:
            return
        
        if not player.board:
            await self.send_or_edit_simple_message(interaction, "❌ Nie masz jednostek na planszy!")
            return
        
        msg = await interaction.followup.send("⚔️ Szukam przeciwnika...", ephemeral=True, wait=True)
        self.last_simple_messages[interaction.user.id] = msg
        
        # Get opponent from database (exclude self, match by wins)
        opponent_data = await self.db.get_random_opponent(exclude_user_id=interaction.user.id, player_wins=player.wins)
        
        if not opponent_data:
            await self.send_or_edit_simple_message(interaction, "❌ Brak przeciwników w bazie! Zagraj więcej rund aby zapisać swój zespół.")
            return
        
        # Build opponent units
        opponent_units = []
        for unit_data in opponent_data['board']:
            unit = next((u for u in self.game_data.units if u.id == unit_data['unit_id']), None)
            if unit:
                opponent_units.append(unit)
        
        if not opponent_units:
            await self.send_or_edit_simple_message(interaction, "❌ Błąd ładowania przeciwnika!")
            return
        
        # Show opponent preview
        opponent_embed = self.create_opponent_preview_embed(opponent_data, opponent_units)
        preview_msg = await interaction.followup.send(embed=opponent_embed, ephemeral=True, wait=True)
        
        # Start combat immediately
        combat_embed = discord.Embed(
            title="⚔️ WALKA W TOKU...",
            description="🎬 Obserwuj przebieg walki!",
            color=discord.Color.orange()
        )
        combat_msg = await interaction.followup.send(embed=combat_embed, ephemeral=True, wait=True)
        
        # Run combat with animation
        result = await self.run_combat_with_animation(combat_msg, player, opponent_units, opponent_data)
        
        # Save player's team and update
        board_units = [{'unit_id': ui.unit_id, 'star_level': ui.star_level} for ui in player.board]
        bench_units = [{'unit_id': ui.unit_id, 'star_level': ui.star_level} for ui in player.bench]
        await self.db.save_opponent_team(
            user_id=interaction.user.id,
            nickname=interaction.user.display_name,
            board_units=board_units,
            bench_units=bench_units,
            wins=player.wins,
            losses=player.losses,
            level=player.level
        )
        
        player.round_number += 1
        
        # Award XP and gold based on result
        leveled_up = player.add_xp(2)  # Always +2 XP, handle level up properly
        if result['winner'] == 'player':
            player.gold += 1  # +1g bonus for win
        
        # Calculate interest: 1g per 10g, max 5g
        interest = min(5, player.gold // 10)
        base_income = 5
        total_income = base_income + interest
        player.gold += total_income
        
        self.game_manager.generate_shop(player, force_new=True)
        
        # Check for game over and save to leaderboard
        if player.hp <= 0:
            await self.db.save_to_leaderboard(
                user_id=interaction.user.id,
                nickname=interaction.user.display_name,
                wins=player.wins,
                losses=player.losses,
                level=player.level,
                round_number=player.round_number,
                team_units=player_team
            )
            await self.db.save_player(player)
            
            # Show GAME OVER screen without menu
            game_over_embed = discord.Embed(
                title="💀 GAME OVER",
                description="Twoje HP spadło do 0!",
                color=discord.Color.dark_red()
            )
            game_over_embed.add_field(
                name="📊 Finalne Statystyki",
                value=f"🏆 Wygrane: **{player.wins}**\n"
                      f"💀 Przegrane: **{player.losses}**\n"
                      f"📈 Poziom: **{player.level}**\n"
                      f"🔄 Runda: **{player.round_number}**",
                inline=False
            )
            winrate = int(player.wins / max(player.wins + player.losses, 1) * 100)
            game_over_embed.add_field(
                name="🎯 Winrate",
                value=f"**{winrate}%**",
                inline=True
            )
            game_over_embed.set_footer(text="💾 Twój wynik został zapisany na rankingu!\nUżyj /ranking aby zobaczyć topkę")
            await combat_msg.edit(embed=game_over_embed, view=None)
            
            # Auto-reset after 2 seconds
            await asyncio.sleep(2)
            
            # Delete player data and start fresh
            bot_logger.info(f"[GAME_OVER] Deleting old player data for user {interaction.user.id}")
            await self.db.delete_player(interaction.user.id)
            
            # Show fresh game menu
            bot_logger.info(f"[GAME_OVER] Creating new player for user {interaction.user.id}")
            new_player = self.game_manager.create_new_player(interaction.user.id)
            await self.db.save_player(new_player)
            bot_logger.info(f"[GAME_OVER] New game created successfully")
            
            embed = self.create_game_state_embed(new_player)
            view = GameView(self, interaction.user.id)
            await interaction.followup.send("🎮 **Nowa gra rozpoczęta!**", embed=embed, view=view, ephemeral=True)
            return
        
        await self.db.save_player(player)
        
        # Show final result with game menu
        embed = self.create_combat_result_embed(player, result, opponent_data, interest=interest)
        view = GameView(self, interaction.user.id)
        await combat_msg.edit(embed=embed, view=view)
    
    def create_game_state_embed(self, player: PlayerState) -> discord.Embed:
        """Create main game state embed"""
        embed = discord.Embed(
            title="🎮 Waffen Tactics",
            description=f"🔄 Runda **{player.round_number}** | ❤️ HP: **{player.hp}/100**",
            color=discord.Color.blue()
        )
        
        # Resources - synchronize XP display with shop
        xp_for_next = player.xp_to_next_level
        xp_progress = player.xp if player.level < 10 else 0
        xp_bar_filled = int((xp_progress / max(xp_for_next, 1)) * 10) if xp_for_next > 0 else 0
        xp_bar = "▰" * xp_bar_filled + "▱" * (10 - xp_bar_filled)
        embed.add_field(
            name="💰 Zasoby",
            value=f"Gold: **{player.gold}g**\n"
                  f"Poziom: **{player.level}** (max jednostek: {player.max_board_size})\n"
                  f"XP: {xp_bar} {xp_progress}/{xp_for_next}",
            inline=True
        )
        
        # Stats
        winrate = int(player.wins / max(player.wins + player.losses, 1) * 100)
        streak_emoji = "🔥" if player.streak > 0 else "💀" if player.streak < 0 else "➖"
        embed.add_field(
            name="📊 Statystyki",
            value=f"Wygrane: **{player.wins}** | Przegrane: **{player.losses}**\n"
                  f"Winrate: **{winrate}%**\n"
                  f"Passa: {streak_emoji} **{abs(player.streak)}**",
            inline=True
        )
        
        # Units summary
        total_units = len(player.bench) + len(player.board)
        embed.add_field(
            name="👥 Jednostki",
            value=f"Plansza: **{len(player.board)}/{player.max_board_size}**\n"
                  f"Ławka: **{len(player.bench)}/{player.max_bench_size}**\n"
                  f"Razem: **{total_units}**",
            inline=True
        )
        
        # Synergies with preview
        synergies = self.game_manager.get_board_synergies(player)
        if synergies:
            synergy_lines = []
            for name, (count, tier) in list(synergies.items())[:5]:  # Limit to 5
                synergy_lines.append(f"**{name}** [{count}] T{tier}")
            
            synergy_text = "\n".join(synergy_lines)
            if len(synergies) > 5:
                synergy_text += f"\n... i {len(synergies) - 5} więcej"
            
            embed.add_field(name="✨ Aktywne Synergies", value=synergy_text, inline=False)
        else:
            embed.add_field(name="✨ Synergies", value="Postaw jednostki na planszy!", inline=False)
        
        embed.set_footer(text="💡 Kupuj jednostki w sklepie | Buduj synergies | Walcz z przeciwnikami!")
        return embed
    
    def create_shop_embed(self, player: PlayerState) -> discord.Embed:
        """Create shop embed"""
        # Calculate XP progress
        xp_for_next = player.xp_to_next_level
        xp_progress = player.xp if player.level < 10 else 0
        xp_bar_filled = int((xp_progress / max(xp_for_next, 1)) * 10) if xp_for_next > 0 else 0
        xp_bar = "■" * xp_bar_filled + "□" * (10 - xp_bar_filled)
        
        embed = discord.Embed(
            title="🏪 Sklep",
            description=f"💰 Gold: **{player.gold}g** | 📊 Poziom: **{player.level}**\n"
                        f"XP: **{xp_progress}/{xp_for_next}** {xp_bar}\n"
                        f"🔄 Reroll: **2g** | 📈 +4 XP: **4g**",
            color=discord.Color.gold()
        )
        
        for i, unit_id in enumerate(player.last_shop):
            if unit_id:
                unit = next((u for u in self.game_data.units if u.id == unit_id), None)
                if unit:
                    # Get base stats
                    stats = unit.stats
                    factions = ", ".join(unit.factions)
                    classes = ", ".join(unit.classes)
                    
                    stats_text = f"⚔️ {int(stats.attack)} | ❤️ {int(stats.hp)} | 🛡️ {int(stats.defense)}"
                    traits_text = f"🏴 {factions}\n🎭 {classes}"
                    
                    embed.add_field(
                        name=f"{unit.name} - {unit.cost}g ⭐",
                        value=f"{stats_text}\n{traits_text}",
                        inline=True
                    )
            else:
                embed.add_field(name="—", value="Pusty slot", inline=True)
        
        # Add bench preview
        if player.bench:
            bench_preview = []
            for ui in player.bench[:5]:  # Show first 5
                unit = next((u for u in self.game_data.units if u.id == ui.unit_id), None)
                if unit:
                    stars = '⭐' * ui.star_level
                    bench_preview.append(f"{unit.name} {stars}")
            if bench_preview:
                embed.add_field(
                    name="📦 Ławka ({}/{})".format(len(player.bench), player.max_bench_size),
                    value="\n".join(bench_preview),
                    inline=True
                )
        
        # Add board preview with synergies
        if player.board:
            board_preview = []
            for ui in player.board[:5]:  # Show first 5
                unit = next((u for u in self.game_data.units if u.id == ui.unit_id), None)
                if unit:
                    stars = '⭐' * ui.star_level
                    board_preview.append(f"{unit.name} {stars}")
            if board_preview:
                embed.add_field(
                    name="🎯 Plansza ({}/{})".format(len(player.board), player.max_board_size),
                    value="\n".join(board_preview),
                    inline=True
                )
            
            # Show active synergies
            synergies = self.game_manager.get_board_synergies(player)
            if synergies:
                synergy_lines = []
                for name, (count, tier) in list(synergies.items())[:4]:
                    synergy_lines.append(f"**{name}** [{count}] T{tier}")
                embed.add_field(
                    name="✨ Aktywne Synergies",
                    value="\n".join(synergy_lines),
                    inline=False
                )
        
        embed.set_footer(text="💡 Kup 3 jednostki tego samego typu aby upgrade: ⭐→⭐⭐→⭐⭐⭐")
        return embed
    
    def format_trait_effect(self, effect: dict) -> str:
        """Format trait effect into readable text"""
        bot_logger = logging.getLogger('waffen_tactics')
        
        try:
            eff_type = effect.get('type')
            
            if eff_type == 'stat_buff':
                if 'stat' not in effect:
                    bot_logger.warning(f"[FORMAT_TRAIT] stat_buff without 'stat' field: {effect}")
                    return f"✨ {effect.get('description', 'Buff')}"
                    
                stat_name = effect['stat']
                value = effect.get('value', 0)
                is_pct = effect.get('is_percentage', False)
                stat_emoji = {
                    'attack': '⚔️', 'defense': '🛡️', 'hp': '❤️', 
                    'attack_speed': '⚡', 'mana': '🔮'
                }.get(stat_name, '📊')
                return f"{stat_emoji} +{value}{'%' if is_pct else ''} {stat_name}"
            elif eff_type == 'on_enemy_death':
                stats = ', '.join(effect.get('stats', []))
                value = effect.get('value', 0)
                return f"💀 +{value} {stats} per kill"
            elif eff_type == 'start_of_combat':
                return f"✨ {effect.get('description', 'Special effect')}"
            else:
                # Generic fallback for unknown effect types
                bot_logger.debug(f"[FORMAT_TRAIT] Unknown effect type: {effect}")
                return f"✨ {effect.get('description', str(eff_type))}"
        except Exception as e:
            bot_logger.error(f"[FORMAT_TRAIT] Error formatting effect {effect}: {e}")
            return "✨ Specjalny efekt"
        else:
            return f"🔥 {eff_type}"
    
    def create_bench_embed(self, player: PlayerState) -> discord.Embed:
        """Create bench embed"""
        embed = discord.Embed(
            title="📋 Ławka",
            description=f"Jednostki: **{len(player.bench)}/{player.max_bench_size}** | 💰 Gold: **{player.gold}g**",
            color=discord.Color.greyple()
        )
        
        if player.bench:
            # Count duplicates for upgrade info
            from collections import Counter
            unit_counts = Counter()
            for ui in player.bench:
                unit_counts[(ui.unit_id, ui.star_level)] += 1
            
            for ui in player.bench:
                unit = next((u for u in self.game_data.units if u.id == ui.unit_id), None)
                if unit:
                    stars = '⭐' * ui.star_level
                    # Calculate stats based on star level
                    multiplier = ui.star_level
                    stats = unit.stats
                    atk = int(stats.attack * multiplier)
                    hp = int(stats.hp * multiplier)
                    defense = int(stats.defense * multiplier)
                    
                    stats_text = f"⚔️{atk} ❤️{hp} 🛡️{defense}"
                    sell_value = unit.cost * ui.star_level
                    
                    # Show upgrade hint
                    count = unit_counts[(ui.unit_id, ui.star_level)]
                    upgrade_hint = f" ({count}/3 do ⭐⭐)" if ui.star_level < 3 and count >= 2 else ""
                    
                    # Show traits
                    factions = ", ".join(unit.factions[:2]) if unit.factions else "-"
                    classes = ", ".join(unit.classes[:2]) if unit.classes else "-"
                    traits_text = f"🏴 {factions}\n🎭 {classes}"
                    
                    embed.add_field(
                        name=f"{unit.name} {stars}{upgrade_hint}",
                        value=f"{stats_text}\n{traits_text}\n💰 {sell_value}g",
                        inline=True
                    )
        else:
            embed.add_field(name="Pusta ławka", value="Kup jednostki w sklepie!", inline=False)
        
        # Show potential synergies from bench
        if player.bench:
            from collections import Counter
            faction_counts = Counter()
            class_counts = Counter()
            
            for ui in player.bench:
                unit = next((u for u in self.game_data.units if u.id == ui.unit_id), None)
                if unit:
                    for faction in unit.factions:
                        faction_counts[faction] += 1
                    for cls in unit.classes:
                        class_counts[cls] += 1
            
            trait_lines = []
            for name, count in list(faction_counts.items())[:3]:
                trait_lines.append(f"🏴 **{name}**: {count}x")
            for name, count in list(class_counts.items())[:3]:
                trait_lines.append(f"🎭 **{name}**: {count}x")
            
            if trait_lines:
                embed.add_field(
                    name="📊 Traity na Ławce",
                    value="\n".join(trait_lines[:5]),
                    inline=False
                )
        
        # Add board preview with active synergies
        if player.board:
            board_preview = []
            for ui in player.board[:5]:  # Show first 5
                unit = next((u for u in self.game_data.units if u.id == ui.unit_id), None)
                if unit:
                    stars = '⭐' * ui.star_level
                    board_preview.append(f"{unit.name} {stars}")
            if board_preview:
                embed.add_field(
                    name="🎯 Plansza ({}/{})".format(len(player.board), player.max_board_size),
                    value="\n".join(board_preview),
                    inline=True
                )
            
            # Show active synergies
            synergies = self.game_manager.get_board_synergies(player)
            if synergies:
                synergy_lines = []
                for name, (count, tier) in list(synergies.items())[:4]:
                    synergy_lines.append(f"**{name}** [{count}] T{tier}")
                embed.add_field(
                    name="✨ Aktywne Synergies",
                    value="\n".join(synergy_lines),
                    inline=True
                )
        
        embed.set_footer(text="💡 Wybierz jednostkę z listy, potem użyj przycisków")
        return embed
    
    def create_board_embed(self, player: PlayerState) -> discord.Embed:
        """Create board embed"""
        embed = discord.Embed(
            title="⚔️ Plansza Bojowa",
            description=f"Jednostki: **{len(player.board)}/{player.max_board_size}** | 💰 Gold: **{player.gold}g**",
            color=discord.Color.red()
        )
        
        if player.board:
            # Calculate total power
            total_hp = 0
            total_atk = 0
            
            for ui in player.board:
                unit = next((u for u in self.game_data.units if u.id == ui.unit_id), None)
                if unit:
                    stars = '⭐' * ui.star_level
                    multiplier = ui.star_level
                    stats = unit.stats
                    atk = int(stats.attack * multiplier)
                    hp = int(stats.hp * multiplier)
                    defense = int(stats.defense * multiplier)
                    
                    total_hp += hp
                    total_atk += atk
                    
                    factions = ", ".join(unit.factions[:2]) if unit.factions else "-"
                    classes = ", ".join(unit.classes[:2]) if unit.classes else "-"
                    
                    embed.add_field(
                        name=f"{unit.name} {stars}",
                        value=f"⚔️{atk} ❤️{hp} 🛡️{defense}\n🏴 {factions}\n🎭 {classes}",
                        inline=True
                    )
            
            embed.add_field(
                name="📊 Łączna Siła",
                value=f"⚔️ Atak: **{total_atk}**\n❤️ HP: **{total_hp}**",
                inline=False
            )
        else:
            embed.add_field(name="Pusta plansza", value="Przenieś jednostki z ławki!", inline=False)
        
        # Add bench preview
        if player.bench:
            bench_preview = []
            for ui in player.bench[:5]:  # Show first 5
                unit = next((u for u in self.game_data.units if u.id == ui.unit_id), None)
                if unit:
                    stars = '⭐' * ui.star_level
                    bench_preview.append(f"{unit.name} {stars}")
            if bench_preview:
                embed.add_field(
                    name="📦 Ławka ({}/{})".format(len(player.bench), player.max_bench_size),
                    value="\n".join(bench_preview),
                    inline=True
                )
        
        # Synergies with detailed effects
        synergies = self.game_manager.get_board_synergies(player)
        if synergies:
            synergy_lines = []
            for name, (count, tier) in synergies.items():
                # Get trait info
                trait = next((t for t in self.game_data.traits if t["name"] == name), None)
                if trait:
                    thresholds = trait["thresholds"]
                    next_threshold = None
                    for t in thresholds:
                        if count < t:
                            next_threshold = t
                            break
                    
                    threshold_text = f" → {next_threshold}" if next_threshold else " ✅"
                    
                    # Get current tier effect
                    effect_text = ""
                    if tier > 0 and tier <= len(trait.get('effects', [])):
                        effect = trait['effects'][tier - 1]
                        effect_text = f"\n  ➡️ {self.format_trait_effect(effect)}"
                    
                    synergy_lines.append(f"**{name}** [{count}]{threshold_text}{effect_text}")
            
            embed.add_field(
                name="✨ Aktywne Synergies",
                value="\n".join(synergy_lines) if synergy_lines else "Brak aktywnych",
                inline=False
            )
        else:
            embed.add_field(
                name="✨ Synergies",
                value="Brak - postaw więcej jednostek tej samej frakcji/klasy!",
                inline=False
            )
        
        embed.set_footer(text="💡 Postaw jednostki strategicznie. Synergies wzmacniają całą drużynę!")
        return embed
    
    async def run_combat_with_animation(self, message, player: PlayerState, opponent_units: list, opponent_data: dict) -> dict:
        """Run combat with live animation updates"""
        import asyncio
        
        # Build player units
        player_units = []
        for ui in player.board:
            unit = next((u for u in self.game_data.units if u.id == ui.unit_id), None)
            if unit:
                player_units.append(unit)
        
        # Start combat
        result = self.game_manager.start_combat(player, opponent_units)
        
        # Parse combat log for key events
        log_lines = result.get('log', [])
        
        # Safety: if no logs, create minimal progress
        if not log_lines:
            log_lines = ["Walka rozpoczęta", "Jednostki walczą...", "Walka zakończona"]
        
        # Show combat progress every ~20 lines
        update_interval = max(1, len(log_lines) // 5)
        
        for i in range(0, len(log_lines), update_interval):
            progress = min(100, int((i / len(log_lines)) * 100))
            current_time = i * 0.1  # Approximate time
            
            # Get recent events
            recent_events = log_lines[max(0, i-5):i]
            events_text = "\n".join([f"• {line}" for line in recent_events[-5:]])
            
            embed = discord.Embed(
                title=f"⚔️ Walka vs {opponent_data['nickname']}",
                description=f"🔥 **Walka w toku...** {progress}%",
                color=discord.Color.orange()
            )
            
            embed.add_field(
                name="📊 Postęp",
                value=f"Czas: **{current_time:.1f}s** / {result.get('duration', 120):.1f}s",
                inline=False
            )
            
            if events_text:
                embed.add_field(
                    name="📣 Ostatnie Zdarzenia",
                    value=events_text[:1000],  # Discord limit
                    inline=False
                )
            
            try:
                await message.edit(embed=embed)
                await asyncio.sleep(0.5)  # Small delay between updates
            except:
                pass  # Ignore edit errors
        
        return result
    
    def create_opponent_preview_embed(self, opponent_data: dict, opponent_units: list) -> discord.Embed:
        """Create opponent preview embed"""
        embed = discord.Embed(
            title=f"⚔️ Przeciwnik: {opponent_data['nickname']}",
            description=f"🏆 Wygrane: **{opponent_data['wins']}** | 📊 Poziom: **{opponent_data['level']}**",
            color=discord.Color.orange()
        )
        
        # Show opponent units
        for unit_info in opponent_data['team']:
            unit = next((u for u in opponent_units if u.id == unit_info['unit_id']), None)
            if unit:
                stars = '⭐' * unit_info['star_level']
                multiplier = unit_info['star_level']
                stats = unit.stats
                atk = int(stats.attack * multiplier)
                hp = int(stats.hp * multiplier)
                defense = int(stats.defense * multiplier)
                
                embed.add_field(
                    name=f"{unit.name} {stars}",
                    value=f"⚔️{atk} ❤️{hp} 🛡️{defense}",
                    inline=True
                )
        
        embed.set_footer(text="🎮 Rozpoczynam walkę...")
        return embed
    
    def create_profile_embed(self, player: PlayerState) -> discord.Embed:
        """Create profile embed"""
        embed = discord.Embed(
            title="👤 Profil Gracza",
            color=discord.Color.purple()
        )
        
        embed.add_field(name="Poziom", value=str(player.level), inline=True)
        embed.add_field(name="HP", value=str(player.hp), inline=True)
        embed.add_field(name="Gold", value=f"{player.gold}g", inline=True)
        
        embed.add_field(name="Runda", value=str(player.round_number), inline=True)
        embed.add_field(name="Wygrane", value=str(player.wins), inline=True)
        embed.add_field(name="Przegrane", value=str(player.losses), inline=True)
        
        return embed
    
    def create_combat_result_embed(self, player: PlayerState, result: dict, opponent_data: dict = None, interest: int = 0) -> discord.Embed:
        """Create combat result embed"""
        won = result['winner'] == 'player'
        
        title = "⚔️ Wynik Walki"
        if opponent_data:
            title += f" vs {opponent_data['nickname']}"
        
        embed = discord.Embed(
            title=title,
            description="🎉 WYGRANA!" if won else "💀 PRZEGRANA",
            color=discord.Color.green() if won else discord.Color.red()
        )
        
        # Combat stats
        duration = result.get('duration', 0)
        survivors_a = result.get('team_a_survivors', 0)
        survivors_b = result.get('team_b_survivors', 0)
        
        embed.add_field(
            name="📊 Statystyki Walki",
            value=f"Czas: **{duration:.1f}s**\n"
                  f"Twoi ocaleni: **{survivors_a}**\n"
                  f"Przeciwnik: **{survivors_b}**",
            inline=True
        )
        
        embed.add_field(name="HP", value=f"{player.hp} ❤️", inline=True)
        
        # Show damage only if player actually took damage (lost)
        if not won and result.get('damage_taken', 0) > 0:
            embed.add_field(name="Obrażenia", value=f"-{result['damage_taken']} ❤️", inline=True)
        
        embed.add_field(name="Passa", value=str(player.streak), inline=True)
        embed.add_field(name="Bilans", value=f"{player.wins}W - {player.losses}L", inline=True)
        
        # Show income breakdown with interest
        income_text = f"+5g (base)"
        if interest > 0:
            income_text += f"\n+{interest}g (interest)"
        income_text += f"\n= **{player.gold}g** total"
        embed.add_field(name="💰 Dochód", value=income_text, inline=True)
        
        # Show combat log summary (last 15 events)
        log_lines = result.get('log', [])
        if log_lines:
            # Take last 15 lines or all if less
            summary_lines = log_lines[-15:]
            log_text = "\n".join([f"• {line}" for line in summary_lines])
            embed.add_field(
                name="📜 Przebieg Walki (ostatnie zdarzenia)",
                value=log_text[:1024],  # Discord field limit
                inline=False
            )
        
        if player.hp <= 0:
            embed.add_field(
                name="💀 GAME OVER",
                value="Twoja drużyna została pokonana! Użyj `/reset` aby rozpocząć od nowa.",
                inline=False
            )
        
        return embed
    
    def run(self):
        """Run the bot"""
        self.client.run(self.token)


if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    
    if not TOKEN:
        print("❌ Brak DISCORD_BOT_TOKEN w zmiennych środowiskowych!")
        print("Ustaw token: export DISCORD_BOT_TOKEN='twoj_token'")
        exit(1)
    
    bot = WaffenTacticsBot(TOKEN)
    bot.run()
