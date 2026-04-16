#!/usr/bin/env bash
# Auto-mount persistent NTFS disks (Windows SSD + HDD) on boot.
# Idempotent: safe to re-run. Run with: sudo bash auto-mount-disks.sh
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "Run with sudo"; exit 1; }

UUID_SSD="8402F7AD02F7A27A"   # /dev/nvme0n1p3 — Windows C:
UUID_HDD="BA1883111882CBB7"   # /dev/sdb1 — HDD anonshield_data
MOUNT_SSD="/mnt/win_ssd"
MOUNT_HDD="/media/kapelinski/BA1883111882CBB7"

COMMON_OPTS="nofail,x-systemd.automount,x-systemd.device-timeout=10s,uid=1000,gid=1000,remove_hiberfile,windows_names,big_writes"

log() { echo -e "\e[32m==> $*\e[0m"; }
warn() { echo -e "\e[33m!! $*\e[0m"; }

log "Backing up /etc/fstab"
cp /etc/fstab "/etc/fstab.bak.$(date +%Y%m%d-%H%M%S)"

ensure_fstab_entry() {
    local uuid="$1" mnt="$2" tag="$3"
    if grep -q "UUID=${uuid}" /etc/fstab; then
        warn "fstab already has entry for ${tag} (UUID=${uuid}) — skipping"
        return 0
    fi
    mkdir -p "${mnt}"
    echo "# ${tag} (auto-added $(date +%F))" >> /etc/fstab
    echo "UUID=${uuid} ${mnt} ntfs-3g ${COMMON_OPTS} 0 0" >> /etc/fstab
    log "Added fstab entry: ${tag} → ${mnt}"
}

ensure_fstab_entry "${UUID_SSD}" "${MOUNT_SSD}" "Windows SSD"
ensure_fstab_entry "${UUID_HDD}" "${MOUNT_HDD}" "HDD (anonshield_data)"

log "Reloading systemd"
systemctl daemon-reload

log "Fixing NTFS dirty flag if needed (Windows fast-startup residue)"
for dev in /dev/nvme0n1p3 /dev/sdb1; do
    if [[ -b "$dev" ]] && ! mount | grep -q "$dev"; then
        ntfsfix -d "$dev" 2>&1 | tail -3 || true
    fi
done

log "Mounting all fstab entries (mount -a)"
mount -a || warn "mount -a reported errors — run 'systemctl status \"mnt-win_ssd.automount\"' to debug"

log "Current mounts:"
findmnt "${MOUNT_SSD}" "${MOUNT_HDD}" 2>/dev/null || true

log "Done. Both disks will auto-mount on every boot."
log "To revert one entry, remove its line from /etc/fstab and run 'systemctl daemon-reload'."
