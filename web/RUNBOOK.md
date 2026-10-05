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
runs every check on the pull request first (Python tests including the end-to-end
CLI runs, the web backend tests, the frontend build, the CLI and web images, the
scans). On `main`, once they pass, it pushes the web images to GHCR
(`ghcr.io/anonshield/anonshield-web-backend` and `-frontend`, tagged with the
commit and `latest`) and runs the deploy on the self-hosted runner of the host
that serves anonshield.org (label `anonshield-prod`). The deploy:

1. copies `web/docker-compose.a10.yml`, `web/Caddyfile.a10` and `warm_cache.sh`
   into `~/anonshield_deploy/web` (the host's `.env` is never touched);
2. pulls the images for the commit and restarts the stack
   (`docker compose -f docker-compose.a10.yml up -d`);
3. runs a real anonymization job through the API (`warm_cache.sh`);
4. fails unless `https://anonshield.org/api/health` reports the deployed commit
   (`"version"`), so a stack that was not updated cannot pass as healthy;
5. removes this app's previous images (never a global prune: the host is shared).

Nothing is built on the host. To run the stack by hand there:

```bash
cd ~/anonshield_deploy/web
docker compose -f docker-compose.a10.yml ps          # status
docker compose -f docker-compose.a10.yml logs -f backend
IMAGE_TAG=<commit> docker compose -f docker-compose.a10.yml up -d   # roll back/forward
```

The runner lives in `~/actions-runner` on the host and is started at boot by the
user crontab (`@reboot ~/actions-runner/keepalive.sh`), which restarts it if it
exits; its log is `~/actions-runner/keepalive.log`. To remove it:
`cd ~/actions-runner && ./config.sh remove --token "$(gh api -X POST repos/AnonShield/anonshield/actions/runners/remove-token --jq .token)"`
and drop the crontab line.

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
