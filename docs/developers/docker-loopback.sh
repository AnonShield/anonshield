#!/usr/bin/env bash
# Setup Docker data-root on an ext4 loopfile hosted on /mnt/win_ssd (NTFS).
# Idempotent. Run with: sudo bash docker-loopback.sh
# Prereq: auto-mount-disks.sh has been run (/mnt/win_ssd available).
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "Run with sudo"; exit 1; }

LOOPFILE="/mnt/win_ssd/docker-ext4.img"
SIZE_GB="${SIZE_GB:-100}"
DATA_ROOT="/var/lib/docker"

log() { echo -e "\e[32m==> $*\e[0m"; }
warn() { echo -e "\e[33m!! $*\e[0m"; }
die() { echo -e "\e[31mxx $*\e[0m"; exit 1; }

mountpoint -q /mnt/win_ssd || die "/mnt/win_ssd not mounted — run auto-mount-disks.sh first"

log "Stopping Docker"
systemctl stop docker.socket docker.service 2>/dev/null || true
systemctl stop containerd 2>/dev/null || true

if [[ ! -f "$LOOPFILE" ]]; then
    log "Creating ${SIZE_GB}G sparse loopfile at ${LOOPFILE}"
    truncate -s "${SIZE_GB}G" "$LOOPFILE" || {
        warn "truncate failed — falling back to fallocate"
        fallocate -l "${SIZE_GB}G" "$LOOPFILE" 2>/dev/null || \
            dd if=/dev/zero of="$LOOPFILE" bs=1G count="$SIZE_GB" status=progress
    }
    log "Formatting as ext4"
    mkfs.ext4 -F -L docker-data "$LOOPFILE"
else
    warn "Loopfile already exists at ${LOOPFILE} — reusing"
fi

log "Mounting loopfile at ${DATA_ROOT}"
mkdir -p "$DATA_ROOT"
if ! mountpoint -q "$DATA_ROOT"; then
    mount -o loop "$LOOPFILE" "$DATA_ROOT"
fi

if ! grep -q "docker-ext4.img" /etc/fstab; then
    log "Adding loopfile to /etc/fstab"
    cp /etc/fstab "/etc/fstab.bak.docker.$(date +%Y%m%d-%H%M%S)"
    echo "${LOOPFILE} ${DATA_ROOT} ext4 loop,defaults,nofail,x-systemd.requires-mounts-for=/mnt/win_ssd 0 0" >> /etc/fstab
    systemctl daemon-reload
fi

log "Writing /etc/docker/daemon.json"
mkdir -p /etc/docker
[[ -f /etc/docker/daemon.json ]] && cp /etc/docker/daemon.json "/etc/docker/daemon.json.bak.$(date +%Y%m%d-%H%M%S)"

cat > /etc/docker/daemon.json <<'JSON'
{
  "data-root": "/var/lib/docker",
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  },
  "default-runtime": "nvidia",
  "runtimes": {
    "nvidia": {
      "path": "nvidia-container-runtime",
      "runtimeArgs": []
    }
  }
}
JSON

if ! command -v nvidia-container-runtime >/dev/null 2>&1; then
    warn "nvidia-container-runtime not found — removing GPU runtime from daemon.json"
    cat > /etc/docker/daemon.json <<'JSON'
{
  "data-root": "/var/lib/docker",
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {"max-size": "100m", "max-file": "3"}
}
JSON
    warn "Install nvidia-container-toolkit later to enable GPU in Docker:"
    warn "  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg"
    warn "  curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list"
    warn "  sudo apt update && sudo apt install -y nvidia-container-toolkit"
    warn "  sudo nvidia-ctk runtime configure --runtime=docker"
fi

log "Starting Docker"
systemctl start docker.socket docker.service

log "Verifying"
docker info 2>/dev/null | grep -E "Docker Root Dir|Storage Driver|Runtimes" || die "docker info failed"
df -h "$DATA_ROOT" | tail -1

log "Done. Docker data-root is now on ${LOOPFILE} (${SIZE_GB} GB)."
log "Test: docker run --rm hello-world"
[[ -x "$(command -v nvidia-container-runtime)" ]] && log "GPU test: docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi"
