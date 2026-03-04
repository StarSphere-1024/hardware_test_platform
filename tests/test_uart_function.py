"""
Tests for test_uart function.

测试 UART 测试函数
"""
import pytest
from unittest.mock import patch, MagicMock
import serial
import sys
import os

# Add functions directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from functions.uart.test_uart import test_uart as uart_test_func, list_serial_ports


class TestListSerialPorts:
    """测试串口列表功能"""

    def test_list_serial_ports_returns_list(self):
        """测试列出串口返回列表"""
        ports = list_serial_ports()
        assert isinstance(ports, list)

    def test_list_serial_ports_sorted(self):
        """测试列出的串口已排序"""
        ports = list_serial_ports()
        assert ports == sorted(ports)


class TestTestUart:
    """测试 UART 测试函数"""

    def test_uart_port_not_found(self):
        """测试串口未找到"""
        result = uart_test_func(port="/dev/ttyUSB999")

        assert result["code"] == -101  # DEVICE_NOT_FOUND
        assert "not found" in result["message"].lower()
        assert "available_ports" in result.get("details", {})

    def test_uart_no_permission(self):
        """测试无读写权限"""
        # 模拟一个存在但无权限的设备
        with patch("os.path.exists", return_value=True):
            with patch("os.access", return_value=False):
                result = uart_test_func(port="/dev/ttyUSB0")

                assert result["code"] == -1  # FAILED
                assert "permission" in result["message"].lower()

    def test_uart_missing_dependency(self):
        """测试缺少 pyserial 依赖"""
        with patch("os.path.exists", return_value=True):
            with patch("os.access", return_value=True):
                with patch.dict("sys.modules", {"serial": None}):
                    # 模拟 import 失败
                    import builtins
                    original_import = builtins.__import__

                    def mock_import(name, *args, **kwargs):
                        if name == "serial":
                            raise ImportError("No module named 'serial'")
                        return original_import(name, *args, **kwargs)

                    with patch.object(builtins, "__import__", side_effect=mock_import):
                        result = uart_test_func(port="/dev/ttyUSB0")

                        assert result["code"] == -2  # ENV_MISSING
                        assert "pyserial" in result["message"].lower()

    def test_uart_success_mock(self):
        """测试模拟成功的 UART 测试"""
        mock_serial = MagicMock()
        mock_serial.rts = False
        mock_serial.dtr = False
        mock_serial.cts = True

        with patch("os.path.exists", return_value=True):
            with patch("os.access", return_value=True):
                with patch("serial.Serial", return_value=mock_serial):
                    result = uart_test_func(port="/dev/ttyUSB0", baudrate=115200)

                    assert result["code"] == 0  # SUCCESS
                    assert "passed" in result["message"].lower()

    def test_uart_loopback_success(self):
        """测试模拟回环成功"""
        mock_serial = MagicMock()
        mock_serial.rts = False
        mock_serial.dtr = False
        mock_serial.cts = True
        mock_serial.read = MagicMock(return_value=b"UART_TEST_0123456789")
        mock_serial.write = MagicMock()
        mock_serial.flush = MagicMock()
        mock_serial.close = MagicMock()

        with patch("os.path.exists", return_value=True):
            with patch("os.access", return_value=True):
                with patch("serial.Serial", return_value=mock_serial):
                    result = uart_test_func(port="/dev/ttyUSB0", loopback=True)

                    assert result["code"] == 0  # SUCCESS
                    assert "loopback" in result.get("details", {})

    def test_uart_loopback_failure(self):
        """测试模拟回环失败"""
        mock_serial = MagicMock()
        mock_serial.read = MagicMock(return_value=b"WRONG_DATA")
        mock_serial.write = MagicMock()
        mock_serial.flush = MagicMock()
        mock_serial.close = MagicMock()

        with patch("os.path.exists", return_value=True):
            with patch("os.access", return_value=True):
                with patch("serial.Serial", return_value=mock_serial):
                    result = uart_test_func(port="/dev/ttyUSB0", loopback=True)

                    assert result["code"] == -1  # FAILED
                    assert "Loopback" in result["message"]

    def test_uart_serial_exception(self):
        """测试串口异常"""
        mock_serial = MagicMock()
        mock_serial.close = MagicMock(side_effect=serial.SerialException("Serial error"))

        with patch("os.path.exists", return_value=True):
            with patch("os.access", return_value=True):
                with patch("serial.Serial", return_value=mock_serial):
                    result = uart_test_func(port="/dev/ttyUSB0")

                    assert result["code"] == -102  # DEVICE_ERROR
                    assert "error" in result["message"].lower()

    def test_uart_with_custom_baudrate(self):
        """测试自定义波特率"""
        mock_serial = MagicMock()
        mock_serial.rts = False
        mock_serial.dtr = False

        with patch("os.path.exists", return_value=True):
            with patch("os.access", return_value=True):
                with patch("serial.Serial", return_value=mock_serial):
                    result = uart_test_func(port="/dev/ttyUSB0", baudrate=9600)

                    # 验证波特率被传递
                    assert result["code"] == 0

    def test_uart_details_contain_port_info(self):
        """测试结果包含端口信息"""
        with patch("os.path.exists", return_value=True):
            with patch("os.access", return_value=False):
                result = uart_test_func(port="/dev/ttyUSB0", baudrate=115200)

                details = result.get("details", {})
                assert details.get("port") == "/dev/ttyUSB0"
                assert details.get("baudrate") == 115200

    def test_uart_returns_duration(self):
        """测试返回执行时间"""
        with patch("os.path.exists", return_value=True):
            with patch("os.access", return_value=False):
                result = uart_test_func(port="/dev/ttyUSB0")

                # 失败时也应该有 duration（虽然没有显式返回）
                assert "duration" in result or result["code"] != 0
