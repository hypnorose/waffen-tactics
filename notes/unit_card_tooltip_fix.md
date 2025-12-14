# Plan Naprawienia Tooltipu w UnitCard.tsx

## Problem
- W `UnitCard.tsx` tooltip pokazuje statystyki, ale nie wyróżnia buffów synergii (np. zielony "+" dla zwiększonych wartości).
- Obecnie wyświetla tylko `displayStats` (buffed lub base), bez wskazania różnicy między base a buffed.
- Użytkownik widzi "statystyki bez buffów", bo nie ma wizualnego oznaczenia buffów.

## Cel
- Tooltip powinien pokazywać base statystyki + zielony "+" dla buffów (np. "HP: 100 (+20)" jeśli buffed to 120).
- To pozwoli UI na wyświetlanie różnicy bez własnych obliczeń — wszystko z backendu.

## Kroki Implementacji
1. **Zaktualizować logikę tooltipu w `UnitCard.tsx`**:
   - Obliczyć różnicę między `buffedStats` a `baseStats` dla każdej statystyki (hp, attack, defense, attack_speed, max_mana).
   - W JSX tooltipu wyświetlić base wartość + zielony "+" jeśli buff > 0.

2. **Zmiany w kodzie**:
   - Dodać zmienne dla buffów: `const hpBuff = (buffedStats?.hp || 0) - (baseStats?.hp || 0);` itp.
   - W tooltipie: `<span>HP: {baseStats?.hp || displayStats?.hp} {hpBuff > 0 && <span className="text-green-500">+{hpBuff}</span>}</span>`

3. **Testowanie**:
   - Uruchomić `./start-all.sh`, sprawdzić tooltip na planszy z jednostkami mającymi synergie.
   - Upewnić się, że "+" pokazuje tylko dla buffed > base.

## Pliki do Zmiany
- `/home/ubuntu/waffen-tactics-game/waffen-tactics-web/src/components/UnitCard.tsx`

## Notatki Dodatkowe
- Jeśli `baseStats` nie jest dostępne, użyć `displayStats` jako base.
- Zielony kolor: `text-green-500` (Tailwind CSS).
- Po zmianach commit: `git commit -m "Fix UnitCard tooltip to show buffs with green +"`.