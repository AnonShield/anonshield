# AnonShield Runbook

Everything you need to deploy, maintain, and modify the web app. The goal is one
obvious command per task.

The app runs on your host under `~/anonshield_deploy/web` as four Docker
containers (backend, frontend, worker-fast, redis) behind the host's Caddy, which
serves `https://anonshield.org`. All operations go through `make` from that
`web/` directory.

## Deploy

From your dev machine, after editing code:

```bash
./scripts/deploy.sh <host>   # sync, build, start, warm the cache, on the host
```

That is the whole deploy. It never overwrites the host's `web/.env` or `web/certs`.

To deploy by hand on the host instead:

```bash
ssh <host>
cd ~/anonshield_deploy/web
make deploy                      # build, start, warm the cache, show status
```

## Maintenance (on the host: `cd ~/anonshield_deploy/web`)

```bash
make            # or: make help   list every command
make status     # what is running and is it healthy
make health     # quick backend health check
make logs       # follow logs (make logs SVC=backend to filter)
make stats      # live CPU and memory per container
make restart    # restart the stack
make warm       # preload the NER model so the first request is fast
make shell      # shell inside the backend container
make down       # stop everything
make clean      # reclaim disk (prune build cache and dangling images)
```

The containers use `restart: unless-stopped`, so they come back after a reboot.

## Modify and redeploy

1. Change code in this repo and commit it.
2. Run `./scripts/deploy.sh <host>`. It rebuilds only what changed (Docker layer
   cache) and warms the model cache.
3. Verify: `curl -fsS https://anonshield.org/api/health` and open the site.

## Continuous deployment (CI/CD)

Pushing to `main` deploys automatically. The pipeline (`.github/workflows/ci-cd.yml`)
runs, on GitHub-hosted runners: the Python tests, the frontend build, a dependency
and container vulnerability scan (pip-audit, npm audit, Trivy), and a secret scan
plus SAST (gitleaks, bandit). Then, only if the tests, the build, and the secret
scan pass, it runs the deploy on a self-hosted runner on this host: it syncs the
code into `~/anonshield_deploy` and runs `make deploy`. Pull requests run all the
checks but never the deploy. Dependabot (`.github/dependabot.yml`) opens weekly
update PRs and raises alerts for the Python, npm, Docker, and Actions ecosystems.

The self-hosted runner runs as a user systemd service on the host (no inbound SSH,
no host name in the repo; it connects out to GitHub and is picked by the generic
label `anonshield-prod`):

```bash
systemctl --user status gh-runner      # is the runner up
systemctl --user restart gh-runner     # restart it
journalctl --user -u gh-runner -f      # follow its logs
```

To remove it: `systemctl --user disable --now gh-runner`, then
`cd ~/actions-runner && ./config.sh remove --token "$(gh api -X POST repos/AnonShield/anonshield/actions/runners/remove-token --jq .token)"`.

The manual `./scripts/deploy.sh <host>` path still works and is unchanged; CI/CD
just automates the same steps.

## Configuration

- `web/.env` (on the host, not in git): `ANON_SECRET_KEY` (required, keep it
  stable so pseudonyms stay consistent across runs), `ANON_MAX_SIZE_MB`,
  `PUBLIC_API_URL`.
- `web/docker-compose.host.yml` (in git): the host override. It publishes the
  backend to `127.0.0.1:18000` and the frontend to `127.0.0.1:13000` for the host
  Caddy, skips the containerized Caddy, and caps memory (backend 3G, worker 6G,
  frontend 1G, redis 512M). Edit the limits here if the host has more or less room.
- The public route lives in the host Caddyfile (`/etc/caddy/Caddyfile`), in the
  `anonshield.org` block: `/api/*` to `127.0.0.1:18000`, everything else to
  `127.0.0.1:13000`. After editing it: `sudo caddy validate --config
  /etc/caddy/Caddyfile && sudo systemctl reload caddy`.

## Troubleshooting

- Backend shows `unhealthy` but the site works: the healthcheck uses Python (the
  lean image has no curl); if it is wrong the app can still be fine. Check
  `make health`.
- First request is slow: run `make warm` (downloads the NER model once).
- A favicon or asset looks stale in the browser: that is Cloudflare's edge cache.
  The origin is correct (`make` rebuilds it); the cache expires on its own, or
  purge it in the Cloudflare dashboard.
- Disk getting full on `/`: `make clean`.
