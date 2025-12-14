"""Player state models for Discord bot game sessions"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class UnitInstance:
    """A single unit instance owned by player"""
    unit_id: str  # Reference to unit from units.json
    star_level: int = 1  # 1, 2, or 3 stars
    instance_id: Optional[str] = None  # Unique ID for this specific instance
    hp_stacks: int = 0  # DEPRECATED: use persistent_buffs instead
    persistent_buffs: Dict[str, float] = field(default_factory=dict)  # persistent stat buffs accumulated over rounds
    
    def __post_init__(self):
        if self.instance_id is None:
            import uuid
            self.instance_id = str(uuid.uuid4())[:8]


@dataclass
class PlayerState:
    """Complete player state for a game session"""
    user_id: int  # Discord user ID
    username: str = "Player"  # Discord username
    
    # Resources
    gold: int = 10
    level: int = 1
    xp: int = 0
    hp: int = 100
    
    # Units
    bench: List[UnitInstance] = field(default_factory=list)  # Max 9 units
    board: List[UnitInstance] = field(default_factory=list)  # Max based on level
    
    # Progress
    round_number: int = 1
    wins: int = 0
    losses: int = 0
    streak: int = 0
    
    # Game state
    last_shop: List[str] = field(default_factory=list)  # Last 5 unit IDs offered
    shop_rerolls: int = 0
    locked_shop: bool = False
    
    # Timestamps
    created_at: Optional[datetime] = None
    last_played: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_played is None:
            self.last_played = datetime.now()
    
    @property
    def max_board_size(self) -> int:
        """Maximum units allowed on board based on level"""
        return min(1 + self.level, 10)  # Level 1 = 2 units, max 10
    
    @property
    def max_bench_size(self) -> int:
        """Maximum units allowed on bench"""
        return 9
    
    @property
    def xp_to_next_level(self) -> int:
        """XP needed to reach next level"""
        if self.level >= 10:
            return 0
        # Balanced XP progression: 2, 2, 4, 8, 12, 20, 24, 32, 40
        xp_table = [0, 2, 4, 8, 16, 28, 48, 72, 104, 144]
        return xp_table[self.level] if self.level < len(xp_table) else 0
    
    def add_xp(self, amount: int) -> bool:
        """Add XP and return True if leveled up (handles multiple level ups)"""
        if self.level >= 10:
            return False
        
        self.xp += amount
        leveled_up = False
        
        # Handle multiple level ups
        while self.level < 10:
            needed = self.xp_to_next_level
            if needed > 0 and self.xp >= needed:
                self.level += 1
                self.xp -= needed  # Subtract requirement, keep overflow
                leveled_up = True
            else:
                break
        
        return leveled_up
    
    def can_afford(self, cost: int) -> bool:
        """Check if player can afford something"""
        return self.gold >= cost
    
    def spend_gold(self, amount: int) -> bool:
        """Spend gold if possible"""
        if self.can_afford(amount):
            self.gold -= amount
            return True
        return False
    
    def find_matching_units(self, unit_id: str, star_level: int, location: str = 'both') -> List[UnitInstance]:
        """Find all units matching unit_id and star_level"""
        units = []
        if location in ['bench', 'both']:
            units.extend([u for u in self.bench if u.unit_id == unit_id and u.star_level == star_level])
        if location in ['board', 'both']:
            units.extend([u for u in self.board if u.unit_id == unit_id and u.star_level == star_level])
        return units
    
    def can_upgrade_unit(self, unit_id: str, star_level: int) -> bool:
        """Check if player has 3 copies to upgrade"""
        if star_level >= 3:
            return False
        matching = self.find_matching_units(unit_id, star_level)
        return len(matching) >= 3
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'gold': self.gold,
            'level': self.level,
            'xp': self.xp,
            'hp': self.hp,
            'bench': [{'unit_id': u.unit_id, 'star_level': u.star_level, 'instance_id': u.instance_id, 'hp_stacks': getattr(u, 'hp_stacks', 0), 'persistent_buffs': getattr(u, 'persistent_buffs', {})} 
                     for u in self.bench],
            'board': [{'unit_id': u.unit_id, 'star_level': u.star_level, 'instance_id': u.instance_id, 'hp_stacks': getattr(u, 'hp_stacks', 0), 'persistent_buffs': getattr(u, 'persistent_buffs', {})} 
                     for u in self.board],
            'round_number': self.round_number,
            'wins': self.wins,
            'losses': self.losses,
            'streak': self.streak,
            'last_shop': self.last_shop,
            'shop_rerolls': self.shop_rerolls,
            'locked_shop': self.locked_shop,
            'max_board_size': self.max_board_size,
            'max_bench_size': self.max_bench_size,
            'xp_to_next_level': self.xp_to_next_level,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_played': self.last_played.isoformat() if self.last_played else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PlayerState':
        """Create from dictionary"""
        bench = [UnitInstance(**u) for u in data.get('bench', [])]
        board = [UnitInstance(**u) for u in data.get('board', [])]
        
        created_at = None
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])
        
        last_played = None
        if data.get('last_played'):
            last_played = datetime.fromisoformat(data['last_played'])
        
        return cls(
            user_id=data['user_id'],
            username=data.get('username', 'Player'),
            gold=data.get('gold', 10),
            level=data.get('level', 1),
            xp=data.get('xp', 0),
            hp=data.get('hp', 100),
            bench=bench,
            board=board,
            round_number=data.get('round_number', 1),
            wins=data.get('wins', 0),
            losses=data.get('losses', 0),
            streak=data.get('streak', 0),
            last_shop=data.get('last_shop', []),
            shop_rerolls=data.get('shop_rerolls', 0),
            locked_shop=data.get('locked_shop', False),
            created_at=created_at,
            last_played=last_played,
        )
