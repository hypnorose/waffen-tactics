# VPS Caddy service

`waffentactics-caddy.service` is the versioned production ownership contract
for the public Caddy proxy. It replaces the unmanaged `sudo nohup caddy run`
path used by the legacy `start-all.sh` script.

Install or update it only during an authorized VPS operation:

```bash
sudo install -m 0644 ops/systemd/waffentactics-caddy.service \
  /etc/systemd/system/waffentactics-caddy.service
sudo systemctl daemon-reload
sudo systemctl enable --now waffentactics-caddy.service
sudo systemctl is-enabled waffentactics-caddy.service
sudo systemctl is-active waffentactics-caddy.service
```

Before enabling it, validate the target Caddyfile and inspect the existing
manually launched process. Do not kill or replace an existing proxy while the
release owner has not authorized the cutover. Preserve unrelated untracked VPS
artifacts.
