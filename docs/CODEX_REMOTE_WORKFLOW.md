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

## Useful Commands

```powershell
ssh waffentactics-vps "cd ~/waffen-tactics-game && git status --short --branch"
ssh waffentactics-vps "cd ~/waffen-tactics-game && ./status.sh"
ssh waffentactics-vps "cd ~/waffen-tactics-game && ./stop-all.sh"
ssh waffentactics-vps "cd ~/waffen-tactics-game && ./start-all.sh"
ssh waffentactics-vps "tail -n 120 ~/waffen-tactics-game/waffen-tactics-web/backend/api.log"
ssh waffentactics-vps "tail -n 120 ~/waffen-tactics-game/waffen-tactics-web/vite.log"
```

## Current Imported State

This local workspace was imported from the VPS working tree and currently preserves the VPS branch state, including the two commits ahead of `origin/main` and the uncommitted changes that were already present on the server.

Before new feature work, create a checkpoint branch or commit so this imported snapshot is preserved and easy to compare against.
