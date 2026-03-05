# 常见问题排查

## 1) 无法连接远程开发板

- 检查网络：`ping 192.168.100.91`
- 检查 SSH 凭据：用户名/密码是否正确
- 检查 `sshpass` 是否安装：`command -v sshpass`

## 2) 部署失败

- 本地构建失败：先在项目根目录执行 `python setup.py bdist_wheel`。
- 远程创建 venv 失败：确认远程 `python3 -m venv` 可用。
- 依赖离线安装失败：检查远程磁盘空间和 `wheels_source/` 内容。

## 3) case 执行失败

- 配置不存在：确认 `cases/*_case.json` 文件名。
- 函数未找到：确认 `functions/<module>/__init__.py` 暴露目标函数。
- 参数缺失：对照 case 的 `params` 与函数签名。

## 4) reports 或 tmp 没有更新

- 检查是否在正确目录执行：`$REMOTE_DIR`
- 检查权限：`ls -ld reports tmp logs`
- 检查运行命令退出码：失败时先修复首个错误再重跑。

## 5) dashboard 快照未生成

- 先执行一次 case 或 fixture，确保 `tmp/` 有结果文件。
- 重跑：`remote-hardware-testing/scripts/run_full_test.sh rk3576_full_test`
- 检查 `reports/dashboard_*.txt` 是否存在。
