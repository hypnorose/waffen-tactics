import sys
import os

# Ensure local source packages are importable for tests
ROOT = os.path.abspath(os.path.dirname(__file__))
WAFFEN_SRC = os.path.join(ROOT, "waffen-tactics", "src")
BACKEND = os.path.join(ROOT, "waffen-tactics-web", "backend")

for p in (WAFFEN_SRC, BACKEND):
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
