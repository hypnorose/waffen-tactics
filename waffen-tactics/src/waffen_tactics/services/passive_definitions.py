"""Canonical unit passive definitions.

The legacy ``skill`` field remains available for old fixtures, but combat uses
only these readable, non-cast passive definitions.
"""

from copy import deepcopy
from typing import Any, Dict


def _definition(description: str, kind: str, **values: Any) -> Dict[str, Any]:
    return {"description": description, "kind": kind, **values}


PASSIVE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "rafcikd": _definition("Gdy po raz pierwszy spada poniżej 50% HP, otrzymuje 20% redukcji obrażeń na 4 sekundy.", "threshold", threshold=50, effect="damage_reduction", value=20, duration=4),
    "falconbalkon": _definition("Co trzeci podstawowy atak daje mu 10 many.", "attack_count", every=3, effect="mana_self", value=10),
    "piwniczak": _definition("Co czwarty podstawowy atak zmniejsza obronę celu o 10% na 3 sekundy.", "attack_count", every=4, effect="defense_break", value=10, duration=3),
    "capybara": _definition("Jej dodatkowy atak przy pełnej manie leczy ją za 8% maksymalnego HP.", "bonus_attack", effect="heal_self_percent", value=8),
    "kubica": _definition("Na początku walki jego pozycja zmienia efekt: z przodu otrzymuje +15% ataku, a z tyłu +15% prędkości ataku.", "position_start", front={"effect": "stat", "stat": "attack", "value": 15, "value_type": "percentage"}, back={"effect": "stat", "stat": "attack_speed", "value": 15, "value_type": "percentage"}),
    "denvii": _definition("Jego dodatkowy atak zadaje 25% obrażeń wszystkim przeciwnikom z przedniej linii, a głównemu celowi zmniejsza obronę o 10% na 3 sekundy.", "bonus_attack", effect="frontline_secondary", value=25, secondary_value=25, defense_break=10, duration=3),
    "miki": _definition("Priorytetowo atakuje tylną linię przeciwnika.", "start_target", preference="backline"),
    "yossarian": _definition("Jego dodatkowy atak daje wszystkim sojusznikom 5 many.", "bonus_attack", effect="team_mana", value=5),
    "olsak": _definition("Na początku walki otrzymuje +8 obrony.", "start_stat", stat="defense", value=8),
    "pepe": _definition("Co czwarty podstawowy atak odbiera celowi 10 many.", "attack_count", every=4, effect="mana_burn", value=10),
    "hyodo888": _definition("Na początku walki otrzymuje 10% maksymalnego HP.", "start_stat", stat="max_hp", value=10, value_type="percentage"),
    "grzalcia": _definition("Gdy pierwszy sojusznik spadnie poniżej 35% HP, leczy go za 10% maksymalnego HP.", "ally_threshold", threshold=35, effect="heal_percent", value=10),
    "adrianski": _definition("Co piąty podstawowy atak ogłusza cel na 0.75 sekundy, a Adrianski skupia na nim kolejne ataki.", "attack_count", every=5, effect="stun_focus", value=0.75),
    "laylo": _definition("Priorytetowo atakuje cele poniżej 30% HP, a przeciw nim zadaje o 25% więcej obrażeń.", "conditional_attack", threshold=30, effect="target_low_hp", value=25),
    "szachowymentor": _definition("Na początku walki wroga jednostka z najwyższym atakiem zadaje o 15% mniej obrażeń przez całą walkę.", "start_enemy_highest_attack", value=15),
    "mrvlook": _definition("Na początku walki otrzymuje 8% redukcji obrażeń.", "start_effect", effect="damage_reduction", value=8),
    "wodazlodowca": _definition("Na początku walki otrzymuje tarczę równą 12% maksymalnego HP.", "start_effect", effect="shield_percent", value=12),
    "turboglovica": _definition("Jej dodatkowy atak zmniejsza prędkość ataku celu o 15% na 3 sekundy.", "bonus_attack", effect="attack_speed_break", value=15, duration=3),
    "operatorkosiarki": _definition("Priorytetowo atakuje przednią linię, a jego dodatkowy atak zmniejsza obronę celu o 20% na 4 sekundy.", "start_target_bonus", preference="frontline", effect="defense_break", value=20, duration=4),
    "beligol": _definition("Jego dodatkowy atak ignoruje 35% obrony celu i utrzymuje go jako cel dla kolejnych ataków.", "bonus_attack", effect="ignore_defense_focus", value=35),
    "xntentacion": _definition("Gdy pierwszy sojusznik spadnie poniżej 30% HP, otrzymuje on regenerację przez 5 sekund.", "ally_threshold", threshold=30, effect="regen_percent", value=5, duration=5),
    "dawid_czerw": _definition("Na początku walki sojusznicy w przedniej linii otrzymują +8 obrony.", "start_scope_stat", scope="frontline", stat="defense", value=8),
    "jaskol95": _definition("Jej dodatkowy atak daje jej 15% prędkości ataku na 2 sekundy.", "bonus_attack", effect="attack_speed", value=15, duration=2),
    "igor_janik": _definition("Jego dodatkowy atak daje mu +10 ataku na 3 sekundy.", "bonus_attack", effect="attack", value=10, duration=3),
    "olaczka": _definition("Jej dodatkowy atak zadaje 35% obrażeń wszystkim przeciwnikom z przedniej linii.", "bonus_attack", effect="frontline_secondary", value=35),
    "merex": _definition("Gdy po raz pierwszy spada poniżej 45% HP, otrzymuje tarczę równą 20% maksymalnego HP i przez czas jej trwania priorytetowo przyjmuje ataki.", "threshold", threshold=45, effect="shield_focus", value=20),
    "socjopata": _definition("Jego dodatkowy atak blokuje zdobywanie many przez cel na 2 sekundy.", "bonus_attack", effect="mana_lock", duration=2),
    "neko": _definition("Na początku walki pozycja zmienia efekt: z przodu otrzymuje 10% kradzieży życia, a z tyłu atakuje najsłabszy cel.", "position_start", front={"effect": "lifesteal", "value": 10}, back={"effect": "target", "preference": "lowest_hp"}),
    "noname": _definition("Na początku walki cały zespół otrzymuje +5 obrony.", "start_scope_stat", scope="team", stat="defense", value=5),
    "dumb": _definition("Jego dodatkowy atak wybiera przeciwnika z najmniejszą ilością HP.", "start_target_bonus", preference="lowest_hp"),
    "maxas12": _definition("Na początku walki otrzymuje +10 ataku.", "start_stat", stat="attack", value=10),
    "mrozu": _definition("Jego dodatkowy atak daje mu 20% prędkości ataku na 2 sekundy.", "bonus_attack", effect="attack_speed", value=20, duration=2),
    "v7": _definition("Co czwarty podstawowy atak zmniejsza atak celu o 10% na 3 sekundy.", "attack_count", every=4, effect="attack_break", value=10, duration=3),
    "wu_hao": _definition("Co trzeci podstawowy atak zadaje 25% obrażeń drugiemu przeciwnikowi z przedniej linii.", "attack_count", every=3, effect="frontline_secondary", value=25),
    "frajdzia": _definition("Jej ataki zadają o 20% więcej obrażeń celom poniżej 50% HP.", "conditional_attack", threshold=50, effect="damage_low_hp", value=20),
    "wrzechu": _definition("Jej dodatkowy atak zadaje 30% obrażeń najsłabiej rannemu przeciwnikowi poza głównym celem.", "bonus_attack", effect="weakest_secondary", value=30),
    "galanonim": _definition("Na początku walki cały wrogi zespół ma o 5% mniej ataku i obrony.", "start_enemy_debuff", attack=5, defense=5),
    "stalin": _definition("Po zabiciu przeciwnika cały zespół otrzymuje +8 ataku i 10% prędkości ataku na 4 sekundy.", "kill", effect="team_rally", attack=8, attack_speed=10, duration=4),
    "krasu": _definition("Jego dodatkowy atak zadaje 20% obrażeń każdemu przeciwnikowi.", "bonus_attack", effect="all_secondary", value=20),
    "atomowy_coggers": _definition("Gdy po raz pierwszy spada poniżej 35% HP, jego następny atak zadaje 25% obrażeń wszystkim przeciwnikom z przedniej linii.", "threshold", threshold=35, effect="arm_frontline_wave", value=25),
    "szalwia": _definition("Na początku walki pozycja zmienia efekt: przednia linia otrzymuje 5% redukcji obrażeń, a tylna linia +2 regeneracji many.", "position_scope_start", front={"scope": "frontline", "effect": "damage_reduction", "value": 5}, back={"scope": "backline", "effect": "mana_regen", "value": 2}),
    "bosman": _definition("Na początku walki sojusznicy w przedniej linii otrzymują +5 ataku.", "start_scope_stat", scope="frontline", stat="attack", value=5),
    "un4given": _definition("Gdy po raz pierwszy spada poniżej 50% HP, otrzymuje 20% prędkości ataku na 3 sekundy.", "threshold", threshold=50, effect="attack_speed", value=20, duration=3),
    "beudzik": _definition("Co trzeci podstawowy atak daje mu 10% prędkości ataku na 2 sekundy.", "attack_count", every=3, effect="attack_speed", value=10, duration=2),
    "buba": _definition("Na początku walki otrzymuje 8% kradzieży życia.", "start_effect", effect="lifesteal", value=8),
    "hikki": _definition("Co piąty podstawowy atak odbiera celowi 15 many.", "attack_count", every=5, effect="mana_burn", value=15),
    "alyson_stark": _definition("Na początku walki sojusznicy w przedniej linii otrzymują +8 ataku.", "start_scope_stat", scope="frontline", stat="attack", value=8),
    "flaminga": _definition("Jej dodatkowy atak nakłada na cel krótkie obrażenia w czasie.", "bonus_attack", effect="dot", value=8, ticks=3, interval=1),
    "vitas": _definition("Co trzeci podstawowy atak sprawia, że jego następny atak ignoruje 25% tarczy celu.", "attack_count", every=3, effect="shield_pierce", value=25),
    "fiko": _definition("Na początku walki pozycja zmienia efekt: z przodu otrzymuje 12% maksymalnego HP, a z tyłu 10% redukcji obrażeń.", "position_start", front={"effect": "stat", "stat": "max_hp", "value": 12, "value_type": "percentage"}, back={"effect": "damage_reduction", "value": 10}),
    "puszmen12": _definition("Po trzech kolejnych atakach w ten sam cel następny atak zadaje 30% więcej obrażeń.", "attack_count_same_target", every=3, effect="damage", value=30),
    "pan_yakuza": _definition("Po zabiciu przeciwnika otrzymuje +5 ataku do końca walki, maksymalnie 3 razy.", "kill", effect="self_attack_stack", value=5, cap=3),
}


def get_passive_definition(unit_id: str) -> Dict[str, Any] | None:
    """Return a defensive copy so combat state cannot mutate global data."""
    definition = PASSIVE_DEFINITIONS.get(unit_id)
    return deepcopy(definition) if definition else None
