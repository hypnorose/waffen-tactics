"""
Effect Processor - Coordinates effect processing using utility classes
"""
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from .stat_calculator import StatCalculator
from .stat_buff_handlers import StatBuffHandler, AttackBuffHandler, DefenseBuffHandler, HpBuffHandler, AttackSpeedBuffHandler, ManaRegenBuffHandler
from .recipient_resolver import RecipientResolver

if TYPE_CHECKING:
    from .combat_unit import CombatUnit


class EffectProcessor:
    """Coordinates effect processing using utility classes"""

    def __init__(self):
        self.stat_calculator = StatCalculator()
        self.recipient_resolver = RecipientResolver()
        self.buff_handlers = {
            'attack': AttackBuffHandler(),
            'defense': DefenseBuffHandler(),
            'hp': HpBuffHandler(),
            'attack_speed': AttackSpeedBuffHandler(),
            'mana_regen': ManaRegenBuffHandler()
        }

    def process_effect(
        self,
        effect: Dict[str, Any],
        source_unit: 'CombatUnit',
        attacking_team: Optional[List['CombatUnit']] = None,
        defending_team: Optional[List['CombatUnit']] = None,
        attacking_hp: Optional[List[int]] = None,
        defending_hp: Optional[List[int]] = None,
        side: str = ""
    ) -> Dict[str, Any]:
        """
        Process a single effect using utility classes.

        Args:
            effect: The effect configuration
            source_unit: The unit applying the effect
            attacking_team: Attacking team units
            defending_team: Defending team units
            attacking_hp: Attacking team HP values
            defending_hp: Defending team HP values
            side: Which side the effect is happening on

        Returns:
            Processing result with any changes
        """
        result = {
            'processed': False,
            'changes': {},
            'errors': []
        }

        try:
            action = effect.get('action', '')
            target = effect.get('target', 'self')
            only_same_trait = effect.get('only_same_trait', False)

            # Find recipients
            recipients = self.recipient_resolver.find_recipients(
                source_unit, target, only_same_trait,
                attacking_team, defending_team, side
            )

            if not recipients:
                result['errors'].append(f"No recipients found for target {target}")
                return result

            # Process action
            if action == 'kill_buff':
                result = self._process_kill_buff(effect, recipients, result)
            elif action == 'collect_stat':
                result = self._process_collect_stat(effect, source_unit, result)
            else:
                result['errors'].append(f"Unknown action: {action}")

        except Exception as e:
            result['errors'].append(f"Error processing effect: {str(e)}")

        return result

    def _process_kill_buff(
        self,
        effect: Dict[str, Any],
        recipients: List['CombatUnit'],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process kill_buff action"""
        stat_type = effect.get('stat_type', '')
        buff_type = effect.get('buff_type', 'flat')
        value = effect.get('value', 0)

        if stat_type not in self.buff_handlers:
            result['errors'].append(f"Unknown stat type: {stat_type}")
            return result

        handler = self.buff_handlers[stat_type]

        for recipient in recipients:
            try:
                # Calculate buff increment using StatCalculator
                base_value = getattr(recipient, stat_type, 0)
                buff_value = self.stat_calculator.calculate_buff(base_value, value, buff_type == 'percentage')
                increment = buff_value

                # Apply buff using handler - but we need to call it properly
                # For now, just apply the buff directly to the stat
                current_value = getattr(recipient, stat_type, 0)
                new_value = current_value + increment
                setattr(recipient, stat_type, new_value)

                # Track changes
                if 'buffs_applied' not in result['changes']:
                    result['changes']['buffs_applied'] = []
                result['changes']['buffs_applied'].append({
                    'unit_id': getattr(recipient, 'id', 'unknown'),
                    'stat_type': stat_type,
                    'increment': increment
                })

            except Exception as e:
                result['errors'].append(f"Error applying buff to recipient: {str(e)}")

        result['processed'] = True
        return result

    def _process_collect_stat(
        self,
        effect: Dict[str, Any],
        source_unit: 'CombatUnit',
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process collect_stat action"""
        stat_type = effect.get('stat_type', '')

        if not hasattr(source_unit, 'collected_stats'):
            source_unit.collected_stats = {}

        if stat_type not in source_unit.collected_stats:
            source_unit.collected_stats[stat_type] = 0

        # This would be called when collecting stats from defeated enemies
        # The actual collection logic is handled elsewhere
        result['processed'] = True
        return result
