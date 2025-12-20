"""
Skill Parser - Parses and validates skill definitions from JSON
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from waffen_tactics.models.skill import Skill, Effect, EffectType, TargetType


class SkillParseError(Exception):
    """Raised when skill parsing fails"""
    pass


class SkillParser:
    """Parses and validates skill definitions"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._effect_schema = self._build_effect_schema()

    def _build_effect_schema(self) -> Dict[str, Dict[str, Any]]:
        """Build validation schema for effects"""
        return {
            EffectType.DAMAGE: {
                'required': ['amount'],
                'optional': ['damage_type']
            },
            EffectType.HEAL: {
                'required': ['amount'],
                'optional': []
            },
            EffectType.SHIELD: {
                'required': ['amount', 'duration'],
                'optional': []
            },
            EffectType.BUFF: {
                'required': ['stat', 'value', 'duration'],
                'optional': ['value_type']  # 'flat' or 'percentage'
            },
            EffectType.DEBUFF: {
                'required': ['stat', 'value', 'duration'],
                'optional': ['value_type']
            },
            EffectType.STUN: {
                'required': ['duration'],
                'optional': []
            },
            EffectType.DELAY: {
                'required': ['duration'],
                'optional': []
            },
            EffectType.REPEAT: {
                'required': ['count', 'effects'],
                'optional': []
            },
            EffectType.CONDITIONAL: {
                'required': ['condition', 'effects'],
                'optional': ['else_effects']
            },
            EffectType.DAMAGE_OVER_TIME: {
                'required': ['damage', 'duration', 'interval'],
                'optional': ['damage_type']
            }
        }

    def parse_skill_from_unit_data(self, unit_data: Dict[str, Any]) -> Optional[Skill]:
        """Parse skill from unit JSON data"""
        skill_data = unit_data.get('skill')
        if not skill_data:
            return None

        try:
            # If unit data omits mana_cost (many legacy unit defs), prefer to
            # fill it from unit's max_mana so parsing doesn't fail during bulk load.
            sd = skill_data.copy()
            if 'mana_cost' not in sd:
                sd['mana_cost'] = unit_data.get('max_mana') or (unit_data.get('stats') or {}).get('max_mana') or 100
            return self._parse_skill(sd)
        except Exception as e:
            unit_id = unit_data.get('id', 'unknown')
            self.logger.error(f"Failed to parse skill for unit {unit_id}: {e}")
            self.logger.debug(f"Skill data for unit {unit_id}: {skill_data}")
            raise SkillParseError(f"Failed to parse skill for unit {unit_id}: {e}")

    def _parse_skill(self, skill_data: Dict[str, Any]) -> Skill:
        """Parse skill dictionary into Skill object"""
        if not isinstance(skill_data, dict):
            raise SkillParseError("Skill data must be a dictionary")

        # Validate required fields
        required_fields = ['name', 'description', 'effects', 'mana_cost']
        for field in required_fields:
            if field not in skill_data:
                raise SkillParseError(f"Missing required field: {field}")

        # Parse effects
        effects = []
        for i, effect_data in enumerate(skill_data['effects']):
            try:
                effect = self._parse_effect(effect_data)
                effects.append(effect)
            except Exception as e:
                self.logger.error(f"Error parsing effect {i} in skill '{skill_data.get('name', 'unknown')}': {e}")
                self.logger.debug(f"Effect data {i}: {effect_data}")
                raise SkillParseError(f"Error parsing effect {i}: {e}")

        return Skill(
            name=skill_data['name'],
            description=skill_data['description'],
            mana_cost=skill_data.get('mana_cost'),  # Will be None for new data; use unit.max_mana at runtime
            effects=effects
        )

    def _parse_effect(self, effect_data: Dict[str, Any]) -> Effect:
        """Parse effect dictionary into Effect object"""
        if not isinstance(effect_data, dict):
            raise SkillParseError("Effect data must be a dictionary")

        if 'type' not in effect_data:
            raise SkillParseError("Effect missing 'type' field")

        effect_type_str = effect_data['type']
        try:
            effect_type = EffectType(effect_type_str)
        except ValueError:
            self.logger.error(f"Unknown effect type: {effect_type_str}")
            self.logger.debug(f"Effect data: {effect_data}")
            raise SkillParseError(f"Unknown effect type: {effect_type_str}")

        # Validate effect parameters
        self._validate_effect_params(effect_type, effect_data)

        # Parse target
        target_str = effect_data.get('target', 'self')
        try:
            target = TargetType(target_str)
        except ValueError:
            raise SkillParseError(f"Unknown target type: {target_str}")

        # Remove type and target from params
        params = effect_data.copy()
        params.pop('type', None)
        params.pop('target', None)

        return Effect(
            type=effect_type,
            target=target,
            params=params
        )

    def _validate_effect_params(self, effect_type: EffectType, effect_data: Dict[str, Any]):
        """Validate effect parameters against schema"""
        schema = self._effect_schema.get(effect_type)
        if not schema:
            return  # Unknown effect type, skip validation

        # Check required fields
        for required in schema['required']:
            if required not in effect_data:
                self.logger.error(f"Effect {effect_type.value} missing required parameter: {required}")
                self.logger.debug(f"Effect data: {effect_data}")
                raise SkillParseError(f"Effect {effect_type.value} missing required parameter: {required}")

        # Special validation for nested effects
        if effect_type == EffectType.REPEAT:
            if not isinstance(effect_data.get('effects'), list):
                raise SkillParseError("Repeat effect must have 'effects' list")
            for i, nested_effect in enumerate(effect_data['effects']):
                try:
                    self._parse_effect(nested_effect)
                except Exception as e:
                    self.logger.error(f"Error in repeat effect {i}: {e}")
                    self.logger.debug(f"Nested effect data {i}: {nested_effect}")
                    raise SkillParseError(f"Error in repeat effect {i}: {e}")

        elif effect_type == EffectType.CONDITIONAL:
            if not isinstance(effect_data.get('effects'), list):
                raise SkillParseError("Conditional effect must have 'effects' list")
            for i, nested_effect in enumerate(effect_data['effects']):
                try:
                    self._parse_effect(nested_effect)
                except Exception as e:
                    self.logger.error(f"Error in conditional effect {i}: {e}")
                    self.logger.debug(f"Nested effect data {i}: {nested_effect}")
                    raise SkillParseError(f"Error in conditional effect {i}: {e}")

            else_effects = effect_data.get('else_effects')
            if else_effects and not isinstance(else_effects, list):
                raise SkillParseError("Conditional effect 'else_effects' must be a list")


# Global parser instance
skill_parser = SkillParser()
