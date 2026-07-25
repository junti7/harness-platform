#!/usr/bin/env bash
# Deploy the committed smartfarm Pi hub without touching config.yaml or its DB.
set -euo pipefail

PI_HOST="${SMARTFARM_PI_SSH_HOST:-pi@192.168.0.23}"
PI_ROOT="${SMARTFARM_PI_ROOT:-/home/pi/harness-smartfarm-pi-hub}"
SOURCE_HUB="hardware/smartfarm/pi_hub/hub.py"
SOURCE_STOP="hardware/smartfarm/pi_hub/emergency_stop.py"

for path in "$SOURCE_HUB" "$SOURCE_STOP"; do
  git cat-file -e "origin/main:$path"
  if [ -n "$(git diff origin/main -- "$path")" ] || [ -n "$(git status --porcelain -- "$path")" ]; then
    echo "✖ $path differs from origin/main; commit and push first"
    exit 1
  fi
done

remote_stage="$PI_ROOT/.deploy-smartfarm-$$"
cleanup() {
  ssh -o BatchMode=yes -o ConnectTimeout=10 "$PI_HOST" "rm -rf '$remote_stage'" >/dev/null 2>&1 || true
}
trap cleanup EXIT

ssh -o BatchMode=yes -o ConnectTimeout=10 "$PI_HOST" "mkdir -p '$remote_stage'"
scp -q "$SOURCE_HUB" "$PI_HOST:$remote_stage/hub.py"
scp -q "$SOURCE_STOP" "$PI_HOST:$remote_stage/emergency_stop.py"

ssh -o BatchMode=yes -o ConnectTimeout=10 "$PI_HOST" "PI_ROOT='$PI_ROOT' STAGE='$remote_stage' bash -s" <<'REMOTE'
set -euo pipefail
cd "$PI_ROOT"

echo "▶ Pi hub preflight"
test -f config.yaml
test -f smartfarm.db
.venv/bin/python -m py_compile "$STAGE/hub.py" "$STAGE/emergency_stop.py"

backup="backups/pre-dashboard-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$backup"
cp hub.py "$backup/hub.py"
[ -f emergency_stop.py ] && cp emergency_stop.py "$backup/emergency_stop.py"
echo "  backup=$PI_ROOT/$backup"

install -m 0644 "$STAGE/hub.py" hub.py
install -m 0755 "$STAGE/emergency_stop.py" emergency_stop.py
sudo systemctl restart harness-smartfarm-hub

for _ in $(seq 1 15); do
  [ "$(systemctl is-active harness-smartfarm-hub)" = "active" ] && break
  sleep 1
done
test "$(systemctl is-active harness-smartfarm-hub)" = "active"
sleep 2
journalctl -u harness-smartfarm-hub -n 20 --no-pager | tail -20
echo "  ✓ Pi hub active"
REMOTE

trap - EXIT
cleanup
echo "▶ Smartfarm Pi hub deployment complete"
