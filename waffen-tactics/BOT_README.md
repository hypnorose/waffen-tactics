# Waffen Tactics Discord Bot

Discord bot do gry w Waffen Tactics - auto-battler inspirowany Teamfight Tactics.

## Funkcje

- **Sklep**: Kupuj jednostki, rerolluj oferty (2g), lockuj sklep
- **Ławka**: Trzymaj do 9 jednostek na ławce
- **Plansza**: Stawiaj jednostki do walki (max zależy od poziomu)
- **Auto-upgrade**: 3x ⭐ → ⭐⭐, 3x ⭐⭐ → ⭐⭐⭐
- **Synergies**: Aktywuj traity fakcji i klas
- **Combat**: Walcz z przeciwnikami, zdobywaj rundy
- **Progresja**: Zdobywaj XP, leveluj (1-10), zwiększaj max jednostek

## Instalacja

```bash
cd /home/ubuntu/mentorbot/waffen-tactics

# Zainstaluj zależności
pip install -r bot_requirements.txt

# Ustaw token bota
export DISCORD_BOT_TOKEN='twoj_token_tutaj'

# Uruchom bota
python3 discord_bot.py
```

## Komendy

- `/graj` - Rozpocznij lub wznów grę
- `/reset` - Zresetuj swoją grę
- `/profil` - Zobacz statystyki

## Interfejs

Bot używa przycisków Discord:

- 🏪 **Sklep** - Przeglądaj i kupuj jednostki
- 📋 **Ławka** - Zarządzaj jednostkami na ławce
- ⚔️ **Plansza** - Ustaw jednostki do walki
- 🔄 **Reroll (2g)** - Odśwież ofertę sklepu
- 📈 **Kup XP (4g)** - Zdobądź 4 XP
- ⚔️ **Walcz!** - Rozpocznij rundę walki

## System gwiazd

- Kup 3 jednostki ⭐ → Automatyczny upgrade do ⭐⭐
- Zbierz 3 jednostki ⭐⭐ → Automatyczny upgrade do ⭐⭐⭐
- Jednostki wyższych gwiazd mają lepsze statystyki
- Wartość sprzedaży = cost × star_level

## Mechaniki

- **Gold**: Zarabiaj 5g per runda + dochód z pasmy
- **HP**: Start 100, tracisz HP za przegrane (przeciwnik survives + numer rundy)
- **Level**: Kupuj XP za 4g, max poziom 10
- **Board size**: Zależy od poziomu (lvl 1 = 2, lvl 10 = 10)
- **Synergies**: Fakcje i klasy dają bonusy po osiągnięciu progów

## Persistence

Gra zapisuje się automatycznie w SQLite (`waffen_tactics_game.db`).
Stan gracza zachowany między sesjami.
