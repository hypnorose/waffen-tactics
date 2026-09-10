# Release Validation Gate

This is the canonical pre-release checklist for Waffen Tactics. It separates
local automated evidence from runtime evidence and must be completed against
the exact local revision intended for deployment.

## 1. Scope and ownership

- **Local source of truth:** `C:\Users\yoss\Documents\waffentactics`.
- **Runtime target:** VPS alias `waffentactics-vps`, path
  `/home/ubuntu/waffen-tactics-game`.
- **Release owner:** the person authorizing deployment owns the final go/no-go
  decision and any explicit waiver.
- **Feature owner:** the Linear issue owner resolves code or content failures;
  the release owner resolves deployment and runtime failures.

Do not close the gate when a blocking Linear issue is unresolved. A blocking
item may be waived only by an explicit user decision recorded in Linear.

## 2. Local automated gate

Run from the repository root on the exact revision to be deployed:

```powershell
git status --short --branch
git diff --check
python -W error -m pytest -q waffen-tactics\tests
python -W error -m pytest -q waffen-tactics-web\backend
Push-Location waffen-tactics-web
try {
    npm run typecheck
    npx vitest run
    npm run build
} finally {
    Pop-Location
}
```

Expected evidence:

- core and backend tests pass, with skips recorded rather than hidden;
- frontend typecheck, tests, and production build pass;
- `git diff --check` reports no whitespace errors;
- the final revision and working-tree state are recorded in the Linear issue.

For balance-sensitive changes, also run the scoped audit and attach its output
or summary, including seed, unit/trait counts, errors, timeouts, and whether
the result is deterministic:

```powershell
python tools\balance_audit.py --help
```

Use the audit's project-approved invocation for the change under review; do
not treat a smoke run as a full balance sign-off.

## 3. Replay and contract evidence

For event/replay changes, run the relevant backend contract tests and the
frontend replay harness described in [Event Replay Testing](EVENT_REPLAY_TESTING.md).
Record:

- the input seed or event-stream identifier;
- event count and snapshot count;
- desync count and the first failing sequence, if any;
- the exact frontend/backend revisions used.

Build success is not replay proof. A passing Python reconstructor is not proof
that the browser Game View renders the same result.

For `regen_gain`, the canonical event must include the finite
`post_hp_regen_per_sec` value after exactly one authoritative mutation. Replay
must apply that post-state to `unit.buffed_stats.hp_regen_per_sec` and keep the
display-only `regenMap` entry; it must not infer the value from
`amount_per_sec` or overwrite the reducer from a snapshot. A runtime export
such as `desync_logs_1789057936444.json` is evidence of the symptom and must be
reproduced by a deterministic reducer/compare test before the release issue is
advanced.

## 4. Revision alignment before deployment

Before using `deploy.ps1`, confirm:

```powershell
git branch --show-current
git rev-parse HEAD
git status --short --branch
```

The intended source revision must be committed. The deploy helper refuses a
dirty tracked tree unless `-AutoCommit` is explicitly supplied; untracked files
are never silently included. Review the paths it reports before proceeding.

## 5. VPS deployment and post-deployment checks

Deployment is an authorized release action, not part of local test proof:

```powershell
.\deploy.ps1 -RunTests
ssh waffentactics-vps "cd ~/waffen-tactics-game && git status --short --branch && git rev-parse HEAD && ./status.sh"
ssh waffentactics-vps "tail -n 120 ~/waffen-tactics-game/waffen-tactics-web/backend/api.log"
ssh waffentactics-vps "tail -n 120 ~/waffen-tactics-game/waffen-tactics-web/vite.log"
```

Expected evidence:

- VPS `HEAD` matches the intended local revision;
- `status.sh` reports the expected services running;
- `ss -lntp` shows the backend on `127.0.0.1:8000` and the Vite server on
  `127.0.0.1:3000`; neither application port is publicly listening;
- backend and frontend logs show no new startup or runtime errors;
- rollback and failure owner are recorded if any check fails.

Do not copy emergency VPS edits into the source tree without following the
[Emergency VPS change reconciliation procedure](CODEX_REMOTE_WORKFLOW.md#emergency-vps-change-reconciliation).

## 6. Manual runtime gate

These checks cannot be replaced by unit tests, builds, or Console output:

- open the deployed Game View and run a representative victory and defeat;
- verify the next-action guidance, opponent formation/target preview, passive
  and trait identity, and round report are player-readable;
- verify replay and live combat present the same canonical summary;
- repeat the critical UI checks at 1280x720 and 1920x1080;
- verify the public HTTPS app and `/api` path work through Caddy while direct
  access to ports 3000 and 8000 from outside the VPS is unavailable;
- record browser/console errors, screenshots, seed, and timestamp in Linear.

Mark the issue `Needs Manual Test` until this evidence exists. Do not claim
player-runtime acceptance from local tests alone.

## 7. Go/no-go and rollback

The gate is **GO** only when sections 2–6 have evidence and every blocking
Linear issue is `Done` or has an explicit user waiver. Otherwise it is **NO-GO**.

If deployment fails, the release owner stops further rollout, preserves the
local revision and VPS status/log evidence, and opens or updates the owning
Linear issue. Rollback uses the documented deployment procedure and an
approved known-good revision; never use an unreviewed manual VPS edit as the
new source of truth.
