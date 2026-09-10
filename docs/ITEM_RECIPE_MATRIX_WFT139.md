# WFT-139 — macierz 21 receptur itemów

Status: **zaakceptowany content i jawny kontrakt runtime; aktywacja runtime i balans pozostają osobnymi zadaniami**<br>
Źródło: Plane, WFT-139, komentarz `58175dd5-e14e-49f5-8ffe-359fa02bca56`, 2026-09-10<br>
Zakres: 6 bazowych itemów, 15 par różnych itemów oraz 6 kombinacji `A + A`.

Machine-readable copy: [`waffen-tactics/item_recipe_matrix_wft139.json`](../waffen-tactics/item_recipe_matrix_wft139.json).

To jest trwała kopia zaakceptowanej tabeli zapisanej w Plane. Jest źródłem prawdy dla
receptur, a machine-readable copy zawiera również zaakceptowane pola kontraktu
runtime z WFT-140, ale nie jest jeszcze aktywnym datasetem runtime. Wcześniejsze
AI-generated propozycje zostały zastąpione przez ten input autora.

## Bazowe itemy

| Item | Bazowe statystyki |
| --- | --- |
| Przyprawy | +8 ataku |
| Oranżada | +3 regeneracji many |
| Płaszcz | +100 HP |
| Sejf | +12 obrony |
| Zakolanówki | +0,12 szybkości ataku |
| Notatnik | +2 HP regeneracji/s |

## 21 receptur

| # | Składniki | Wynik | Statystyki / efekt |
| ---: | --- | --- | --- |
| 1 | Przyprawy + Przyprawy | ETF przyprawowy | +30 ataku. |
| 2 | Przyprawy + Oranżada | Helena o smaku kurkumy | +10 ataku, +3 regeneracji many, +5 many przy ataku. |
| 3 | Przyprawy + Płaszcz | Płaszcz ze 100% bawełny | +200 HP, +10 ataku, tarcza równa 30% maksymalnego HP na starcie walki. |
| 4 | Przyprawy + Sejf | Skrytka na oregano | +12 ataku, +15 obrony, trafiony przeciwnik ma -30% obrony przez 2 s. |
| 5 | Przyprawy + Zakolanówki | Ponętne stópki | +15 ataku, +0,20 szybkości ataku, bonusowy atak zadaje dodatkowe obrażenia równe 2× atakowi właściciela. |
| 6 | Przyprawy + Notatnik | Pikante słówka | +15 ataku, +4 HP regeneracji/s, +10% life steal. |
| 7 | Oranżada + Oranżada | Mandarynkowy Sodastream | +12 regeneracji many, bonusowy atak zwraca 30 many. |
| 8 | Oranżada + Płaszcz | Bluza z Bytom | +150 HP, +4 regeneracji many, co 3 s leczy sojusznika z najmniejszym aktualnym HP za 15% jego maksymalnego HP. |
| 9 | Oranżada + Sejf | Kolekcja syropów | +15 obrony, +3 regeneracji many. Pierwsze zejście właściciela do 50% maksymalnego HP lub niżej daje na 3 s +20 many/s oraz tarczę równą 20% maksymalnego HP. |
| 10 | Oranżada + Zakolanówki | Kremik owocowy | +4 regeneracji many, +0,18 szybkości ataku, co 4. zwykły atak zadaje 100 obrażeń trzem losowym żyjącym wrogom. |
| 11 | Oranżada + Notatnik | Telewizor 4K 50 cali | +4 regeneracji many, +4 HP regeneracji/s, przy każdym uzyskaniu many właściciel odzyskuje tyle samo HP. |
| 12 | Płaszcz + Płaszcz | Płaszcz 200% WEŁNY | +600 HP. |
| 13 | Płaszcz + Sejf | Forteca z książek | +200 HP, +20 obrony, wszyscy wrogowie w przednim rzędzie tracą 1% maksymalnego HP/s. |
| 14 | Płaszcz + Zakolanówki | Fartuszek Femboya | +150 HP, +0,15 szybkości ataku, bonusowy atak zadaje dodatkowe obrażenia równe 15% maksymalnego HP właściciela. |
| 15 | Płaszcz + Notatnik | Full-plate cum-armor | +200 HP, +6 HP regeneracji/s, dodatkowo odzyskuje 2% maksymalnego HP/s. |
| 16 | Sejf + Sejf | Skruszony ząb | +30 obrony, bezpośrednio atakujący otrzymuje obrażenia równe 50% aktualnej obrony właściciela. |
| 17 | Sejf + Zakolanówki | Zestaw do makijażu po Edycie | +15 obrony, +0,15 szybkości ataku. Przy ataku właściciel zyskuje +1 ataku, +0,10 szybkości ataku i +1 obrony; maksymalnie 10 stacków. |
| 18 | Sejf + Notatnik | Fap-folder | +18 obrony, +4 HP regeneracji/s. Po otrzymaniu bezpośredniego trafienia właściciel zyskuje +0,2 HP regeneracji/s i +0,5 obrony; maksymalnie 30 stacków. |
| 19 | Zakolanówki + Zakolanówki | Stópki rozmiar 44 | +0,35 szybkości ataku, bonusowy atak trafia do 5 dodatkowych żyjących wrogów. |
| 20 | Zakolanówki + Notatnik | Idealny traf | +0,18 szybkości ataku, +3 HP regeneracji/s, każdy zwykły atak zadaje dodatkowe obrażenia równe aktualnej regeneracji HP właściciela. |
| 21 | Notatnik + Notatnik | Encyklopedia seksu | +12 HP regeneracji/s. Regeneracja HP właściciela jest również przyznawana dwóm losowym sojusznikom; po śmierci wybranego sojusznika wybierany jest zastępca. |

## Prototypowe zasady interpretacji

- Skrót `s` oznacza szybkość ataku.
- „Dodatkowe obrażenia 2× atak” i „15% maksymalnego HP” są dodatkowym komponentem obrażeń bonusowego ataku, a nie zamianą jego bazowych obrażeń.
- „Co X atak” liczy zwykłe ataki; bonus attack nie zwiększa tego licznika, chyba że receptura mówi o bonusowym ataku wprost.
- Efekty czasowe są odświeżane przez ponowne wywołanie, a nie stackowane, chyba że opis podaje maksymalną liczbę stacków.
- Redukcja obrony Skrytki na oregano jest mnożnikowa (-30% aktualnej obrony celu), trwa 2 s i odświeża się przy kolejnym trafieniu.
- Losowe cele są wybierane wyłącznie spośród żywych, legalnych celów; w ramach jednego proc nie powtarzają się.
- Mana jest ograniczana do maksymalnej many jednostki, a leczenie nie powoduje overhealu.
- „Forteca z książek” zadaje obrażenia procentowe co sekundę wszystkim żyjącym wrogom w przednim rzędzie.

## Następny krok

WFT-139 i kontrakt runtime WFT-140 są zamknięte po stronie decyzji/contentu i prototypowej
semantyki. Następne kroki to implementacja jednego źródła danych oraz auto-combine/persistence
zgodnie z zależnościami zapisanymi w Plane. Osobny pass balansu nadal jest wymagany przed
traktowaniem liczb jako finalnych. Legacy item data pozostaje bez zmian.
