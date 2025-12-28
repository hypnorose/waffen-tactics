# Jak pobierać Win Streak w Waffen Tactics

## Wprowadzenie

Win Streak (seria zwycięstw) jest przechowywana w stanie gracza i śledzi liczbę kolejnych zwycięstw.

## Struktura Danych

W modelu `PlayerState` pole `streak` przechowuje aktualną serię zwycięstw:

```python
@dataclass
class PlayerState:
    # ... inne pola ...
    streak: int = 0  # Aktualna seria zwycięstw
```

## Jak pobierać Win Streak

### W Backend (Python)

Win Streak jest dostępny w obiekcie `PlayerState`:

```python
# W game_manager.py lub podobnym
player_state = PlayerState(...)
current_streak = player_state.streak

# Przy zwycięstwie zwiększ streak
player_state.streak += 1

# Przy porażce zresetuj streak
player_state.streak = 0
```

### W Frontend (TypeScript/React)

Win Streak jest dostępny w `playerState` pobranym z API:

```typescript
// W komponencie React
const playerState = useGameStore(state => state.playerState)

if (playerState) {
  const winStreak = playerState.streak
  console.log(`Aktualna seria zwycięstw: ${winStreak}`)
}
```

### W API Response

Win Streak jest zwracany w odpowiedzi z endpointu `/api/player/state`:

```json
{
  "user_id": 123,
  "username": "Player",
  "gold": 50,
  "level": 3,
  "xp": 10,
  "hp": 100,
  "streak": 5,
  "wins": 12,
  "losses": 3,
  // ... pozostałe pola
}
```

## Logika Aktualizacji

### Przy Zwycięstwie
```python
player_state.wins += 1
player_state.streak += 1
player_state.hp = min(100, player_state.hp + 10)  # Opcjonalne leczenie
```

### Przy Porażce
```python
player_state.losses += 1
player_state.streak = 0  # Reset streak
player_state.hp = max(0, player_state.hp - 20)  # Obrażenia
```

## Wyświetlanie w UI

W komponencie GameStats lub podobnym:

```tsx
<div className="text-center">
  <div className="text-2xl font-bold text-orange-500">
    {playerState.streak} 🔥
  </div>
  <div className="text-sm text-text/60">Seria Zwycięstw</div>
</div>
```

## Uwagi Implementacyjne

- Streak jest resetowany tylko przy porażce
- Maksymalna wartość streak nie jest ograniczona
- Streak jest częścią stanu gracza zapisywanego w bazie danych
- Przy restartowaniu gry streak może być zachowany lub zresetowany (zależy od logiki)</content>
<parameter name="filePath">/home/ubuntu/waffen-tactics-game/winstreak_guide.md