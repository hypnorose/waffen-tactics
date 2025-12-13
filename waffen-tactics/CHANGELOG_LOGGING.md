# 🔧 Changelog - Enhanced Logging Update

## Co zostało dodane:

### 1. ✅ Rotacja logów (10MB, 5 backupów)
- **bot.log** - wszystkie logi (DEBUG + INFO + WARNING + ERROR)
- **bot_errors.log** - tylko błędy (ERROR)
- Automatyczna rotacja przy 10MB
- Zachowuje 5 backupów (.1, .2, .3, .4, .5)

### 2. ✅ Rozbudowane logowanie w discord_bot.py

Dodano logi w kluczowych miejscach:

#### Wybór jednostki:
```
[SELECT_UNIT_BENCH] User {id} selecting unit
[SELECT_UNIT_BENCH] Selected instance_id: {id}
[SELECT_UNIT_BOARD] User {id} selecting unit
[SELECT_UNIT_BOARD] Selected instance_id: {id}
```

#### Przenoszenie jednostek:
```
[MOVE_TO_BOARD] User {id} triggered move_to_board
[MOVE_TO_BOARD] Expected user_id: X, Actual: Y
[MOVE_TO_BOARD] Selected instance_id: {id}

[MOVE_UNIT_TO_BOARD] Starting for user {id}, instance {id}
[MOVE_UNIT_TO_BOARD] Player state - Board: X/Y, Bench: A/B
[MOVE_UNIT_TO_BOARD] Bench units: [list]
[MOVE_UNIT_TO_BOARD] Success! New board size: X

[MOVE_TO_BENCH] User {id} triggered move_to_bench
[MOVE_UNIT_TO_BENCH] Starting for user {id}, instance {id}
[MOVE_UNIT_TO_BENCH] Success! New bench size: X
```

### 3. ✅ Rozbudowane logowanie w game_manager.py

```
[GM_MOVE_TO_BOARD] Request to move {id} to board
[GM_MOVE_TO_BOARD] Current state - Board: X/Y, Bench: A/B
[GM_MOVE_TO_BOARD] Bench instance_ids: [list]
[GM_MOVE_TO_BOARD] Found unit: panzer_iv (star 1)
[GM_MOVE_TO_BOARD] Moved successfully! New state - Board: X, Bench: Y

[GM_MOVE_TO_BENCH] Request to move {id} to bench
[GM_MOVE_TO_BENCH] Found unit: tiger (star 2)
[GM_MOVE_TO_BENCH] Moved successfully! New state - Board: X, Bench: Y
```

### 4. ✅ Naprawione błędy

#### KeyError: 'stat' w format_trait_effect
**Przed:**
```python
stat_name = effect['stat']  # ❌ KeyError jeśli nie ma 'stat'
```

**Po:**
```python
if 'stat' not in effect:
    return f"✨ {effect.get('description', 'Buff')}"
# + try/except wrapper
```

#### TypeError: create_new_player() missing user_id
**Przed:**
```python
new_player = self.game_manager.create_new_player()  # ❌ Brak user_id
```

**Po:**
```python
new_player = self.game_manager.create_new_player(interaction.user.id)  # ✅
```

### 5. ✅ Narzędzia

**view_logs.sh** - interaktywny viewer logów:
- Szukaj po user_id
- Szukaj po słowie kluczowym
- Pokaż logi przenoszenia (MOVE)
- Live tail
- Archiwizacja

**LOGGING.md** - kompletny przewodnik:
- Format logów
- Tagi logów
- Debugging "To nie twoja gra"
- Przykłady użycia
- Najczęstsze problemy

## Jak używać:

### Sprawdź logi interaktywnie:
```bash
cd /home/ubuntu/mentorbot/waffen-tactics
./view_logs.sh
```

### Debugging na żywo:
```bash
# Monitor wszystkiego
tail -f bot.log

# Monitor tylko przenoszenia jednostek
tail -f bot.log | grep --line-buffered "MOVE_"

# Monitor konkretnego gracza
tail -f bot.log | grep --line-buffered "1028467918356353056"

# Monitor błędów
tail -f bot_errors.log
```

### Szukaj problemów:
```bash
# Szukaj błędów przenoszenia
grep -E "\[MOVE_|SELECT_UNIT" bot.log | tail -50

# Szukaj ostrzeżeń i błędów
grep -E "\[WARNING\]|\[ERROR\]" bot.log | tail -50

# Szukaj "User mismatch" (To nie twoja gra)
grep "User mismatch" bot.log
```

## Poziomy logów:

- **DEBUG** (aiosqlite queries) - wszystko, bardzo szczegółowe
- **INFO** (bot operations) - normalne operacje
- **WARNING** (validation failures) - ostrzeżenia
- **ERROR** (exceptions) - błędy

## Dlaczego "To nie twoja gra"?

Logi pokażą dokładnie:
```
[2025-12-12 16:37:00] [INFO] [waffen_tactics] [SELECT_UNIT_BENCH] User 123 selecting unit
[2025-12-12 16:37:00] [INFO] [waffen_tactics] [SELECT_UNIT_BENCH] Selected instance_id: abc-123
[2025-12-12 16:37:02] [WARNING] [waffen_tactics] [MOVE_TO_BOARD] User mismatch! Expected 456, got 123
```

Oznacza to, że:
- User 123 kliknął jednostkę w grze
- Ale gra należy do user 456
- Więc dostaje "To nie twoja gra!"

**Rozwiązanie:** Użyj `/graj` aby rozpocząć własną grę.

## Lokalizacja plików:

```
/home/ubuntu/mentorbot/waffen-tactics/
├── bot.log              # Główny log (wszystko)
├── bot_errors.log       # Tylko błędy
├── bot.log.1 ... .5     # Backupy (automatyczne)
├── bot_errors.log.1...5 # Backupy błędów
├── view_logs.sh         # Interaktywny viewer
└── LOGGING.md           # Pełna dokumentacja
```

## Status:

✅ Rotacja logów działa
✅ Logi szczegółowe działają
✅ Bot działa stabilnie
✅ Błędy naprawione
✅ Narzędzia gotowe

Możesz teraz debugować problemy typu "To nie twoja gra" lub "Nie można przenieść" z pełnymi szczegółami!
