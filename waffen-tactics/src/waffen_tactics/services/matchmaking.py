import random
from typing import List
from waffen_tactics.models.player import TeamSnapshot

class MatchmakingService:
    def __init__(self, snapshots: List[TeamSnapshot]):
        self.snapshots = snapshots

    def find_opponent(self, wins: int, rounds: int) -> TeamSnapshot:
        # Simple banding: select snapshot with closest (wins, rounds)
        def score(s: TeamSnapshot):
            return abs(s.wins - wins) 
        candidates = sorted(self.snapshots, key=score)
        return candidates[0] if candidates else random.choice(self.snapshots) if self.snapshots else None
