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

1. copies `web/docker-compose.a10.yml`, `web/Caddyfile.a10`, `warm_cache.sh` and
   `deploy-a10.sh` into `~/anonshield_deploy/web` (the host's `.env` is never touched);
2. runs `deploy-a10.sh <commit>`, a blue-green deploy that never takes the site down.
   There are two copies of the app, `azul` (18080) and `verde` (18081), sharing one
   Redis and the jobs volume. The commit starts in the copy that is stopped while the
   other keeps serving, gets a real anonymization job (`warm_cache.sh`), and only once it
   reports the commit on `/api/health` is the old copy drained (its health check answers
   503 to the host Caddy) and stopped, its worker finishing the job it was running. If the
   new copy never reports the commit, it is stopped and the old one goes on serving;
3. fails unless `https://anonshield.org/api/health` reports the deployed commit
   (`"version"`), so a stack that was not updated cannot pass as healthy;
4. removes this app's previous images (never a global prune: the host is shared).

Nothing is built on the host. To run the stack by hand there:

```bash
cd ~/anonshield_deploy/web
alias anon='docker compose -p web -f docker-compose.a10.yml --env-file .env --env-file cores.env'
anon ps                                  # status (cores.env holds each copy's image tag)
anon --profile verde logs -f backend-verde
bash deploy-a10.sh <commit>              # roll back/forward, same blue-green swap
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
  `anonshield.org` block: `reverse_proxy 127.0.0.1:18081 127.0.0.1:18080` with
  `lb_policy first` and an active health check on `/api/health` sent with
  `X-Health-Check: proxy` (verde first, so a deploy can replace azul while verde
  serves). After editing it: `caddy validate --config /etc/caddy/Caddyfile
  --adapter caddyfile && caddy reload --config /etc/caddy/Caddyfile`.

## Troubleshooting

- Backend shows `unhealthy` but the site works: the healthcheck uses Python (the
  lean image has no curl); if it is wrong the app can still be fine. Check
  `make health`.
- First request is slow: run `make warm` (downloads the NER model once).
- A favicon or asset looks stale in the browser: that is Cloudflare's edge cache.
  The origin is correct (`make` rebuilds it); the cache expires on its own, or
  purge it in the Cloudflare dashboard.
- Disk getting full on `/`: `make clean`.
