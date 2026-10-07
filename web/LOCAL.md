# Run AnonShield on your computer

Install Docker Desktop (Windows/macOS) or Docker Engine with Compose (Linux), and start Docker. Clone this repository, open a terminal in its root, and run:

```sh
docker compose -f web/docker-compose.local.yml up -d --build
```

Open **http://localhost:8080/app**. The first build downloads the application and language packages; allow several minutes and several GB of disk space. The default NER model downloads the first time it is used. Choose **Regex** for emails, IP addresses and other structured identifiers when you do not need names or locations.

Local processing uses your CPU and never sends uploaded documents to the hosted AnonShield service. Package and model downloads require Internet access; cached models are reused. The interface listens only on `127.0.0.1`; it is not exposed to your network.

## Everyday commands

Run these from the repository root:

```sh
docker compose -f web/docker-compose.local.yml ps                 # status
docker compose -f web/docker-compose.local.yml logs -f --tail=80  # logs; Ctrl+C exits
docker compose -f web/docker-compose.local.yml down               # stop
docker compose -f web/docker-compose.local.yml up -d --build      # start or update
```

Wait for active jobs to finish and download their results before stopping. Queue/status data is temporary. Input files are removed after processing; output is removed after download. The generated HMAC key, metrics and downloaded models survive normal stops and rebuilds in Docker volumes. **Do not use `down -v` if you want to keep the key and cache.** Losing the key changes the pseudonyms generated without a custom key. For reproducible identifiers across installations, enter the same custom key in the interface.

## Storage and optional limits

Local mode imposes no file-size, extracted-ZIP-size or requests-per-minute quota, and enables processing XML files above the CLI's default 200 MB threshold. Disk space and memory are still finite; large NER documents and XML files may require substantial RAM. Uploads and processing temporary files use disk-backed volumes. Docker Desktop's disk image size and memory allocation can be increased in its settings. Docker Engine stores these volumes under its configured data directory.

To select a port or optionally restore upload limits, create `web/.env`:

```dotenv
ANON_LOCAL_PORT=8081
ANON_MAX_SIZE_MB=0
ANON_MAX_SIZE_KEY_MB=0
ANON_MAX_ZIP_SIZE_MB=0
```

Run the startup command again, then open http://localhost:8081/app. Sizes are in MB; `0` means unlimited. `ANON_MAX_SIZE_KEY_MB` applies when a custom key is entered. A value such as `100` limits an upload to 100 MB. These local settings do not change the hosted service's limits.

## If something goes wrong

| What you see | What to do |
| --- | --- |
| Cannot connect to the Docker daemon | Start Docker Desktop or the Docker service, then rerun the command. |
| Port is already allocated | Set `ANON_LOCAL_PORT=8081` in `web/.env`, rerun startup, and use port 8081. |
| Browser cannot connect during the first build | Wait for the startup command to finish; check `ps` and `logs` above. |
| A first NER job takes a long time | The model may be downloading. Read `logs -f worker-fast`; later jobs reuse it. |
| Not enough disk space | Increase Docker's disk allocation or free space on the drive storing Docker's data. Keep space for the input, temporary files and output. |
| A worker exits with code 137 | Increase Docker's memory allocation, split the file, or choose Regex if it fits your entity types. |

For optional Make shortcuts, run `make -C web local`, `local-status`, `local-logs`, or `local-down`.
