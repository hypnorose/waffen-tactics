# Reforged deploy (Phase 11)

Runs on the same VPS as the live `waffentactics.pl` site, in parallel, fully
isolated: its own checkout, its own port, its own SQLite file, its own
systemd unit. The live site's process and Caddyfile are not touched except
to append one new site block.

This is a runbook for whoever has VPS access — these steps have not been run
against production; nothing here has been executed remotely.

## One-time setup

```bash
# separate checkout, not a subdirectory of the existing waffen-tactics-game checkout
cd /home/ubuntu
git clone <repo-url> waffen-tactics-reforged
cd waffen-tactics-reforged
git checkout reforged
cd reforged
corepack enable
pnpm install
pnpm turbo run build
```

Create `apps/server/.env.production` (never commit this):

```
PORT=8091
HOST=127.0.0.1
DB_FILE=/home/ubuntu/waffen-tactics-reforged/reforged/apps/server/reforged.sqlite3
JWT_SECRET=<generate with: openssl rand -base64 48>
```

Install the API as a systemd service:

```bash
sudo install -m 0644 ops/systemd/reforged-api.service /etc/systemd/system/reforged-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now reforged-api.service
sudo systemctl is-active reforged-api.service
```

Append the site block from `ops/Caddyfile.reforged` to the existing
production Caddyfile (`waffen-tactics-web/Caddyfile` in the `main` checkout —
that repo still owns the live Caddy process; do not start a second one), then:

```bash
caddy validate --config <path-to-Caddyfile> --adapter caddyfile
sudo systemctl reload waffentactics-caddy
```

Point `reforged.waffentactics.pl` at the VPS in DNS before or alongside this
step — Caddy's automatic HTTPS needs the record resolving to issue a cert.

## Redeploying after a change

```bash
cd /home/ubuntu/waffen-tactics-reforged
git pull
pnpm install
pnpm turbo run build
sudo systemctl restart reforged-api.service
```

The frontend is static (`apps/web/dist`) — Caddy serves it directly, no
restart needed for frontend-only changes once the build completes.

## Verifying

```bash
curl -sf https://reforged.waffentactics.pl/api/content/units | head -c 200
curl -sf https://waffentactics.pl | head -c 200   # confirm the live site is unaffected
```
