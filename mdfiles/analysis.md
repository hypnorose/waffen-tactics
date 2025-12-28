# Analiza logiki efektów synergii w Waffen Tactics

## Wstęp
Na podstawie logów z api.log, analizuję dlaczego efekt "on_enemy_death" dla Streamerów nie jest triggerowany podczas walki.

## Logi z przygotowania do walki
```
DEBUG: Unit Pepe has effects: []
DEBUG: Unit Piwniczak has effects: []
DEBUG: Unit Jaskół95 has effects: ['on_enemy_death']
DEBUG: Unit xntentacion has effects: ['on_enemy_death']
DEBUG: Unit Igor Janik has effects: ['on_enemy_death']
DEBUG: Unit Turbogłowica has effects: ['stat_buff']
DEBUG: Unit Szałwia has effects: ['stat_buff']
```

- Jednostki Pepe i Piwniczak nie mają efektów (prawdopodobnie nie należą do frakcji z synergiami).
- Jaskół95, xntentacion, Igor Janik mają 'on_enemy_death' - to Streamerzy.
- Turbogłowica i Szałwia mają 'stat_buff' - prawdopodobnie statyczne buffy.

## Problem: Brak eventów walki
W logach widać:
```
Combat finished for user 198814213056102400, waiting for user to close...
```

Ale nie ma żadnych eventów typu 'unit_attack', 'unit_died', 'stat_buff' itp.

To oznacza, że symulacja walki nie generuje żadnych eventów, co sugeruje:
1. Walka kończy się natychmiast (np. błąd w kodzie).
2. Jednostki są zbyt słabe/nie atakują.
3. Błąd w CombatSimulator.simulate().

## Sprawdzone elementy
1. **Efekty są przypisane**: Jednostki mają poprawne efekty w effects_for_unit.
2. **Event callback jest przekazywany**: W combat_shared.py, event_callback jest używany.
3. **Debug printy**: Dodałem printy w combat_effect_processor.py, ale nie pojawiają się w logach, co potwierdza, że _process_unit_death nie jest wywoływane.

## Możliwe przyczyny
1. **Błąd w symulacji**: CombatSimulator.simulate() rzuca wyjątek lub kończy się natychmiast.
2. **Brak ataków**: Jednostki nie atakują (np. attack_speed = 0 lub błąd w logice ataku).
3. **Natychmiastowe zakończenie**: Walka kończy się bez walki (np. jedna strona ma 0 jednostek).

## Rekomendacje
1. Dodać więcej debugów w CombatSimulator.simulate() - sprawdzić czy pętla walki się wykonuje.
2. Sprawdzić czy jednostki mają poprawne staty (attack > 0, attack_speed > 0).
3. Dodać logi dla każdego ticku symulacji.

## Kod związany
- `combat_shared.py`: CombatSimulator.simulate()
- `combat_effect_processor.py`: _process_unit_death()
- `game_combat.py`: generate_combat_events()</content>
<parameter name="filePath">/home/ubuntu/waffen-tactics-game/analysis.md