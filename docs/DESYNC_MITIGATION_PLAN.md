# Plan redukcji i diagnostyki DESYNCów

## Cel
Usunąć lub znacząco zredukować rozbieżności między stanem gry po stronie serwera a stanem wyświetlanym w UI (DESYNC). Zapewnić solidną weryfikację (automatyczną i manualną), czytelne logowanie i narzędzia developerskie do debugowania, a także wdrożyć proces, który zapobiega regresjom.

---

## Szybkie podsumowanie etapów
- Faza 0 — Przygotowanie i reproducja
- Faza 1 — Audyt miejsc emisji eventów
- Faza 2 — Backend: canonicalizacja eventów i atomowość mutacji
- Faza 3 — Frontend: deterministyczna reconcylacja i magazyn stanu UI
- Faza 4 — Narzędzia debugowe/UI (Desync Inspector)
- Faza 5 — Testy replay, integracja z CI
- Faza 6 — Telemetria i monitoring produkcyjny
- Faza 7 — Rollout i walidacja manualna

---

## Aktualny status (aktualizacja: 2025-12-18)

- Backend canonicalizer: Completed. Added `event_canonicalizer.py` with canonical emitters (stat buffs, heals, mana updates, regen, DoT ticks, stuns, unit death, shield applied).
- Replaced many raw `event_callback(...)` calls across the simulator/effect sites with calls to canonical emitters to ensure server mutates in-memory state prior to emission.
- Shield canonicalized: `services/effects/shield.py` now uses `emit_shield_applied` so `recipient.shield` and `recipient.effects` are updated before the event is returned.
- Frontend fixes: `template_id` preserved in unit init payloads; deterministic recompute implemented; Dev-only `Desync Inspector` UI added.
- Tests: Added unit tests for canonical emitters and replay-based snapshot consistency checks; fixed and normalized `sim_with_skills.jsonl` so replay tests are stable. Full test run: all backend tests pass locally (238 passed, 1 warning at time of update).
- Minor parser/backcompat: `SkillParser.parse_skill_from_unit_data` injects `mana_cost` from unit data if missing to avoid failing bulk loads of legacy unit definitions.

## What changed in practice (files of interest)
- `waffen-tactics/src/waffen_tactics/services/event_canonicalizer.py` — new central emitter + `emit_shield_applied`.
- `waffen-tactics/src/waffen_tactics/services/effects/shield.py` — now delegates to canonical emitter and returns canonical payload.
- Multiple service modules updated to call canonical emitters: `combat_simulator.py`, `combat_effect_processor.py`, `combat_per_second_buff_processor.py`, `combat_regeneration_processor.py`, `combat_attack_processor.py`, `stat_buff_handlers.py`.
- Tests: `waffen-tactics/tests/test_event_canonicalizer.py` and `waffen-tactics/tests/test_event_snapshot_consistency.py` — added/updated to validate canonical emitter behavior and event→snapshot consistency.

## Remaining work / next steps
- Persist authoritative UI game state (frontend store) and wire `Desync Inspector` export into automated reports (next priority).
- Add CI job to run replay tests and raise alerts on regressions.
- Telemetry: instrument minimal DESYNC reports (timestamp, seq, unit_id, diff) and route to monitoring.
- Manual verification & rollout checklist: finish canary rollout and observe telemetry for 1 week.

If you'd like, I'll proceed now to (pick one):
- Add the CI job and replay runner (fast follow); or
- Implement the frontend `persist authoritative UI game state` step and add export integration to `Desync Inspector`.


---

## Faza 0 — Przygotowanie (0.5 dni)
- Zrób backup krytycznych plików: `useCombatOverlayLogic.ts`, `game_combat.py`, `combat_simulator.py`, `combat_effect_processor.py`.
- Upewnij się, że masz działający harness/replayer (`tmp_simulate_combat.py`) i plik z przykładowym przebiegiem `sim_with_skills.jsonl`.
- Cel: odtworzyć desync lokalnie deterministycznie.

---

## Faza 1 — Audyt (1 dzień)
- Wypisz wszystkie miejsca backendu, które emitują eventy wpływające na stan gry (HP, mana, buffy, efekty). Prawdopodobne pliki:
  - `waffen-tactics/src/waffen_tactics/services/combat_simulator.py`
  - `waffen-tactics/src/waffen_tactics/services/combat_effect_processor.py`
  - `combat_regeneration_processor.py`, `combat_per_second_buff_processor.py` itp.
- Zbierz przykładowe payloady (legacy vs. canonical): `amount` vs `value`, `stat` vs `stats`, brak `value_type`.
- Wynik: raport z listą emitterów oraz przykładowymi payloadami i problemami.

---

## Faza 2 — Backend (2–4 dni)
Cel: Emitować spójne, kanoniczne eventy i mutować stan serwera przed emisją.

Kroki:
1. Ujednolić kształt `stat_buff` i podobnych eventów do formatu:
   ```json
   {
     "type": "stat_buff",
     "data": {
       "caster_id": "...",
       "unit_id": "...",
       "stats": ["attack"],
       "value": 20,
       "value_type": "flat", // lub "percent"
       "duration": 5,
       "source": "skill_xyz"
     }
   }
   ```
2. W miejscach, gdzie emitujesz `stat_buff`: najpierw **zmutuj** in-memory stan jednostki (dodaj canonical effect do `unit.effects`, zaktualizuj `buffed_stats`/liczbowo), potem **emituj** event. Dzięki temu następny `state_snapshot` będzie zawierał skutek.
3. Zaktualizuj `Unit.to_dict()` / serializację snapshotów tak, by zawsze zawierały: `effects`, `buffed_stats`, `template_id`, `avatar`.
4. Jeśli nie możesz od razu przepisać wszystkich emitterów, dodaj centralny adapter w `combat_simulator`/SSE-route, który konwertuje legacy payloady do formy canonical.

Pliki do zmiany: `combat_effect_processor.py`, `combat_simulator.py`, `combat_unit.py`, `game_combat.py` (SSE)

Testy: uruchom lokalny symulator i upewnij się, że `stat_buff` event jest natychmiast odzwierciedlony w następnym `state_snapshot`.

---

## Faza 3 — Frontend (2–3 dni)
Cel: Klient trzyma rekosyliacyjny, deterministyczny stan i daje bogate informacje o desyncu.

Kroki:
1. W `useCombatOverlayLogic.ts` (lub dedykowanym store):
   - Wprowadź strukturę `unitsById: Record<string, Unit>` i `lastSnapshotSeq`.
   - Przyjmuj eventy i stosuj deterministyczne, lokalne update'y (optimistic) ale zawsze reconcyluj z `state_snapshot`.
2. Implementuj `normalizeEffectForCompare(effect)` i `recomputeBuffedStats(unit)`:
   - `recomputeBuffedStats` bierze `base_stats` i listę canonical `effects` i zwraca spójne `buffed_stats`.
3. Kolejkuj `state_snapshot` które przychodzą przed `units_init` i flushuj po otrzymaniu `units_init`.
4. Przy aplikowaniu `state_snapshot` **zawsze** zachowuj `avatar` / `template_id` / `skill` / `factions` z poprzedniego UI jeśli snapshot ich nie zawiera.
5. Porównanie (diff): przy `state_snapshot` porównuj pozycję UI ze snapshotem — twórz pełny diff zawierający:
   - `hp`, `max_hp`, `attack`, `defense`, `attack_speed`, `current_mana`, `effects[]` (canonical shape), `persistent_buffs`, `shield` itd.
6. Grace window: zapobiegaj spamowi DESYNC — wprowadź krótkie okno (np. 250–500 ms) dla transientowych rozbieżności zanim uznasz je za krytyczne.

Dodatkowo: dodaj prostą funkcję `exportDesyncReport(unitId, diff, pendingEvents)` do szybkiego zbierania raportów.

---

## Faza 4 — Narzędzia debugowe UI (1–2 dni)
- `Desync Inspector` (dev-only panel): lista desynców, rozwiń pełen diff, przyciski `Reconcile` (nadpisz UI serwerem) i `Revert` (cofnij UI do poprzedniego snapshotu), `Export` (zapakuj snapshot + pending events w JSON).
- Zadbaj o czytelne formatowanie logów w konsoli: każdy `[DESYNC]` zawiera `unit_id`, `seq`, `timestamp`, `diff (full)`, `pending_events`.

---

## Faza 5 — Testy replay i CI (1–2 dni)
- Rozszerz istniejący test replay (np. `waffen-tactics/tests/test_event_snapshot_consistency.py`) o dokładniejsze asercje: po `stat_buff` musi wystąpić snapshot z odpowiednim `effect` i `buffed_stats`.
- Dodaj frontendowe testy jednostkowe dla `normalizeEffectForCompare` i `recomputeBuffedStats`.
- Dodaj job CI, który buduje backend/frontend i uruchamia replay tests.

---

## Faza 6 — Telemetria i monitoring (1 dzień + wdrożenie)
- Zbieraj anonimowe raporty DESYNC (minimalny JSON) do Sentry/ELK:
  - `timestamp`, `unit_id`, `diff`, `seq`, `pending_events_count`, `client_version`.
- Ustal alerty (np. >5 desynców/min na instancję) i dashboard do analiz.

---

## Faza 7 — Rollout i walidacja (1 dzień + 1 tydz. obserwacji)
- Wdróż zmiany na canary/qa.
- Przeprowadź manualny checklist testów (poniżej).
- Obserwuj telemetry przez tydzień i adresuj najczęstsze przypadki.

---

## Manualny checklist (do weryfikacji)
1. Uruchom backend lokalnie i frontend dev.
2. Odtwórz symulację `tmp_simulate_combat.py` lub zagraj krótką rundę.
3. Otwórz Desync Inspector i obserwuj pipeline eventów:
   - `units_init` → `attack` → `stat_buff` → `state_snapshot`
4. Po `stat_buff` sprawdź, czy następny snapshot zawiera `effects` i odpowiednio zaktualizowane `buffed_stats`.
5. Wywołaj scenariusz z szybkim buff/debuff, sprawdź czy grace window nie produkuje fałszywych alarmów.
6. Eksportuj przykładowy desync JSON i zweryfikuj kompletny diff.

---

## Rekomendacje i uwagi techniczne
- Preferuj `seq` nad `timestamp` do porządkowania eventów (monotoniczne ID generowane przez serwer).
- Przy porównaniach wartości liczbowych stosuj tolerancję (np. `epsilon = 0.1`) dla floatów.
- Preferuj canonical effects (tablica `stats`, `value`, `value_type`) — ułatwia porównywanie i testy.
- Jeżeli backend nie może być natychmiast zmieniony, buduj adapter po stronie SSE który naprawia payloady i dodaje brakujące pola.

---

## Priorytety krótkoterminowe (co wdrożyć natychmiast)
1. Adapter w backendzie (szybki patch) który konwertuje legacy payloady do canonical i **mutuje stan przed emisją**.
2. Frontend: rozszerzyć `useCombatOverlayLogic` o `recomputeBuffedStats` i pełne diffowanie przy `state_snapshot`.
3. Dodać `Desync Inspector` minimalny (lista + export).

---

## Szacowane nakłady czasu (orientacyjne)
- Audyt: 1d
- Szybki backend-adapter: 0.5–1d
- Pełna canonicalizacja backendu: 2–3d
- Frontend reconciling + Desync Inspector: 1.5–3d
- Testy replay + CI: 1–2d
- Rollout + monitoring: 1d + 1 tydz obserwacji

---

## Pliki do przeglądu / zmiany (lista)
- Backend: `waffen-tactics/src/waffen_tactics/services/combat_simulator.py`, `combat_effect_processor.py`, `combat_regeneration_processor.py`, `combat_unit.py`, `game_combat.py` (SSE route in web backend)
- Frontend: `waffen-tactics-web/src/hooks/useCombatOverlayLogic.ts`, `waffen-tactics-web/src/components/CombatUnitCard.tsx`, nowy `waffen-tactics-web/src/components/DesyncInspector.tsx`
- Tests: `waffen-tactics/tests/test_event_snapshot_consistency.py`, `waffen-tactics-web/tests/*`

---

## Następne kroki (co mogę zrobić teraz)
- Opcja A (frontend-first): dodać `template_id?: string` do `Unit` interfejsu i wdrożyć `Desync Inspector` minimalny.
- Opcja B (backend-first): zrobić szybki adapter w `combat_simulator` który canonicalizuje eventy i mutuje stan przed emisją.

Napisz, którą opcję preferujesz — wdrożę ją i przygotuję PR + krótką instrukcję testową.
