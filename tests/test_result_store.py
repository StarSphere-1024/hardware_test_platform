"""
Tests for result_store module.

测试结果存储模块
"""
import json
import pytest
from pathlib import Path
from datetime import datetime

from framework.core.result_store import ResultStore, TestResult, get_result_store


class TestTestResult:
    """测试 TestResult 数据类"""

    def test_create_basic_result(self):
        """测试创建基本结果"""
        result = TestResult(
            module="eth",
            case_name="test_case",
            status="pass",
            timestamp="2026-03-03T10:00:00",
            duration=1.5,
        )
        assert result.module == "eth"
        assert result.case_name == "test_case"
        assert result.status == "pass"
        assert result.duration == 1.5
        assert result.retry_count == 0
        assert result.platform == "linux"

    def test_create_with_details(self):
        """测试创建带详细信息的result"""
        details = {"latency_ms": 2.5, "packet_loss": 0}
        result = TestResult(
            module="eth",
            case_name="test_case",
            status="pass",
            timestamp="2026-03-03T10:00:00",
            duration=1.5,
            details=details,
        )
        assert result.details == details
        assert result.details["latency_ms"] == 2.5

    def test_create_with_error(self):
        """测试创建带错误信息的 result"""
        result = TestResult(
            module="eth",
            case_name="test_case",
            status="fail",
            timestamp="2026-03-03T10:00:00",
            duration=1.5,
            error="Connection timeout",
        )
        assert result.status == "fail"
        assert result.error == "Connection timeout"

    def test_to_dict(self):
        """测试转换为字典"""
        result = TestResult(
            module="eth",
            case_name="test_case",
            status="pass",
            timestamp="2026-03-03T10:00:00",
            duration=1.5,
        )
        d = result.to_dict()
        assert d["module"] == "eth"
        assert d["status"] == "pass"
        assert isinstance(d, dict)

    def test_running_factory(self):
        """测试创建运行中状态"""
        result = TestResult.running("eth", "eth_test")
        assert result.status == "running"
        assert result.module == "eth"
        assert result.case_name == "eth_test"
        assert result.duration == 0.0

    def test_success_factory(self):
        """测试创建成功状态"""
        result = TestResult.success("eth", "eth_test", 2.5, {"key": "value"})
        assert result.status == "pass"
        assert result.duration == 2.5
        assert result.details == {"key": "value"}

    def test_failure_factory(self):
        """测试创建失败状态"""
        result = TestResult.failure("eth", "eth_test", 2.5, "error msg", 3)
        assert result.status == "fail"
        assert result.duration == 2.5
        assert result.error == "error msg"
        assert result.retry_count == 3


class TestResultStore:
    """测试 ResultStore 类"""

    def test_init_creates_dir(self, temp_dir: Path):
        """测试初始化创建目录"""
        store = ResultStore(tmp_dir=str(temp_dir / "new_tmp"))
        assert store.tmp_dir.exists()
        assert store.tmp_dir.is_dir()

    def test_write_result(self, temp_dirs):
        """测试写入结果"""
        store = ResultStore(tmp_dir=str(temp_dirs["tmp"]))
        result = TestResult.success("eth", "eth_test", 1.5)
        path = store.write(result)

        assert path.exists()
        assert path.suffix == ".json"

    def test_write_is_atomic(self, temp_dirs):
        """测试原子写入"""
        store = ResultStore(tmp_dir=str(temp_dirs["tmp"]))
        result = TestResult.success("eth", "eth_test", 1.5)

        store.write(result)

        # 确保没有临时文件残留
        temp_files = list(temp_dirs["tmp"].glob("*.tmp"))
        assert len(temp_files) == 0

    def test_read_result(self, temp_dirs):
        """测试读取结果"""
        store = ResultStore(tmp_dir=str(temp_dirs["tmp"]))
        original = TestResult.success("eth", "eth_test", 1.5, {"key": "value"})
        store.write(original)

        read_result = store.read("eth")
        assert read_result is not None
        assert read_result.module == "eth"
        assert read_result.status == "pass"
        assert read_result.details["key"] == "value"

    def test_read_nonexistent(self, temp_dirs):
        """测试读取不存在的结果"""
        store = ResultStore(tmp_dir=str(temp_dirs["tmp"]))
        result = store.read("nonexistent")
        assert result is None

    def test_list_results(self, temp_dirs):
        """测试列出所有结果"""
        store = ResultStore(tmp_dir=str(temp_dirs["tmp"]))
        store.write(TestResult.success("eth", "eth_test", 1.0))
        store.write(TestResult.success("uart", "uart_test", 2.0))
        store.write(TestResult.failure("i2c", "i2c_test", 0.5, "error"))

        results = store.list_results()
        assert len(results) == 3
        modules = [r.module for r in results]
        assert "eth" in modules
        assert "uart" in modules
        assert "i2c" in modules

    def test_clear_single_module(self, temp_dirs):
        """测试清除单个模块结果"""
        store = ResultStore(tmp_dir=str(temp_dirs["tmp"]))
        store.write(TestResult.success("eth", "eth_test", 1.0))
        store.write(TestResult.success("uart", "uart_test", 2.0))

        store.clear("eth")

        assert not (temp_dirs["tmp"] / "eth_result.json").exists()
        assert (temp_dirs["tmp"] / "uart_result.json").exists()

    def test_clear_all(self, temp_dirs):
        """测试清除所有结果"""
        store = ResultStore(tmp_dir=str(temp_dirs["tmp"]))
        store.write(TestResult.success("eth", "eth_test", 1.0))
        store.write(TestResult.success("uart", "uart_test", 2.0))

        store.clear()

        results = list(temp_dirs["tmp"].glob("*_result.json"))
        assert len(results) == 0

    def test_write_running_status(self, temp_dirs):
        """测试写入运行中状态"""
        store = ResultStore(tmp_dir=str(temp_dirs["tmp"]))
        path = store.write_running_status("eth", "eth_test")

        assert path.exists()
        result = store.read("eth")
        assert result.status == "running"

    def test_write_success_helper(self, temp_dirs):
        """测试成功写入辅助方法"""
        store = ResultStore(tmp_dir=str(temp_dirs["tmp"]))
        path = store.write_success("eth", "eth_test", 2.5, {"latency": 10})

        assert path.exists()
        result = store.read("eth")
        assert result.status == "pass"
        assert result.duration == 2.5

    def test_write_failure_helper(self, temp_dirs):
        """测试失败写入辅助方法"""
        store = ResultStore(tmp_dir=str(temp_dirs["tmp"]))
        path = store.write_failure("eth", "eth_test", 2.5, "timeout error", 2)

        assert path.exists()
        result = store.read("eth")
        assert result.status == "fail"
        assert result.error == "timeout error"
        assert result.retry_count == 2

    def test_json_content_valid(self, temp_dirs):
        """测试写入的 JSON 内容有效"""
        store = ResultStore(tmp_dir=str(temp_dirs["tmp"]))
        result = TestResult(
            module="eth",
            case_name="test_case",
            status="pass",
            timestamp="2026-03-03T10:00:00",
            duration=1.5,
            details={"key": "value"},
        )
        store.write(result)

        # 直接读取文件验证 JSON 格式
        with open(temp_dirs["tmp"] / "eth_result.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["module"] == "eth"
        assert data["status"] == "pass"
        assert "timestamp" in data


class TestGetResultStore:
    """测试全局 result_store 获取"""

    def test_get_result_store_singleton(self, temp_dir):
        """测试单例模式"""
        # 注意：这是一个全局单例测试
        # 在实际使用中需要重置全局变量
        store = get_result_store()
        assert isinstance(store, ResultStore)
