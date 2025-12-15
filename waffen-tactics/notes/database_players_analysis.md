# Analiza tabeli players w bazie danych Waffen Tactics

## Data analizy: 15 grudnia 2025

## Aktualny stan bazy danych

Na podstawie analizy bazy `waffen_tactics_game.db`:

- **players**: 28 rekordów
- **opponent_teams**: 410 rekordów
- **leaderboard**: 45 rekordów

## Przeznaczenie tabeli players

Tabela `players` przechowuje **aktualny stan gry** każdego gracza:

### Struktura rekordu:
- `user_id` (INTEGER PRIMARY KEY) - unikalny identyfikator Discord gracza
- `state_json` (TEXT) - kompletny stan gry w formacie JSON
- `updated_at` (TIMESTAMP) - czas ostatniej aktualizacji

### Zawartość state_json:
```json
{
  "level": 8,
  "gold": 25,
  "health": 85,
  "round_number": 12,
  "xp": 45,
  "board": [...],  // jednostki na planszy (max 10)
  "bench": [...],  // jednostki na ławce (max 9)
  "shop": [...],   // dostępne jednostki do kupienia
  "shop_lock": false,
  "traits": [...], // aktywne synergie
  // ... inne dane gry
}
```

## Problem z "historycznymi danymi"

### Obserwacja:
W panelu admina może pojawić się wrażenie, że jest "aż tyle historycznych danych" w tabeli players.

### Przyczyna:
**LEFT JOIN** w query `/admin/games`:
```sql
SELECT p.user_id, p.state_json, p.updated_at, COALESCE(ot.nickname, 'Unknown') as nickname
FROM players p
LEFT JOIN opponent_teams ot ON p.user_id = ot.user_id AND ot.is_active = 1
```

Jeśli gracz ma **wiele drużyn** w `opponent_teams` (np. historię walk), JOIN zwraca **wiele wierszy** dla tego samego gracza.

### Rozwiązanie:
- Tabela `players` ma **tylko jeden rekord na gracza** (ON CONFLICT DO UPDATE)
- Wielokrotne wyświetlanie to efekt JOIN, nie duplikaty w tabeli

## Realne zapotrzebowanie na dane

### Obecne użycie:
- **28 graczy aktywnych** = 28 rekordów w players
- Każdy stan gry: ~2-5KB JSON (board + bench + shop + stats)

### Przyszłe potrzeby:
- **Oczekiwana liczba graczy**: 100-500 aktywnych
- **Częstotliwość zapisów**: każdy ruch gracza (problem wydajnościowy)

### Rekomendacje optymalizacji:

#### 1. Ogranicz częstotliwość zapisów
```python
# Zamiast zapisywać przy każdym ruchu:
if should_save_state():
    await db_manager.save_player(player)
```

#### 2. Zapisuj tylko przy kluczowych zmianach:
- Kupno jednostki
- Koniec rundy
- Zmiana poziomu
- Co 30 sekund maksymalnie

#### 3. Wielkość danych na gracza:
- **Aktualnie**: ~3KB na gracza
- **Przy 500 graczach**: ~1.5MB bazy
- **Z historią**: znacznie więcej

#### 4. Strategia archiwizacji:
- Trzymaj tylko **ostatni stan** w `players`
- Przenieś starsze stany do tabeli `player_history` (jeśli potrzebne)
- Albo zapisuj tylko co godzina/dzień

## Wnioski

1. **Tabela players jest prawidłowo zoptymalizowana** - jeden rekord na gracza
2. **Problem wydajnościowy** wynika z częstych zapisów, nie z nadmiaru danych
3. **Realne zapotrzebowanie**: 100-500 graczy × 3KB = 0.3-1.5MB
4. **Rekomendacja**: Ogranicz zapis tylko do kluczowych zmian

## Propozycje implementacji

### W DatabaseManager.save_player():
```python
async def save_player(self, player: PlayerState, force: bool = False):
    current_time = time.time()
    if not force and current_time - self.last_save.get(player.user_id, 0) < 30:
        return  # Nie zapisuj częściej niż co 30 sekund

    # ... reszta kodu
    self.last_save[player.user_id] = current_time
```

### W game logic:
```python
# Zapisuj tylko przy ważnych zmianach
if action in ['buy_unit', 'sell_unit', 'end_round', 'level_up']:
    await db_manager.save_player(player)
```</content>
<parameter name="filePath">/home/ubuntu/waffen-tactics-game/waffen-tactics/notes/database_players_analysis.md