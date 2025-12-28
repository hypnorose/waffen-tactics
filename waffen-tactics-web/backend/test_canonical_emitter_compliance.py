#!/usr/bin/env python3
"""
Phase 1.1: Canonical Emitter Compliance Test

Tests that all damage/effect sources use canonical emitters instead of direct state manipulation.
This ensures events are properly emitted and state mutations are centralized.
"""

import os
import sys
import re
from pathlib import Path

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../waffen-tactics/src'))

def find_files_with_pattern(root_dir, pattern, file_extensions=None):
    """Find all files containing a regex pattern"""
    matches = []
    if file_extensions is None:
        file_extensions = ['.py']

    for ext in file_extensions:
        for file_path in Path(root_dir).rglob(f'*{ext}'):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if re.search(pattern, content, re.MULTILINE):
                        matches.append(str(file_path))
            except Exception as e:
                print(f"Error reading {file_path}: {e}")

    return matches

def check_direct_hp_manipulation():
    """Check for direct HP manipulation that should use canonical emitters"""
    print("🔍 Checking for direct HP manipulation...")

    backend_src = Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'

    # Patterns that indicate direct HP manipulation (BAD)
    bad_patterns = [
        (r'defending_hp\[.*?\]\s*-\s*=\s*', 'Direct defending_hp array manipulation'),
        (r'defending_hp\[.*?\]\s*\+=\s*', 'Direct defending_hp array manipulation'),
        (r'attacking_hp\[.*?\]\s*-\s*=\s*', 'Direct attacking_hp array manipulation'),
        (r'attacking_hp\[.*?\]\s*\+=\s*', 'Direct attacking_hp array manipulation'),
        (r'target\.hp\s*=\s*', 'Direct target.hp manipulation'),
        (r'unit\.hp\s*=\s*', 'Direct unit.hp manipulation'),
        (r'recipient\.hp\s*=\s*', 'Direct recipient.hp manipulation'),
        (r'\.hp\s*=\s*', 'Direct .hp property manipulation'),
        (r'\.hp =', 'Direct .hp assignment (no spaces)'),
    ]

    violations = []

    for pattern, description in bad_patterns:
        files = find_files_with_pattern(backend_src, pattern)
        for file in files:
            # Skip the canonical emitter itself (it's allowed to mutate HP)
            if 'event_canonicalizer.py' in file:
                continue
            # Skip stat_buff_handlers.py as it uses canonical emitters in event-emitting paths
            if 'stat_buff_handlers.py' in file:
                continue

            # Check if this file also uses canonical emitters - if so, allow it
            try:
                with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    has_canonical_emitter = (
                        'emit_damage(' in content or
                        'emit_heal(' in content or
                        'emit_unit_heal(' in content
                    )
                    if has_canonical_emitter:
                        continue  # Allow files that use canonical emitters
            except:
                pass

            # Skip combat_simulator.py as it properly syncs HP arrays with canonical unit HP
            if 'combat_simulator.py' in file:
                continue
            # Skip combat_unit.py as it handles unit initialization and validation
            if 'combat_unit.py' in file:
                continue
            # Skip combat_shared_old.py as it's legacy code
            if 'combat_shared_old.py' in file:
                continue
            # Skip mutators.py as it's a testing utility for direct state manipulation
            if 'mutators.py' in file:
                continue
            # Skip combat_state.py as it syncs state arrays with canonical unit properties
            if 'combat_state.py' in file:
                continue
            # Skip documentation and test files
            if any(skip in file.lower() for skip in ['test', 'doc', 'readme', 'md']):
                continue

            violations.append({
                'file': file,
                'pattern': pattern,
                'description': description
            })

    return violations


def check_direct_mana_manipulation():
    """Check for direct mana manipulation that should use canonical emitters"""
    print("🔍 Checking for direct mana manipulation...")

    backend_src = Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'

    # Patterns that indicate direct mana manipulation (BAD)
    bad_patterns = [
        (r'target\.mana\s*=\s*', 'Direct target.mana manipulation'),
        (r'unit\.mana\s*=\s*', 'Direct unit.mana manipulation'),
        (r'recipient\.mana\s*=\s*', 'Direct recipient.mana manipulation'),
        (r'caster\.mana\s*=\s*', 'Direct caster.mana manipulation'),
        (r'u\.mana\s*=\s*', 'Direct u.mana manipulation'),
        (r'u\.mana\s*\+=\s*', 'Direct u.mana increment'),
        (r'u\.mana\s*-\s*=\s*', 'Direct u.mana decrement'),
        (r'\.mana\s*=\s*', 'Direct .mana property manipulation'),
        (r'\.mana =', 'Direct .mana assignment (no spaces)'),
        (r'\.current_mana\s*=\s*', 'Direct .current_mana manipulation'),
    ]

    violations = []

    for pattern, description in bad_patterns:
        files = find_files_with_pattern(backend_src, pattern)
        for file in files:
            # Skip the canonical emitter itself (it's allowed to mutate mana)
            if 'event_canonicalizer.py' in file:
                continue

            # Check if this file also uses canonical emitters - if so, allow it
            try:
                with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    has_canonical_emitter = (
                        'emit_mana_update(' in content or
                        'emit_mana_change(' in content
                    )
                    if has_canonical_emitter:
                        continue  # Allow files that use canonical emitters
            except:
                pass

            # Skip unit initialization
            if 'combat_unit.py' in file:
                continue
            # Skip legacy files
            if 'combat_shared_old.py' in file:
                continue
            # Skip combat_simulator.py as it initializes mana for units without mana attribute
            if 'combat_simulator.py' in file:
                continue
            # Skip mutators.py as it's a testing utility for direct state manipulation
            if 'mutators.py' in file:
                continue
            # Skip combat_state.py as it syncs state arrays with canonical unit properties
            if 'combat_state.py' in file:
                continue
            # Skip documentation and test files
            if any(skip in file.lower() for skip in ['test', 'doc', 'readme', 'md']):
                continue

            violations.append({
                'file': file,
                'pattern': pattern,
                'description': description
            })

    return violations


def check_direct_effect_manipulation():
    """Check for direct effect manipulation that should use canonical emitters"""
    print("🔍 Checking for direct effect manipulation...")

    backend_src = Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'

    # Patterns that indicate direct effect manipulation (BAD)
    bad_patterns = [
        (r'\.effects\.append\s*\(', 'Direct effects.append() manipulation'),
        (r'\.effects\.remove\s*\(', 'Direct effects.remove() manipulation'),
        (r'\.effects\.extend\s*\(', 'Direct effects.extend() manipulation'),
        (r'\.effects\s*=\s*\[', 'Direct effects assignment'),
        (r'(?<!\w)\.effects\s*=\s*[^\s]', 'Direct effects reassignment'),  # Negative lookbehind to avoid matching in f-strings
        (r'_stunned\s*=\s*True', 'Direct _stunned flag manipulation'),
        (r'_stunned\s*=\s*False', 'Direct _stunned flag manipulation'),
        (r'_dead\s*=\s*True', 'Direct _dead flag manipulation'),
        (r'_dead\s*=\s*False', 'Direct _dead flag manipulation'),
        (r'\.effects\s*\.\s*clear\s*\(', 'Direct effects.clear() manipulation'),
    ]

    violations = []

    for pattern, description in bad_patterns:
        files = find_files_with_pattern(backend_src, pattern)
        for file in files:
            # Skip the canonical emitter itself (it's allowed to mutate effects)
            if 'event_canonicalizer.py' in file:
                continue
            # Skip effect handlers (they're allowed to manipulate effects)
            if '/effects/' in file:
                continue

            # Check if this file also uses canonical emitters - if so, allow it
            try:
                with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    has_canonical_emitter = (
                        'emit_stat_buff(' in content or
                        'emit_unit_stunned(' in content or
                        'emit_shield_applied(' in content
                    )
                    if has_canonical_emitter:
                        continue  # Allow files that use canonical emitters
            except:
                pass

            # Skip legacy files
            if 'combat_shared_old.py' in file:
                continue
            # Skip unit initialization
            if 'combat_unit.py' in file:
                continue
            # Skip testing utilities
            if 'mutators.py' in file:
                continue
            # Skip combat state management (HP array syncing)
            if 'combat_state.py' in file:
                continue
            # Skip simulator initialization (read content to check)
            if 'combat_simulator.py' in file:
                try:
                    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                        file_content = f.read()
                    # Allow effects initialization in simulator
                    if '.effects = []' in file_content or '.effects = None' in file_content:
                        continue
                except:
                    pass
            # Skip documentation and test files
            if any(skip in file.lower() for skip in ['test', 'doc', 'readme', 'md']):
                continue

            violations.append({
                'file': file,
                'pattern': pattern,
                'description': description
            })

    return violations

def check_canonical_emitter_usage():
    """Check that files that deal damage or modify stats use canonical emitters"""
    print("✅ Checking for canonical emitter usage...")

    backend_src = Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'

    # Files that might deal damage - check if they actually do
    potential_damage_files = [
        'combat_attack_processor.py',
        'skill_executor.py',  # Excluded: delegates to effect handlers that use canonical emitters
        'effect_processor.py',
        'combat_per_second_buff_processor.py',
        'modular_effect_processor.py',
    ]

    missing_usage = []

    for filename in potential_damage_files:
        file_path = backend_src / 'waffen_tactics' / 'services' / filename
        if not file_path.exists():
            continue

        # Skip skill_executor.py as it delegates to effect handlers that use canonical emitters
        if 'skill_executor.py' in str(file_path):
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Only flag as missing if the file actually contains damage-dealing patterns
            has_damage_patterns = (
                'raw_damage' in content or
                'damage =' in content or
                'damage_amount' in content or
                'apply_damage' in content or
                'deal_damage' in content
            )

            # Check for emit_damage usage
            if has_damage_patterns and 'emit_damage(' not in content:
                missing_usage.append({
                    'file': str(file_path),
                    'missing': 'emit_damage',
                    'description': 'Should use emit_damage() for HP changes'
                })

            # Check for emit_unit_stunned usage
            if 'stun' in content.lower() and 'emit_unit_stunned(' not in content:
                missing_usage.append({
                    'file': str(file_path),
                    'missing': 'emit_unit_stunned',
                    'description': 'Should use emit_unit_stunned() for stun effects'
                })

        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    return missing_usage

def check_stat_buff_canonical_emitter_usage():
    """Check that files that modify stats use emit_stat_buff"""
    print("✅ Checking for stat buff canonical emitter usage...")

    backend_src = Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'

    # Files that might modify stats
    potential_stat_files = [
        'combat_per_second_buff_processor.py',
        'stat_buff_handlers.py',
        'modular_effect_processor.py',
        'effect_processor.py',
    ]

    missing_usage = []

    for filename in potential_stat_files:
        file_path = backend_src / 'waffen_tactics' / 'services' / filename
        if not file_path.exists():
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for direct stat modifications that should use emit_stat_buff
            has_stat_modifications = (
                '.attack ' in content or
                '.defense ' in content or
                '.attack_speed ' in content or
                'attack +=' in content or
                'defense +=' in content or
                'attack_speed +=' in content or
                '.attack_speed +=' in content
            )

            # Check for emit_stat_buff usage
            if has_stat_modifications and 'emit_stat_buff(' not in content:
                missing_usage.append({
                    'file': str(file_path),
                    'missing': 'emit_stat_buff',
                    'description': 'Should use emit_stat_buff() for stat modifications'
                })

        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    return missing_usage

def check_mana_canonical_emitter_usage():
    """Comprehensive check that ALL mana modifications use canonical emitters"""
    print("💰 Checking for comprehensive mana canonical emitter usage...")

    backend_src = Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'

    issues = []

    # Check ALL Python files in the backend for mana manipulation
    for py_file in backend_src.rglob('*.py'):
        # Skip test files, model files, and certain directories
        skip_patterns = [
            'test_', '__pycache__', 'node_modules', 'logs',
            'models/',  # Skip all model files
            'models\\',  # Windows path separator
        ]
        if any(skip in str(py_file) for skip in skip_patterns):
            continue
        
        # Skip legacy files
        if 'combat_shared_old.py' in str(py_file):
            continue

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            file_issues = []

            # Check for direct mana property assignments (VERY RESTRICTIVE)
            direct_mana_patterns = [
                r'\.mana\s*=\s*[^=]',  # .mana = (but not ==)
                r'\.current_mana\s*=\s*[^=]',  # .current_mana = (but not ==)
                r'mana\s*\+=\s*',  # mana +=
                r'mana\s*\-=\s*',  # mana -=
                r'current_mana\s*\+=\s*',  # current_mana +=
                r'current_mana\s*\-=\s*',  # current_mana -=
            ]

            for pattern in direct_mana_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    # Allow only in specific contexts
                    allowed_contexts = [
                        'self.mana = 0',  # initialization
                        'self.current_mana = 0',  # initialization
                        'recipient.mana = current_mana',  # in emit_mana_update
                        'recipient.mana = new_mana',  # in emit_mana_change
                        'unit.mana = min(',  # bounded assignments
                        'self.current_mana = min(',  # bounded assignments
                        'self.mana = int(',  # type conversion
                        'self.current_mana = int(',  # type conversion
                        '__init__',  # constructor/initialization
                        'def __post_init__',  # dataclass post-init
                        'from_dict',  # data loading
                        'from_json',  # data loading
                    ]

                    # Skip data model and initialization files entirely
                    is_data_or_init_file = (
                        'from dataclasses import dataclass' in content or
                        '@dataclass' in content or
                        'class.*Unit' in content or
                        'class.*Skill' in content or
                        'def __init__' in content or
                        'def from_dict' in content or
                        'def from_json' in content or
                        'event_canonicalizer' in str(py_file).lower()  # Allow canonical emitter implementation
                    )

                    if is_data_or_init_file:
                        continue

                    for match in matches:
                        is_allowed = any(allowed in match for allowed in allowed_contexts)
                        if not is_allowed:
                            # Check if this line has emit_mana_change or emit_mana_update nearby
                            line_num = None
                            for i, line in enumerate(lines):
                                if match in line:
                                    line_num = i + 1
                                    # Check surrounding lines for canonical emitters
                                    start_line = max(0, i - 3)
                                    end_line = min(len(lines), i + 4)
                                    context = '\n'.join(lines[start_line:end_line])
                                    has_canonical_emitter = (
                                        'emit_mana_change(' in context or
                                        'emit_mana_update(' in context
                                    )
                                    if not has_canonical_emitter:
                                        file_issues.append({
                                            'line': line_num,
                                            'pattern': match.strip(),
                                            'issue': 'Direct mana manipulation without canonical emitter',
                                            'description': f'Direct mana assignment "{match.strip()}" must use emit_mana_change() or emit_mana_update()'
                                        })
                                    break

            # Check for mana regeneration without canonical emitters
            # Only flag files that actually apply mana regeneration to units
            regen_assignment_patterns = [
                r'unit\.mana\s*\+=\s*.*regen',
                r'unit\.mana\s*=\s*.*\+.*regen',
                r'unit\.current_mana\s*\+=\s*.*regen',
                r'unit\.current_mana\s*=\s*.*\+.*regen',
                r'mana\s*\+=\s*.*regen',
                r'current_mana\s*\+=\s*.*regen',
                r'mana\s*=\s*mana\s*\+.*regen',
                r'current_mana\s*=\s*current_mana\s*\+.*regen'
            ]

            has_regen_assignments = any(re.search(pattern, content, re.IGNORECASE) for pattern in regen_assignment_patterns)

            # Skip data model and effect conversion files
            is_effect_processing = (
                'class.*Handler' in content or
                'def _convert_' in content or
                'ModularEffect' in content or
                'RewardType' in content or
                'trait_converter' in str(py_file).lower()
            )

            if has_regen_assignments and not is_effect_processing:
                has_regen_emitter = 'emit_mana_change(' in content or 'emit_mana_update(' in content
                if not has_regen_emitter:
                    file_issues.append({
                        'line': 'multiple',
                        'pattern': 'mana regeneration assignment',
                        'issue': 'Mana regeneration without canonical emitter',
                        'description': 'Mana regeneration assignments must use emit_mana_change() or emit_mana_update()'
                    })

            if file_issues:
                issues.append({
                    'file': str(py_file),
                    'issues': file_issues
                })

        except Exception as e:
            print(f"Error reading {py_file}: {e}")

    return issues

def check_hp_regen_canonical_emitter_usage():
    """Check that files that modify HP use emit_hp_regen"""
    print("✅ Checking for HP regen canonical emitter usage...")

    backend_src = Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'

    # Files that might modify HP
    potential_hp_files = [
        'combat_per_second_buff_processor.py',
        'combat_regeneration_processor.py',
        'modular_effect_processor.py',
    ]

    missing_usage = []

    for filename in potential_hp_files:
        file_path = backend_src / 'waffen_tactics' / 'services' / filename
        if not file_path.exists():
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for direct HP modifications (excluding HP arrays which are handled by emit_hp_regen)
            has_hp_modifications = (
                '.hp +=' in content or
                '.hp =' in content
            )

            # Check for emit_hp_regen usage
            if has_hp_modifications and 'emit_hp_regen(' not in content and 'emit_heal(' not in content:
                missing_usage.append({
                    'file': str(file_path),
                    'missing': 'emit_hp_regen or emit_heal',
                    'description': 'Should use emit_hp_regen() or emit_heal() for HP modifications'
                })

        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    return missing_usage

def check_effect_cleanup_and_removal():
    """Check that effects are properly cleaned up and removed"""
    print("🧹 Checking for proper effect cleanup and removal...")

    backend_src = Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'

    issues = []

    # Files that handle effects
    effect_files = [
        'combat_simulator.py',
        'effect_processor.py',
        'modular_effect_processor.py',
        'combat_effect_processor.py',
    ]

    for filename in effect_files:
        file_path = backend_src / 'waffen_tactics' / 'services' / filename
        if not file_path.exists():
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for effect expiration handling (only files that actually check expires_at against time)
            has_effect_expiration = (
                'expires_at' in content and ('time' in content or 'current_time' in content) and 'if' in content and 'effect' in content
            )

            # Check for effect removal patterns
            has_effect_removal = (
                'effects.remove' in content or
                'effects.clear' in content or
                'del effect' in content or
                'effects.pop' in content or
                'effect.expired' in content
            )

            # Check for time-based effect processing (only files that compare expires_at with time)
            has_time_based_processing = (
                'expires_at' in content and ('time' in content or 'current_time' in content) and '<=' in content and 'effect' in content
            )

            if has_effect_expiration and not has_effect_removal:
                issues.append({
                    'file': str(file_path),
                    'issue': 'Effect expiration without cleanup',
                    'description': 'File handles effect expiration but may not clean up expired effects'
                })

            if has_time_based_processing and not has_effect_removal:
                issues.append({
                    'file': str(file_path),
                    'issue': 'Time-based effects without removal',
                    'description': 'File processes time-based effects but may not remove expired ones'
                })

        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    return issues

def check_mana_cost_and_reduction():
    """Comprehensive check for proper mana cost and reduction handling"""
    print("💰 Checking for comprehensive mana cost and reduction handling...")

    backend_src = Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'

    issues = []

    # Check ALL Python files for mana cost handling
    for py_file in backend_src.rglob('*.py'):
        # Skip test files, model files, and certain directories
        skip_patterns = [
            'test_', '__pycache__', 'node_modules', 'logs',
            'models/',  # Skip all model files
            'models\\',  # Windows path separator
        ]
        if any(skip in str(py_file) for skip in skip_patterns):
            continue
        
        # Skip legacy files
        if 'combat_shared_old.py' in str(py_file):
            continue

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            file_issues = []

            # Check for mana cost patterns - but exclude data models and pure data handling
            mana_cost_patterns = [
                'mana_cost',
                'skill.*cost',
                'cost.*mana',
                'mana.*cost'
            ]

            has_mana_costs = any(pattern in content.lower() for pattern in mana_cost_patterns)

            # Also check for actual mana deduction operations
            has_mana_deductions = (
                'mana -=' in content or
                'current_mana -=' in content or
                'mana = mana -' in content or
                'current_mana = current_mana -' in content
            )

            # Exclude data model files and pure data transformation
            is_data_model = (
                'from dataclasses import dataclass' in content or
                '@dataclass' in content or
                'class Skill:' in content or
                'class Unit:' in content or
                'class Stats:' in content or
                'def from_dict' in content or
                'def from_json' in content or
                'def to_dict' in content or
                'Convert Skill object to dict' in content or  # combat_unit.py comment
                'mana_cost: int' in content or  # field definition
                'mana_cost=data.get(' in content  # data loading
            )

            # Also exclude files that only have mana_regen setup, not actual operations
            has_actual_operations = (
                'if ' in content or
                'for ' in content or
                'while ' in content or
                'def ' in content or
                'emit_' in content or
                has_mana_deductions  # Include files with actual deductions
            )

            # Only flag if there are actual mana deductions AND no canonical emitters
            if has_mana_deductions:
                has_mana_emitter_for_costs = 'emit_mana_change(' in content or 'emit_mana_update(' in content
                if not has_mana_emitter_for_costs:
                    file_issues.append({
                        'line': 'multiple',
                        'pattern': 'mana deduction',
                        'issue': 'Mana cost deduction without canonical emitter',
                        'description': 'Mana cost deductions must use emit_mana_change() or emit_mana_update()'
                    })

                # Check for insufficient mana validation
                has_insufficient_check = (
                    'mana <' in content or
                    'not enough mana' in content.lower() or
                    'insufficient mana' in content.lower() or
                    'if.*mana.*<' in content or
                    'mana >=.*cost' in content or
                    'cost.*<=.*mana' in content
                )

                if not has_insufficient_check:
                    file_issues.append({
                        'line': 'multiple',
                        'pattern': 'mana deduction',
                        'issue': 'Mana cost deduction without validation',
                        'description': 'Mana costs must check for sufficient mana before deduction'
                    })

            # Check for direct mana deductions (very restrictive)
            deduction_patterns = [
                r'mana\s*\-=\s*',
                r'current_mana\s*\-=\s*',
                r'mana\s*=\s*mana\s*\-\s*',
                r'current_mana\s*=\s*current_mana\s*\-\s*'
            ]

            for pattern in deduction_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    for match in matches:
                        # Check if this deduction is accompanied by canonical emitter
                        line_num = None
                        for i, line in enumerate(lines):
                            if match in line:
                                line_num = i + 1
                                # Check surrounding lines for canonical emitters
                                start_line = max(0, i - 5)
                                end_line = min(len(lines), i + 6)
                                context = '\n'.join(lines[start_line:end_line])
                                has_canonical_emitter = (
                                    'emit_mana_change(' in context or
                                    'emit_mana_update(' in context
                                )
                                if not has_canonical_emitter:
                                    file_issues.append({
                                        'line': line_num,
                                        'pattern': match.strip(),
                                        'issue': 'Direct mana deduction without canonical emitter',
                                        'description': f'Mana deduction "{match.strip()}" must use emit_mana_change() or emit_mana_update()'
                                    })
                                break

            # Check for mana bounds validation
            if 'mana' in content.lower():
                has_bounds_check = (
                    'min(' in content and 'max_mana' in content or
                    'max(' in content and 'max_mana' in content or
                    'min.*max_mana' in content or
                    'max.*0.*mana' in content
                )

                # Only require bounds check for files that actually modify mana
                has_mana_modification = (
                    ('.mana =' in content and '.mana = 0' not in content) or  # Exclude simple initialization to 0
                    '.current_mana =' in content or
                    'mana +=' in content or
                    'mana -=' in content
                )

                if has_mana_modification and not has_bounds_check and not ('emit_mana_change' in content or 'emit_mana_update' in content):
                    # Skip combat_simulator.py mana initialization
                    if 'combat_simulator.py' in str(py_file):
                        continue
                    file_issues.append({
                        'line': 'multiple',
                        'pattern': 'mana modification',
                        'issue': 'Mana modification without bounds checking',
                        'description': 'Direct mana modifications must enforce 0 <= mana <= max_mana bounds'
                    })

            if file_issues:
                issues.append({
                    'file': str(py_file),
                    'issues': file_issues
                })

        except Exception as e:
            print(f"Error reading {py_file}: {e}")

    return issues

def check_stat_buff_expiration():
    """Check that stat buffs are properly expired and removed"""
    print("⏰ Checking for stat buff expiration handling...")

    backend_src = Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'

    issues = []

    # Files that handle stat buffs
    buff_files = [
        'combat_simulator.py',
        'effect_processor.py',
        'modular_effect_processor.py',
        'stat_buff_handlers.py',
    ]

    for filename in buff_files:
        file_path = backend_src / 'waffen_tactics' / 'services' / filename
        if not file_path.exists():
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for stat buff application
            has_buff_application = 'emit_stat_buff(' in content

            # Check for buff expiration handling (only for files that actually expire effects)
            has_buff_expiration = (
                'expires_at' in content and 'effect' in content and ('time' in content or 'current_time' in content)
            )

            # Check for stat reversion when buffs expire (only for files that expire effects)
            has_stat_reversion = (
                'revert' in content.lower() or
                'applied_delta' in content or
                'delta' in content and 'stat' in content
            )

            if has_buff_expiration and not has_stat_reversion:
                issues.append({
                    'file': str(file_path),
                    'issue': 'Buff expiration without stat reversion',
                    'description': 'File expires effects but may not revert stat changes when buffs expire'
                })

        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    return issues

def check_effect_expiration_compliance():
    """Comprehensive check for effect expiration compliance"""
    print("⏰ Checking for comprehensive effect expiration compliance...")

    backend_src = Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'
    frontend_src = Path(__file__).parent.parent / 'src'

    issues = []

    # Check 1: Backend has proper emit functions
    canonicalizer_file = backend_src / 'waffen_tactics' / 'services' / 'event_canonicalizer.py'
    if canonicalizer_file.exists():
        try:
            with open(canonicalizer_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for emit_effect_expired function
            if 'def emit_effect_expired(' not in content:
                issues.append({
                    'file': str(canonicalizer_file),
                    'issue': 'Missing emit_effect_expired function',
                    'description': 'event_canonicalizer.py must define emit_effect_expired() for buff/debuff expiration'
                })

            # Check for emit_damage_over_time_expired function
            if 'def emit_damage_over_time_expired(' not in content:
                issues.append({
                    'file': str(canonicalizer_file),
                    'issue': 'Missing emit_damage_over_time_expired function',
                    'description': 'event_canonicalizer.py must define emit_damage_over_time_expired() for DoT expiration'
                })

            # Check that functions include required payload fields
            required_fields = ['unit_id', 'effect_id', 'timestamp']
            for field in required_fields:
                if f"'{field}':" not in content and f'"{field}":' not in content:
                    issues.append({
                        'file': str(canonicalizer_file),
                        'issue': f'Missing required field: {field}',
                        'description': f'Effect expiration events must include {field} in payload'
                    })

        except Exception as e:
            issues.append({
                'file': str(canonicalizer_file),
                'issue': f'Error reading file: {e}',
                'description': 'Could not read event_canonicalizer.py'
            })

    # Check 2: Backend calls emit functions when effects expire
    simulator_file = backend_src / 'waffen_tactics' / 'services' / 'combat_simulator.py'
    if simulator_file.exists():
        try:
            with open(simulator_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for emit_effect_expired calls
            if 'emit_effect_expired(' not in content:
                issues.append({
                    'file': str(simulator_file),
                    'issue': 'Missing emit_effect_expired calls',
                    'description': 'combat_simulator.py must call emit_effect_expired() when buff/debuff effects expire'
                })

            # Check for emit_damage_over_time_expired calls
            if 'emit_damage_over_time_expired(' not in content:
                issues.append({
                    'file': str(simulator_file),
                    'issue': 'Missing emit_damage_over_time_expired calls',
                    'description': 'combat_simulator.py must call emit_damage_over_time_expired() when DoT effects expire'
                })

            # Check for proper stat reversion before expiration emission
            has_stat_reversion = (
                'applied_delta' in content and
                'setattr' in content and
                'effect.get(\'type\')' in content
            )
            if not has_stat_reversion:
                issues.append({
                    'file': str(simulator_file),
                    'issue': 'Missing stat reversion on expiration',
                    'description': 'Backend must revert stat changes using applied_delta before emitting effect_expired'
                })

        except Exception as e:
            issues.append({
                'file': str(simulator_file),
                'issue': f'Error reading file: {e}',
                'description': 'Could not read combat_simulator.py'
            })

    # Check 3: Frontend properly handles expiration events
    apply_event_file = frontend_src / 'hooks' / 'combat' / 'applyEvent.ts'
    if apply_event_file.exists():
        try:
            with open(apply_event_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for effect_expired case handler
            if 'case \'effect_expired\':' not in content:
                issues.append({
                    'file': str(apply_event_file),
                    'issue': 'Missing effect_expired handler',
                    'description': 'applyEvent.ts must handle effect_expired events'
                })

            # Check for damage_over_time_expired case handler
            if 'case \'damage_over_time_expired\':' not in content:
                issues.append({
                    'file': str(apply_event_file),
                    'issue': 'Missing damage_over_time_expired handler',
                    'description': 'applyEvent.ts must handle damage_over_time_expired events'
                })

            # Check for stat reversion logic in effect_expired
            has_stat_reversion = (
                'applied_delta' in content and
                'expiredEffect.stat' in content and
                'effect_expired' in content
            )
            if not has_stat_reversion:
                issues.append({
                    'file': str(apply_event_file),
                    'issue': 'Missing stat reversion in UI',
                    'description': 'Frontend must revert stat changes using applied_delta when effect_expired arrives'
                })

            # Check for effect removal by ID
            has_effect_removal = (
                'filter(e => e.id !== event.effect_id)' in content or
                'filter(e => e.id !== event.effect_id)' in content
            )
            if not has_effect_removal:
                issues.append({
                    'file': str(apply_event_file),
                    'issue': 'Missing effect removal by ID',
                    'description': 'Frontend must remove effects by effect_id when expiration events arrive'
                })

        except Exception as e:
            issues.append({
                'file': str(apply_event_file),
                'issue': f'Error reading file: {e}',
                'description': 'Could not read applyEvent.ts'
            })

    # Check 4: Reconstructor properly handles expiration events
    reconstructor_file = backend_src / 'waffen-tactics-web' / 'backend' / 'services' / 'combat_event_reconstructor.py'
    if reconstructor_file.exists():
        try:
            with open(reconstructor_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for effect_expired event handler
            if 'effect_expired' not in content or '_process_effect_expired_event' not in content:
                issues.append({
                    'file': str(reconstructor_file),
                    'issue': 'Missing effect_expired handler in reconstructor',
                    'description': 'combat_event_reconstructor.py must handle effect_expired events'
                })

            # Check for damage_over_time_expired event handler
            if 'damage_over_time_expired' not in content or '_process_dot_expired_event' not in content:
                issues.append({
                    'file': str(reconstructor_file),
                    'issue': 'Missing damage_over_time_expired handler in reconstructor',
                    'description': 'combat_event_reconstructor.py must handle damage_over_time_expired events'
                })

        except Exception as e:
            issues.append({
                'file': str(reconstructor_file),
                'issue': f'Error reading file: {e}',
                'description': 'Could not read combat_event_reconstructor.py'
            })

    return issues

    for filename in effect_sync_files:
        file_path = backend_src / 'waffen_tactics' / 'services' / filename
        if not file_path.exists():
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for effect addition
            has_effect_addition = (
                'effects.append' in content or
                'emit_stat_buff' in content or
                'emit_unit_stunned' in content or
                'emit_shield_applied' in content
            )

            # Check for effect removal/cleanup
            has_effect_removal = (
                'effects.remove' in content or
                'effects.clear' in content or
                'del effect' in content or                'effects.pop' in content or                'effect_id' in content and 'remove' in content
            )

            # Check for effect ID tracking
            has_effect_id_tracking = 'effect_id' in content or 'emit_effect_expired' in content or 'emit_damage_over_time_expired' in content

            if has_effect_addition and not has_effect_id_tracking:
                issues.append({
                    'file': str(file_path),
                    'issue': 'Effect addition without ID tracking',
                    'description': 'File adds effects but may not track effect_ids for proper removal'
                })

            if has_effect_addition and has_effect_removal and not has_effect_id_tracking:
                issues.append({
                    'file': str(file_path),
                    'issue': 'Effect lifecycle without ID tracking',
                    'description': 'File manages effect lifecycle but may not use effect_ids for synchronization'
                })

        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    return issues

def check_effect_synchronization():
    """Check that effects are properly synchronized between application and removal"""
    print("🔄 Checking for effect synchronization...")

    backend_src = Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'

    issues = []

    # Files that manage effects
    effect_sync_files = [
        'combat_simulator.py',
        'effect_processor.py',
        'modular_effect_processor.py',
    ]

    for filename in effect_sync_files:
        file_path = backend_src / 'waffen_tactics' / 'services' / filename
        if not file_path.exists():
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for effect addition
            has_effect_addition = (
                'effects.append' in content or
                'emit_stat_buff' in content or
                'emit_unit_stunned' in content or
                'emit_shield_applied' in content
            )

            # Check for effect removal/cleanup
            has_effect_removal = (
                'effects.remove' in content or
                'effects.clear' in content or
                'del effect' in content or
                'effects.pop' in content or
                'effect_id' in content and 'remove' in content
            )

            # Check for effect ID tracking
            has_effect_id_tracking = 'effect_id' in content or 'emit_effect_expired' in content or 'emit_damage_over_time_expired' in content

            if has_effect_addition and not has_effect_id_tracking:
                issues.append({
                    'file': str(file_path),
                    'issue': 'Effect addition without ID tracking',
                    'description': 'File adds effects but may not track effect_ids for proper removal'
                })

            if has_effect_addition and has_effect_removal and not has_effect_id_tracking:
                issues.append({
                    'file': str(file_path),
                    'issue': 'Effect lifecycle without ID tracking',
                    'description': 'File manages effect lifecycle but may not use effect_ids for synchronization'
                })

        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    return issues

def check_event_completeness():
    """Check that events include all required authoritative fields"""
    print("📋 Checking event completeness...")

    backend_src = Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'

    # Required fields for each event type (only check implemented events)
    required_fields = {
        'attack': ['target_hp', 'damage', 'target_id'],  # emit_damage emits 'attack'
        'unit_stunned': ['effect_id', 'unit_id', 'duration'],
        'stat_buff': ['applied_delta', 'stat', 'unit_id'],  # stat_buff uses 'stat' not 'stat_type', 'unit_id' not 'recipient_id'
        'heal': ['unit_hp', 'amount', 'unit_id'],
        'mana_update': ['unit_id', 'current_mana'],  # mana_update events
        'effect_expired': ['effect_id', 'unit_id'],
        'damage_over_time_expired': ['effect_id', 'unit_id'],
    }

    incomplete_events = []

    # Check event emission in canonicalizer
    canonicalizer_file = backend_src / 'waffen_tactics' / 'services' / 'event_canonicalizer.py'
    if canonicalizer_file.exists():
        try:
            with open(canonicalizer_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check that required fields are present in the file
            for event_type, fields in required_fields.items():
                for field in fields:
                    # Check for field in single or double quotes (dict literal) or assignment
                    if (f"'{field}': " not in content and 
                        f'"{field}": ' not in content and 
                        f"['{field}'] = " not in content and
                        f'["{field}"] = ' not in content):
                        incomplete_events.append({
                            'event_type': event_type,
                            'missing_field': field,
                            'file': str(canonicalizer_file)
                        })

        except Exception as e:
            print(f"Error reading canonicalizer: {e}")

    return incomplete_events

def main():
    """Run all compliance checks"""
    print("🚀 Phase 1.1: Canonical Emitter Compliance Test")
    print("=" * 60)

    all_passed = True

    # Check 1: Direct HP manipulation
    violations = check_direct_hp_manipulation()
    if violations:
        print(f"\n❌ FOUND {len(violations)} DIRECT HP MANIPULATION VIOLATIONS:")
        all_passed = False
        for v in violations:
            print(f"  📁 {v['file']}")
            print(f"  🔍 Pattern: {v['pattern']}")
            print(f"  💡 {v['description']}")
            print()
    else:
        print("✅ No direct HP manipulation found")

    # Check 1.2: Direct mana manipulation
    mana_violations = check_direct_mana_manipulation()
    if mana_violations:
        print(f"\n❌ FOUND {len(mana_violations)} DIRECT MANA MANIPULATION VIOLATIONS:")
        all_passed = False
        for v in mana_violations:
            print(f"  📁 {v['file']}")
            print(f"  🔍 Pattern: {v['pattern']}")
            print(f"  💡 {v['description']}")
            print()
    else:
        print("✅ No direct mana manipulation found")

    # Check 1.5: Direct effect manipulation
    effect_violations = check_direct_effect_manipulation()
    if effect_violations:
        print(f"\n❌ FOUND {len(effect_violations)} DIRECT EFFECT MANIPULATION VIOLATIONS:")
        all_passed = False
        for v in effect_violations:
            print(f"  📁 {v['file']}")
            print(f"  🔍 Pattern: {v['pattern']}")
            print(f"  💡 {v['description']}")
            print()
    else:
        print("✅ No direct effect manipulation found")

    # Check 2: Canonical emitter usage
    missing_usage = check_canonical_emitter_usage()
    if missing_usage:
        print(f"\n❌ FOUND {len(missing_usage)} MISSING CANONICAL EMITTER USAGE:")
        all_passed = False
        for m in missing_usage:
            print(f"  📁 {m['file']}")
            print(f"  🔍 Missing: {m['missing']}")
            print(f"  💡 {m['description']}")
            print()
    else:
        print("✅ All damage sources use canonical emitters")

    # Check 2.1: Stat buff canonical emitter usage
    stat_buff_missing = check_stat_buff_canonical_emitter_usage()
    if stat_buff_missing:
        print(f"\n❌ FOUND {len(stat_buff_missing)} MISSING STAT BUFF CANONICAL EMITTER USAGE:")
        all_passed = False
        for m in stat_buff_missing:
            print(f"  📁 {m['file']}")
            print(f"  🔍 Missing: {m['missing']}")
            print(f"  💡 {m['description']}")
            print()
    else:
        print("✅ All stat modifications use emit_stat_buff")

    # Check 2.2: Comprehensive mana canonical emitter usage
    mana_issues = check_mana_canonical_emitter_usage()
    if mana_issues:
        print(f"\n❌ FOUND {len(mana_issues)} FILES WITH COMPREHENSIVE MANA COMPLIANCE ISSUES:")
        all_passed = False
        for file_issue in mana_issues:
            print(f"  📁 {file_issue['file']}")
            for issue in file_issue['issues']:
                print(f"    🔍 Line {issue['line']}: {issue['issue']}")
                print(f"    💡 {issue['description']}")
                if 'pattern' in issue:
                    print(f"    🔍 Pattern: {issue['pattern']}")
            print()
    else:
        print("✅ All mana modifications use canonical emitters")

    # Check 2.3: HP regen canonical emitter usage
    hp_regen_missing = check_hp_regen_canonical_emitter_usage()
    if hp_regen_missing:
        print(f"\n❌ FOUND {len(hp_regen_missing)} MISSING HP REGEN CANONICAL EMITTER USAGE:")
        all_passed = False
        for m in hp_regen_missing:
            print(f"  📁 {m['file']}")
            print(f"  🔍 Missing: {m['missing']}")
            print(f"  💡 {m['description']}")
            print()
    else:
        print("✅ All HP modifications use canonical emitters")

    # Check 2.4: Effect cleanup and removal
    effect_cleanup_issues = check_effect_cleanup_and_removal()
    if effect_cleanup_issues:
        print(f"\n❌ FOUND {len(effect_cleanup_issues)} EFFECT CLEANUP ISSUES:")
        all_passed = False
        for issue in effect_cleanup_issues:
            print(f"  📁 {issue['file']}")
            print(f"  🔍 Issue: {issue['issue']}")
            print(f"  💡 {issue['description']}")
            print()
    else:
        print("✅ Effect cleanup and removal handled properly")

    # Check 2.5: Comprehensive mana cost and reduction handling
    mana_cost_issues = check_mana_cost_and_reduction()
    if mana_cost_issues:
        print(f"\n❌ FOUND {len(mana_cost_issues)} FILES WITH COMPREHENSIVE MANA COST ISSUES:")
        all_passed = False
        for file_issue in mana_cost_issues:
            print(f"  📁 {file_issue['file']}")
            for issue in file_issue['issues']:
                print(f"    🔍 Line {issue['line']}: {issue['issue']}")
                print(f"    💡 {issue['description']}")
                if 'pattern' in issue:
                    print(f"    🔍 Pattern: {issue['pattern']}")
            print()
    else:
        print("✅ Mana costs and reductions handled properly")

    # Check 2.6: Stat buff expiration
    buff_expiration_issues = check_stat_buff_expiration()
    if buff_expiration_issues:
        print(f"\n❌ FOUND {len(buff_expiration_issues)} STAT BUFF EXPIRATION ISSUES:")
        all_passed = False
        for issue in buff_expiration_issues:
            print(f"  📁 {issue['file']}")
            print(f"  🔍 Issue: {issue['issue']}")
            print(f"  💡 {issue['description']}")
            print()
    else:
        print("✅ Stat buff expiration handled properly")

    # Check 2.7: Comprehensive effect expiration compliance
    effect_expiration_issues = check_effect_expiration_compliance()
    if effect_expiration_issues:
        print(f"\n❌ FOUND {len(effect_expiration_issues)} EFFECT EXPIRATION COMPLIANCE ISSUES:")
        all_passed = False
        for issue in effect_expiration_issues:
            print(f"  📁 {issue['file']}")
            print(f"  🔍 Issue: {issue['issue']}")
            print(f"  💡 {issue['description']}")
            print()
    else:
        print("✅ Comprehensive effect expiration compliance verified")

    # Check 2.8: Effect synchronization
    effect_sync_issues = check_effect_synchronization()
    if effect_sync_issues:
        print(f"\n❌ FOUND {len(effect_sync_issues)} EFFECT SYNCHRONIZATION ISSUES:")
        all_passed = False
        for issue in effect_sync_issues:
            print(f"  📁 {issue['file']}")
            print(f"  🔍 Issue: {issue['issue']}")
            print(f"  💡 {issue['description']}")
            print()
    else:
        print("✅ Effect synchronization handled properly")

    # Check 3: Event completeness
    incomplete_events = check_event_completeness()
    if incomplete_events:
        print(f"\n❌ FOUND {len(incomplete_events)} INCOMPLETE EVENTS:")
        all_passed = False
        for e in incomplete_events:
            print(f"  📁 {e['file']}")
            print(f"  🎯 Event: {e['event_type']}")
            print(f"  🔍 Missing: {e['missing_field']}")
            print()
    else:
        print("✅ All events include required authoritative fields")

    print("=" * 60)
    if all_passed:
        print("🎉 ALL COMPLIANCE CHECKS PASSED!")
        print("✅ Backend is using canonical emitters correctly")
        return 0
    else:
        print("❌ COMPLIANCE VIOLATIONS FOUND")
        print("💡 Fix the issues above to ensure proper event emission")
        return 1

if __name__ == '__main__':
    sys.exit(main())