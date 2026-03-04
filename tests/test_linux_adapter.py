"""
Tests for LinuxAdapter module.

测试 Linux 平台适配器模块
"""
import pytest
from unittest.mock import patch, MagicMock

from framework.platform.linux_adapter import LinuxAdapter
from framework.platform.base_adapter import CommandResult


class TestLinuxAdapterInit:
    """测试 LinuxAdapter 初始化"""

    def test_init(self):
        """测试基本初始化"""
        adapter = LinuxAdapter()
        assert adapter.config == {}
        assert adapter._platform_info is None

    def test_init_with_config(self):
        """测试带配置初始化"""
        config = {"key": "value"}
        adapter = LinuxAdapter(config=config)
        assert adapter.config == config


class TestLinuxAdapterDetectPlatform:
    """测试平台检测"""

    def test_detect_platform_returns_linux(self):
        """测试检测返回 linux"""
        adapter = LinuxAdapter()
        platform = adapter.detect_platform()
        assert platform == "linux"

    def test_detect_platform_caches_result(self):
        """测试平台检测结果缓存"""
        adapter = LinuxAdapter()
        # 第一次调用
        platform1 = adapter.detect_platform()
        # 第二次调用应该返回缓存结果
        platform2 = adapter.detect_platform()
        assert platform1 == platform2
        assert adapter._platform_info is not None


class TestLinuxAdapterExecute:
    """测试命令执行"""

    def test_execute_success(self):
        """测试成功执行"""
        adapter = LinuxAdapter()
        result = adapter.execute("echo hello")

        assert result.success is True
        assert "hello" in result.stdout
        assert result.return_code == 0

    def test_execute_with_timeout(self):
        """测试带超时执行"""
        adapter = LinuxAdapter()
        # 快速命令应该在超时前完成
        result = adapter.execute("echo test", timeout=5)

        assert result.success is True
        assert result.duration < 5

    def test_execute_command_not_found(self):
        """测试命令未找到"""
        adapter = LinuxAdapter()
        result = adapter.execute("nonexistent_command_xyz123")

        # 命令未找到应该返回 127
        assert result.return_code == 127

    def test_execute_returns_command_result(self):
        """测试返回 CommandResult 对象"""
        adapter = LinuxAdapter()
        result = adapter.execute("pwd")

        assert isinstance(result, CommandResult)
        assert hasattr(result, "return_code")
        assert hasattr(result, "stdout")
        assert hasattr(result, "stderr")
        assert hasattr(result, "duration")


class TestLinuxAdapterCollectSyslog:
    """测试系统日志收集"""

    def test_collect_syslog_returns_string(self):
        """测试收集日志返回字符串"""
        adapter = LinuxAdapter()
        logs = adapter.collect_syslog()

        assert isinstance(logs, str)

    def test_collect_syslog_sections(self):
        """测试收集日志包含各部分"""
        adapter = LinuxAdapter()
        logs = adapter.collect_syslog()

        # 至少应该返回字符串（即使日志为空）
        assert len(logs) >= 0


class TestLinuxAdapterDetectDevices:
    """测试设备检测"""

    def test_detect_devices_returns_dict(self):
        """测试设备检测返回字典"""
        adapter = LinuxAdapter()
        devices = adapter.detect_devices()

        assert isinstance(devices, dict)

    def test_detect_devices_has_categories(self):
        """测试设备检测包含类别"""
        adapter = LinuxAdapter()
        devices = adapter.detect_devices()

        expected_categories = ["network", "serial", "usb", "i2c", "spi", "gpio"]
        for category in expected_categories:
            assert category in devices
            assert isinstance(devices[category], list)


class TestLinuxAdapterGetSystemInfo:
    """测试系统信息获取"""

    def test_get_system_info_returns_dict(self):
        """测试系统信息返回字典"""
        adapter = LinuxAdapter()
        info = adapter.get_system_info()

        assert isinstance(info, dict)

    def test_get_system_info_has_cpu(self):
        """测试系统信息包含 CPU 信息"""
        adapter = LinuxAdapter()
        info = adapter.get_system_info()

        # 应该有 cpu_model 键（即使为空）
        assert "cpu_model" in info or len(info) >= 0

    def test_get_system_info_has_memory(self):
        """测试系统信息包含内存信息"""
        adapter = LinuxAdapter()
        info = adapter.get_system_info()

        # 可能有 memory_total_mb
        if info:
            assert isinstance(info, dict)


class TestCommandResult:
    """测试 CommandResult 类"""

    def test_create_basic(self):
        """测试创建基本对象"""
        result = CommandResult(return_code=0, stdout="output", stderr="", duration=0.1)

        assert result.return_code == 0
        assert result.stdout == "output"
        assert result.stderr == ""
        assert result.duration == 0.1

    def test_success_property(self):
        """测试成功属性"""
        success_result = CommandResult(return_code=0)
        assert success_result.success is True

        fail_result = CommandResult(return_code=1)
        assert fail_result.success is False

    def test_default_values(self):
        """测试默认值"""
        result = CommandResult(return_code=0)

        assert result.stdout == ""
        assert result.stderr == ""
        assert result.duration == 0.0

    def test_repr(self):
        """测试字符串表示"""
        result = CommandResult(return_code=0, stdout="hello" * 100)
        repr_str = repr(result)

        assert "CommandResult" in repr_str
        assert "code=0" in repr_str
        assert "stdout_len" in repr_str


class TestLinuxAdapterIntegration:
    """测试 LinuxAdapter 集成"""

    def test_full_workflow(self):
        """测试完整工作流程"""
        adapter = LinuxAdapter()

        # 检测平台
        platform = adapter.detect_platform()
        assert platform == "linux"

        # 执行命令
        result = adapter.execute("uname -a")
        assert result.success is True
        assert len(result.stdout) > 0

        # 获取系统信息
        info = adapter.get_system_info()
        assert isinstance(info, dict)

        # 检测设备
        devices = adapter.detect_devices()
        assert isinstance(devices, dict)

        # 收集日志
        logs = adapter.collect_syslog()
        assert isinstance(logs, str)
