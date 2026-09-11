"""Database manager for player states"""
import aiosqlite
import json
from typing import Optional, Dict, Callable, Tuple, Any
from pathlib import Path
from ..models.player_state import PlayerState
import datetime


class PlayerActionConflictError(RuntimeError):
    """A player mutation could not obtain a valid serialization boundary."""


class InvalidStoredPlayerStateError(RuntimeError):
    """The database contains a state payload that cannot be decoded safely."""


class DatabaseManager:
    async def get_opponent_team(self, user_id: int) -> Optional[Dict]:
        """Get opponent team by user_id"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT user_id, nickname, team_json, wins, losses, level, avatar FROM opponent_teams WHERE user_id = ? AND is_active = 1 ORDER BY id DESC LIMIT 1", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    team_data = json.loads(row[2])
                    # Handle legacy format
                    if isinstance(team_data, list):
                        team_data = {'board': team_data, 'bench': []}
                    return {
                        'user_id': row[0],
                        'nickname': row[1],
                        'board': team_data['board'],
                        'bench': team_data['bench'],
                        'wins': row[3],
                        'losses': row[4],
                        'level': row[5],
                        'avatar': row[6]
                    }
        return None

    """Manages SQLite database for player states"""
    def __init__(self, db_path: str = "game_data.db"):
        self.db_path = db_path
    
    async def initialize(self):
        """Create tables if they don't exist"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    user_id INTEGER PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS opponent_teams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    nickname TEXT NOT NULL,
                    team_json TEXT NOT NULL,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    avatar TEXT DEFAULT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS leaderboard (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    nickname TEXT NOT NULL,
                    wins INTEGER NOT NULL,
                    losses INTEGER NOT NULL,
                    level INTEGER NOT NULL,
                    round_number INTEGER NOT NULL,
                    team_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await self._ensure_action_results_table(db)
            
            # Migration: Add losses column to opponent_teams if it doesn't exist
            try:
                await db.execute("ALTER TABLE opponent_teams ADD COLUMN losses INTEGER DEFAULT 0")
            except aiosqlite.OperationalError:
                # Column already exists
                pass
            
            # Migration: Add is_active column to opponent_teams if it doesn't exist
            try:
                await db.execute("ALTER TABLE opponent_teams ADD COLUMN is_active BOOLEAN DEFAULT 1")
            except aiosqlite.OperationalError:
                # Column already exists
                pass
            
            # Migration: Add avatar column to opponent_teams if it doesn't exist
            try:
                await db.execute("ALTER TABLE opponent_teams ADD COLUMN avatar TEXT DEFAULT NULL")
            except aiosqlite.OperationalError:
                # Column already exists
                pass
            # Migration: Add avatar_local and avatar_updated_at columns to opponent_teams
            try:
                await db.execute("ALTER TABLE opponent_teams ADD COLUMN avatar_local TEXT DEFAULT NULL")
            except aiosqlite.OperationalError:
                pass
            try:
                await db.execute("ALTER TABLE opponent_teams ADD COLUMN avatar_updated_at TIMESTAMP DEFAULT NULL")
            except aiosqlite.OperationalError:
                pass
            await db.commit()

    @staticmethod
    async def _ensure_action_results_table(db):
        """Create the durable idempotency ledger inside the current transaction."""
        await db.execute("""
            CREATE TABLE IF NOT EXISTS player_action_results (
                user_id INTEGER NOT NULL,
                action_key TEXT NOT NULL,
                action_name TEXT NOT NULL,
                success INTEGER NOT NULL,
                message TEXT NOT NULL,
                state_json TEXT,
                result_id TEXT,
                result_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, action_key)
            )
        """)
        for column, definition in (
            ('result_id', 'TEXT'),
            ('result_json', 'TEXT'),
        ):
            try:
                await db.execute(
                    f"ALTER TABLE player_action_results ADD COLUMN {column} {definition}"
                )
            except aiosqlite.OperationalError:
                pass

    @staticmethod
    def _serialize_player(player: PlayerState) -> str:
        """Serialize and round-trip validate state before it can be committed."""
        try:
            state_json = json.dumps(player.to_dict(), allow_nan=False)
            decoded = json.loads(state_json)
            PlayerState.from_dict(decoded)
            return state_json
        except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise InvalidStoredPlayerStateError(
                f"Player {getattr(player, 'user_id', None)} produced invalid state_json"
            ) from exc

    async def apply_player_action(
        self,
        user_id: int,
        action_name: str,
        mutation: Callable[[PlayerState], Tuple[bool, str]],
        idempotency_key: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[PlayerState]]:
        """Atomically load, mutate, persist, and optionally ledger one player action.

        SQLite's RESERVED write lock serializes all writers to this database,
        including separate worker processes. The idempotency ledger is written
        in the same transaction as the player row, so a retry returns the
        original outcome instead of executing business logic again.
        """
        normalized_key = str(idempotency_key).strip() if idempotency_key else None
        if normalized_key and len(normalized_key) > 200:
            raise PlayerActionConflictError("Idempotency key is too long")

        try:
            async with aiosqlite.connect(self.db_path, timeout=5.0) as db:
                await db.execute("PRAGMA busy_timeout = 5000")
                await db.execute("BEGIN IMMEDIATE")
                await self._ensure_action_results_table(db)

                if normalized_key:
                    async with db.execute(
                        """SELECT action_name, success, message, state_json
                           FROM player_action_results
                           WHERE user_id = ? AND action_key = ?""",
                        (int(user_id), normalized_key),
                    ) as cursor:
                        existing = await cursor.fetchone()
                    if existing:
                        stored_action, success, message, state_json = existing
                        if stored_action != action_name:
                            raise PlayerActionConflictError(
                                f"Idempotency key already belongs to action '{stored_action}'"
                            )
                        cached_player = None
                        if state_json:
                            try:
                                cached_player = PlayerState.from_dict(json.loads(state_json))
                            except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
                                raise InvalidStoredPlayerStateError(
                                    f"Cached result for player {user_id} is invalid"
                                ) from exc
                        await db.commit()
                        return bool(success), message, cached_player

                async with db.execute(
                    "SELECT state_json FROM players WHERE user_id = ?",
                    (int(user_id),),
                ) as cursor:
                    row = await cursor.fetchone()
                if not row:
                    await db.rollback()
                    return False, "No game found", None

                try:
                    player = PlayerState.from_dict(json.loads(row[0]))
                except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
                    raise InvalidStoredPlayerStateError(
                        f"Stored state for player {user_id} is invalid"
                    ) from exc

                success, message = mutation(player)
                state_json = self._serialize_player(player) if success else None
                if success:
                    await db.execute(
                        """UPDATE players
                           SET state_json = ?, updated_at = CURRENT_TIMESTAMP
                           WHERE user_id = ?""",
                        (state_json, int(user_id)),
                    )
                if normalized_key:
                    await db.execute(
                        """INSERT INTO player_action_results
                           (user_id, action_key, action_name, success, message, state_json)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (int(user_id), normalized_key, action_name, int(bool(success)), message, state_json),
                    )
                await db.commit()
                return bool(success), message, player if success else None
        except PlayerActionConflictError:
            raise
        except InvalidStoredPlayerStateError:
            raise
        except aiosqlite.OperationalError as exc:
            if "locked" in str(exc).lower() or "busy" in str(exc).lower():
                raise PlayerActionConflictError(
                    f"Player {user_id} action could not acquire the database lock"
                ) from exc
            raise

    async def apply_player_lifecycle_action(
        self,
        user_id: int,
        action_name: str,
        mutation: Callable[
            [Optional[PlayerState]],
            Tuple[bool, str, Optional[PlayerState], Optional[Dict[str, Any]]],
        ],
        idempotency_key: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[PlayerState]]:
        """Atomically apply start/reset/surrender lifecycle transitions.

        Lifecycle actions can create a missing player and surrender also writes
        a leaderboard row. Keeping both operations inside the same write
        transaction as the player row prevents a stale load/save pair from
        overwriting a concurrent player mutation or recording a duplicate
        surrender on retry.

        ``mutation`` receives the current player, or ``None`` when no player
        exists, and returns ``(success, message, next_player,
        leaderboard_entry)``. The final tuple is deliberately the same shape
        as ``apply_player_action`` so route handlers can share their response
        handling.
        """
        normalized_key = str(idempotency_key).strip() if idempotency_key else None
        if normalized_key and len(normalized_key) > 200:
            raise PlayerActionConflictError("Idempotency key is too long")

        try:
            async with aiosqlite.connect(self.db_path, timeout=5.0) as db:
                await db.execute("PRAGMA busy_timeout = 5000")
                await db.execute("BEGIN IMMEDIATE")
                await self._ensure_action_results_table(db)

                if normalized_key:
                    async with db.execute(
                        """SELECT action_name, success, message, state_json
                           FROM player_action_results
                           WHERE user_id = ? AND action_key = ?""",
                        (int(user_id), normalized_key),
                    ) as cursor:
                        existing = await cursor.fetchone()
                    if existing:
                        stored_action, success, message, state_json = existing
                        if stored_action != action_name:
                            raise PlayerActionConflictError(
                                f"Idempotency key already belongs to action '{stored_action}'"
                            )
                        cached_player = None
                        if state_json:
                            try:
                                cached_player = PlayerState.from_dict(json.loads(state_json))
                            except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
                                raise InvalidStoredPlayerStateError(
                                    f"Cached result for player {user_id} is invalid"
                                ) from exc
                        await db.commit()
                        return bool(success), message, cached_player

                async with db.execute(
                    "SELECT state_json FROM players WHERE user_id = ?",
                    (int(user_id),),
                ) as cursor:
                    row = await cursor.fetchone()

                current_player = None
                if row:
                    try:
                        current_player = PlayerState.from_dict(json.loads(row[0]))
                    except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
                        raise InvalidStoredPlayerStateError(
                            f"Stored state for player {user_id} is invalid"
                        ) from exc

                success, message, next_player, leaderboard_entry = mutation(current_player)
                state_json = self._serialize_player(next_player) if success else None

                if success:
                    if row:
                        await db.execute(
                            """UPDATE players
                               SET state_json = ?, updated_at = CURRENT_TIMESTAMP
                               WHERE user_id = ?""",
                            (state_json, int(user_id)),
                        )
                    else:
                        await db.execute(
                            """INSERT INTO players (user_id, state_json, updated_at)
                               VALUES (?, ?, CURRENT_TIMESTAMP)""",
                            (int(user_id), state_json),
                        )

                    if leaderboard_entry:
                        await db.execute(
                            """INSERT INTO leaderboard
                               (user_id, nickname, wins, losses, level, round_number, team_json)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (
                                int(leaderboard_entry['user_id']),
                                str(leaderboard_entry['nickname']),
                                int(leaderboard_entry['wins']),
                                int(leaderboard_entry['losses']),
                                int(leaderboard_entry['level']),
                                int(leaderboard_entry['round_number']),
                                json.dumps(leaderboard_entry.get('team_units', []), allow_nan=False),
                            ),
                        )

                if normalized_key:
                    await db.execute(
                        """INSERT INTO player_action_results
                           (user_id, action_key, action_name, success, message, state_json)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            int(user_id), normalized_key, action_name,
                            int(bool(success)), message, state_json,
                        ),
                    )
                await db.commit()
                return bool(success), message, next_player if success else None
        except PlayerActionConflictError:
            raise
        except InvalidStoredPlayerStateError:
            raise
        except aiosqlite.OperationalError as exc:
            if "locked" in str(exc).lower() or "busy" in str(exc).lower():
                raise PlayerActionConflictError(
                    f"Player {user_id} lifecycle action could not acquire the database lock"
                ) from exc
            raise

    async def get_player_action_result(
        self,
        user_id: int,
        action_name: str,
        idempotency_key: str,
    ) -> Optional[Dict[str, Any]]:
        """Read a completed idempotent action without opening a write transaction."""
        normalized_key = str(idempotency_key).strip() if idempotency_key else None
        if not normalized_key:
            return None
        async with aiosqlite.connect(self.db_path, timeout=5.0) as db:
            async with db.execute(
                """SELECT action_name, success, message, state_json, result_id, result_json
                   FROM player_action_results
                   WHERE user_id = ? AND action_key = ?""",
                (int(user_id), normalized_key),
            ) as cursor:
                row = await cursor.fetchone()
        if not row:
            return None
        stored_action, success, message, state_json, result_id, result_json = row
        if stored_action != action_name:
            raise PlayerActionConflictError(
                f"Idempotency key already belongs to action '{stored_action}'"
            )
        cached_player = None
        if state_json:
            try:
                cached_player = PlayerState.from_dict(json.loads(state_json))
            except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
                raise InvalidStoredPlayerStateError(
                    f"Cached result for player {user_id} is invalid"
                ) from exc
        parsed_result = None
        if result_json:
            try:
                parsed_result = json.loads(result_json)
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise InvalidStoredPlayerStateError(
                    f"Cached result metadata for player {user_id} is invalid"
                ) from exc
        return {
            'success': bool(success),
            'message': message,
            'player': cached_player,
            'result_id': result_id,
            'result': parsed_result,
        }

    async def commit_player_state_action(
        self,
        user_id: int,
        action_name: str,
        player: PlayerState,
        expected_state_json: Optional[str],
        idempotency_key: Optional[str],
        result_id: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        message: str = 'Action applied',
    ) -> Dict[str, Any]:
        """Commit a complete action result with CAS and durable idempotency.

        The caller computes a result from an earlier snapshot. The compare-and-
        swap predicate prevents that stale snapshot from overwriting another
        mutation. A matching idempotency key is resolved first, so concurrent
        retries return the first committed result instead of executing its
        side effects again.
        """
        normalized_key = str(idempotency_key).strip() if idempotency_key else None
        if normalized_key and len(normalized_key) > 200:
            raise PlayerActionConflictError("Idempotency key is too long")
        state_json = self._serialize_player(player)
        result_json = json.dumps(result, allow_nan=False) if result is not None else None

        try:
            async with aiosqlite.connect(self.db_path, timeout=5.0) as db:
                await db.execute("PRAGMA busy_timeout = 5000")
                await db.execute("BEGIN IMMEDIATE")
                await self._ensure_action_results_table(db)

                if normalized_key:
                    async with db.execute(
                        """SELECT action_name, success, message, state_json, result_id, result_json
                           FROM player_action_results
                           WHERE user_id = ? AND action_key = ?""",
                        (int(user_id), normalized_key),
                    ) as cursor:
                        existing = await cursor.fetchone()
                    if existing:
                        stored_action, success, stored_message, cached_json, stored_result_id, stored_result_json = existing
                        if stored_action != action_name:
                            raise PlayerActionConflictError(
                                f"Idempotency key already belongs to action '{stored_action}'"
                            )
                        cached_player = None
                        if cached_json:
                            try:
                                cached_player = PlayerState.from_dict(json.loads(cached_json))
                            except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
                                raise InvalidStoredPlayerStateError(
                                    f"Cached result for player {user_id} is invalid"
                                ) from exc
                        cached_result = None
                        if stored_result_json:
                            try:
                                cached_result = json.loads(stored_result_json)
                            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                                raise InvalidStoredPlayerStateError(
                                    f"Cached result metadata for player {user_id} is invalid"
                                ) from exc
                        await db.commit()
                        return {
                            'success': bool(success),
                            'message': stored_message,
                            'player': cached_player,
                            'result_id': stored_result_id,
                            'result': cached_result,
                            'committed': False,
                        }

                if expected_state_json is None:
                    cursor = await db.execute(
                        """UPDATE players
                           SET state_json = ?, updated_at = CURRENT_TIMESTAMP
                           WHERE user_id = ?""",
                        (state_json, int(user_id)),
                    )
                else:
                    cursor = await db.execute(
                        """UPDATE players
                           SET state_json = ?, updated_at = CURRENT_TIMESTAMP
                           WHERE user_id = ? AND state_json = ?""",
                        (state_json, int(user_id), expected_state_json),
                    )
                if cursor.rowcount != 1:
                    raise PlayerActionConflictError(
                        f"Player {user_id} changed while action '{action_name}' was running"
                    )

                if normalized_key:
                    await db.execute(
                        """INSERT INTO player_action_results
                           (user_id, action_key, action_name, success, message, state_json, result_id, result_json)
                           VALUES (?, ?, ?, 1, ?, ?, ?, ?)""",
                        (
                            int(user_id), normalized_key, action_name, message,
                            state_json, result_id, result_json,
                        ),
                    )
                await db.commit()
                return {
                    'success': True,
                    'message': message,
                    'player': player,
                    'result_id': result_id,
                    'result': result,
                    'committed': True,
                }
        except PlayerActionConflictError:
            raise
        except InvalidStoredPlayerStateError:
            raise
        except aiosqlite.OperationalError as exc:
            if "locked" in str(exc).lower() or "busy" in str(exc).lower():
                raise PlayerActionConflictError(
                    f"Player {user_id} action could not acquire the database lock"
                ) from exc
            raise
    
    async def save_player(self, player: PlayerState):
        """Atomically save validated player state."""
        state_json = self._serialize_player(player)
        
        async with aiosqlite.connect(self.db_path, timeout=5.0) as db:
            await db.execute("PRAGMA busy_timeout = 5000")
            await db.execute("BEGIN IMMEDIATE")
            await db.execute("""
                INSERT INTO players (user_id, state_json, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    state_json = excluded.state_json,
                    updated_at = CURRENT_TIMESTAMP
            """, (player.user_id, state_json))
            await db.commit()
    
    async def load_player(self, user_id: int) -> Optional[PlayerState]:
        """Load player state by user ID"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT state_json FROM players WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    try:
                        data = json.loads(row[0])
                        return PlayerState.from_dict(data)
                    except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
                        raise InvalidStoredPlayerStateError(
                            f"Stored state for player {user_id} is invalid"
                        ) from exc
        return None
    
    async def delete_player(self, user_id: int):
        """Delete player state"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM players WHERE user_id = ?", (user_id,))
            await db.commit()
    
    async def list_all_players(self):
        """Load all players from database"""
        players = []
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT state_json FROM players") as cursor:
                async for row in cursor:
                    data = json.loads(row[0])
                    players.append(PlayerState.from_dict(data))
        return players
    
    async def save_to_leaderboard(self, user_id: int, nickname: str, wins: int, losses: int, level: int, round_number: int, team_units: list):
        """Save final game result to leaderboard"""
        team_json = json.dumps(team_units)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO leaderboard (user_id, nickname, wins, losses, level, round_number, team_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, nickname, wins, losses, level, round_number, team_json))
            await db.commit()
    
    async def get_leaderboard(self, limit: int = 10, period: Optional[str] = '24h') -> list:
        """Get top players from leaderboard table.

        period: '24h' (default) or 'all'. When '24h', only rows with created_at
        within the last 24 hours are returned.
        """
        async with aiosqlite.connect(self.db_path) as db:
            if period is None or period == 'all':
                async with db.execute("""
                    SELECT nickname, wins, losses, level, round_number, created_at
                    FROM leaderboard
                    ORDER BY wins DESC, round_number DESC
                    LIMIT ?
                """, (limit,)) as cursor:
                    rows = await cursor.fetchall()
                    return rows
            # default: last 24 hours
            cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
            cutoff_str = cutoff.strftime('%Y-%m-%d %H:%M:%S')
            async with db.execute("""
                SELECT nickname, wins, losses, level, round_number, created_at
                FROM leaderboard
                WHERE created_at >= ?
                ORDER BY wins DESC, round_number DESC
                LIMIT ?
            """, (cutoff_str, limit)) as cursor:
                rows = await cursor.fetchall()
                return rows
    
    async def has_system_opponents(self) -> bool:
        """Check whether the active system-opponent pool is populated."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM opponent_teams WHERE user_id <= 100000 AND is_active = 1") as cursor:
                row = await cursor.fetchone()
                return row[0] >= 15 if row else False
    
    async def save_opponent_team(self, user_id: int, nickname: str, board_units: list, bench_units: list, wins: int, losses: int, level: int, avatar: Optional[str] = None):
        """Save team snapshot - keeps history of all teams"""
        team_json = json.dumps({'board': board_units, 'bench': bench_units})
        
        async with aiosqlite.connect(self.db_path) as db:
            # Don't delete - just insert new entry for history
            # Only delete old system bots (1-100) to keep them at 1 entry each
            if user_id <= 100:
                await db.execute("DELETE FROM opponent_teams WHERE user_id = ?", (user_id,))
            
            # Insert new team
            await db.execute("INSERT INTO opponent_teams (user_id, nickname, team_json, wins, losses, level, avatar) VALUES (?, ?, ?, ?, ?, ?, ?)", (user_id, nickname, team_json, wins, losses, level, avatar))
            await db.commit()
            
            # Deactivate old teams after saving new one
            await self.deactivate_old_teams()
    
    async def reset_leaderboard(self):
        """Reset leaderboard by deleting all entries"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM leaderboard")
            await db.commit()

    async def reset_opponent_teams(self):
        """Reset opponent teams by deleting all entries"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM opponent_teams")
            await db.commit()
    
    async def deactivate_old_teams(self):
        """Deactivate old teams - for each round count, keep only 10 newest active teams"""
        async with aiosqlite.connect(self.db_path) as db:
            # For each distinct round count (wins + losses), keep only 10 newest teams active
            await db.execute("""
                WITH ranked_teams AS (
                    SELECT id, (wins + losses) as total_rounds,
                           ROW_NUMBER() OVER (PARTITION BY (wins + losses) ORDER BY created_at DESC) as rn
                    FROM opponent_teams
                    WHERE is_active = 1
                )
                UPDATE opponent_teams
                SET is_active = 0
                WHERE id IN (
                    SELECT id FROM ranked_teams WHERE rn > 10
                )
            """)
            await db.commit()
    
    async def get_random_opponent(self, exclude_user_id: Optional[int] = None, player_wins: int = 0, player_rounds: int = 0, player_level: int = 1) -> Optional[Dict]:
        """Get opponent team - prefer real players close by rounds, else system bots.

        Tries several round-difference windows (1,3,5) to improve matchmaking
        before falling back to system opponents.
        """
        async with aiosqlite.connect(self.db_path) as db:

            def _build_from_row(row):
                if not row:
                    return None
                team_json_idx = None
                for i, val in enumerate(row):
                    if isinstance(val, str):
                        s = val.strip()
                        if s.startswith('{') or s.startswith('['):
                            team_json_idx = i
                            break

                if team_json_idx is None:
                    team_json_idx = 2 if len(row) > 2 and isinstance(row[2], str) else 1

                nickname_idx = team_json_idx - 1 if team_json_idx - 1 >= 0 else 0

                def _safe(idx):
                    return row[idx] if 0 <= idx < len(row) else None

                nickname = _safe(nickname_idx)
                user_id = _safe(0) if isinstance(_safe(0), int) and nickname_idx != 0 else _safe(0)
                team_json_val = _safe(team_json_idx)
                try:
                    team_data = json.loads(team_json_val) if isinstance(team_json_val, str) else {'board': [], 'bench': []}
                    if isinstance(team_data, list):
                        team_data = {'board': team_data, 'bench': []}
                except Exception:
                    team_data = {'board': [], 'bench': []}

                return {
                    'user_id': user_id,
                    'nickname': nickname,
                    'board': team_data.get('board', []),
                    'bench': team_data.get('bench', []),
                    'wins': _safe(team_json_idx + 1) or 0,
                    'losses': _safe(team_json_idx + 2) or 0,
                    'level': _safe(team_json_idx + 3) or 1,
                    'avatar': _safe(team_json_idx + 4),
                    'avatar_local': _safe(team_json_idx + 5)
                }

            row = None

            async def try_real(delta: int, exclude: Optional[int] = None):
                if exclude is not None:
                    count_q = """
                        SELECT COUNT(*) FROM opponent_teams
                        WHERE user_id != ? AND user_id > 100000 AND is_active = 1
                        AND ABS((wins + losses) - ?) <= ?
                    """
                    async with db.execute(count_q, (exclude, player_rounds, delta)) as cursor:
                        cnt = await cursor.fetchone()
                    if not cnt or cnt[0] == 0:
                        return None
                    sel_q = """
                        SELECT user_id, nickname, team_json, wins, losses, level, avatar, avatar_local
                        FROM opponent_teams
                        WHERE user_id != ? AND user_id > 100000 AND is_active = 1 AND ABS((wins + losses) - ?) <= ?
                        ORDER BY ABS((wins + losses) - ?) ASC, RANDOM()
                        LIMIT 1
                    """
                    async with db.execute(sel_q, (exclude, player_rounds, delta, player_rounds)) as cursor:
                        return await cursor.fetchone()
                else:
                    count_q = """
                        SELECT COUNT(*) FROM opponent_teams
                        WHERE user_id > 100000 AND is_active = 1 AND ABS((wins + losses) - ?) <= ?
                    """
                    async with db.execute(count_q, (player_rounds, delta)) as cursor:
                        cnt = await cursor.fetchone()
                    if not cnt or cnt[0] == 0:
                        return None
                    sel_q = """
                        SELECT user_id, nickname, team_json, wins, losses, level, avatar, avatar_local
                        FROM opponent_teams
                        WHERE user_id > 100000 AND is_active = 1 AND ABS((wins + losses) - ?) <= ?
                        ORDER BY ABS((wins + losses) - ?) ASC, RANDOM()
                        LIMIT 1
                    """
                    async with db.execute(sel_q, (player_rounds, delta, player_rounds)) as cursor:
                        return await cursor.fetchone()

            # Try progressively wider windows for real players
            for delta in (1, 3, 5):
                row = await try_real(delta, exclude_user_id)
                if row:
                    break

            if not row:
                # Fall back to the active system-opponent pool.
                async with db.execute(
                    """
                    SELECT user_id, nickname, team_json, wins, losses, level, avatar, avatar_local
                    FROM opponent_teams
                    WHERE user_id <= 100000 AND is_active = 1 {exclude_clause}
                    ORDER BY ABS((wins + losses) - ?) ASC, RANDOM()
                    LIMIT 1
                    """.format(exclude_clause="AND user_id != ?" if exclude_user_id is not None else ""),
                    (player_rounds, ) if exclude_user_id is None else (exclude_user_id, player_rounds)
                ) as cursor:
                    # Note: parameter order for the exclude case is (exclude_user_id, player_rounds)
                    # because the WHERE clause ? comes before the ORDER BY ? in the query
                    row = await cursor.fetchone()

            return _build_from_row(row)

    async def get_random_system_opponent(self, player_rounds: int = 0, player_level: int = 1) -> Optional[Dict]:
        """Select an active system opponent (user_id <= 100000).

        This mirrors the selection logic used by the combat service, which
        expects a dedicated method to fetch system opponents.
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT user_id, nickname, team_json, wins, losses, level, avatar, avatar_local
                FROM opponent_teams
                WHERE user_id <= 100000 AND is_active = 1
                ORDER BY ABS((wins + losses) - ?) ASC, RANDOM()
                LIMIT 1
                """,
                (player_rounds,)
            ) as cursor:
                row = await cursor.fetchone()

        # Reuse parsing logic: build dict from row
        if not row:
            return None

        team_json_idx = None
        for i, val in enumerate(row):
            if isinstance(val, str):
                s = val.strip()
                if s.startswith('{') or s.startswith('['):
                    team_json_idx = i
                    break

        if team_json_idx is None:
            team_json_idx = 2 if len(row) > 2 and isinstance(row[2], str) else 1

        def _safe(idx):
            return row[idx] if 0 <= idx < len(row) else None

        nickname_idx = team_json_idx - 1 if team_json_idx - 1 >= 0 else 0
        nickname = _safe(nickname_idx)
        user_id = _safe(0) if isinstance(_safe(0), int) and nickname_idx != 0 else _safe(0)
        team_json_val = _safe(team_json_idx)
        try:
            team_data = json.loads(team_json_val) if isinstance(team_json_val, str) else {'board': [], 'bench': []}
            if isinstance(team_data, list):
                team_data = {'board': team_data, 'bench': []}
        except Exception:
            team_data = {'board': [], 'bench': []}

        return {
            'user_id': user_id,
            'nickname': nickname,
            'board': team_data.get('board', []),
            'bench': team_data.get('bench', []),
            'wins': _safe(team_json_idx + 1) or 0,
            'losses': _safe(team_json_idx + 2) or 0,
            'level': _safe(team_json_idx + 3) or 1,
            'avatar': _safe(team_json_idx + 4),
            'avatar_local': _safe(team_json_idx + 5)
        }

    async def set_opponent_avatar_local(self, user_id: int, avatar_local: str):
        """Set the local avatar filename for opponent_teams entries matching user_id."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE opponent_teams SET avatar_local = ?, avatar_updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", (avatar_local, user_id))
            await db.commit()
    
    async def add_sample_teams(self, units: list):
        """Seed system opponents from the shared deterministic definitions."""
        from .encounter_definitions import build_system_opponent_payloads

        for payload in build_system_opponent_payloads(units):
            await self.save_opponent_team(**payload)
