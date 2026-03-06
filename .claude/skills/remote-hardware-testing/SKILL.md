---
name: remote-hardware-testing
description: 使用 SSH/sshpass 在远程 RK3576 开发板部署并执行硬件测试平台，支持单 case 调试、逐模块验证、全量 fixture 回归、报告回传与 dashboard 快照。用户提出远程板联调、远程部署 package_and_deploy_offline.py、批量执行 cases、修复 functions/cases 后复测、或导出 reports/tmp 快照时使用。
---

# Remote Hardware Testing

执行远程 RK3576 板卡硬件测试闭环：部署 → 单项调试 → 问题修复 → 全量回归 → 报告与快照归档。

## 快速开始

1. 导出远程连接变量（可覆盖默认值）。

```bash
export REMOTE_HOST=192.168.100.91
export REMOTE_USER=seeed
export REMOTE_PASS=seeed
export REMOTE_DIR=/home/seeed/hardware_test
```

2. 部署平台到远程板。

```bash
python remote-hardware-testing/scripts/deploy_test_platform.py
```

GPIO/权限相关测试在必要时可切换 root：

```bash
python remote-hardware-testing/scripts/deploy_test_platform.py --as-root
remote-hardware-testing/scripts/run_single_case.sh --as-root gpio_case
```

如需复用远程已有环境（跳过重建 venv、重装依赖与重装 wheel），使用：

```bash
python remote-hardware-testing/scripts/deploy_test_platform.py --fast-reuse
```

3. 逐个执行 case（建议按模块顺序）。

```bash
remote-hardware-testing/scripts/run_single_case.sh cases/eth_case.json
remote-hardware-testing/scripts/run_single_case.sh gpio_case
```

4. 拉取报告并检查失败项。

```bash
remote-hardware-testing/scripts/fetch_reports.sh
```

5. 修复 `functions/` 或 `cases/` 后重新部署并复测。

6. 执行全量测试并生成 dashboard 快照。

```bash
remote-hardware-testing/scripts/run_full_test.sh rk3576_full_test
remote-hardware-testing/scripts/fetch_reports.sh
```

## 工作流（固定顺序）

1. 执行 `deploy_test_platform.py` 完成离线打包与远程部署。
	- 快速复测可使用 `deploy_test_platform.py --fast-reuse`，仅同步工作区代码。
2. 使用 `run_single_case.sh` 按模块逐个跑 `cases/*_case.json`。
3. 使用 `check_remote_status.sh` 与 `fetch_reports.sh` 检查 `reports/`、`tmp/` 与 `logs/`。
4. 修复本地 `functions/*/test_*.py` 或 `cases/*.json`，然后重复部署和单项验证。
5. 使用 `run_full_test.sh` 跑 `fixtures/rk3576_full_test.json`。
6. 确认已生成 `reports/dashboard_*.txt` 快照并拉取到本地归档。

## 脚本索引

- `scripts/deploy_test_platform.py`：封装 `package_and_deploy_offline.py`。
- `scripts/run_single_case.sh`：远程执行单个 case。
- `scripts/run_full_test.sh`：远程执行全量 fixture，并触发 dashboard 文本快照。
- `scripts/fetch_reports.sh`：回传远程 `reports/`、`logs/`、`tmp/`。
- `scripts/check_remote_status.sh`：检查远程连通性、资源、进程和最新测试产物。

## 参考资料（按需加载）

- 需要模块清单和执行顺序时，读取 `references/test-modules.md`。
- 需要手工命令或快速排障时，读取 `references/remote-commands.md`。
- 出现部署/执行异常时，读取 `references/troubleshooting.md`。
- 需要板级引脚备注时，读取 `references/rk3576-pinout.md`。

## 执行约束

- 在项目根目录执行脚本。
- 优先使用环境变量传入敏感信息，避免硬编码到日志。
- 每次修复后至少复跑对应单 case，再执行全量 fixture。
- 交付前确保 20 个模块 case 可执行，并保留最近一轮 dashboard 快照。