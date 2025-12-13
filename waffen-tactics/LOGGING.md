# 📋 Logging & Debugging Guide

## System logowania

Bot ma zaawansowany system logowania z rotacją plików:

### Pliki logów

- **bot.log** - wszystkie logi (DEBUG, INFO, WARNING, ERROR)
- **bot_errors.log** - tylko błędy (ERROR)
- **bot.log.1, bot.log.2...** - automatyczne backupy (max 5)
- **bot_errors.log.1, bot_errors.log.2...** - backupy błędów (max 5)

### Rotacja

Logi automatycznie rotują gdy przekroczą **10MB**:
- Stary plik → `.1`
- `.1` → `.2`
- `.5` → usuwany

## Komendy do przeglądania logów

### Szybki podgląd
```bash
# Ostatnie 50 linii
tail -50 bot.log

# Ostatnie błędy
tail -50 bot_errors.log

# Live tail (na żywo)
tail -f bot.log
```

### Interaktywny viewer
```bash
./view_logs.sh
```

Menu opcji:
1. Ostatnie 50 linii wszystkich logów
2. Ostatnie 50 linii błędów
3. Szukaj po user_id
4. Szukaj po słowie kluczowym
5. Pokaż logi przenoszenia jednostek (MOVE)
6. Pokaż wszystkie WARNING i ERROR
7. Live tail wszystkich logów
8. Live tail tylko błędów
9. Wyświetl rozmiary plików logów
0. Wyczyść stare logi (backup)

### Wyszukiwanie

```bash
# Szukaj po user_id
grep "1028467918356353056" bot.log | tail -50

# Szukaj błędów przenoszenia
grep -E "\[MOVE_|SELECT_UNIT" bot.log | tail -50

# Szukaj tylko WARNING i ERROR
grep -E "\[WARNING\]|\[ERROR\]" bot.log | tail -50

# Szukaj po słowie kluczowym
grep -i "jednostka" bot.log | tail -50

# Live grep (na żywo)
tail -f bot.log | grep --line-buffered "MOVE_TO_BOARD"
```

## Format logów

```
[YYYY-MM-DD HH:MM:SS] [LEVEL] [logger_name] Message
```

Przykład:
```
[2025-12-12 16:36:55] [INFO] [waffen_tactics] [MOVE_TO_BOARD] User 1028467918356353056 (Player1) triggered move_to_board
```

## Tagi logów

### Operacje na jednostkach
- `[SELECT_UNIT_BENCH]` - wybór jednostki z ławki
- `[SELECT_UNIT_BOARD]` - wybór jednostki z planszy
- `[MOVE_TO_BOARD]` - przenoszenie z ławki na planszę
- `[MOVE_TO_BENCH]` - przenoszenie z planszy na ławkę
- `[GM_MOVE_TO_BOARD]` - game manager: move to board
- `[GM_MOVE_TO_BENCH]` - game manager: move to bench

### Inne operacje
- `[BUY_UNIT]` - kupowanie jednostki
- `[SELL_UNIT]` - sprzedaż jednostki
- `[COMBAT]` - walka
- `[GAME_OVER]` - koniec gry
- `[FORMAT_TRAIT]` - formatowanie efektów traitów

## Debugging "To nie twoja gra"

Jeśli widzisz błąd "To nie twoja gra!" lub "Nie można przenieść jednostki":

```bash
# 1. Szukaj logów tego user_id
grep "TWOJE_USER_ID" bot.log | tail -100

# 2. Sprawdź logi przenoszenia
grep -E "\[MOVE_|SELECT_UNIT" bot.log | grep "TWOJE_USER_ID" | tail -50

# 3. Szukaj ostrzeżeń
grep "User mismatch\|not found" bot.log | grep "TWOJE_USER_ID"
```

Logi pokażą:
- Czy user_id się zgadza
- Czy jednostka została wybrana (selected_instance_id)
- Czy jednostka istnieje na ławce/planszy
- Aktualny stan gracza (board size, bench size)

## Przykład debugowania

```bash
# Problem: nie można przenieść jednostki z ławki
# Krok 1: Live tail podczas próby
tail -f bot.log | grep --line-buffered "MOVE_TO_BOARD"

# Krok 2: Kliknij przycisk w bocie
# Logi pokażą:
[INFO] [SELECT_UNIT_BENCH] User 123 selecting unit
[INFO] [SELECT_UNIT_BENCH] Selected instance_id: abc-def-123
[INFO] [MOVE_TO_BOARD] User 123 triggered move_to_board
[INFO] [MOVE_TO_BOARD] Expected user_id: 123, Actual: 123
[INFO] [MOVE_TO_BOARD] Selected instance_id: abc-def-123
[INFO] [MOVE_UNIT_TO_BOARD] Starting for user 123, instance abc-def-123
[INFO] [MOVE_UNIT_TO_BOARD] Player state - Board: 2/3, Bench: 5/7
[INFO] [MOVE_UNIT_TO_BOARD] Bench units: ['abc-def-123', 'xyz-789', ...]
[INFO] [GM_MOVE_TO_BOARD] Request to move abc-def-123 to board
[INFO] [GM_MOVE_TO_BOARD] Current state - Board: 2/3, Bench: 5/7
[INFO] [GM_MOVE_TO_BOARD] Bench instance_ids: ['abc-def-123', 'xyz-789', ...]
[INFO] [GM_MOVE_TO_BOARD] Found unit: panzer_iv (star 1)
[INFO] [GM_MOVE_TO_BOARD] Moved successfully! New state - Board: 3, Bench: 4
[INFO] [MOVE_UNIT_TO_BOARD] Success! New board size: 3

# Jeśli błąd:
[ERROR] [GM_MOVE_TO_BOARD] Unit abc-def-123 not found on bench!
[ERROR] [GM_MOVE_TO_BOARD] Available bench units: [('xyz-789', 'tiger'), ...]
# → Jednostka nie jest na ławce (prawdopodobnie stan się desynchronizował)
```

## Rozmiary i czyszczenie

```bash
# Sprawdź rozmiary
ls -lh bot*.log*

# Usuń wszystkie stare backupy
rm bot.log.* bot_errors.log.*

# Zarchiwizuj i wyczyść
./view_logs.sh  # Opcja 0

# Ręczny backup
timestamp=$(date +%Y%m%d_%H%M%S)
mv bot.log "archive/bot_${timestamp}.log"
mv bot_errors.log "archive/bot_errors_${timestamp}.log"
```

## Poziomy logowania

W discord_bot.py można zmienić poziom:

```python
# DEBUG - wszystko (bardzo szczegółowe)
main_handler.setLevel(logging.DEBUG)

# INFO - normalne operacje
main_handler.setLevel(logging.INFO)

# WARNING - tylko ostrzeżenia i błędy
main_handler.setLevel(logging.WARNING)

# ERROR - tylko błędy
main_handler.setLevel(logging.ERROR)
```

## Najczęstsze problemy

### "To nie twoja gra!"
**Logi:** `[WARNING] User mismatch! Expected X, got Y`
**Przyczyna:** Kliknąłeś przycisk w grze innego gracza
**Rozwiązanie:** Użyj `/graj` aby rozpocząć własną grę

### "Jednostka nie jest na ławce!"
**Logi:** `[ERROR] Unit abc-123 not found on bench!`
**Przyczyna:** 
- Jednostka została już przeniesiona
- Stan gry się desynchronizował
- Kliknąłeś stary przycisk
**Rozwiązanie:** Odśwież widok (wróć do menu i wejdź ponownie)

### "Plansza pełna!"
**Logi:** `[WARNING] Board full! 5/5`
**Przyczyna:** Masz już maksymalną liczbę jednostek na planszy
**Rozwiązanie:** Przenieś jednostkę z planszy na ławkę, lub sprzedaj

## Tips

- Używaj `grep --line-buffered` dla live tailing z filtrem
- Logi są w UTF-8, można szukać emoji: `grep "⚔️" bot.log`
- Każdy log ma timestamp - sortuj chronologicznie
- WARNING i ERROR automatycznie idą do bot_errors.log
- Rotacja automatyczna - nie musisz ręcznie czyścić

## Przykłady użycia

```bash
# Monitor konkretnego gracza na żywo
tail -f bot.log | grep --line-buffered "1028467918356353056"

# Zobacz wszystkie błędy z ostatniej godziny
grep "$(date +%Y-%m-%d\ %H)" bot_errors.log

# Znajdź wszystkie udane przeniesienia
grep "Moved successfully" bot.log | wc -l

# Zobacz najpopularniejsze błędy
grep ERROR bot.log | cut -d']' -f4 | sort | uniq -c | sort -rn

# Eksportuj logi konkretnego user_id do pliku
grep "TWOJE_USER_ID" bot.log > my_debug.log
```
