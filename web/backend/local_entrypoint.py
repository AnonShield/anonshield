"""Bootstrap the local stack's persistent key and disk-backed temporary files."""
import fcntl
import os
import secrets
import sys
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


def main() -> None:
    jobs = Path(os.environ["ANON_JOBS_DIR"])
    if not os.environ.get("ANON_SECRET_KEY"):
        os.environ["ANON_SECRET_KEY"] = persistent_key(jobs / ".secret-key")
    Path(os.environ["TMPDIR"]).mkdir(parents=True, exist_ok=True)
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
