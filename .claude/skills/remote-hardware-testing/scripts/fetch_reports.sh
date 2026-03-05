#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${REMOTE_HOST:-192.168.100.91}"
REMOTE_USER="${REMOTE_USER:-seeed}"
REMOTE_PASS="${REMOTE_PASS:-seeed}"
REMOTE_DIR="${REMOTE_DIR:-/home/seeed/hardware_test}"

OUTPUT_DIR="${1:-remote-artifacts/$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$OUTPUT_DIR"

if ! command -v sshpass >/dev/null 2>&1; then
  echo "[ERROR] sshpass 未安装"
  exit 2
fi

echo "[INFO] 拉取 reports/ logs/ tmp/ 到本地: ${OUTPUT_DIR}"

for sub in reports logs tmp; do
  mkdir -p "$OUTPUT_DIR/$sub"
  sshpass -p "$REMOTE_PASS" scp -o StrictHostKeyChecking=no -r \
    "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/$sub/" "$OUTPUT_DIR/" >/dev/null 2>&1 || true
done

echo "[INFO] 已完成。文件统计:"
find "$OUTPUT_DIR" -type f | wc -l | awk '{print "  total files:", $1}'
find "$OUTPUT_DIR/reports" -type f 2>/dev/null | head -n 10 || true
