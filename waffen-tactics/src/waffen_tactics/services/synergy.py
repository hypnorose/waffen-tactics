from collections import Counter
from typing import Dict, List, Tuple
from waffen_tactics.models.unit import Unit

class SynergyEngine:
    def __init__(self, traits: List[Dict]):
        self.thresholds: Dict[str, List[int]] = {}
        self.trait_effects: Dict[str, List[Dict]] = {}
        for t in traits:
            name = t["name"]
            self.thresholds[name] = list(t.get("thresholds", []))
            self.trait_effects[name] = t.get("effects", [])

    def compute(self, units: List[Unit]) -> Dict[str, Tuple[int, int]]:
        # Count unique units only (by unit.id)
        seen_ids = set()
        unique_units = []
        for u in units:
            if u.id not in seen_ids:
                seen_ids.add(u.id)
                unique_units.append(u)
        
        counts = Counter()
        for u in unique_units:
            for f in u.factions:
                counts[f] += 1
            for c in u.classes:
                counts[c] += 1
        
        active: Dict[str, Tuple[int, int]] = {}
        for trait, n in counts.items():
            th = self.thresholds.get(trait, [])
            if not th:
                continue
            achieved = 0
            for i, v in enumerate(th, start=1):
                if n >= v:
                    achieved = i
                else:
                    break
            if achieved > 0:
                active[trait] = (n, achieved)
        return active
