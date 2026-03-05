#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${REMOTE_HOST:-192.168.100.91}"
REMOTE_USER="${REMOTE_USER:-seeed}"
REMOTE_PASS="${REMOTE_PASS:-seeed}"
REMOTE_DIR="${REMOTE_DIR:-/home/seeed/hardware_test}"

FIXTURE_NAME="${1:-rk3576_full_test}"
SN="${2:-}"

if [[ "$FIXTURE_NAME" == *.json ]]; then
  FIXTURE_PATH="$FIXTURE_NAME"
elif [[ "$FIXTURE_NAME" == fixtures/* ]]; then
  FIXTURE_PATH="$FIXTURE_NAME"
else
  FIXTURE_PATH="fixtures/${FIXTURE_NAME}.json"
fi

if ! command -v sshpass >/dev/null 2>&1; then
  echo "[ERROR] sshpass 未安装"
  exit 2
fi

RUN_CMD="venv/bin/run_fixture '$FIXTURE_PATH'"

echo "[INFO] 执行全功能 fixture: ${FIXTURE_PATH}"
sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" \
  "cd '$REMOTE_DIR' && source venv/bin/activate && $RUN_CMD"

echo "[INFO] 生成 dashboard 快照..."
sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" <<EOF
set -e
cd '$REMOTE_DIR'
source venv/bin/activate
python - <<'PY'
from framework.dashboard.cli_dashboard import CLIDashboard

dashboard = CLIDashboard(tmp_dir="tmp", refresh_interval=1.0)
layout = dashboard._generate_layout()
dashboard._save_snapshot(layout)
print("dashboard snapshot generated in reports/")
PY
EOF

echo "[INFO] 最近报告文件:"
sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" \
  "cd '$REMOTE_DIR' && ls -1t reports/* 2>/dev/null | head -n 20 || true"
