"""Materialize the Plane-approved Set 2 dataset into the active JSON files."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def passive(unit_id: str, name: str, description: str, trigger: str, runtime_type: str, **runtime):
    return {
        "id": f"set2.passive.{unit_id}",
        "name": name,
        "description": description,
        "trigger": trigger,
        "target": "self",
        "conditions": {},
        "effect": {"type": "set2_unit", "runtime": runtime_type},
        "limit": {"stacking": "none"},
        "kind": "set2_unit",
        "runtime": {"type": runtime_type, **runtime},
    }


UNITS = [
    ("anamol04", "Anamol04", 2, "fighter", "Szachista", "Konfident", "anamol04.png", passive("anamol04", "Anamol04", "Bonusowy atak leczy 8% maks. HP i daje +15% szybkości ataku na 2 s.", "on_bonus_attack", "heal_and_attack_speed", heal_percent=8, attack_speed_percent=15)),
    ("fiko", "Fiko", 5, "duelist", "Figlarz", "Starociota", "fiko.png", passive("fiko", "Fiko", "Bonusowy atak ogłusza na 1,5 s i zadaje dodatkowe 100% obrażeń.", "on_bonus_attack", "stun_and_double_damage")),
    ("uhla", "Uhla", 3, "fighter", "Konfident", "Konfident", "uhla.png", passive("uhla", "Uhla", "40% many zdobytej za atak przekazuje innemu Konfidentowi, maks. 5 many na zdarzenie.", "on_attack", "mana_transfer", percent=40, cap=5)),
    ("szanowny_kantor", "Szanowny Kantor", 4, "defender", "Twórca", "Femboy", "kantor.png", passive("szanowny_kantor", "Szanowny Kantor", "Na starcie losowy sojusznik z pierwszej linii otrzymuje tarczę 150 na 4 s.", "on_start", "frontline_ally_shield", amount=150)),
    ("chessowy_mentos", "Chessowy Mentos", 2, "mage", "Twórca", "Muzyk", "chessowymentos.png", passive("chessowy_mentos", "Chessowy Mentos", "Generuje o 100% więcej many przez pierwsze 4,4 s.", "on_start", "start_mana_generation")),
    ("yossarian", "Yossarian", 3, "duelist", "Figlarz", "Starociota", "yossarian.png", passive("yossarian", "Yossarian", "Bonusowy atak zamienia linię jednego losowego wroga.", "on_bonus_attack", "swap_enemy_line")),
    ("galanonim", "GalAnonim", 5, "fighter", "Muzyk", "Femboy", "galanonimpl-avatar-1024.png", passive("galanonim", "GalAnonim", "Bonusowy atak leczy sojusznika z najmniejszym HP za wartość bonusowych obrażeń, maks. 120.", "on_bonus_attack", "heal_lowest_bonus_damage", cap=120)),
    ("pytl", "Pytl", 4, "mage", "Konfident", "Inwestor", "_pytl-avatar-1024.png", passive("pytl", "Pytl", "Wrogowie z mniejszym HP atakują o 15% wolniej.", "on_start", "start_enemy_attack_debuff")),
    ("sofronow", "Sofronow", 1, "defender", "Szachista", "Starociota", "sofronow960-avatar-1024.png", passive("sofronow", "Sofronow", "Na starcie zadaje najsłabszemu wrogowi obrażenia równe 15% jego maks. HP.", "on_start", "start_enemy_damage_lowest")),
    ("alyson_stark", "AlysonStark", 4, "duelist", "Weeb", "Starociota", "alyson.jpg", passive("alyson_stark", "AlysonStark", "Sojusznicy z mniejszym atakiem otrzymują +30% szybkości ataku.", "on_start", "start_attack_speed_if_lower")),
    ("skibidi_kubus", "SkibidiKubuś", 1, "duelist", "Nowociota", None, "skibidi.png", passive("skibidi_kubus", "SkibidiKubuś", "Ma 10/20/30% szansy na unik.", "on_damage_received", "dodge", chance_percent=10)),
    ("aus_sher", "auSSher", 3, "mage", "Weeb", "Nowociota", "ausher.png", passive("aus_sher", "auSSher", "Bonusowy atak leczy sojusznika z największym atakiem za 10% jego maks. HP.", "on_bonus_attack", "heal_highest_attack", heal_percent=10)),
    ("szalwia", "szalwia", 3, "mage", "Figlarz", "Femboy", "szalwia.png", passive("szalwia", "szalwia", "Na starcie osłabia najsilniejszego wroga o 15% ataku na 3 s i ogłusza innego na 0,75 s.", "on_start", "start_enemy_attack_debuff")),
    ("mr0czeq1", "mr0czeq1", 2, "mage", "Nowociota", "Femboy", "mroczeq.png", passive("mr0czeq1", "mr0czeq1", "Na starcie daje sobie i losowemu sojusznikowi +1 many/s.", "on_start", "start_random_mana_regen")),
    ("optimusprime", "OptimusPrime", 3, "fighter", "Haxball", "Muzyk", "optimusprime67676767-avatar-1024.png", passive("optimusprime", "OptimusPrime", "Bonusowy atak usuwa 40% aktualnej many celu, maks. 10.", "on_bonus_attack", "mana_burn", percent=40, cap=10)),
    ("kotmarcek", "KotMarcek", 2, "duelist", "Femboy", "Haxball", "marcek_heban-avatar-1024.png", passive("kotmarcek", "KotMarcek", "Na starcie +15% szybkości ataku; bonusowy atak przekazuje ten bonus losowemu sojusznikowi.", "on_start", "start_attack_speed")),
    ("bbobel", "bbobel", 1, "defender", "Nowociota", "Konfident", "bbobel.png", passive("bbobel", "bbobel", "Przy 50% HP leczy 20% maks. HP przez 3 s, raz na walkę.", "on_damage_received", "half_hp_regen", heal_percent=20, duration=3)),
    ("fallensmokk", "FallenSmokk", 2, "fighter", "Nowociota", "Weeb", "fallensmok.png", passive("fallensmokk", "FallenSmokk", "Śmierć sojusznika daje +15% ataku i obrony na 3 s, maks. 2 stosy.", "on_ally_death", "ally_death_buff")),
    ("jaeger", "Jaeger", 1, "defender", "Nowociota", "Figlarz", "jaeger.png", passive("jaeger", "Jaeger", "Bonusowy atak daje tarczę równą 10% maks. HP na 3 s.", "on_bonus_attack", "bonus_shield", percent=10)),
    ("kaktusek", "Kaktusek", 2, "fighter", "Wierny widz", "Weeb", "kaktusekmatusek-avatar-1024.png", passive("kaktusek", "Kaktusek", "Po śmierci trzy razy uderza ten sam losowy cel za 100% ataku, raz na walkę.", "on_death", "death_strike")),
    ("empty_melancholy", "EmptyMelancholy", 3, "defender", "Wierny widz", "Weeb", "melancholykillsme-avatar-1024.png", passive("empty_melancholy", "EmptyMelancholy", "Po otrzymaniu trafienia zyskuje +8 obrony na 1 s, efekt się odświeża bez kumulacji.", "on_damage_received", "defense_on_hit")),
    ("4tune", "4Tune", 4, "duelist", "Figlarz", "Inwestor", "4tune.png", passive("4tune", "4Tune", "Śmierć sojusznika daje +100% do następnego bonusowego ataku, maks. 2 stosy.", "on_ally_death", "set2_4tune")),
    ("jadlainwestycji", "JaDlaInwestycji", 3, "duelist", "Wierny widz", "Inwestor", "xkuba.h-avatar-1024.png", passive("jadlainwestycji", "JaDlaInwestycji", "+15% obrażeń przeciwko jednostkom 4g i +30% przeciwko 5g.", "on_attack", "damage_vs_cost")),
    ("boczek", "boczek", 1, "defender", "Wierny widz", "Konfident", "vmwu-avatar-1024.png", passive("boczek", "boczek", "Na starcie +4 HP/s do końca walki.", "on_start", "start_hp_regen", amount=4)),
    ("merex", "merex", 5, "duelist", "Femboy", "Starociota", "nos.gov-avatar-1024.png", passive("merex", "merex", "Po zadaniu obrażeń zyskuje +4% szybkości ataku, maks. +40%, odnowienie 0,5 s.", "on_damage_dealt", "attack_speed_after_damage")),
    ("marcel_galadotka", "Marcel Galadotka", 2, "mage", "Wierny widz", "Nowociota", "marcelgaladotka-avatar-1024.png", passive("marcel_galadotka", "Marcel Galadotka", "Za każdy normalny atak otrzymuje dodatkowe 2 many; bonusowy atak nie daje tej premii.", "on_attack", "normal_attack_mana", amount=2)),
    ("klemens_zydoslawski", "Klemens Żydosławski", 4, "mage", "Figlarz", "Twórca", "klemens.png", passive("klemens_zydoslawski", "Klemens Żydosławski", "Bonusowy atak trafia każdego wroga z pierwszej linii za 15% własnego ataku.", "on_bonus_attack", "bonus_frontline_damage", percent=15)),
    ("nicosc", "Nicość", 4, "defender", "Konfident", "Wierny widz", "niko_official-avatar-1024.png", passive("nicosc", "Nicość", "Raz na walkę odradza się z 50% maks. HP i jest nieobieralna przez 0,75 s.", "on_death", "revive")),
    ("knauff", "Knauff", 3, "duelist", "Haxball", "Inwestor", "knauff.png", passive("knauff", "Knauff", "Poniżej 50% HP otrzymuje +30% szybkości ataku.", "on_damage_received", "low_hp_attack_speed")),
    ("vitas", "Vitas", 5, "duelist", "Figlarz", "Starociota", "vitas.png", passive("vitas", "Vitas", "Bonusowy atak ogłusza tylną linię wroga na 1 s.", "on_bonus_attack", "bonus_stun_backline")),
    ("szachowymentor", "SzachowyMentor", 5, "mage", "Weeb", "Szachista", "szachowymentor.1996-avatar-1024.png", passive("szachowymentor", "SzachowyMentor", "Za każdego sojusznika z tyłu +1 many/s, maks. 3; co 5 s tarcza 40 za każdego sojusznika z przodu, maks. 120/tick i 240 łącznie.", "per_second", "mentor_shield")),
    ("9wojtaz9", "9wojtaz9", 1, "duelist", "Wierny widz", "Konfident", "9wojtaz9.png", passive("9wojtaz9", "9wojtaz9", "Bonusowy atak ogłusza jeden cel na 0,25 s.", "on_bonus_attack", "bonus_stun", duration=0.25)),
]


TRAITS = [
    ("konfident", "Konfident", [3, 5, 7], "on_attack", "trait", [15, 25, 35], "Mana zdobyta z ataku jest przekazywana jednemu innemu żyjącemu Konfidentowi; bez samoprzepływu i rekurencji."),
    ("wierny_widz", "Wierny widz", [3, 5, 6], "per_second", "trait", [10, 15, 20], "Po 5 s: +10/15/20% ataku i obrony oraz tarcza 5/8/10% maks. HP; raz na walkę."),
    ("nowociota", "Nowociota", [3, 5, 7], "passive", "trait", [40, 60, 80], "Przez pierwsze 2 s +40/60/80% szybkości ataku; odświeżane po zabiciu, bez kumulacji."),
    ("figlarz", "Figlarz", [2, 4, 6], "passive", "team", [1, 1, 1], "Na starcie ogłusza wszystkich wrogów na 1 s; powtarza po śmierci Figlarza, raz na zdarzenie śmierci."),
    ("weeb", "Weeb", [2, 4, 6], "passive", "trait", [15, 25, 35], "Najsilniejsza jednostka z tylnej linii otrzymuje +15/25/35% szybkości ataku; remisy rozstrzyga stabilne ID."),
    ("starociota", "Starociota", [2, 3, 5], "passive", "trait", [10, 20, 30], "+10/20/30 obrony i +2/4/6 HP/s; po śmierci Starocioty efekt odświeża się bez kumulacji."),
    ("inwestor", "Inwestor", [2, 3, 4], "passive", "team", [5, 10, 15], "Bonus do wszystkich statystyk wynosi 5/10/15% wartości sprzedaży jednostek na planszy, maks. 30%."),
    ("femboy", "Femboy", [2, 3, 5], "on_bonus_attack", "trait", [10, 15, 20], "Bonusowy atak leczy wszystkich sojuszników za 10/15/20% ataku Femboya; bez overhealu."),
    ("szachista", "Szachista", [2, 3], "passive", "trait", [10, 20], "Pierwsza linia zaczyna z tarczą 10/20% maks. HP, tylna zadaje +25/50% obrażeń bonusowego ataku."),
    ("tworca", "Twórca", [2, 3], "per_second", "team", [2, 4], "Cała drużyna regeneruje 2/4 many na sekundę."),
    ("muzyk", "Muzyk", [1, 2], "on_bonus_attack", "trait", [5, 10], "Bonusowy atak daje 5/10 many każdemu innemu żyjącemu sojusznikowi; Muzyk jest wykluczony."),
    ("haxball", "Haxball", [2, 3], "on_damage_received", "trait", [50, 50], "50% obrażeń otrzymywanych przez Haxballa dzieli się równo między innych żyjących Haxballów; brak odbiorcy oznacza brak przekierowania."),
]


def trait_record(trait_id: str, name: str, thresholds: list[int], trigger: str, target: str, values: list[int], description: str):
    tiers = []
    for tier, value in enumerate(values, start=1):
        tiers.append([
            {
                "trigger": trigger,
                "conditions": {},
                "target": target,
                "effect": {"type": "set2_trait", "trait": name, "tier": tier, "value": value},
                "limit": {"stacking": "none"},
                "rewards": [{"type": "special", "effect": "set2_trait", "trait": name, "tier": tier, "value": value}],
            }
        ])
    return {
        "id": f"set2.trait.{trait_id}",
        "name": name,
        "type": "trait",
        "description": description,
        "target": target,
        "thresholds": thresholds,
        "threshold_descriptions": [description for _ in thresholds],
        "modular_effects": tiers,
    }


def main() -> None:
    units = []
    for unit_id, name, cost, role, trait_a, trait_b, avatar, passive_definition in UNITS:
        traits = [trait for trait in (trait_a, trait_b) if trait]
        record = {
            "id": unit_id,
            "name": name,
            "factions": traits[:1],
            "classes": traits[1:],
            "traits": traits,
            "cost": cost,
            "role": role,
            "max_mana": 40 + cost * 10,
            "avatar": f"/avatars/set2/{avatar}",
            "skill": {
                "name": "Atak podstawowy",
                "description": "Zadaje podstawowe obrażenia wybranemu celowi.",
                "mana_cost": 40 + cost * 10,
                "effects": [{"type": "damage", "target": "single_enemy", "amount": 100}],
            },
            "passive": passive_definition,
        }
        if len(traits) != 2:
            record["trait_exception"] = "SkibidiKubuś ma jeden trait zgodnie z kontraktem Plane."
        units.append(record)

    factions = sorted({trait for unit in units for trait in unit["factions"]})
    classes = sorted({trait for unit in units for trait in unit["classes"]})
    (ROOT / "units.json").write_text(json.dumps({"units": units, "factions": factions, "classes": classes}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    traits = [trait_record(*definition) for definition in TRAITS]
    (ROOT / "traits.json").write_text(json.dumps({"traits": traits}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
