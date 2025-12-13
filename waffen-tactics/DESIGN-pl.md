# Waffen Tactics – Dokument Projektowy v0.1

## Przegląd
Gra auto-battler inspirowana Teamfight Tactics, zaimplementowana jako bot Discord z interaktywnymi przyciskami.
- Gracze budują drużyny z 51 unikalnych jednostek z 14 traitami (6 frakcji, 8 klas)
- Walka bez tur, symulowana w czasie rzeczywistym (dt=0.1s)
- System upgrade gwiazd: 3× ⭐ → ⭐⭐, 3× ⭐⭐ → ⭐⭐⭐
- Trwały stan gracza w bazie SQLite
- Asynchroniczne PvP z zapisanymi składami drużyn

## Podstawowe Dane

### Jednostki (units.json)
- **51 jednostek** z `id`, `name`, `cost` (1-5), `factions[]`, `classes[]`
- Statystyki bazowe skalują się z kosztem:
  - Atak: 40 + 12×koszt
  - HP: 420 + 120×koszt
  - Obrona: 12 + 6×koszt
  - Szybkość Ataku: 0.7 + 0.06×koszt
  - Max Mana: 100 (stała)

### Traity (traits.json)
- **14 traitów** z wielopoziomowymi progami aktywacji
- Typy efektów: `stat_buff`, `on_enemy_death`, `on_ally_death`, `per_round_buff`, `enemy_debuff`, `hp_regen_on_kill`, `per_trait_buff`, `mana_regen`, `on_sell_bonus`, `stat_steal`
- Przykład: Srebrna Gwardia [3,5,7] → +15/25/40 obrony

### Umiejętności
- Generyczna umiejętność: 60 + 25×koszt obrażeń, kosztuje 100 many
- Ładowanie: +10 many per atak
- Przyszłość: unikalne umiejętności per klasa/frakcja

## Progresja Gracza

### Zasoby
- **Gold**: Start 10g, +5g per runda
- **HP**: Start 100, tracisz HP na przegranej (ocaleni + numer rundy)
- **Poziom**: 1-10, zwiększa max jednostek na planszy (2→10)
- **XP**: Kup 4 XP za 4g, nagrody XP z walki

### Korzyści z Poziomu
| Poziom | Max Jednostek | Szanse w Sklepie (Koszt 1/2/3/4/5) |
|--------|---------------|-------------------------------------|
| 1      | 2             | 100/0/0/0/0                         |
| 5      | 6             | 50/30/15/4/1                        |
| 10     | 10            | 5/20/35/25/15                       |

## Faza Sklepu

### Mechaniki
- **5 slotów** odświeżanych każdą rundę
- **Reroll**: 2g za nową ofertę (prawidłowo zachowuje duplikaty)
- **Kup**: Koszt jednostki w goldzie, trafia na ławkę (max 9)
- **Sprzedaj**: Zwrot = koszt × poziom_gwiazdy
- **Lock Shop**: Zachowaj oferty na następną rundę (jeszcze nie zaimplementowane)

### System Auto-Upgrade
Gdy gracz zdobywa 3. kopię tej samej jednostki na tym samym poziomie gwiazdy:
1. Usuń 3 kopie z ławki/planszy
2. Stwórz 1 jednostkę na star_level + 1
3. Umieść na ławce (lub planszy jeśli ławka pełna)
4. Rekursywnie: sprawdź dalsze upgrade

### Funkcje UI
- Wyświetlanie statów jednostki: ⚔️ Atak, ❤️ HP, 🛡️ Obrona
- Pokazywanie frakcji i klas dla każdej jednostki
- Wskazówki upgrade: "(2/3 do ⭐⭐)"
- Footer sklepu z przypomnieniem o upgrade

## Zarządzanie Planszą

### Ławka (max 9 jednostek)
- Tymczasowe przechowywanie kupionych jednostek
- Przenieś na planszę przyciskiem "➡️ Na planszę"
- Sprzedaj za gold przyciskiem "💰 Sprzedaj"
- Pokazuje staty jednostki skalowane przez poziom gwiazdy

### Plansza (max według poziomu)
- Aktywne jednostki bojowe
- Usuń na ławkę przyciskiem "⬅️ Na ławkę"
- Wyświetla całkowitą moc drużyny (suma HP/Atak)
- Kalkulacja synergii w czasie rzeczywistym

### Wyświetlanie Synergii
- Aktywne traity z obecnym tierem
- Postęp licznika: [obecny/następny próg]
- Przykład: "**Gamer** [5] - Tier 2 (następny: 7)"

## Faza Walki

### Mechaniki Symulacji
- **Time-stepped**: dt = 0.1s ticks, max 120s
- **Prawdopodobieństwo ataku**: attack_speed × dt per tick
- **Wybór celu**: 60% priorytet najwyższa obrona, 40% losowy
- **Formuła obrażeń**: max(1, atak - obrona)
- **System many**: +10 per atak, rzuć umiejętność przy 100
- **Zwycięstwo**: Wszystkie jednostki wroga HP ≤ 0

### Rozwiązanie Walki
- **Wygrana**: +0 obrażeń, nagroda gold, passa++
- **Przegrana**: Obrażenia = ocaleni + numer_rundy, passa--
- **Game Over**: HP ≤ 0, użyj `/reset` aby zacząć od nowa

### Przeciwnicy (Przyszłość)
- Zapisane snapshoty drużyn w bazie
- Matchmaking według wygranych/rund
- Kontrola AI podczas symulacji walki

## Interfejs Bota Discord

### Komendy
- `/graj` - Rozpocznij/wznów grę (wysyła na DM)
- `/reset` - Zresetuj postęp
- `/profil` - Zobacz statystyki

### Interaktywne UI
Przyciski głównego menu:
- 🏪 **Sklep** - Przeglądaj i kupuj jednostki
- 📋 **Ławka** - Zarządzaj jednostkami na ławce
- ⚔️ **Plansza** - Zobacz planszę i synergies
- 🔄 **Reroll (2g)** - Odśwież sklep
- 📈 **Kup XP (4g)** - Kup 4 XP
- ⚔️ **Walcz!** - Rozpocznij rundę walki

### Informacje w Embedach
**Embed Stanu Gry:**
- Zasoby: Gold, Poziom, pasek XP
- Staty: Bilans W/L, winrate, passa z emoji
- Jednostki: Liczba plansza/ławka/razem
- Aktywne synergies (do 5 wyświetlanych)

**Embed Sklepu:**
- Nazwa jednostki, koszt, poziom gwiazdy
- Staty: Atak/HP/Obrona
- Frakcje i klasy
- Koszty akcji w opisie

**Embedy Ławka/Plansza:**
- Staty jednostki skalowane przez poziom gwiazdy
- Wartość sprzedaży
- Wskaźniki postępu upgrade
- Całkowita moc drużyny na planszy

## Architektura Techniczna

### Serwisy Backend
- **GameManager**: Obsługuje wszystkie akcje gracza (kup, sprzedaj, przenieś, upgrade)
- **ShopService**: Generuje oferty bazując na szansach poziomu
- **SynergyEngine**: Oblicza aktywne traity ze składu drużyny
- **CombatSimulator**: Symulacja walki krokowa w czasie
- **DatabaseManager**: Persistence SQLite z async operacjami

### Modele Danych
- **PlayerState**: Kompletny stan gry (zasoby, jednostki, postęp)
- **UnitInstance**: Indywidualna jednostka z star_level i instance_id
- **Unit**: Szablon z units.json ze statami/umiejętnościami
- **GameData**: Załadowane jednostki, traity, frakcje, klasy

### Struktura Plików
```
waffen-tactics/
├── src/waffen_tactics/
│   ├── models/
│   │   ├── unit.py
│   │   ├── player.py
│   │   └── player_state.py
│   ├── services/
│   │   ├── data_loader.py
│   │   ├── shop.py
│   │   ├── synergy.py
│   │   ├── combat.py
│   │   ├── game_manager.py
│   │   └── database.py
│   └── cli.py
├── tests/
│   ├── test_combat.py
│   ├── test_data_loader.py
│   └── test_traits.py
├── units.json (51 jednostek)
├── traits.json (14 traitów)
├── discord_bot.py (główny bot)
├── .env (token bota)
└── waffen_tactics_game.db (dane graczy)
```

## Obecny Status (v0.1)

### ✅ Zaimplementowane
- Bot Discord ze slash commands i wsparciem DM
- Pełny system sklepu z auto-upgrade
- Zarządzanie ławką i planszą
- 51 jednostek ze statami bazowanymi na koszcie
- 14 traitów ze szczegółowymi definicjami efektów
- Symulator walki time-stepped
- Persistence SQLite
- Interaktywne UI z przyciskami i aktualizacją real-time
- Kompleksowe testy jednostkowe (47 testów przechodzi)

### 🚧 W Trakcie
- Aplikacja efektów traitów w walce (zdefiniowane ale nieaktywne)
- Unikalne umiejętności per klasa/frakcja
- Rozszerzone UI z więcej statystykami

### 📋 Planowane
- System matchmakingu przeciwników
- Przechowywanie snapshotów drużyn
- Funkcjonalność lock sklepu
- Tryb turniejowy
- Rankingi
- Wizualne wskaźniki efektów traitów
- System replay walki
- System itemów
- Balansowanie ekonomii

## Statystyki w UI

### Sklep
- Nazwa, koszt, gwiazdy jednostki
- ⚔️ Atak, ❤️ HP, 🛡️ Obrona
- 🏴 Frakcje
- 🎭 Klasy
- Przypomnienie o kosztach akcji (Reroll 2g, XP 4g)

### Ławka
- Staty przeskalowane przez poziom gwiazdy
- Licznik do następnego upgrade "(2/3 do ⭐⭐)"
- 💰 Wartość sprzedaży
- Licznik zajętości (X/9)

### Plansza
- Szczegółowe staty każdej jednostki
- 📊 Całkowita Siła drużyny (suma Atak/HP)
- ✨ Aktywne synergies z postępem
- Wskazanie następnego progu traita
- Frakcje i klasy każdej jednostki

### Główne Menu
- Pasek postępu XP (◰◰◰◱◱◱◱◱◱◱)
- Winrate procentowy
- 🔥 Emoji passowania (ogień/czaszka/kreska)
- Liczba jednostek razem
- Preview do 5 synergii

## Ekonomia

### Przychody
- +5g per runda (bazowo)
- Bonus za passę (planowane)
- Odsetki od banku (planowane)

### Wydatki
- Jednostki: 1g-5g (według kosztu)
- Reroll: 2g
- XP: 4g za 4 XP
- Level up: automatyczny przy pełnym XP

### Sprzedaż
- Wartość = koszt × poziom_gwiazdy
- ⭐: 1×koszt
- ⭐⭐: 2×koszt  
- ⭐⭐⭐: 3×koszt

## Balans Jednostek

### Tier 1 (Koszt 1)
- Atak: 52, HP: 540, Obrona: 18
- Szybkość Ataku: 0.76
- Umiejętność: 85 obrażeń

### Tier 5 (Koszt 5)
- Atak: 100, HP: 1020, Obrona: 42
- Szybkość Ataku: 1.0
- Umiejętność: 185 obrażeń

### Upgrade Gwiazd
- ⭐⭐: 2× staty bazowe
- ⭐⭐⭐: 3× staty bazowe
- Koszt uzyskania:
  - ⭐⭐: 3 jednostki (3×koszt gold)
  - ⭐⭐⭐: 9 jednostek (9×koszt gold)

## Porady dla Graczy

### Strategia Ekonomiczna
1. Nie wydawaj wszystkiego - zostaw gold na reroll
2. Leveluj strategicznie - więcej slotów = mocniejsza drużyna
3. Sprzedawaj słabe jednostki na początku rundy

### Budowanie Drużyny
1. Wybierz 2-3 główne traity do budowy
2. Szukaj synergii między frakcjami i klasami
3. Balance między tankami (wysoka obrona) a DPS (wysoki atak)

### Upgrade
1. Trzymaj pary jednostek na ławce dla przyszłych upgrade
2. Priorytetowo upgrade carry units (high cost)
3. ⭐⭐⭐ jednostki są warte 3× więcej niż ⭐

### Walka
1. Postaw tanki na froncie (wysoka obrona przyciąga ataki)
2. DPS w tylnej linii dla bezpieczeństwa
3. Sprawdzaj synergies przed walką - każdy tier ma znaczenie!
