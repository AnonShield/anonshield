# Run AnonShield on your computer

Install Docker Desktop (Windows/macOS) or Docker Engine (Linux), start it, and run:

```sh
docker run -d --name anonshield -p 127.0.0.1:8080:8080 -v anonshield:/data anonshield/anon:web
```

Open **http://localhost:8080**. The first start downloads the image (a few GB) and, in the background, the default NER model (about 1 GB); later starts reuse both. Choose **Regex** for emails, IP addresses and other structured identifiers when you do not need names or locations.

Everything runs in this one container on your CPU. Uploaded documents never leave your computer, and the interface listens only on `127.0.0.1`, so other machines on your network cannot reach it. There is no upload-size, ZIP-size or rate limit; disk space and memory are the limits.

With the command-line wrapper ([`docker/run.sh`](../docker/run.sh), or `run.ps1` on Windows), `./run.sh --web` does the same: it downloads the image, starts the container, waits until it is ready and prints the address; `--port 8081`, `--stop` and `--update` cover the rest.

## Everyday commands

```sh
docker stop anonshield       # stop
docker start anonshield      # start again
docker logs -f anonshield    # messages; Ctrl+C exits
```

To update, download the new image and recreate the container; your data stays in the volume:

```sh
docker pull anonshield/anon:web
docker rm -f anonshield
docker run -d --name anonshield -p 127.0.0.1:8080:8080 -v anonshield:/data anonshield/anon:web
```

## What is kept

The `anonshield` volume keeps the HMAC key generated on the first start, the model cache and the metrics. Uploads are deleted after processing and results after download, so download a result before stopping the container. **Do not remove the volume (`docker volume rm anonshield`) if you want the same pseudonyms later.** To get the same pseudonyms on another installation, enter the same custom key in the interface.

## Options

Add these to the `docker run` command:

| Option | Effect |
| --- | --- |
| `-p 127.0.0.1:8081:8080` instead of `-p 127.0.0.1:8080:8080` | Use port 8081 (then open http://localhost:8081). Change only the first number: the app listens on 8080 inside the container. |
| `-e ANON_MAX_SIZE_MB=100` | Limit uploads to 100 MB (`ANON_MAX_SIZE_KEY_MB` when a custom key is entered, `ANON_MAX_ZIP_SIZE_MB` for the unpacked size of a ZIP). `0`, the default, means no limit. |
| `--restart unless-stopped` | Start it again with Docker. |

To build the same container from this repository instead of downloading it, run `docker compose -f web/docker-compose.local.yml up -d --build` from the repository root (or `make -C web local`). It uses the same `anonshield` volume, so the key and models carry over.

## If something goes wrong

| What you see | What to do |
| --- | --- |
| `Cannot connect to the Docker daemon` | Start Docker Desktop or the Docker service, then run the command again. |
| `port is already allocated` | Another program uses port 8080: use another port (see Options). |
| `The container name "/anonshield" is already in use` | It already exists: `docker start anonshield`, or remove it with `docker rm -f anonshield` and run the command again. |
| The page does not open right after the command | Wait a few seconds: `docker ps` shows `healthy` when it is ready. |
| `docker ps -a` shows `Exited (1)` | Run `docker logs anonshield`: the last line says which part stopped and why. A process killed for lack of memory asks for more Docker memory, a split file, or Regex. |
| `Cannot write to /data` | Mount a named volume as in the command above, not a host folder. |
| Not enough disk space | Free space or increase Docker Desktop's disk size; leave room for the input, the temporary files and the result. |
