# Code Coverage Report

Generated on: December 26, 2025

## Summary
- **Total Lines**: 4706
- **Covered Lines**: 2938
- **Missed Lines**: 1768
- **Coverage Percentage**: 62%

## Coverage by File

| File | Statements | Missed | Coverage | Missing Lines |
|------|------------|--------|----------|---------------|
| waffen-tactics/src/waffen_tactics/__init__.py | 1 | 0 | 100% | |
| waffen-tactics/src/waffen_tactics/animation/renderers.py | 45 | 16 | 64% | 26, 31, 35, 46, 52-59, 70, 74-77, 88, 92-95 |
| waffen-tactics/src/waffen_tactics/animation/system.py | 40 | 6 | 85% | 68, 80-88, 116, 120, 144 |
| waffen-tactics/src/waffen_tactics/animation/types.py | 73 | 11 | 85% | 32, 120, 124-133, 139 |
| waffen-tactics/src/waffen_tactics/cli.py | 75 | 75 | 0% | 1-96 |
| waffen-tactics/src/waffen_tactics/core/combat_core.py | 50 | 6 | 88% | 21-23, 41, 61, 64 |
| waffen-tactics/src/waffen_tactics/core/types.py | 42 | 0 | 100% | |
| waffen-tactics/src/waffen_tactics/emitters/mutators.py | 24 | 8 | 67% | 12-13, 17-18, 30-31, 34-35 |
| waffen-tactics/src/waffen_tactics/emitters/payload.py | 3 | 0 | 100% | |
| waffen-tactics/src/waffen_tactics/engine/combat_state.py | 68 | 24 | 65% | 39, 45, 72-78, 89-95, 166-176 |
| waffen-tactics/src/waffen_tactics/engine/event_dispatcher.py | 127 | 34 | 73% | 32-33, 39, 51-56, 59-64, 85-86, 97-100, 116-119, 129-134, 152-153, 186-189 |
| waffen-tactics/src/waffen_tactics/models/__init__.py | 2 | 0 | 100% | |
| waffen-tactics/src/waffen_tactics/models/player.py | 19 | 0 | 100% | |
| waffen-tactics/src/waffen_tactics/models/player_state.py | 97 | 7 | 93% | 75, 83, 109, 122-125 |
| waffen-tactics/src/waffen_tactics/models/skill.py | 59 | 0 | 100% | |
| waffen-tactics/src/waffen_tactics/models/unit.py | 83 | 5 | 94% | 21, 101, 132, 134, 136 |
| waffen-tactics/src/waffen_tactics/services/combat.py | 11 | 0 | 100% | |
| waffen-tactics/src/waffen_tactics/services/combat_attack_processor.py | 112 | 12 | 89% | 62-65, 164, 198-199, 211, 218-224 |
| waffen-tactics/src/waffen_tactics/services/combat_effect_processor.py | 442 | 336 | 24% | 44-45, 66, 94, 100-101, 111, 116-120, 129-130, 140-141, 152-153, 157-158, 225, 243-285, 305-371, 389-444, 475-675, 688-701, 730, 741-757 |
| waffen-tactics/src/waffen_tactics/services/combat_manager.py | 99 | 81 | 18% | 18, 26-28, 88-203 |
| waffen-tactics/src/waffen_tactics/services/combat_per_second_buff_processor.py | 124 | 71 | 43% | 35-36, 52-66, 68-84, 105-108, 110-115, 118, 124-138, 140-156, 160-164 |
| waffen-tactics/src/waffen_tactics/services/combat_regeneration_processor.py | 78 | 25 | 68% | 35-38, 56-57, 76-96, 103-104 |
| waffen-tactics/src/waffen_tactics/services/combat_shared.py | 3 | 0 | 100% | |
| waffen-tactics/src/waffen_tactics/services/combat_simulator.py | 491 | 246 | 50% | 92-93, 95-98, 111-112, 132-133, 137-138, 151-153, 159-244, 248-272, 276-307, 311-335, 363-364, 369-370, 375-376, 383-384, 406-407, 432-433, 449, 462-471, 530-626, 645, 669-670, 677-678, 697, 729-730, 739-747, 758-759, 780-790, 864-866, 884-893, 895-896, 901-903 |
| waffen-tactics/src/waffen_tactics/services/combat_unit.py | 174 | 35 | 80% | 55, 82-89, 98, 148, 152, 156, 160, 196, 282-283, 286-287, 290-291, 294-295, 298-299, 302-303, 306-307, 322, 333-338, 346 |
| waffen-tactics/src/waffen_tactics/services/combat_win_conditions.py | 12 | 8 | 33% | 12-16, 29-32 |
| waffen-tactics/src/waffen_tactics/services/data_loader.py | 68 | 6 | 91% | 50, 100-102, 112-113 |
| waffen-tactics/src/waffen_tactics/services/database.py | 228 | 85 | 63% | 20, 98-99, 102-103, 168-175, 215-217, 221-223, 254, 264, 277-279, 306-314, 324-332, 338, 364-406, 420-422, 426-517 |
| waffen-tactics/src/waffen_tactics/services/effect_processor.py | 58 | 0 | 100% | |
| waffen-tactics/src/waffen_tactics/services/effects/__init__.py | 26 | 3 | 88% | 28, 32, 51 |
| waffen-tactics/src/waffen_tactics/services/effects/buff.py | 38 | 18 | 53% | 22, 27-29, 60, 65-79 |
| waffen-tactics/src/waffen_tactics/services/effects/conditional.py | 90 | 53 | 41% | 26, 53, 58-72, 89-125, 129-152 |
| waffen-tactics/src/waffen_tactics/services/effects/damage.py | 25 | 7 | 72% | 19, 38-39, 46-47, 52-53 |
| waffen-tactics/src/waffen_tactics/services/effects/damage_over_time.py | 36 | 13 | 64% | 21, 26, 49, 75-86 |
| waffen-tactics/src/waffen_tactics/services/effects/debuff.py | 42 | 20 | 52% | 22, 27-29, 35-36, 66, 71-85 |
| waffen-tactics/src/waffen_tactics/services/effects/delay.py | 28 | 8 | 71% | 21-22, 32-33, 36-37, 43-44 |
| waffen-tactics/src/waffen_tactics/services/effects/heal.py | 19 | 4 | 79% | 18, 38, 43-44 |
| waffen-tactics/src/waffen_tactics/services/effects/repeat.py | 82 | 38 | 54% | 20, 46, 53-60, 76-77, 80, 84-89, 99, 104, 110-127, 131-146 |
| waffen-tactics/src/waffen_tactics/services/effects/shield.py | 22 | 8 | 64% | 19, 43-51 |
| waffen-tactics/src/waffen_tactics/services/effects/stun.py | 22 | 7 | 68% | 18, 33, 35, 40-45 |
| waffen-tactics/src/waffen_tactics/services/event_canonicalizer.py | 332 | 122 | 63% | 42, 50, 62, 73, 78-80, 83-88, 91-95, 100-101, 105-111, 151-153, 186-193, 214-215, 230, 240-246, 249-250, 263-264, 315-316, 334-335, 350-351, 377-378, 392-393, 426-428, 431-439, 457-458, 461, 465-466, 485-526, 572-573, 603-604, 630, 640-642, 655, 659-660, 687, 698-699, 717-718, 742-760, 787-788, 794-795, 827-829, 860-862 |
| waffen-tactics/src/waffen_tactics/services/game_manager.py | 52 | 6 | 88% | 31, 63, 86-88, 97 |
| waffen-tactics/src/waffen_tactics/services/modular_effect_processor.py | 299 | 96 | 68% | 83, 87, 91-93, 101, 107, 111-113, 148-164, 177, 183, 187-189, 216-221, 236, 238, 255-266, 281, 303, 307-316, 320-355, 364-382, 391-406, 412, 419, 426, 433-445, 479-480, 537, 551-552, 566-567, 571-572 |
| waffen-tactics/src/waffen_tactics/services/recipient_resolver.py | 36 | 0 | 100% | |
| waffen-tactics/src/waffen_tactics/services/shop.py | 81 | 27 | 67% | 42, 47-48, 61, 70, 76-88, 94-102, 108, 111, 119 |
| waffen-tactics/src/waffen_tactics/services/skill_executor.py | 94 | 14 | 85% | 44, 47, 106, 126-129, 165, 177, 181-182, 187-193 |
| waffen-tactics/src/waffen_tactics/services/skill_parser.py | 99 | 23 | 77% | 72, 81-85, 90, 119, 122, 139-140, 157, 169, 173-176, 180, 184-187, 191 |
| waffen-tactics/src/waffen_tactics/services/stat_buff_handlers.py | 144 | 40 | 72% | 35, 40, 45, 82, 120, 157-159, 198, 235, 244, 247, 250, 266-274, 281, 284, 287, 303-311, 318, 321, 324, 339-348 |
| waffen-tactics/src/waffen_tactics/services/stat_calculator.py | 31 | 0 | 100% | |
| waffen-tactics/src/waffen_tactics/services/synergy.py | 195 | 75 | 62% | 38, 65, 69, 77, 83, 87, 94, 104-107, 115, 122, 124-133, 164, 168, 176-178, 198-233, 239-268 |
| waffen-tactics/src/waffen_tactics/services/unit_manager.py | 205 | 89 | 57% | 30, 36, 42, 46, 57-58, 64, 84-88, 91, 96, 106-124, 130, 135-140, 152-153, 161-162, 165-166, 176-178, 200-201, 211-213, 228-263, 271, 287-288, 296, 301-302, 305-310 |

## Analysis of Uncovered Files

### Files with 0% Coverage (Potential Dead Code)
- `cli.py`: 75 lines, all missed. This appears to be a command-line interface that's not tested.

### Files with Low Coverage (<50%)
- `combat_effect_processor.py`: 24% coverage (336/442 lines missed) - Large processor with many untested branches
- `combat_manager.py`: 18% coverage (81/99 lines missed) - Combat management logic largely untested
- `combat_per_second_buff_processor.py`: 43% coverage - Per-second buff processing
- `combat_simulator.py`: 50% coverage - Main combat simulation logic
- Various effect handlers in `services/effects/`: Many have 40-70% coverage

### Files with High Coverage (>90%)
- Model classes: `player.py`, `player_state.py`, `skill.py`, `unit.py`
- Core services: `combat.py`, `combat_shared.py`, `effect_processor.py`, `recipient_resolver.py`, `stat_calculator.py`

### Potential Dead Code Candidates
1. **cli.py** - 0% coverage, 75 lines. If this CLI is not used, it could be dead code.
2. **combat_manager.py** - 18% coverage. May contain unused combat management features.
3. **combat_effect_processor.py** - 24% coverage. Large file with many untested effect processing paths.
4. **unit_manager.py** - 57% coverage. Unit management with significant uncovered code.

### Recommendations
- Review `cli.py` for necessity - if unused, consider removal
- Add tests for `combat_manager.py` and `combat_effect_processor.py` 
- Investigate uncovered branches in effect handlers
- Consider refactoring large files with low coverage into smaller, more testable units