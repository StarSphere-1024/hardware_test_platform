#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${REMOTE_HOST:-192.168.100.91}"
REMOTE_USER="${REMOTE_USER:-seeed}"
REMOTE_PASS="${REMOTE_PASS:-seeed}"
REMOTE_DIR="${REMOTE_DIR:-/home/seeed/hardware_test}"
BOARD_PROFILE_NAME="${BOARD_PROFILE:-${REMOTE_BOARD_PROFILE:-}}"
AS_ROOT=false

if ! command -v sshpass >/dev/null 2>&1; then
  echo "[ERROR] sshpass 未安装"
  exit 2
fi

usage() {
  echo "Usage: $0 [--host H] [--user U] [--password P] [--remote-dir D] [--board-profile B] [--as-root] <case-name|case-path>"
  echo "Examples:"
  echo "  $0 gpio_case"
  echo "  $0 --user seeed --password seeed eth_case"
  echo "  $0 --as-root gpio_case"
}

CASE_INPUT=""
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
    --board-profile)
      BOARD_PROFILE_NAME="$2"; shift 2 ;;
    --as-root)
      AS_ROOT=true; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      if [[ -z "$CASE_INPUT" ]]; then
        CASE_INPUT="$1"
        shift
      else
        echo "[ERROR] Unexpected argument: $1"
        usage
        exit 1
      fi
      ;;
  esac
done

if [[ -z "$CASE_INPUT" ]]; then
  usage
  exit 1
fi

if [[ "$AS_ROOT" == true ]]; then
  REMOTE_USER="root"
fi

if [[ "$CASE_INPUT" == *.json ]]; then
  CASE_PATH="$CASE_INPUT"
elif [[ "$CASE_INPUT" == cases/* ]]; then
  CASE_PATH="$CASE_INPUT"
else
  CASE_PATH="cases/${CASE_INPUT}.json"
fi

echo "[INFO] 远程执行单 case: ${CASE_PATH}"
BOARD_PROFILE_CMD=""
if [[ -n "$BOARD_PROFILE_NAME" ]]; then
  BOARD_PROFILE_CMD="BOARD_PROFILE='$BOARD_PROFILE_NAME' "
fi
sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" \
  "cd '$REMOTE_DIR' && source venv/bin/activate && ${BOARD_PROFILE_CMD}PYTHONPATH='$REMOTE_DIR' venv/bin/run_case '$CASE_PATH'"

echo "[INFO] 最近报告文件:"
sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" \
  "cd '$REMOTE_DIR' && ls -1t reports/* 2>/dev/null | head -n 10 || true"
