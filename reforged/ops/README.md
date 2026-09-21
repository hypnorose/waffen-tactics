# Reforged deploy

**Status: live on waffentactics.pl.** Per the user's call, Reforged replaced
the old game on the main domain outright (not a parallel subdomain) — the
old Flask/gunicorn backend was stopped and its Caddy block repointed. This
runbook reflects what's actually deployed, for whoever has VPS access next.

## Current production layout

- Checkout: `/home/ubuntu/waffen-tactics-reforged/reforged` (branch `reforged`)
- API: `reforged-api.service` (systemd), Fastify on `127.0.0.1:8091`
- Frontend: static build at `apps/web/dist`, served directly by Caddy
- DB: SQLite at `apps/server/reforged.sqlite3`, env in `apps/server/.env.production` (JWT_SECRET generated on deploy, not in git)
- Caddy: `waffentactics.pl` block in `/home/ubuntu/waffen-tactics-game/waffen-tactics-web/Caddyfile` proxies `/api/*` to `localhost:8091` and serves the Reforged `dist/` — **no `strip_prefix`**, since the Fastify routes already include `/api`
- Old backend: gunicorn processes stopped (were unmanaged `nohup`, not systemd); `waffen-tactics-game` checkout left on disk but not serving anything

**Caddy reload gotcha**: this box's `waffentactics-caddy.service` has
`ExecReload=kill -USR1`, which this Caddy build logs as `"not implemented"`
— `systemctl reload` silently no-ops. Use `caddy reload --config <path>
--adapter caddyfile --address localhost:2019` instead (talks to the admin
API directly). The systemd unit's ExecReload should probably be fixed the
same way, but that's shared infra outside this branch's scope.

## Redeploying after a change

```bash
cd /home/ubuntu/waffen-tactics-reforged/reforged
git pull
pnpm install
pnpm turbo run build
sudo systemctl restart reforged-api.service   # only needed if apps/server changed
caddy reload --config /home/ubuntu/waffen-tactics-game/waffen-tactics-web/Caddyfile \
  --adapter caddyfile --address localhost:2019   # only needed if the Caddyfile changed
```

Frontend-only changes need neither restart — Caddy serves `dist/` directly.

## Verifying

```bash
curl -sf https://waffentactics.pl/api/content/units | head -c 200
curl -sf https://waffentactics.pl/ | head -c 200
sudo systemctl is-active reforged-api.service waffentactics-caddy.service
```
