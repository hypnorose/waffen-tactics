Genetic search for best 10v10 team

Run locally from repo root:

```bash
python experiments/genetic_search.py --pop 20 --gens 10 --eval-games 6 --verbose
```

Notes:
- Uses the project's `run_combat_simulation` and game data loader.
- Results saved to `experiments/best_teams.json` by default.
