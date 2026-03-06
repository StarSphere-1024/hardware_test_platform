#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${REMOTE_HOST:-192.168.100.91}"
REMOTE_USER="${REMOTE_USER:-seeed}"
REMOTE_PASS="${REMOTE_PASS:-seeed}"
REMOTE_DIR="${REMOTE_DIR:-/home/seeed/hardware_test}"
AS_ROOT=false

usage() {
  echo "Usage: $0 [--host H] [--user U] [--password P] [--remote-dir D] [--as-root]"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      REMOTE_HOST="$2"; shift 2 ;;
    --user)
      REMOTE_USER="$2"; shift 2 ;;
    --password|--pass)
      REMOTE_PASS="$2"; shift 2 ;;
    --remote-dir)
      REMOTE_DIR="$2"; shift 2 ;;
    --as-root)
      AS_ROOT=true; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "[ERROR] Unexpected argument: $1"
      usage
      exit 1 ;;
  esac
done

if [[ "$AS_ROOT" == true ]]; then
  REMOTE_USER="root"
fi

if ! command -v sshpass >/dev/null 2>&1; then
  echo "[ERROR] sshpass 未安装"
  exit 2
fi

echo "[INFO] 检查远程板状态: ${REMOTE_USER}@${REMOTE_HOST}"
sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" <<EOF
set -e
echo "===== BASIC ====="
hostname
date
uptime

echo ""
echo "===== RESOURCE ====="
free -h || true
df -h | head -n 10 || true

echo ""
echo "===== PROJECT ====="
if [[ -d '$REMOTE_DIR' ]]; then
  cd '$REMOTE_DIR'
  echo "remote_dir exists: $REMOTE_DIR"
  [[ -d venv ]] && echo "venv: ok" || echo "venv: missing"
  [[ -d cases ]] && echo "cases: ok" || echo "cases: missing"
  [[ -d functions ]] && echo "functions: ok" || echo "functions: missing"
  [[ -x venv/bin/run_case ]] && echo "run_case entrypoint: ok" || echo "run_case entrypoint: missing"
  [[ -x venv/bin/run_fixture ]] && echo "run_fixture entrypoint: ok" || echo "run_fixture entrypoint: missing"
  [[ -x venv/bin/run_case ]] && echo "run_case entrypoint: ok" || echo "run_case entrypoint: missing"
  [[ -x venv/bin/run_fixture ]] && echo "run_fixture entrypoint: ok" || echo "run_fixture entrypoint: missing"

  echo ""
  echo "===== RECENT REPORTS ====="
  ls -1t reports/* 2>/dev/null | head -n 10 || echo "no reports"

  echo ""
  echo "===== RECENT TMP ====="
  ls -1t tmp/* 2>/dev/null | head -n 10 || echo "no tmp files"
else
  echo "remote_dir missing: $REMOTE_DIR"
  exit 3
fi
EOF
