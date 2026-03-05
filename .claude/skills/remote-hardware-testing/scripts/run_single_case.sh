#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${REMOTE_HOST:-192.168.100.91}"
REMOTE_USER="${REMOTE_USER:-seeed}"
REMOTE_PASS="${REMOTE_PASS:-seeed}"
REMOTE_DIR="${REMOTE_DIR:-/home/seeed/hardware_test}"

if ! command -v sshpass >/dev/null 2>&1; then
  echo "[ERROR] sshpass 未安装"
  exit 2
fi

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <case-name|case-path>"
  echo "Examples:"
  echo "  $0 cases/eth_case.json"
  echo "  $0 eth_case"
  exit 1
fi

CASE_INPUT="$1"
if [[ "$CASE_INPUT" == *.json ]]; then
  CASE_PATH="$CASE_INPUT"
elif [[ "$CASE_INPUT" == cases/* ]]; then
  CASE_PATH="$CASE_INPUT"
else
  CASE_PATH="cases/${CASE_INPUT}.json"
fi

echo "[INFO] 远程执行单 case: ${CASE_PATH}"
sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" \
  "cd '$REMOTE_DIR' && source venv/bin/activate && venv/bin/run_case '$CASE_PATH'"

echo "[INFO] 最近报告文件:"
sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" \
  "cd '$REMOTE_DIR' && ls -1t reports/* 2>/dev/null | head -n 10 || true"
