# 远程命令参考

## 环境变量

```bash
export REMOTE_HOST=192.168.100.91
export REMOTE_USER=seeed
export REMOTE_PASS=seeed
export REMOTE_DIR=/home/seeed/hardware_test
```

## 连接与状态

```bash
remote-hardware-testing/scripts/check_remote_status.sh
```

## 部署

```bash
python remote-hardware-testing/scripts/deploy_test_platform.py
```

## 单用例执行

```bash
remote-hardware-testing/scripts/run_single_case.sh cases/eth_case.json
remote-hardware-testing/scripts/run_single_case.sh wifi_case
```

## 全功能执行

```bash
remote-hardware-testing/scripts/run_full_test.sh rk3576_full_test
```

## 拉取结果

```bash
remote-hardware-testing/scripts/fetch_reports.sh
remote-hardware-testing/scripts/fetch_reports.sh remote-artifacts/manual_collect
```

## 手工远程执行（需要时）

```bash
sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST"
cd "$REMOTE_DIR"
source venv/bin/activate
./bin/run_case --config cases/eth_case.json
./bin/run_fixture --name rk3576_full_test
```
