Step-by-step analysis of the logs you pasted, what was wrong, what I changed, and what to verify next.

Summary of the problem shown by the logs

Repeated DESYNC entries for effects and buffed_stats:
Example: Player unit dd472aa1 has UI effects [] but Server shows [{"type":"buff","stat":"defense","value":25,...}].
Later we see UI has a local effect (with id/expiresAt/caster_name), server has a similar effect but with a different source string ("skill_dd472aa1") and the buffed_stats values differ (UI shows 55 vs Server 30).
RECONCILE logs show the client was forced to accept server HP values (UI=null -> Server=494), meaning UI was not yet initialized or has stale values when snapshot arrived.
You also had duplicate skill_cast prints (same event logged twice), and repeated snapshots with same seq which the client ignored as older — this indicates event ordering/duplication issues.
Root causes (why these symptoms happened)

Effect normalization / comparison bug

The client was filtering out any effect object that contained client-only metadata (id, expiresAt, caster_name) by completely removing the effect from the comparison list. That made the UI normalized list empty while the server normalized list contained the server effect → false-positive DESYNC.
Client and server used slightly different shapes (server used stat/value or effect object, server source might be skill_x vs client caster_id), so naive string comparison produced noise.
Local buff application double-count / nondeterministic calculation

The client previously updated buffed_stats by incrementally adding deltas using the current buffed_stats as a base. When the client had already applied local effects or when snapshots arrived later, that caused double counting or different totals than the server (UI 55 vs server 30).
There was no reliable base_stats recorded to use as a stable baseline when recomputing buffed_stats.
Out-of-order snapshots and initial placeholders

Snapshots sometimes arrived before units_init had been processed, so UI unit objects had placeholder hp = 0 or null and produced DESYNC logs (UI=0 vs Server=640).
The client would sometimes log RECONCILEs while the UI had not had its initial state set.
Duplicated events (skill_cast printed twice)

Duplicate "Processing skill_cast" logs indicate either duplicated SSE events or the client enqueued the same event twice. This needs checking in event stream production and client enqueueing (we added a guard for early snapshot queuing but duplicates might be elsewhere).
What I implemented (immediate fixes applied)
I modified useCombatOverlayLogic.ts (changes are already applied to your workspace):

Make server snapshots authoritative on merge

When processing state_snapshot, the client now applies server state for runtime fields (hp, shield, current_mana, effects, persistent_buffs, buffed_stats).
Client preserves UI-only display fields (avatar, factions, classes, skill).
I added [RECONCILE] log lines that show field-by-field reconciliation when the client had a different value and the server overwrote it.
Prevent out-of-order snapshot races

Client now queues state_snapshot events that arrive before units_init and flushes them immediately after units_init. This prevents the snapshot arriving while the UI still has placeholders.
Deterministic buff computation (fix double-counting)

On units_init the client now stores a base_stats object for each unit (attack, defense, base hp, attack_speed, max_mana).
When applying a local stat_buff event, instead of incrementally modifying buffed_stats, the client now:
Appends the effect to unit.effects.
Recomputes buffed_stats deterministically from base_stats, persistent_buffs, and the full effects list using a single function recomputeBuffedStats(u).
This guarantees the computed buffed_stats matches the deterministic algorithm (and avoids accumulation errors).
Correct effect normalization (stop removing server-comparable entries)

Added normalizeEffectForCompare(e) to produce canonical server-like effect shapes (type, stat/stats, value, value_type, duration, source).
Instead of filtering out whole effects that have client metadata, the client now strips UI-only keys only for comparison and compares canonical shapes. This prevents false-empty normPrev.
Better, more actionable DESYNC logs

The client now logs:
DESYNC-BUFFS showing per-stat buffed_stats diffs with tolerances.
DESYNC for effects mismatches with both normalized arrays printed and bsDiffs to help correlate a buff change with effect payloads.
DESYNC-EFF for effective HP (hp + shield) mismatches.
Files changed

useCombatOverlayLogic.ts
Added: normalizeEffectForCompare, recomputeBuffedStats, base_stats initialization at units_init.
Updated: snapshot handling (queue early snapshots, seq filtering), effect comparisons, stat_buff handling to append effect + recompute buffed_stats, authoritative merge with RECONCILE logs.
Step-by-step diagnosis for your specific log trace
(Using the output you pasted)

At seq 0..2 the server sends snapshot(s) that include a buff effect for dd472aa1:

Server effect: {"type":"buff","stat":"defense","value":25,...}
UI initially shows no effects because the UI either hasn't attached the locally-created effect in the canonical shape or we were previously filtering it out — thus normPrev was [].
Fix: normalizeEffectForCompare now produces a server-comparable element from the client effect, so normPrev will match normServer if shapes/values match.
RECONCILE showing UI=null → Server=494:

This means the UI's unit hp was uninitialized or cleared. That is prevented now by queuing snapshots until units_init. If you still see null→Server, please check if units_init arrived and was processed before that snapshot (open console to see the [SSE] Flushed queued state_snapshots after units_init log).
buffed_stats mismatch (UI 55 vs Server 30)

Root cause: incremental delta logic on the client double-counted or used the wrong base stat. For example:
If base defense = 30, applying +25 flat should yield 55 — that explains UI 55.
Server reports 30, meaning server's buffed_stats were computed differently (maybe persistent_buffs/past effects not included by client, or server's base differs).
Fix: client now stores base_stats (from units_init) and recomputes buffed_stats from base + all effects, so client will compute the same result if the list of effects and the base match the server. If server base differs, the RECONCILE of hp, attack, defense will show it and client will be replaced by the server state (authoritative).
Effect source name mismatch (client dd472aa1 vs server skill_dd472aa1)

That's a naming/shape mismatch — not a logical bug but a communication mismatch. Once normalization compares source fields, you'll see this mismatch in the DESYNC log and can decide to:
Update backend to use the same source string (recommended),
Or map it on the client (e.g., treat caster_id === dd472aa1 as equivalent to source === skill_dd472aa1).
Problems still worth checking (next actionable items)

Duplicate skill_cast logs: investigate why skill_cast is processed twice. Possible causes:
Backend emitting the event twice, or
The client enqueuing the same SSE chunk twice (e.g., pendingSnapshotsRef flush code or setEventQueue calls). Steps:
Capture raw SSE stream (network tab) and check if server sent duplicate messages.
If server duplicates, fix server emission (likely in combat simulator event emission loop).
Make server effect shapes fully consistent:
The server currently has multiple places emitting stat_buff/buff events with different keys (stat vs stats, amount vs value vs value_type, source naming).
Best practice: choose a single canonical effect shape for the SSE API:
{ type: 'stat_buff', stats: ['defense'], value: 25, value_type: 'flat'|'percentage', duration: 4, source: 'skill_x' }
Update map_event_to_sse_payload and effect emitters under effects to always use that canonical shape. (I can prepare a patch suggestion for the backend if you want.)
Concrete code-level fixes I already implemented (recap)

units_init now stores base_stats, effects, persistent_buffs.
state_snapshot handling:
Queues early snapshots until units_init is seen.
Tracks lastSnapshotSeqRef and ignores older snapshots.
Applies server state authoritatively and prints [RECONCILE] logs.
stat_buff processing:
Appends effect to unit.effects and recomputes buffed_stats via recomputeBuffedStats.
Effect comparison:
Uses normalizeEffectForCompare (canonical shape) for both UI and server effects rather than discarding UI effects with client metadata.
How you can verify / test now

Start services (you already ran start-all.sh).
Open the web client and dev console (F12).
Start a combat and watch for logs:
Look for [SSE] Queued early state_snapshot and [SSE] Flushed queued state_snapshots after units_init (ensures snapshot ordering fix executes).
Observe DESYNC logs — they will now include normPrev, normServer, and bsDiffs. Paste a representative DESYNC here and I’ll analyze it precisely.
Observe [RECONCILE] logs (fields the client overwritten with server authoritative values).
Confirm local effects on unit cards show server-applied effects and buffed_stats reflect server snapshot (no diverging totals).
Reconfirm "Kontynuuj" button appears at combat end.
Recommended next changes (I can implement in order you prefer)

Backend standardization (recommended, high value):
Make effect payloads canonical and consistent in game_combat.map_event_to_sse_payload and effect emitters.
Use value and value_type, always include stats array (even single-stat) to keep shape stable.
Investigate duplicate skill_cast emission:
Capture raw SSE stream in browser network tab; if duplicate messages come from server, fix server emission (combat simulator). If only duplicated client-side, trace enqueueing path.
Add small in-UI debug panel showing recent DESYNC/RECONCILE events (toggleable dev-only panel) so QA can record examples easily.
Add frontend unit tests to simulate sequences (units_init, early snapshot, stat_buff, periodic snapshot) to prevent regressions.
If you want me to continue now, pick from:

(A) I will add a small debug panel in the UI that collects and displays recent DESYNC / RECONCILE entries (makes debugging easier).
(B) I will implement the backend canonicalization of effect payloads (prepare a patch for waffen-tactics/src/waffen_tactics/services/* and game_combat.py).
(C) I will investigate the duplicated skill_cast events by searching for duplicate emission points in the backend and checking client code that enqueues events.
(D) Run a focused reproduction: I can simulate a combat locally and paste filtered DESYNC logs for a single unit for deeper analysis (I can run headless or you can run and paste logs).