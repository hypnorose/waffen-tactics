# Backend Testing Setup Guide

## Overview
This guide explains how to set up and run tests for the Waffen Tactics web backend.

## Prerequisites
- Python 3.12+
- Virtual environment with required packages

## Environment Setup

### 1. Activate Virtual Environment
```bash
source /home/ubuntu/waffen-tactics-game/waffen-tactics/bot_venv/bin/activate
```

### 2. Set Python Path
The backend imports modules from the waffen-tactics package, so PYTHONPATH must include the src directory:
```bash
export PYTHONPATH=/home/ubuntu/waffen-tactics-game/waffen-tactics/src:$PYTHONPATH
```

### 3. Navigate to Backend Directory
```bash
cd /home/ubuntu/waffen-tactics-game/waffen-tactics-web/backend
```

## Running Tests

### Full Test Suite
```bash
source /home/ubuntu/waffen-tactics-game/waffen-tactics/bot_venv/bin/activate
cd /home/ubuntu/waffen-tactics-game/waffen-tactics-web/backend
PYTHONPATH=/home/ubuntu/waffen-tactics-game/waffen-tactics/src python3 -m pytest tests/ -v
```

### Single Test File
```bash
source /home/ubuntu/waffen-tactics-game/waffen-tactics/bot_venv/bin/activate
cd /home/ubuntu/waffen-tactics-game/waffen-tactics-web/backend
PYTHONPATH=/home/ubuntu/waffen-tactics-game/waffen-tactics/src python3 -m pytest tests/test_game_management.py -v
```

### Single Test Method
```bash
source /home/ubuntu/waffen-tactics-game/waffen-tactics/bot_venv/bin/activate
cd /home/ubuntu/waffen-tactics-game/waffen-tactics-web/backend
PYTHONPATH=/home/ubuntu/waffen-tactics-game/waffen-tactics/src python3 -m pytest tests/test_game_management.py::TestGetState::test_get_state_player_exists -v
```

## Test Structure
- `tests/test_game_actions.py` - Unit buying, selling, moving actions
- `tests/test_game_combat.py` - Combat system tests
- `tests/test_game_data.py` - Data retrieval (leaderboard, units, traits)
- `tests/test_game_management.py` - Game state management
- `tests/test_game_state_utils.py` - Utility functions

## Known Issues
- Tests currently fail due to mocking issues and Flask context requirements
- Many tests need to be updated to properly mock async functions and Flask contexts
- Some tests have incorrect function signatures

## Quick Commands
```bash
# One-liner for running all tests
source /home/ubuntu/waffen-tactics-game/waffen-tactics/bot_venv/bin/activate && cd /home/ubuntu/waffen-tactics-game/waffen-tactics-web/backend && PYTHONPATH=/home/ubuntu/waffen-tactics-game/waffen-tactics/src python3 -m pytest tests/ -v

# Check if backend imports work
source /home/ubuntu/waffen-tactics-game/waffen-tactics/bot_venv/bin/activate && cd /home/ubuntu/waffen-tactics-game/waffen-tactics-web/backend && PYTHONPATH=/home/ubuntu/waffen-tactics-game/waffen-tactics/src python3 -c "import api; print('Backend OK')"
```

## Troubleshooting
- If you get "ModuleNotFoundError: No module named 'waffen_tactics'", check PYTHONPATH
- If you get "RuntimeError: Working outside of request context", tests need Flask app context
- If you get "TypeError: An asyncio.Future, a coroutine or an awaitable is required", fix async mocking