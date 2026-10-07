"""Run the whole web app in one container: Redis, the worker and the API, which
also serves the interface (the local image, anonshield/anon:web).

Everything worth keeping (the HMAC key, metrics and the model cache) lives under
ANON_DATA_DIR, the one volume to mount. The container stops when any of the three
processes stops, so Docker's restart policy and `docker ps` see the failure.
"""
import fcntl
import http.client
import os
import secrets
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


def persistent_key(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, "r+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        key = stream.read().strip()
        if not key:
            key = secrets.token_hex(32)
            stream.write(key + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        return key


def healthy(port: str) -> bool:
    connection = http.client.HTTPConnection("127.0.0.1", int(port), timeout=2)
    try:
        connection.request("GET", "/api/health")
        return connection.getresponse().status == 200
    finally:
        connection.close()


def wait_until(ready, children: list[subprocess.Popen], seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if any(child.poll() is not None for child in children):
            return False
        try:
            if ready():
                return True
        except OSError:
            pass
        time.sleep(0.5)
    return False


def main() -> None:
    data = Path(os.environ.get("ANON_DATA_DIR", "/data"))
    try:
        for folder in (data / "jobs", Path(os.environ.get("TMPDIR", data / "cache" / "tmp"))):
            folder.mkdir(parents=True, exist_ok=True)
        if not os.environ.get("ANON_SECRET_KEY"):
            os.environ["ANON_SECRET_KEY"] = persistent_key(data / "secret.key")
    except PermissionError:
        sys.exit(f"Cannot write to {data}. Mount a named volume there (-v anonshield:{data}) "
                 f"or a folder writable by user id {os.getuid()}.")

    port = os.environ.get("ANON_PORT", "8080")
    # Redis keeps only the job queue, in memory; its startup warnings are about
    # persistence, which is off, so its output is not shown.
    redis = subprocess.Popen(["redis-server", "--bind", "127.0.0.1", "--port", "6379",
                              "--save", "", "--appendonly", "no"], stdout=subprocess.DEVNULL)
    children = [redis]
    names = {redis.pid: "Redis"}

    def stop(*_):
        for child in children:
            if child.poll() is None:
                child.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    if wait_until(lambda: socket.create_connection(("127.0.0.1", 6379), timeout=1).close() is None, children, 30):
        worker = subprocess.Popen(["celery", "-A", "workers.celery_app", "--quiet", "worker", "-Q", "fast",
                                   "--pool=solo", "--loglevel=warning"])
        # All interfaces of the container, so that `docker run -p` reaches it;
        # the documented command publishes it on the host's 127.0.0.1 only.
        host = "0.0.0.0"  # nosec B104
        server = subprocess.Popen(["uvicorn", "main:app", "--host", host, "--port", port,
                                   "--log-level", "warning"])
        children += [worker, server]
        names.update({worker.pid: "the worker", server.pid: "the web server"})
        if wait_until(lambda: healthy(port), children, 120):
            print(f"AnonShield is ready. Open http://localhost:{port} "
                  "(or the host port you published with -p).", flush=True)

    while all(child.poll() is None for child in children):
        time.sleep(1)
    stopping = [child for child in children if child.poll() is not None]
    if any(child.returncode not in (0, -signal.SIGTERM) for child in stopping):
        code = stopping[0].returncode
        hint = ("it was killed, usually for lack of memory: give Docker more memory or split the file"
                if code == -signal.SIGKILL else "see the messages above")
        print(f"AnonShield stopped because {names[stopping[0].pid]} exited with code {code}; {hint}.",
              file=sys.stderr, flush=True)
    stop()
    for child in children:
        try:
            child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            child.kill()
    failed = [child for child in children if child.returncode not in (0, -signal.SIGTERM)]
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
