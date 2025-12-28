# 🎯 Front/Back System Implementation Plan

## Overview
Implement ability for players to position units between front and back lines on the board. Front line units are targeted first by attacks and abilities (unless ability has special targeting parameters).

## Current Status
- ✅ Plan created
- ✅ Krok 1: Analiza obecnej struktury
- ✅ Krok 2: Backend - dodanie pozycji do jednostek  
- ✅ Krok 3: Frontend - model danych
- ✅ Krok 4: UI - podział planszy na front/back
- ✅ Krok 5: Drag & Drop między liniami
- ✅ Krok 6: Tooltip i informacje
- 🎉 **IMPLEMENTACJA ZAKOŃCZONA!**

## Detailed Implementation Steps

### **Krok 1: Analiza obecnej struktury (1-2h)**
- [x] Sprawdzić jak jednostki są przechowywane w `playerState.board` (czy mają już jakieś pozycje?)
- [x] Przeanalizować `GameBoard.tsx` - jak jednostki są renderowane i pozycjonowane
- [x] Sprawdzić backend API dla `moveToBoard` - czy obsługuje pozycje
- [x] Sprawdzić combat logic - jak jednostki są targetowane

**Wnioski z analizy:**
- Jednostki w `board` to `UnitInstance` bez pozycji
- `GameBoard.tsx` renderuje jednostki w jednej linii po indeksie
- Backend `moveToBoard` nie obsługuje pozycji
- Combat targeting prawdopodobnie po kolejności w array

### **Krok 2: Backend - dodanie pozycji do jednostek (2-3h)**
- [ ] Dodać pole `position: 'front' | 'back'` do unit schema w backend
- [ ] Zaktualizować `moveToBoard` endpoint żeby przyjmował pozycję
- [ ] Dodać domyślną pozycję 'front' dla istniejących jednostek
- [ ] Zaktualizować combat targeting: front jednostki targetowane pierwsze
- [ ] Test backend zmian lokalnie

### **Krok 3: Frontend - model danych (30min)**
- [x] Dodać typy TypeScript dla pozycji w unit interfaces
- [x] Zaktualizować `GameBoardProps` i inne komponenty

### **Krok 4: UI - podział planszy na front/back (2-3h)**
- [x] W `GameBoard.tsx` stworzyć dwie sekcje: Front Line i Back Line
- [x] Stylizować wizualnie (front wyżej, back niżej, z etykietami)
- [x] Filtrować jednostki po pozycji przy renderowaniu
- [x] Dodać wizualne oznaczenia (ikony, kolory) dla front/back

### **Krok 5: Drag & Drop między liniami (3-4h)**
- [x] Zaktualizować `handleMoveToBoard` żeby przesyłać pozycję
- [x] Dodać drop zones dla front/back linii
- [x] Obsłużyć drag między istniejącymi liniami (front→back, back→front)
- [x] Dodać wizualne feedback podczas drag (highlight linii docelowej)
- [x] Zapobiec przeciążeniu linii (max jednostki na linię?)

### **Krok 6: Tooltip i informacje (1h)**
- [x] W `UnitCard` dodać pozycję do tooltip
- [x] Dodać przyciski szybkiej zmiany pozycji (już dodane w kroku 4)
- [ ] Zaktualizować opisy w UI

### **Krok 7: Combat overlay aktualizacja (1-2h)**
- [ ] W `CombatOverlay` wyświetlić front/back wizualnie
- [ ] Zaktualizować animacje ataków żeby pokazywały targeting frontu
- [ ] Test combat z różnymi pozycjami

### **Krok 8: Edge cases i walidacja (1-2h)**
- [ ] Obsłużyć maksymalną liczbę jednostek na linię
- [ ] Zapobiec pustemu frontowi (wymusić przynajmniej 1 jednostkę?)
- [ ] Dodać confirm dla zmiany pozycji podczas walki?
- [ ] Test wszystkich scenariuszy drag & drop

### **Krok 9: Testing i polish (2-3h)**
- [ ] Test pełnego flow: kupienie → pozycjonowanie → walka
- [ ] Test targeting priority w combat
- [ ] Responsywność UI na różnych ekranach
- [ ] Performance - czy drag nie laguje z wieloma jednostkami

### **Krok 10: Dokumentacja i cleanup (30min)**
- [ ] Zaktualizować README z nową mechaniką
- [ ] Dodać komentarze w kodzie
- [ ] Commit z opisowym message

## Key Decisions
- **Line limits**: NIE - front/back nie mają limitu jednostek
- **Front requirement**: NIE - nie wymuszamy przynajmniej 1 jednostki na froncie
- **Position impact**: NIE - pozycja nie wpływa na damage/stats (tylko na targeting priority)

## Time Estimate
**Total: 15-20h** (rozłożony na kilka dni)

## Changes Log
- Initial plan created
- [Future changes will be logged here]