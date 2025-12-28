# Przykładowe Skille w Systemie Waffen Tactics

## Wprowadzenie

System skilli w Waffen Tactics pozwala jednostkom na wykonywanie specjalnych umiejętności podczas walki. Skille są definiowane w formacie JSON i składają się z efektów, które mogą być wykonywane na różnych celach.

## Struktura Skilla

Każdy skill zawiera:
- `name`: Nazwa skilla
- `description`: Opis działania
- `mana_cost`: Koszt many
- `effects`: Lista efektów do wykonania

## Typy Efektów

### DAMAGE
Zadaje obrażenia celowi.

**Parametry:**
- `amount` (wymagane): Ilość obrażeń
- `damage_type` (opcjonalne): Typ obrażeń ('physical', 'magical')

**Przykład:**
```json
{
  "type": "damage",
  "target": "single_enemy",
  "amount": 150,
  "damage_type": "magical"
}
```

### HEAL
Leczy cel.

**Parametry:**
- `amount` (wymagane): Ilość leczenia

**Przykład:**
```json
{
  "type": "heal",
  "target": "ally_team",
  "amount": 100
}
```

### SHIELD
Tworzy tarczę na cel.

**Parametry:**
- `amount` (wymagane): Siła tarczy
- `duration` (wymagane): Czas trwania w sekundach

**Przykład:**
```json
{
  "type": "shield",
  "target": "self",
  "amount": 200,
  "duration": 5.0
}
```

### BUFF
Zwiększa statystyki celu.

**Parametry:**
- `stat` (wymagane): Statystyka do buffa ('attack', 'defense', 'attack_speed', 'hp')
- `value` (wymagane): Wartość buffa
- `duration` (wymagane): Czas trwania w sekundach
- `value_type` (opcjonalne): Typ wartości ('flat', 'percentage')

**Przykład:**
```json
{
  "type": "buff",
  "target": "ally_team",
  "stat": "attack",
  "value": 50,
  "value_type": "percentage",
  "duration": 10.0
}
```

### DEBUFF
Zmniejsza statystyki celu.

**Parametry:**
- `stat` (wymagane): Statystyka do debuffa
- `value` (wymagane): Wartość debuffa
- `duration` (wymagane): Czas trwania w sekundach
- `value_type` (opcjonalne): Typ wartości

**Przykład:**
```json
{
  "type": "debuff",
  "target": "enemy_team",
  "stat": "defense",
  "value": 30,
  "value_type": "percentage",
  "duration": 8.0
}
```

### STUN
Ogłusza cel, uniemożliwiając atakowanie.

**Parametry:**
- `duration` (wymagane): Czas trwania stun w sekundach

**Przykład:**
```json
{
  "type": "stun",
  "target": "single_enemy",
  "duration": 3.0
}
```

### DELAY
Opóźnia następne efekty.

**Parametry:**
- `duration` (wymagane): Czas opóźnienia w sekundach

**Przykład:**
```json
{
  "type": "delay",
  "target": "self",
  "duration": 2.0
}
```

### REPEAT
Powtarza efekty określoną liczbę razy.

**Parametry:**
- `count` (wymagane): Liczba powtórzeń
- `effects` (wymagane): Lista efektów do powtórzenia

**Przykład:**
```json
{
  "type": "repeat",
  "target": "self",
  "count": 3,
  "effects": [
    {
      "type": "damage",
      "target": "single_enemy",
      "amount": 50
    },
    {
      "type": "delay",
      "target": "self",
      "duration": 1.0
    }
  ]
}
```

### CONDITIONAL
Wykonuje efekty warunkowo.

**Parametry:**
- `condition` (wymagane): Warunek (np. "target_hp_below_50")
- `effects` (wymagane): Efekty do wykonania jeśli warunek spełniony
- `else_effects` (opcjonalne): Efekty do wykonania jeśli warunek nie spełniony

**Przykład:**
```json
{
  "type": "conditional",
  "target": "self",
  "condition": "target_hp_below_50",
  "effects": [
    {
      "type": "heal",
      "target": "single_enemy",
      "amount": 200
    }
  ],
  "else_effects": [
    {
      "type": "damage",
      "target": "single_enemy",
      "amount": 100
    }
  ]
}
```

### DAMAGE_OVER_TIME
Zadaje obrażenia w czasie.

**Parametry:**
- `damage` (wymagane): Obrażenia na tick
- `duration` (wymagane): Całkowity czas trwania
- `interval` (wymagane): Interwał między tickami
- `damage_type` (opcjonalne): Typ obrażeń

**Przykład:**
```json
{
  "type": "damage_over_time",
  "target": "enemy_team",
  "damage": 25,
  "duration": 10.0,
  "interval": 2.0,
  "damage_type": "poison"
}
```

## Typy Celów

- `self`: Własna jednostka
- `single_enemy`: Pojedynczy losowy wróg
- `enemy_team`: Wszystkie żywe jednostki wroga
- `enemy_front`: Pierwsze 3 jednostki wroga (linia frontu)
- `ally_team`: Wszystkie żywe sojusznicze jednostki
- `ally_front`: Pierwsze 3 sojusznicze jednostki (linia frontu)

## Przykładowe Kompletne Skille

### 1. Ogień Piekielny (Hellfire)
```json
{
  "name": "Hellfire",
  "description": "Strzela strumieniem ognia, zadając obrażenia wszystkim wrogom",
  "mana_cost": 80,
  "effects": [
    {
      "type": "damage",
      "target": "enemy_team",
      "amount": 120,
      "damage_type": "magical"
    }
  ]
}
```

### 2. Boska Ochrona (Divine Protection)
```json
{
  "name": "Divine Protection",
  "description": "Otacza sojuszników tarczą i leczy ich",
  "mana_cost": 60,
  "effects": [
    {
      "type": "shield",
      "target": "ally_team",
      "amount": 150,
      "duration": 8.0
    },
    {
      "type": "heal",
      "target": "ally_team",
      "amount": 80
    }
  ]
}
```

### 3. Burza Cieni (Shadow Storm)
```json
{
  "name": "Shadow Storm",
  "description": "Przywołuje burzę cieni, zadając obrażenia w czasie i osłabiając wrogów",
  "mana_cost": 100,
  "effects": [
    {
      "type": "damage_over_time",
      "target": "enemy_team",
      "damage": 30,
      "duration": 12.0,
      "interval": 3.0,
      "damage_type": "magical"
    },
    {
      "type": "debuff",
      "target": "enemy_team",
      "stat": "attack_speed",
      "value": 25,
      "value_type": "percentage",
      "duration": 12.0
    }
  ]
}
```

### 4. Fala Energii (Energy Wave)
```json
{
  "name": "Energy Wave",
  "description": "Wysyła falę energii, która wielokrotnie uderza w wrogów",
  "mana_cost": 70,
  "effects": [
    {
      "type": "repeat",
      "target": "self",
      "count": 4,
      "effects": [
        {
          "type": "damage",
          "target": "enemy_front",
          "amount": 60,
          "damage_type": "magical"
        },
        {
          "type": "delay",
          "target": "self",
          "duration": 0.5
        }
      ]
    }
  ]
}
```

### 5. Sąd Ostateczny (Final Judgment)
```json
{
  "name": "Final Judgment",
  "description": "Sądzi wrogów - zabija słabych, leczy silnych sojuszników",
  "mana_cost": 120,
  "effects": [
    {
      "type": "conditional",
      "target": "self",
      "condition": "target_hp_below_50",
      "effects": [
        {
          "type": "damage",
          "target": "single_enemy",
          "amount": 500,
          "damage_type": "holy"
        }
      ],
      "else_effects": [
        {
          "type": "heal",
          "target": "ally_team",
          "amount": 200
        }
      ]
    }
  ]
}
```

### 6. Taniec Śmierci (Dance of Death)
```json
{
  "name": "Dance of Death",
  "description": "Tańczy z wrogami, zadając obrażenia i zwiększając własną prędkość ataku",
  "mana_cost": 90,
  "effects": [
    {
      "type": "damage",
      "target": "enemy_front",
      "amount": 180,
      "damage_type": "physical"
    },
    {
      "type": "buff",
      "target": "self",
      "stat": "attack_speed",
      "value": 100,
      "value_type": "percentage",
      "duration": 15.0
    },
    {
      "type": "stun",
      "target": "single_enemy",
      "duration": 2.0
    }
  ]
}
```

## Uwagi Implementacyjne

- Wszystkie efekty są wykonywane sekwencyjnie w ramach jednego skilla
- Efekty mogą być łączone w złożone kombinacje
- System obsługuje warunki i powtarzania dla zaawansowanych mechanik
- Każdy efekt generuje odpowiednie eventy do systemu walki
- Mana jest odejmowana przed wykonaniem efektów
- Jeśli wykonanie się nie powiedzie, skill nie zostanie wykonany</content>
<parameter name="filePath">/home/ubuntu/waffen-tactics-game/skill_examples.md