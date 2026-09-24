#!/usr/bin/env bash
# Rebuild the compose images WITHOUT filling Docker's disk (G-51).
#
# 2026-09-24: `docker compose build app worker beat` on a 64 GB Docker Desktop disk image left
# ~5 GB of superseded layers x 3 in place, filled the VM filesystem, and every write in the VM
# then failed with I/O errors -- the API went dark and `docker images` reported zero images. The
# extractor already refuses to run below a free-space floor; the rebuild now does the same.
#
#   MIN_FREE_GB=15 bash bench/rebuild_images.sh [service ...]     (default: app worker beat)
set -euo pipefail
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="$R/backend/deployment/docker-compose.yml"
MIN_FREE_GB="${MIN_FREE_GB:-15}"
SERVICES="${*:-app worker beat}"

vm_free_gb() { docker run --rm alpine:latest sh -c 'df -k / | tail -1' 2>/dev/null | awk '{printf "%d", $4/1024/1024}'; }

echo "=== before ==="; docker system df
echo "pruning dangling images and build cache ..."
docker image prune -f >/dev/null; docker builder prune -f >/dev/null
FREE=$(vm_free_gb); echo "VM filesystem free: ${FREE} GB (need ${MIN_FREE_GB})"
if [ "${FREE:-0}" -lt "$MIN_FREE_GB" ]; then
  echo "REFUSING to build: ${FREE} GB free inside the Docker VM is below ${MIN_FREE_GB} GB." >&2
  echo "Free space (docker image prune -a, or raise the disk image size in Docker Desktop settings) and retry." >&2
  exit 2
fi
docker compose -f "$COMPOSE" build $SERVICES
docker compose -f "$COMPOSE" up -d --force-recreate $SERVICES
sleep 20
echo "=== image check ==="
for s in $SERVICES; do
  printf "%-8s " "$s"; docker compose -f "$COMPOSE" exec -T "$s" python -m app.core.image_check 2>/dev/null | head -1 || echo "(exec failed)"
done
echo "pruning the superseded layers ..."; docker image prune -f >/dev/null
echo "=== after ==="; docker system df; echo "VM filesystem free: $(vm_free_gb) GB"
