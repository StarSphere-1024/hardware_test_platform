#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${REMOTE_HOST:-192.168.100.91}"
REMOTE_USER="${REMOTE_USER:-seeed}"
REMOTE_PASS="${REMOTE_PASS:-seeed}"
REMOTE_DIR="${REMOTE_DIR:-/home/seeed/hardware_test}"
BOARD_PROFILE_NAME="${BOARD_PROFILE:-${REMOTE_BOARD_PROFILE:-}}"
AS_ROOT=false

usage() {
  echo "Usage: $0 [--host H] [--user U] [--password P] [--remote-dir D] [--board-profile B] [--as-root] [fixture-name|fixture-path] [sn]"
  echo "Examples:"
  echo "  $0 rk3576_full_test"
  echo "  $0 --user seeed --password seeed rk3576_full_test"
  echo "  $0 --as-root rk3576_full_test"
}

POSITIONAL=()
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
      POSITIONAL+=("$1")
      shift ;;
  esac
done

if [[ "$AS_ROOT" == true ]]; then
  REMOTE_USER="root"
fi

FIXTURE_NAME="${POSITIONAL[0]:-rk3576_full_test}"
SN="${POSITIONAL[1]:-}"

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

BOARD_PROFILE_CMD=""
if [[ -n "$BOARD_PROFILE_NAME" ]]; then
  BOARD_PROFILE_CMD="BOARD_PROFILE='$BOARD_PROFILE_NAME' "
fi
RUN_CMD="${BOARD_PROFILE_CMD}PYTHONPATH='$REMOTE_DIR' venv/bin/run_fixture '$FIXTURE_PATH'"

echo "[INFO] 执行全功能 fixture: ${FIXTURE_PATH}"
sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" \
  "cd '$REMOTE_DIR' && source venv/bin/activate && $RUN_CMD"

echo "[INFO] 生成 dashboard 快照..."
sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" <<EOF
set -e
cd '$REMOTE_DIR'
source venv/bin/activate
if [[ -n "$BOARD_PROFILE_NAME" ]]; then
export BOARD_PROFILE='$BOARD_PROFILE_NAME'
fi
export PYTHONPATH='$REMOTE_DIR'
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
