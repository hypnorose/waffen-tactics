# System Triggerów w Kombacie Waffen Tactics

## Przegląd

System triggerów pozwala na definiowanie efektów, które aktywują się w określonych momentach walki. Każdy efekt może zawierać listę akcji do wykonania.

## Typy Triggerów

### `on_enemy_death`
Aktywuje się, gdy jednostka zabije wroga.
- Dotyczy zabójcy (jednostki z efektem)
- Przykład: Streamerzy zyskują atak/obronę za zabitego wroga

### `on_ally_death`
Aktywuje się, gdy sojusznik jednostki umrze.
- Dotyczy żywych sojuszników
- Przykład: Denciak zyskuje złoto za śmierć sojusznika

### `per_second_buff`
Aktywuje się co sekundę walki.
- Dotyczy wszystkich jednostek z efektem
- Przykład: Srebrna Gwardia zyskuje obronę co sekundę

### `on_ally_hp_below`
Aktywuje się, gdy sojusznik ma mniej niż X% HP.
- Dotyczy żywych sojuszników poniżej progu
- Przykład: Efekty ratunkowe

## Struktura Efektu

```json
{
  "type": "trigger_type",
  "actions": [
    {
      "type": "action_type",
      // parametry akcji
    }
  ],
  "trigger_once": false  // opcjonalne, dla on_ally_death
}
```

## Typy Akcji

### `stat_buff`
Zwiększa statystyki jednostki.

Parametry:
- `stats`: lista statystyk do buffa (np. `["attack", "defense"]`)
- `value`: wartość buffa
- `is_percentage`: czy wartość jest procentowa (domyślnie false)

### `reward`
Przyznaje nagrodę.

Parametry:
- `reward`: typ nagrody (`"gold"`, `"hp_regen"`)
- `target`: komu przyznać (`"self"`, `"team"`)
- `value`: wartość nagrody
- `chance`: procent szansy na przyznanie (1-100, domyślnie 100)
- `is_percentage`: czy wartość jest procentowa (dla hp_regen)
- `duration`: czas trwania (dla hp_regen)

## Dostępne Statystyki

- `attack`: zwiększa obrażenia
- `defense`: zmniejsza otrzymywane obrażenia
- `hp`: leczy HP (natychmiast)
- `attack_speed`: zwiększa szybkość ataku
- `mana_regen`: zwiększa regenerację many
- `lifesteal`: zwiększa procent kradzieży życia
- `damage_reduction`: zmniejsza procent otrzymywanych obrażeń
- `hp_regen_per_sec`: zwiększa regenerację HP na sekundę

## Dostępne Nagrody

### `gold`
Przyznaje złoto drużynie lub jednostce.

### `hp_regen`
Przyznaje regenerację HP przez określony czas.

## Przykłady

### Femboy (on_enemy_death z hp_regen)
```json
{
  "type": "on_enemy_death",
  "actions": [
    {
      "type": "reward",
      "reward": "hp_regen",
      "target": "self",
      "value": 5,
      "is_percentage": true,
      "duration": 5
    }
  ]
}
```

### Denciak (on_ally_death z gold z szansą)
```json
{
  "type": "on_ally_death",
  "actions": [
    {
      "type": "reward",
      "reward": "gold",
      "value": 1,
      "chance": 50
    }
  ],
  "trigger_once": true
}
```

### Streamer (on_enemy_death ze stat_buff)
```json
{
  "type": "on_enemy_death",
  "actions": [
    {
      "type": "stat_buff",
      "stats": ["attack", "defense"],
      "value": 2
    }
  ]
}
```

### Srebrna Gwardia (per_second_buff)
```json
{
  "type": "per_second_buff",
  "actions": [
    {
      "type": "stat_buff",
      "stats": ["defense"],
      "value": 5
    }
  ]
}
```

## Mechaniki Specjalne

### Buff Amplifier
Jeśli jednostka ma efekt typu `buff_amplifier`, wszystkie buffy są mnożone przez współczynnik.

### Trigger Once
Dla `on_ally_death`, jeśli `trigger_once: true`, nagroda jest przyznana tylko raz na śmierć, nawet jeśli wiele jednostek ma efekt.

### Target Team
Dla reward z `target: "team"`, nagroda jest dzielona między wszystkie żywe jednostki drużyny (dla hp_regen) lub przyznana drużynie (dla gold).

## Wsteczna Kompatybilność

Stary format bez `actions` nadal działa:
```json
{
  "type": "on_enemy_death",
  "stats": ["attack"],
  "value": 5
}
```

## Rozszerzalność

System jest zaprojektowany do łatwego dodawania:
- Nowych typów triggerów
- Nowych typów akcji
- Nowych statystyk
- Nowych nagród

Wystarczy dodać obsługę w odpowiednich metodach `CombatEffectProcessor`.