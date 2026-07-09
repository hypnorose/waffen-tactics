# 📚 Guide Tworzenia Traitów - Waffen Tactics

## 🎯 Wprowadzenie

Ten dokument opisuje pełną specyfikację systemu traitów (synergii) w grze Waffen Tactics, w tym dostępne triggery, typy nagród, wartości i najlepsze praktyki.

## 📋 Struktura Traita

```json
{
  "name": "Nazwa Traita",
  "type": "faction|class",
  "description": "Opis działania traita",
  "target": "team|trait|null",
  "thresholds": [2, 3, 4],
  "threshold_descriptions": [
    "Opis poziomu 1",
    "Opis poziomu 2", 
    "Opis poziomu 3"
  ],
  "modular_effects": [
    [/* efekty dla progu 1 */],
    [/* efekty dla progu 2 */],
    [/* efekty dla progu 3 */]
  ]
}
```

### Pola Podstawowe

| Pole | Typ | Wymagane | Opis |
|------|-----|----------|------|
| `name` | string | ✅ | Unikalna nazwa traita |
| `type` | string | ✅ | `"faction"` lub `"class"` |
| `description` | string | ✅ | Opis efektu traita |
| `target` | string/null | ❌ | `"team"` (cały zespół), `"trait"` (tylko jednostki z tym traitem), `null` (jednostka) |
| `thresholds` | number[] | ✅ | Liczba jednostek potrzebna dla kolejnych poziomów |
| `threshold_descriptions` | string[] | ✅ | Opisy dla każdego poziomu (może zawierać placeholdery jak `<rewards.value>`) |
| `modular_effects` | array[] | ✅ | Tablica efektów dla każdego progu |

## 🎬 Triggery (Kiedy Efekt się Aktywuje)

### 1. **`passive`** - Efekt Pasywny ⭐ ZALECANY dla buff_amplifier, targeting_preference
Aktywny przez cały czas gdy trait jest aktywny. Nie wymaga żadnego zdarzenia.

**Użycie:**
- Stałe bonusy (buff amplifiers)
- Zmiana zachowania (targeting preferences)
- Efekty ekonomiczne poza walką (reroll_chance)

**Przykład:**
```json
{
  "trigger": "passive",
  "conditions": {},
  "rewards": [
    {
      "type": "buff_amplifier",
      "multiplier": 2.0
    }
  ]
}
```

### 2. `on_enemy_death` - Po Zabiciu Wroga
Aktywuje się gdy jednostka z traitem zabije wroga.

**Kontekst:** `current_unit`, `killed_unit`, `collected_stats`

**Przykład:**
```json
{
  "trigger": "on_enemy_death",
  "conditions": {},
  "rewards": [
    {
      "type": "stat_buff",
      "stat": "attack",
      "value": 5
    }
  ]
}
```

### 3. `on_ally_death` - Po Śmierci Sojusznika
Aktywuje się gdy sojusznik jednostki z traitem umrze.

**Kontekst:** `current_unit`, `dead_unit`

**Przykład:**
```json
{
  "trigger": "on_ally_death",
  "conditions": {
    "trigger_once": true
  },
  "rewards": [
    {
      "type": "resource",
      "resource": "gold",
      "value": 1
    }
  ]
}
```

### 4. `per_second` - Co Sekundę Walki
Aktywuje się co sekundę podczas walki.

**Kontekst:** `current_unit`, `all_units`

**Przykład:**
```json
{
  "trigger": "per_second",
  "conditions": {},
  "rewards": [
    {
      "type": "stat_buff",
      "stat": "defense",
      "value": 3
    }
  ]
}
```

### 5. `per_round` - Na Początku Rundy
Aktywuje się na początku każdej rundy (przed walką).

**Kontekst:** `current_unit`, `all_units`, `round_number`

**Przykład:**
```json
{
  "trigger": "per_round",
  "conditions": {},
  "rewards": [
    {
      "type": "stat_buff",
      "stat": "hp",
      "value": 5,
      "value_type": "flat"
    }
  ]
}
```

### 6. `on_ally_hp_below` - Gdy HP Sojusznika Spada
Aktywuje się gdy HP sojusznika spadnie poniżej progu.

**Kontekst:** `current_unit`, `low_hp_unit`, `current_hp_percent`

**Warunki wymagane:** `threshold_percent`

**Przykład:**
```json
{
  "trigger": "on_ally_hp_below",
  "conditions": {
    "trigger_once": true,
    "threshold_percent": 30
  },
  "rewards": [
    {
      "type": "healing",
      "value": 50,
      "value_type": "percentage_of_max"
    }
  ]
}
```

### 7. `per_trait` - Za Każdą Aktywną Synergię
Aktywuje się raz, bonus zależy od liczby aktywnych synergii.

**Kontekst:** `current_unit`, `active_trait_count`

**Przykład:**
```json
{
  "trigger": "per_trait",
  "conditions": {},
  "rewards": [
    {
      "type": "stat_buff",
      "stat": "attack",
      "value": 4,
      "value_type": "per_active_trait"
    }
  ]
}
```

### 8. `on_win` - Po Wygranej Rundzie
Aktywuje się po wygraniu rundy walki.

**Kontekst:** `current_unit`, `all_units`

**Przykład:**
```json
{
  "trigger": "on_win",
  "conditions": {},
  "rewards": [
    {
      "type": "dynamic_scaling",
      "atk_per_win": 1,
      "def_per_win": 1
    }
  ]
}
```

### 9. `on_loss` - Po Przegranej Rundzie
Aktywuje się po przegraniu rundy walki.

**Kontekst:** `current_unit`, `all_units`

**Przykład:**
```json
{
  "trigger": "on_loss",
  "conditions": {},
  "rewards": [
    {
      "type": "dynamic_scaling",
      "percent_per_loss": 5
    }
  ]
}
```

## 🎁 Typy Nagród (Rewards)

### 1. `stat_buff` - Bonusy do Statystyk

**Parametry:**
- `stat` (wymagane): `"attack"`, `"defense"`, `"hp"`, `"attack_speed"`, `"max_mana"`, `"lifesteal"`, `"hp_regen_per_sec"`
- `value` (wymagane): wartość liczbowa
- `value_type`: `"flat"` (domyślnie), `"percentage_of_max"`, `"percentage_of_collected"`, `"per_active_trait"`
- `collect_stat`: (tylko dla `percentage_of_collected`) - `"defense"`, `"attack"`, `"hp"`
- `duration`: `"permanent"` (domyślnie), `"round_end"`, `"seconds"`
- `duration_seconds`: liczba sekund (tylko jeśli `duration: "seconds"`)

**Przykład - Flat bonus:**
```json
{
  "type": "stat_buff",
  "stat": "attack",
  "value": 10
}
```

**Przykład - Procent z zabitego wroga:**
```json
{
  "type": "stat_buff",
  "stat": "defense",
  "value": 10,
  "value_type": "percentage_of_collected",
  "collect_stat": "defense"
}
```

**Przykład - Za każdą synergię:**
```json
{
  "type": "stat_buff",
  "stat": "hp",
  "value": 20,
  "value_type": "per_active_trait"
}
```

### 2. `resource` - Zasoby (Gold/XP/Mana)

**Parametry:**
- `resource` (wymagane): `"gold"`, `"xp"`, `"mana"`
- `value` (wymagane): wartość liczbowa
- `value_type`: `"flat"` (domyślnie)

**Przykład:**
```json
{
  "type": "resource",
  "resource": "gold",
  "value": 1
}
```

### 3. `healing` - Leczenie HP

**Parametry:**
- `value` (wymagane): wartość liczbowa
- `value_type`: `"flat"`, `"percentage_of_max"` (procent max HP jednostki)
- `duration`: `"instant"` (domyślnie), `"seconds"`
- `duration_seconds`: liczba sekund (tylko jeśli `duration: "seconds"`)

**Przykład:**
```json
{
  "type": "healing",
  "value": 50,
  "value_type": "percentage_of_max"
}
```

### 4. `enemy_debuff` - Osłabienie Drużyny Przeciwnika

**Parametry:**
- `stat` (wymagane): `"attack"`, `"defense"`, `"attack_speed"`
- `value` (wymagane): wartość o którą obniżyć statystykę

**Przykład:**
```json
{
  "type": "enemy_debuff",
  "stat": "defense",
  "value": 15
}
```

### 5. `mana_regen` - Regeneracja Many

**Parametry:**
- `value` (wymagane): wartość regeneracji many

**Przykład:**
```json
{
  "type": "mana_regen",
  "value": 3
}
```

### 6. `buff_amplifier` - Wzmocnienie Buffów ⚠️ TYLKO Z TRIGGEREM `passive`

**Parametry:**
- `multiplier` (wymagane): mnożnik buffów (np. `2.0` = podwojone buffy)

**⚠️ WAŻNE:** Buff amplifier **MUSI** używać triggera `passive`, nie `on_enemy_death`!

**Przykład:**
```json
{
  "trigger": "passive",
  "conditions": {},
  "rewards": [
    {
      "type": "buff_amplifier",
      "multiplier": 2.0
    }
  ]
}
```

### 7. `targeting_preference` - Zmiana Celowania

**Parametry:**
- `target_preference` (wymagane): `"backline"`, `"frontline"`, `"lowest_hp"`

**Przykład:**
```json
{
  "type": "targeting_preference",
  "target_preference": "lowest_hp"
}
```

### 8. `reroll_chance` - Szansa na Darmowy Reroll ⚠️ TYLKO Z TRIGGEREM `passive`

**Parametry:**
- `chance_percent` (wymagane): szansa 0-100%

**⚠️ WAŻNE:** Reroll chance **MUSI** używać triggera `passive` i nazwy typu `reroll_free_chance` w kodzie!

**Przykład:**
```json
{
  "trigger": "passive",
  "conditions": {},
  "rewards": [
    {
      "type": "reroll_free_chance",
      "chance_percent": 30
    }
  ]
}
```

### 9. `dynamic_scaling` - Skalowanie za Wygrane/Przegrane

**Parametry:**
- `atk_per_win`: bonus ataku za wygraną
- `def_per_win`: bonus obrony za wygraną
- `hp_percent_per_win`: procent HP za wygraną
- `as_per_win`: bonus attack speed za wygraną
- `percent_per_loss`: procent HP za przegraną

**Przykład:**
```json
{
  "type": "dynamic_scaling",
  "atk_per_win": 1,
  "def_per_win": 1,
  "hp_percent_per_win": 1
}
```

### 10. `special` - Efekty Specjalne

**Parametry:**
- `value` (wymagane): wartość efektu (np. HP regen %)

**Przykład:**
```json
{
  "type": "special",
  "value": 5
}
```

## ⚙️ Warunki (Conditions)

| Warunek | Typ | Domyślnie | Opis |
|---------|-----|-----------|------|
| `chance_percent` | number | 100 | Szansa 0-100% na aktywację |
| `once_per_round` | boolean | false | Tylko raz na rundę |
| `max_triggers` | number/null | null | Maksymalna liczba aktywacji |
| `trigger_once` | boolean | false | Tylko raz na walkę |
| `threshold_percent` | number/null | null | Próg HP dla `on_ally_hp_below` |

**Przykład:**
```json
{
  "trigger": "on_ally_death",
  "conditions": {
    "chance_percent": 50,
    "trigger_once": true
  },
  "rewards": [...]
}
```

## ✅ Najlepsze Praktyki

### 1. **Wybór Właściwego Triggera**

❌ **ŹLE:**
```json
{
  "name": "XN Jugend",
  "modular_effects": [[
    {
      "trigger": "on_enemy_death",  // ❌ Źle - amplifier powinien być zawsze aktywny!
      "rewards": [{
        "type": "buff_amplifier",
        "multiplier": 2
      }]
    }
  ]]
}
```

✅ **DOBRZE:**
```json
{
  "name": "XN Jugend",
  "modular_effects": [[
    {
      "trigger": "passive",  // ✅ Dobrze - amplifier aktywny zawsze
      "conditions": {},
      "rewards": [{
        "type": "buff_amplifier",
        "multiplier": 2
      }]
    }
  ]]
}
```

### 2. **Efekty Poza Walką = `passive`**

Efekty które działają poza walką (reroll, buy xp, etc.) **ZAWSZE** muszą używać triggera `passive`.

❌ **ŹLE:**
```json
{
  "trigger": "on_enemy_death",  // ❌ Reroll działa w sklepie, nie w walce!
  "rewards": [{
    "type": "reroll_chance",
    "chance_percent": 30
  }]
}
```

✅ **DOBRZE:**
```json
{
  "trigger": "passive",  // ✅ Efekt ekonomiczny
  "conditions": {},
  "rewards": [{
    "type": "reroll_free_chance",  // Uwaga: nazwa w kodzie!
    "chance_percent": 30
  }]
}
```

### 3. **Target vs Trigger**

- `target: "team"` - efekt wpływa na cały zespół
- `target: "trait"` - efekt wpływa tylko na jednostki z tym traitem
- `target: null` - efekt wpływa na jednostkę która go wywołała

**Przykład:**
```json
{
  "name": "Srebrna Gwardia",
  "target": "team",  // Cały zespół zyskuje obronę
  "modular_effects": [[
    {
      "trigger": "per_second",
      "rewards": [{
        "type": "stat_buff",
        "stat": "defense",
        "value": 3
      }]
    }
  ]]
}
```

### 4. **Placeholder w Opisach**

Możesz używać placeholderów w `threshold_descriptions`:

- `<rewards.value>` - wartość nagrody
- `<rewards.multiplier>` - mnożnik
- `<conditions.chance_percent>` - szansa procentowa
- `<conditions.threshold_percent>` - próg HP

**Przykład:**
```json
{
  "threshold_descriptions": [
    "Podwaja (<rewards.multiplier>x) wszystkie buffy na tej jednostce",
    "<conditions.chance_percent>% szans na darmowy reroll"
  ]
}
```

## 🔍 Sprawdzanie Poprawności

### Checklist przed dodaniem traita:

- [ ] `name` jest unikalna
- [ ] `type` to `"faction"` lub `"class"`
- [ ] Liczba elementów w `modular_effects` = liczba elementów w `thresholds`
- [ ] Trigger pasuje do typu efektu:
  - `buff_amplifier` → `passive`
  - `reroll_free_chance` → `passive`
  - `targeting_preference` → `passive`
  - Inne ekonomiczne → `passive`
  - Bonusy bojowe → odpowiedni trigger (`on_enemy_death`, `per_second`, etc.)
- [ ] Wszystkie wymagane parametry są obecne
- [ ] `value_type` pasuje do `stat` (np. `percentage_of_collected` ma `collect_stat`)

## 📝 Pełne Przykłady Traitów

### Przykład 1: Trait Bojowy (Streamer)
```json
{
  "name": "Streamer",
  "type": "faction",
  "description": "Za każdego pokonanego wroga zespół zyskuje atak i obronę",
  "target": "team",
  "thresholds": [2, 3, 4],
  "threshold_descriptions": [
    "+<rewards.value[0]> ataku i +<rewards.value[1]> obrony po zabiciu wroga",
    "+<rewards.value[0]> ataku i +<rewards.value[1]> obrony po zabiciu wroga",
    "+<rewards.value[0]> ataku i +<rewards.value[1]> obrony po zabiciu wroga"
  ],
  "modular_effects": [
    [
      {
        "trigger": "on_enemy_death",
        "conditions": {},
        "rewards": [
          {
            "type": "stat_buff",
            "stat": "attack",
            "value": 3
          },
          {
            "type": "stat_buff",
            "stat": "defense",
            "value": 3
          }
        ]
      }
    ],
    [
      {
        "trigger": "on_enemy_death",
        "conditions": {},
        "rewards": [
          {
            "type": "stat_buff",
            "stat": "attack",
            "value": 5
          },
          {
            "type": "stat_buff",
            "stat": "defense",
            "value": 5
          }
        ]
      }
    ],
    [
      {
        "trigger": "on_enemy_death",
        "conditions": {},
        "rewards": [
          {
            "type": "stat_buff",
            "stat": "attack",
            "value": 7
          },
          {
            "type": "stat_buff",
            "stat": "defense",
            "value": 7
          }
        ]
      }
    ]
  ]
}
```

### Przykład 2: Trait Pasywny (XN Jugend - POPRAWIONY)
```json
{
  "name": "XN Jugend",
  "type": "class",
  "description": "Wzmacnia wszystkie buffy na tej jednostce (x2)",
  "target": null,
  "thresholds": [1],
  "threshold_descriptions": [
    "Podwaja (<rewards.multiplier>x) wszystkie buffy na tej jednostce"
  ],
  "modular_effects": [
    [
      {
        "trigger": "passive",
        "conditions": {},
        "rewards": [
          {
            "type": "buff_amplifier",
            "multiplier": 2.0
          }
        ]
      }
    ]
  ]
}
```

### Przykład 3: Trait Ekonomiczny (XN Mod - POPRAWIONY)
```json
{
  "name": "XN Mod",
  "type": "class",
  "description": "30% szans na darmowy reroll gdy aktywne",
  "target": null,
  "thresholds": [1],
  "threshold_descriptions": [
    "<conditions.chance_percent>% szans na darmowy reroll"
  ],
  "modular_effects": [
    [
      {
        "trigger": "passive",
        "conditions": {},
        "rewards": [
          {
            "type": "reroll_free_chance",
            "chance_percent": 30
          }
        ]
      }
    ]
  ]
}
```

### Przykład 4: Trait z Warunkami (Wygnaniec)
```json
{
  "name": "Wygnaniec",
  "type": "class",
  "description": "Leczy pierwszego sojusznika który spadnie poniżej 30% HP",
  "target": null,
  "thresholds": [1],
  "threshold_descriptions": [
    "Leczy pierwszego sojusznika poniżej <conditions.threshold_percent>% HP o <rewards.value>% jego max HP"
  ],
  "modular_effects": [
    [
      {
        "trigger": "on_ally_hp_below",
        "conditions": {
          "trigger_once": true,
          "threshold_percent": 30
        },
        "rewards": [
          {
            "type": "healing",
            "value": 50,
            "value_type": "percentage_of_max"
          }
        ]
      }
    ]
  ]
}
```

## 🐛 Najczęstsze Błędy

1. **Używanie `on_enemy_death` dla efektów pasywnych** → Użyj `passive`
2. **Brak `conditions: {}` dla triggerów bez warunków** → Zawsze dodaj pusty obiekt
3. **Niezgodne nazwy typów w traits.json i kodzie** → `reroll_chance` vs `reroll_free_chance`
4. **Zapominanie o `target`** → Ustaw odpowiednią wartość lub `null`
5. **Za dużo/mało efektów dla progów** → Liczba `modular_effects` = liczba `thresholds`

## 📚 Dalsze Materiały

- [MODULAR_TRAIT_REFERENCE.md](/MODULAR_TRAIT_REFERENCE.md) - Szczegółowa referencja API
- [traits.json](/waffen-tactics/traits.json) - Plik z aktualnymi traitami
- [combat_simulator.py](/waffen-tactics/src/waffen_tactics/services/combat_simulator.py) - Implementacja combatu
