# Codex remote workflow

This is the operational summary for working on the web version of Waffen Tactics with the VPS as the runtime target and the local machine as the source of truth.

For the full planning artifact, see [vps-remote-dev-workflow](</C:/Users/yoss/Documents/waffentactics/.claude/specs/vps-remote-dev-workflow/requirements.md>).

## Current Architecture

- Shared game logic lives in `waffen-tactics/`.
- Web frontend lives in `waffen-tactics-web/src/`.
- Flask backend lives in `waffen-tactics-web/backend/`.
- Root scripts control startup, shutdown, and status.
- The VPS project path is `/home/ubuntu/waffen-tactics-game`.
- Public runtime is `https://waffentactics.pl`, proxied by Caddy to `localhost:8000` and `localhost:3000`.
- Discord is login-only here; we are not maintaining a Discord bot runtime.

## Machines

- Local source of truth: `C:\Users\yoss\Documents\waffentactics`
- SSH alias: `waffentactics-vps`
- VPS runtime: `/home/ubuntu/waffen-tactics-game`

## Working Rules

1. Make the local workspace the canonical place for changes.
2. Use the VPS for runtime validation, log inspection, and smoke testing.
3. Keep runtime-only data out of git: `.env`, virtualenvs, `node_modules`, logs, caches, and local DB artifacts.
4. Avoid leaving manual edits on the VPS; if you need an emergency fix there, capture it back into local git history quickly.
5. Do not broaden scope into Docker/systemd refactors unless the task explicitly asks for that.
6. Do not add or revive Discord bot runtime support as part of this workflow.

## Standard Loop

1. Edit locally.
2. Review locally.
3. Commit locally.
4. Deploy to the VPS.
5. Restart or refresh the runtime.
6. Inspect status and logs over SSH.

## Deploy Helper

Use the root deploy script to push the committed local branch to the VPS and restart the runtime:

```powershell
.\deploy.ps1 -RunTests
```

If you still have uncommitted work and want the script to create a deploy commit first, run:

```powershell
.\deploy.ps1 -AutoCommit -RunTests
```

## Useful Commands

```powershell
ssh waffentactics-vps "cd ~/waffen-tactics-game && git status --short --branch"
ssh waffentactics-vps "cd ~/waffen-tactics-game && ./status.sh"
ssh waffentactics-vps "cd ~/waffen-tactics-game && ./stop-all.sh"
ssh waffentactics-vps "cd ~/waffen-tactics-game && ./start-all.sh"
ssh waffentactics-vps "tail -n 120 ~/waffen-tactics-game/waffen-tactics-web/backend/api.log"
ssh waffentactics-vps "tail -n 120 ~/waffen-tactics-game/waffen-tactics-web/vite.log"
```

## Emergency VPS change reconciliation

The VPS is a runtime target, not a second source of truth. If an emergency
change was made there, capture it before deploying anything else.

1. Freeze normal deploys and record the runtime state:

   ```powershell
   ssh waffentactics-vps "cd ~/waffen-tactics-game && git status --short --branch && git log --oneline -5 && ./status.sh"
   ssh waffentactics-vps "tail -n 120 ~/waffen-tactics-game/waffen-tactics-web/backend/api.log"
   ssh waffentactics-vps "tail -n 120 ~/waffen-tactics-game/waffen-tactics-web/vite.log"
   ```

2. Classify the delta on the VPS before copying anything. Capture tracked
   edits with `git diff --binary HEAD` and list untracked paths with
   `git ls-files --others --exclude-standard`. Treat `.env`, virtualenvs,
   `node_modules`, logs, caches, local SQLite databases, and generated assets
   as runtime-only; do not copy them into the source tree.

3. Copy only reviewed source/config files or the captured patch into a local
   reconciliation staging directory. Keep the original VPS patch and status
   output as evidence. If the VPS has commits not present locally, export
   those commits with `git format-patch` and apply them to a local review
   branch; do not make the VPS branch the canonical base.

4. Review locally with `git diff`, `git diff --check`, and the relevant tests.
   Resolve conflicts by preserving the local canonical source and explicitly
   reapplying only the emergency behavior that is still required. Never use a
   default-position, default-config, or silent content fallback to hide a
   reconciliation conflict.

5. Commit the reviewed local result. Then use the normal deploy helper to push
   the local branch, restart the runtime, and verify it:

   ```powershell
   .\deploy.ps1 -RunTests
   ssh waffentactics-vps "cd ~/waffen-tactics-game && git status --short --branch && ./status.sh"
   ```

6. Re-check backend and frontend logs after the restart. If the emergency
   change cannot be reproduced locally, leave the VPS untouched, record the
   blocker in the issue, and do not continue normal feature work from the
   divergent runtime tree.

## Current Imported State

This local workspace was imported from the VPS working tree and currently preserves the VPS branch state, including the two commits ahead of `origin/main` and the uncommitted changes that were already present on the server.

Before new feature work, create a checkpoint branch or commit so this imported snapshot is preserved and easy to compare against.
