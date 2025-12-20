"""
Simple genetic algorithm to search for a strong 10v10 team (all 2-star).

Usage:
  python experiments/genetic_search.py --pop 30 --gens 20 --eval-games 8

Notes:
- Uses the project's `run_combat_simulation` and `load_game_data`.
- No external GA lib required.
"""
import os
import sys
import random
import json
import argparse
from copy import deepcopy
from statistics import mean, median

# Make engine imports work when running from repo root
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, 'waffen-tactics', 'src'))
# Ensure the backend services package is importable
sys.path.insert(0, os.path.join(ROOT, 'waffen-tactics-web', 'backend'))

from waffen_tactics.services.data_loader import load_game_data
from waffen_tactics.services.combat_shared import CombatUnit
from services.combat_service import run_combat_simulation

# Genetic algorithm hyperparams (defaults)
POP_SIZE = 30
GENERATIONS = 15
TEAM_SIZE = 10
EVAL_GAMES = 6
TOURNAMENT_K = 3
MUTATION_RATE = 0.5
CROSSOVER_RATE = 0.8

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'best_teams.json')


def make_unit_from_template(unit_template, star_level=2, position='front'):
    return CombatUnit(
        id=unit_template.id,
        name=unit_template.name,
        hp=unit_template.stats.hp,
        attack=unit_template.stats.attack,
        defense=unit_template.stats.defense,
        attack_speed=unit_template.stats.attack_speed,
        position=position,
        stats=unit_template.stats,
        skill=unit_template.skill,
        max_mana=unit_template.stats.max_mana,
        star_level=star_level
    )


class GeneticSearch:
    def __init__(self, game_data, population_size=POP_SIZE):
        self.game_data = game_data
        # pool of unit templates
        self.pool = list(game_data.units)
        self.population_size = population_size
        self.population = []  # list of individuals: list of unit ids

    def random_individual(self):
        # choose TEAM_SIZE unique units (if pool smaller, allow duplicates)
        if len(self.pool) >= TEAM_SIZE:
            chosen = random.sample(self.pool, TEAM_SIZE)
        else:
            chosen = [random.choice(self.pool) for _ in range(TEAM_SIZE)]
        return [u.id for u in chosen]

    def init_population(self):
        self.population = [self.random_individual() for _ in range(self.population_size)]

    def build_team(self, individual):
        # return list[CombatUnit] with star_level=2; first 5 front, rest back
        units = []
        for i, uid in enumerate(individual):
            template = next(u for u in self.pool if u.id == uid)
            pos = 'front' if i < 5 else 'back'
            units.append(make_unit_from_template(template, star_level=2, position=pos))
        return units

    def random_opponent(self):
        # sample a random opponent team from pool
        if len(self.pool) >= TEAM_SIZE:
            chosen = random.sample(self.pool, TEAM_SIZE)
        else:
            chosen = [random.choice(self.pool) for _ in range(TEAM_SIZE)]
        units = []
        for i, u in enumerate(chosen):
            pos = 'front' if i < 5 else 'back'
            units.append(make_unit_from_template(u, star_level=2, position=pos))
        return units

    def evaluate(self, individual, n_games=EVAL_GAMES, seed_base=None):
        # return average win rate (0..1)
        def _is_win(res):
            """Return True if team_a won according to result dict or events."""
            winner = res.get('winner')
            if winner is not None:
                w = str(winner).lower()
                return (w in ('team_a', 'a', 'player') or w.startswith('team_a'))

            events = res.get('events') or []
            for ev in events:
                ev_type = None
                ev_data = None
                if isinstance(ev, (list, tuple)) and len(ev) >= 1:
                    ev_type = ev[0]
                    if len(ev) >= 2:
                        ev_data = ev[1]
                elif isinstance(ev, dict):
                    ev_type = ev.get('type') or ev.get('event') or ev.get('name')
                    ev_data = ev
                if ev_type:
                    et = str(ev_type).lower()
                    if et in ('team_a_win', 'team_a_victory', 'team_a_won', 'a_win', 'win', 'victory'):
                        return True
                    if et in ('team_b_win', 'team_b_victory', 'team_b_won', 'b_win', 'defeat', 'loss'):
                        return False
                    if isinstance(ev_data, dict):
                        cand = ev_data.get('winner') or ev_data.get('result')
                        if cand is not None:
                            cs = str(cand).lower()
                            return ('team_a' in cs or cs in ('a', 'player'))

            a_surv = res.get('team_a_survivors') or res.get('team_a_survivor_count') or res.get('team_a_survivors_count') or 0
            b_surv = res.get('team_b_survivors') or res.get('team_b_survivor_count') or res.get('team_b_survivors_count') or 0
            return a_surv > b_surv

        wins = 0
        total = 0

        # If population is small, run full round-robin: each individual vs every other
        if hasattr(self, 'population') and len(self.population) < 50:
            opponents = [p for p in self.population if p != individual]
            if not opponents:
                return 0.0
            for opp_ind in opponents:
                for i in range(n_games):
                    team_a = self.build_team(individual)
                    team_b = self.build_team(opp_ind)
                    if seed_base is not None:
                        # mix in individuals to get deterministic-ish per pairing
                        random.seed((hash(tuple(individual)) + hash(tuple(opp_ind)) + i) & 0xffffffff)
                    res = run_combat_simulation(team_a, team_b)
                    if _is_win(res):
                        wins += 1
                    total += 1
            return wins / float(total) if total else 0.0

        # Otherwise, sample opponents from population (fight each other)
        for i in range(n_games):
            team_a = self.build_team(individual)
            if seed_base is not None:
                random.seed(seed_base + i)
            if not hasattr(self, 'population') or not self.population or len(self.population) < 2:
                raise RuntimeError('Population must contain at least 2 individuals to evaluate against each other')
            opponents = [p for p in self.population if p != individual]
            if not opponents:
                raise RuntimeError('No valid opponents in population')
            opp_ind = random.choice(opponents)
            opponent = self.build_team(opp_ind)
            res = run_combat_simulation(team_a, opponent)
            if _is_win(res):
                wins += 1
        return wins / float(n_games)

    def tournament_select(self, scored_pop, k=TOURNAMENT_K):
        # scored_pop: list of (individual, score)
        aspirants = random.sample(scored_pop, k)
        aspirants.sort(key=lambda x: x[1], reverse=True)
        return deepcopy(aspirants[0][0])

    def crossover(self, a, b):
        # Order-preserving one-point crossover for lists
        if random.random() > CROSSOVER_RATE:
            return deepcopy(a), deepcopy(b)
        pt = random.randint(1, TEAM_SIZE - 1)
        child1 = a[:pt] + [x for x in b if x not in a[:pt]]
        child2 = b[:pt] + [x for x in a if x not in b[:pt]]
        # if duplicates or length mismatch, trim/pad
        child1 = (child1 + random.sample([u.id for u in self.pool], TEAM_SIZE))[:TEAM_SIZE]
        child2 = (child2 + random.sample([u.id for u in self.pool], TEAM_SIZE))[:TEAM_SIZE]
        return child1, child2

    def mutate(self, individual):
        if random.random() > MUTATION_RATE:
            return individual
        idx = random.randrange(TEAM_SIZE)
        replacement = random.choice(self.pool).id
        new = individual[:]
        new[idx] = replacement
        return new

    def run(self, generations=GENERATIONS, eval_games=EVAL_GAMES, verbose=False):
        self.init_population()
        scored = []
        best_seen = None
        history = []
        for gen in range(generations):
            # evaluate population
            scored = []
            for ind in self.population:
                score = self.evaluate(ind, n_games=eval_games)
                scored.append((ind, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            gen_best = scored[0]
            history.append({'gen': gen, 'best_score': gen_best[1]})
            if verbose:
                scores = [s for (_, s) in scored]
                best_score = max(scores) if scores else 0.0
                worst_score = min(scores) if scores else 0.0
                avg_score = mean(scores) if scores else 0.0
                med_score = median(scores) if scores else 0.0
                print(f"Gen {gen}: best={best_score:.2f} worst={worst_score:.2f} avg={avg_score:.2f} med={med_score:.2f}")
                # Print top-3 UNIQUE teams for this generation (preserve order)
                seen = set()
                unique_top = []
                for indiv, sc in scored:
                    key = tuple(indiv)
                    if key in seen:
                        continue
                    seen.add(key)
                    unique_top.append((indiv, sc))
                    if len(unique_top) >= 3:
                        break
                print("Top 3 teams:")
                if not unique_top:
                    print(" None")
                for rank, (indiv, sc) in enumerate(unique_top, start=1):
                    print(f" {rank}. score={sc:.2f} team={indiv}")
            if best_seen is None or gen_best[1] > best_seen[1]:
                best_seen = deepcopy(gen_best)
            # next generation
            new_pop = []
            # elitism: keep top 1
            new_pop.append(deepcopy(scored[0][0]))
            while len(new_pop) < self.population_size:
                p1 = self.tournament_select(scored)
                p2 = self.tournament_select(scored)
                c1, c2 = self.crossover(p1, p2)
                c1 = self.mutate(c1)
                # Ensure we don't add duplicates into the new population.
                # If a candidate already exists, replace with a fresh random individual.
                def _unique_candidate(candidate, existing):
                    tries = 0
                    key = tuple(candidate)
                    while tuple(candidate) in existing and tries < 10:
                        candidate = self.random_individual()
                        tries += 1
                    return candidate

                if len(new_pop) < self.population_size:
                    c1u = _unique_candidate(c1, set(tuple(x) for x in new_pop))
                    new_pop.append(c1u)
                if len(new_pop) < self.population_size:
                    c2 = self.mutate(c2)
                    c2u = _unique_candidate(c2, set(tuple(x) for x in new_pop))
                    new_pop.append(c2u)
            self.population = new_pop
        return best_seen, history


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pop', type=int, default=POP_SIZE)
    parser.add_argument('--gens', type=int, default=GENERATIONS)
    parser.add_argument('--eval-games', type=int, default=EVAL_GAMES)
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--out', default=OUTPUT_PATH)
    args = parser.parse_args()

    game_data = load_game_data()
    gs = GeneticSearch(game_data, population_size=args.pop)
    best, history = gs.run(generations=args.gens, eval_games=args.eval_games, verbose=args.verbose)
    if best:
        best_ind, best_score = best
        result = {
            'best_score': best_score,
            'best_team': best_ind,
            'history': history
        }
        with open(args.out, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Saved best team (score={best_score:.2f}) to {args.out}")
    else:
        print("No best team found")


if __name__ == '__main__':
    main()
