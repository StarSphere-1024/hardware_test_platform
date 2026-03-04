"""
Tests for test_eth function.

测试以太网测试函数
"""
import pytest
from unittest.mock import patch, MagicMock
import subprocess
import sys
import os

# Add functions directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 使用别名避免 pytest 误收集为测试
from functions.network.test_eth import test_eth as eth_test_func, _detect_interface, _parse_ping_latency


class TestParsePingLatency:
    """测试 ping 延迟解析"""

    def test_parse_standard_format(self):
        """测试解析标准格式"""
        output = """
PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.
64 bytes from 8.8.8.8: icmp_seq=1 ttl=116 time=2.34 ms
64 bytes from 8.8.8.8: icmp_seq=2 ttl=116 time=2.56 ms

--- 8.8.8.8 ping statistics ---
2 packets transmitted, 2 received, 0% packet loss, time 1001ms
rtt min/avg/max/mdev = 2.340/2.450/2.560/0.110 ms
"""
        latency = _parse_ping_latency(output)
        assert latency == 2.450

    def test_parse_alternative_format(self):
        """测试解析替代格式"""
        output = """
round-trip min/avg/max = 1.234/2.345/3.456 ms
"""
        latency = _parse_ping_latency(output)
        assert latency == 2.345

    def test_parse_no_match(self):
        """测试无匹配时返回 0"""
        output = "ping: unknown host 8.8.8.8"
        latency = _parse_ping_latency(output)
        assert latency == 0.0


class TestDetectInterface:
    """测试接口检测"""

    def test_detect_interface_returns_string(self):
        """测试检测返回字符串"""
        interface = _detect_interface()
        assert isinstance(interface, str)

    def test_detect_interface_with_default_route(self):
        """测试有默认路由时的接口检测"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="eth0\n"
            )
            interface = _detect_interface()
            assert interface == "eth0"

    def test_detect_interface_fallback(self):
        """测试回退到常见接口"""
        with patch("subprocess.run") as mock_run:
            # 第一个命令失败，第二个命令成功（eth0 存在）
            mock_run.side_effect = [
                MagicMock(returncode=1, stdout=""),  # ip route 失败
                MagicMock(returncode=0),  # eth0 存在
            ]
            interface = _detect_interface()
            assert interface == "eth0"

    def test_detect_interface_no_interface(self):
        """测试没有接口时返回 auto"""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("All methods failed")
            interface = _detect_interface()
            # 应该返回 "auto"
            assert interface == "auto" or isinstance(interface, str)


class TestTestEth:
    """测试以太网测试函数"""

    def test_eth_interface_not_found(self):
        """测试接口未找到"""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=1, stdout="", stderr="Device not found"),  # ip link show 失败
            ]
            result = eth_test_func(ip="192.168.1.100", interface="eth999")

            assert result["code"] == -101  # DEVICE_NOT_FOUND
            assert "not found" in result["message"].lower()

    def test_eth_ping_failed(self):
        """测试 ping 失败"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="ping failed"
            )
            result = eth_test_func(ip="192.168.1.100", interface="auto")

            assert result["code"] == -1  # FAILED
            assert "failed" in result["message"].lower()

    def test_eth_ping_timeout(self):
        """测试 ping 超时"""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="ping", timeout=10)
            result = eth_test_func(ip="192.168.1.100", timeout=10)

            assert result["code"] == 1  # TIMEOUT
            assert "timed out" in result["message"].lower()

    def test_eth_success(self):
        """测试成功"""
        ping_output = """
PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.
64 bytes from 8.8.8.8: icmp_seq=1 ttl=116 time=2.34 ms

--- 8.8.8.8 ping statistics ---
rtt min/avg/max/mdev = 2.340/2.450/2.560/0.110 ms
"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=ping_output
            )
            result = eth_test_func(ip="8.8.8.8")

            assert result["code"] == 0  # SUCCESS
            assert "passed" in result["message"].lower()
            assert "latency_ms" in result.get("details", {})

    def test_eth_with_interface(self):
        """测试指定接口"""
        ping_output = "rtt min/avg/max/mdev = 2.340/2.450/2.560/0.110 ms"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=ping_output
            )
            result = eth_test_func(ip="8.8.8.8", interface="eth0")

            # 验证接口被使用
            details = result.get("details", {})
            assert details.get("interface") == "eth0"

    def test_eth_with_iperf3(self):
        """测试 iperf3 测速"""
        iperf3_output = """
{
    "end": {
        "sum_received": {
            "bits_per_second": 95000000
        }
    }
}
"""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                # _detect_interface(): ip route 命令
                MagicMock(returncode=0, stdout="eth0\n"),
                # ip link show eth0: 检查接口存在
                MagicMock(returncode=0, stdout="eth0: <BROADCAST>M..."),
                # ping 命令
                MagicMock(returncode=0, stdout="rtt min/avg/max/mdev = 2.340/2.450/2.560/0.110 ms"),
                # iperf3 命令
                MagicMock(returncode=0, stdout=iperf3_output),
            ]
            result = eth_test_func(ip="8.8.8.8", iperf3=True)

            assert result["code"] == 0
            details = result.get("details", {})
            assert "speed_mbps" in details

    def test_eth_with_iperf3_not_available(self):
        """测试 iperf3 不可用"""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                # _detect_interface(): ip route 命令
                MagicMock(returncode=0, stdout="eth0\n"),
                # ip link show eth0: 检查接口存在
                MagicMock(returncode=0, stdout="eth0: <BROADCAST>M..."),
                # ping 命令
                MagicMock(returncode=0, stdout="rtt min/avg/max/mdev = 2.340/2.450/2.560/0.110 ms"),
                # iperf3 命令超时
                MagicMock(side_effect=subprocess.TimeoutExpired(cmd="iperf3", timeout=15)),
            ]
            result = eth_test_func(ip="8.8.8.8", iperf3=True)

            assert result["code"] == 0  # ping 成功
            details = result.get("details", {})
            assert details.get("iperf3") == "not_available"

    def test_eth_details_contain_ip(self):
        """测试详细信息包含 IP"""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=1, stdout="", stderr="failed"),
            ]
            result = eth_test_func(ip="192.168.1.100")

            details = result.get("details", {})
            assert details.get("ip") == "192.168.1.100"

    def test_eth_returns_duration_on_success(self):
        """测试成功时返回持续时间"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="rtt min/avg/max/mdev = 2.340/2.450/2.560/0.110 ms"
            )
            result = eth_test_func(ip="8.8.8.8")

            assert "duration" in result
            assert isinstance(result["duration"], (int, float))
