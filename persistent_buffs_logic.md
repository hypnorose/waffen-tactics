# Logika Persistent Buffs w Waffen Tactics

## Wprowadzenie
Persistent buffs to długotrwałe bonusy statów jednostek, które kumulują się między rundami (np. z efektu `per_round_buff` w traitach jak "Starokurwy"). Są przechowywane w `UnitInstance.persistent_buffs` jako słownik `{stat: wartość}`.

## Gdzie są stosowane
Persistent buffs są uwzględniane **po** synergiach w `buffed_stats`, co pozwala na pełne stackowanie (base + synergie + persistent).

## Szczegółowa Logika

### 1. Zastosowanie podczas walki (game_combat.py)
- Po zakończeniu każdej walki (niezależnie od wyniku):
  - Sprawdź aktywne synergie gracza (`player_synergies = game_manager.get_board_synergies(player)`).
  - Dla każdego traitu z efektem `per_round_buff`:
    - Sprawdź `target = trait_obj.get('target', 'trait')`
    - Jeśli `target == 'team'`: zastosuj do wszystkich jednostek na `player.board`
    - Jeśli `target == 'trait'`: zastosuj tylko do jednostek, które mają ten trait (w `unit.factions` lub `unit.classes`)
    - Dla każdej kwalifikującej się jednostki:
      - Oblicz increment:
        - Jeśli `is_percentage: true`: `increment = (unit.stats[stat] * ui.star_level) * (value / 100.0)`
        - Jeśli `is_percentage: false`: `increment = value`
      - Dodaj do istniejącego: `ui.persistent_buffs[stat] += int(increment)`
- Przykład: "Starokurwy" tier 1 dodaje +0.5% HP co rundę → increment = 500 * 0.005 = 2.5 → +2 HP na rundę, niezależnie od wygranej/przegranej.

### 2. Obliczenie Buffed Stats (game_state_utils.py - enrich_player_state)
- Dla każdej jednostki na `player.board`:
  - Oblicz base stats bez persistent buffs:
    - `base_hp = int(base.hp * (1.6 ** (star_level - 1)))`
    - `base_attack = int(base.attack * (1.4 ** (star_level - 1)))`  # Brak persistent dla attack
    - `base_defense = int(base.defense)`  # Brak persistent dla defense
    - `base_attack_speed = float(base.attack_speed)`  # Brak persistent dla attack_speed
  - Następnie zastosuj synergie (`apply_stat_buffs`) na base.
  - Potem dodaj persistent buffs: `buffed_stats[stat] += persistent_buffs.get(stat, 0)`
  - Potem `apply_dynamic_effects`.

### 3. Przykład Stackowania
- Jednostka: base HP = 500, star_level = 1, trait "Starokurwy" tier 1 (+0.5% HP/rundę).
- Runda 1: persistent_buffs["hp"] = 2
- Runda 2: persistent_buffs["hp"] = 4
- W enrich_player_state: base_hp = 500
- Jeśli synergia dodaje +10% HP: buffed_hp = 500 * 1.1 = 550
- Potem dodaj persistent: buffed_hp = 550 + 4 = 554

### 4. Uwagi
- Obecnie tylko HP ma persistent buffs (linia 91 w game_state_utils.py).
- Jeśli dodasz persistent dla innych statów, zaktualizuj game_state_utils.py analogicznie.
- Persistent buffs są resetowane tylko przy sprzedaży jednostki lub innych zdarzeniach (nie zaimplementowane).

## Potencjalne Problemy
- Jeśli persistent_buffs nie są inicjalizowane jako {}, może być błąd.
- Upewnij się, że increment jest int(), aby uniknąć float problemów.</content>
<filePath>/home/ubuntu/waffen-tactics-game/persistent_buffs_logic.md