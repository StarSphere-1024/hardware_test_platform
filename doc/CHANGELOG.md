# Changelog

## 2026-02-28

### 33d3c31c317e74a83af8f502e8452369b5996974 → 47dd4b9b03e5c34111a0a1feeae8a196ca839093

#### 提交列表
- `0957453` Rename fixture files to English names and update fixture_name fields
- `47dd4b9` refactor dashboard to rich-only and add system monitoring integration

#### 变更摘要
1. **Fixture 命名统一为英文**
   - `fixtures/网络功能测试.json` → `fixtures/network_test.json`
   - `fixtures/生产全功能测试.json` → `fixtures/production_full_test.json`
   - `fixtures/功能快速验证.json` → `fixtures/quick_functional_test.json`
   - 同步更新 `fixture_name` 字段为英文，方便 CLI 与自动化脚本调用。

2. **Dashboard 重构为 rich 单实现**
   - 入口改为直接实例化 `CLIDashboard`，移除旧调用路径。
   - 主布局按需求文档重构为分区式：标题、基础信息、系统监控、模块/统计、最近失败、控制栏。
   - 快捷键支持：`Q/R/D/L/S`，并补充 `S` 截图保存到 `reports/`。
   - 终端输入处理修复：避免非阻塞写导致的 `BlockingIOError`，提升退出稳定性。

3. **新增系统监控模块并接入 Fixture 执行链**
   - 新增 `framework/monitoring/__init__.py`
   - 新增 `framework/monitoring/system_monitor.py`
   - `FixtureRunner` 在执行前自动启动监控、结束后自动停止。
   - 监控数据写入 `tmp/system_monitor.json`，供 Dashboard 实时读取。

#### 验证记录
- 语法检查通过：
  - `python3 -m py_compile framework/core/fixture_runner.py framework/dashboard/__main__.py framework/dashboard/cli_dashboard.py framework/monitoring/__init__.py framework/monitoring/system_monitor.py`
- Dashboard 启动验证通过：
  - `python3 -m framework.dashboard --fixture network_test`
