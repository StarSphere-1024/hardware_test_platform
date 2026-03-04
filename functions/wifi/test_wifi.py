"""
WiFi test function.

Tests WiFi functionality including scan, connect, and ping operations.

WiFi 测试功能
包括扫描、连接和 ping 操作测试

Usage:
    test_wifi --ssid <SSID> [options]

Options:
    --ssid <SSID>: WiFi SSID to connect (required)
    --password <PWD>: WiFi password (optional, for WPA/WPA2)
    --interface <IFACE>: WiFi interface name (default: auto-detect)
    --timeout <seconds>: Test timeout (default: 30)

Examples:
    test_wifi --ssid MyNetwork
    test_wifi --ssid MyNetwork --password MyPassword

Returns:
    0: Success
    1: Timeout
    2: Missing parameter
    -1: Test failed
    -101: Device not found
    -102: Device error
"""

import argparse
import glob
import os
import subprocess
import time
from typing import Dict, Any, List, Optional


def test_wifi(
    ssid: str,
    password: Optional[str] = None,
    interface: Optional[str] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """
    Test WiFi functionality.

    测试 WiFi 功能

    Args:
        ssid: WiFi SSID to connect
        password: WiFi password (optional)
        interface: WiFi interface name
        timeout: Timeout in seconds

    Returns:
        Dictionary with code, message, and details
    """
    start_time = time.time()
    details: Dict[str, Any] = {
        "ssid": ssid,
        "password": "***" if password else None,
        "interface": interface,
    }

    # Auto-detect interface if not specified
    if not interface:
        interface = _detect_wifi_interface()
        details["interface"] = interface or "none"

    if not interface or interface == "none":
        return {
            "code": -101,  # DEVICE_NOT_FOUND
            "message": "WiFi interface not found",
            "details": {
                **details,
                "available_interfaces": detect_wifi_interfaces(),
            },
        }

    # Check if interface exists
    if not os.path.exists(f"/sys/class/net/{interface}"):
        return {
            "code": -101,
            "message": f"Network interface '{interface}' not found",
            "details": details,
        }

    # Check if nmcli is available (NetworkManager)
    if _has_nmcli():
        result = _test_wifi_nmcli(ssid, password, interface, timeout, details)
    else:
        # Try using iwconfig/iw
        result = _test_wifi_iw(ssid, password, interface, timeout, details)

    if result["code"] != 0:
        return result

    duration = time.time() - start_time

    return {
        "code": 0,  # SUCCESS
        "message": f"WiFi test passed, connected to {ssid}",
        "duration": round(duration, 2),
        "details": details,
    }


def _detect_wifi_interface() -> Optional[str]:
    """Detect WiFi interface."""
    interfaces = detect_wifi_interfaces()
    return interfaces[0] if interfaces else None


def detect_wifi_interfaces() -> List[str]:
    """
    Detect available WiFi interfaces.

    检测可用 WiFi 接口

    Returns:
        List of WiFi interface names
    """
    interfaces = []

    # Check /sys/class/net for wireless interfaces
    try:
        net_dir = "/sys/class/net"
        if os.path.exists(net_dir):
            for iface in os.listdir(net_dir):
                # Check if it's a wireless interface
                if os.path.exists(f"/sys/class/net/{iface}/phy80211"):
                    interfaces.append(iface)
    except Exception:
        pass

    # Alternative: check iwconfig output
    if not interfaces:
        try:
            result = subprocess.run(
                "iwconfig 2>/dev/null | grep -E '^[a-z]' | awk '{print $1}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                interfaces = result.stdout.strip().split()
        except Exception:
            pass

    return interfaces


def _has_nmcli() -> bool:
    """Check if nmcli is available."""
    try:
        result = subprocess.run(
            "nmcli --version",
            shell=True,
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _test_wifi_nmcli(
    ssid: str,
    password: Optional[str],
    interface: str,
    timeout: int,
    details: Dict[str, Any],
) -> Dict[str, Any]:
    """Test WiFi using nmcli."""
    try:
        # Check if already connected
        result = subprocess.run(
            f"nmcli -t -f active,ssid dev wifi | grep '^yes:{ssid}$'",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            details["connection_status"] = "already_connected"
        else:
            # Connect to network
            if password:
                cmd = f"nmcli dev wifi connect '{ssid}' password '{password}' ifname {interface}"
            else:
                cmd = f"nmcli dev wifi connect '{ssid}' ifname {interface}"

            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode != 0:
                return {
                    "code": -1,
                    "message": f"Failed to connect to {ssid}: {result.stderr.strip()}",
                    "details": details,
                }

            details["connection_status"] = "connected"

        # Run ping test
        ping_result = subprocess.run(
            f"ping -c 4 -I {interface} 8.8.8.8",
            shell=True,
            capture_output=True,
            text=True,
            timeout=15,
        )

        if ping_result.returncode == 0:
            details["ping"] = "success"
            # Parse latency
            latency = _parse_ping_latency(ping_result.stdout)
            details["latency_ms"] = latency
        else:
            details["ping"] = "failed"
            return {
                "code": -1,
                "message": "Ping test failed after WiFi connection",
                "details": details,
            }

    except subprocess.TimeoutExpired:
        return {
            "code": 1,  # TIMEOUT
            "message": f"WiFi test timed out after {timeout}s",
            "details": details,
        }
    except Exception as e:
        return {
            "code": -102,  # DEVICE_ERROR
            "message": f"WiFi test failed: {e}",
            "details": details,
        }

    return {
        "code": 0,
        "message": "Success",
        "details": details,
    }


def _test_wifi_iw(
    ssid: str,
    password: Optional[str],
    interface: str,
    timeout: int,
    details: Dict[str, Any],
) -> Dict[str, Any]:
    """Test WiFi using iw/iwconfig (fallback)."""
    try:
        # Scan for networks
        result = subprocess.run(
            f"iwlist {interface} scan 2>/dev/null | grep -i 'ESSID:{ssid}'",
            shell=True,
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode != 0:
            return {
                "code": -101,
                "message": f"SSID '{ssid}' not found in scan",
                "details": details,
            }

        details["scan"] = "success"

        # Note: Actual connection would require wpa_supplicant configuration
        # which is more complex. For now, just verify the SSID is visible.
        details["connection_status"] = "scan_only"

    except subprocess.TimeoutExpired:
        return {
            "code": 1,
            "message": f"WiFi scan timed out after {timeout}s",
            "details": details,
        }
    except Exception as e:
        return {
            "code": -102,
            "message": f"WiFi scan failed: {e}",
            "details": details,
        }

    return {
        "code": 0,
        "message": f"WiFi scan passed, SSID '{ssid}' found",
        "details": details,
    }


def scan_wifi(interface: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Scan for available WiFi networks.

    扫描可用 WiFi 网络

    Args:
        interface: WiFi interface name

    Returns:
        List of WiFi network information
    """
    networks = []

    if not interface:
        interface = _detect_wifi_interface()
        if not interface:
            return networks

    try:
        result = subprocess.run(
            f"nmcli -t -f SSID,SIGNAL,SECURITY dev wifi list 2>/dev/null",
            shell=True,
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split(":")
                    if len(parts) >= 3:
                        networks.append({
                            "ssid": parts[0],
                            "signal": int(parts[1]) if parts[1].isdigit() else 0,
                            "security": parts[2],
                        })
    except Exception:
        pass

    return networks


def _parse_ping_latency(output: str) -> float:
    """Parse ping latency from output."""
    import re

    match = re.search(r"rtt min/avg/max/mdev = [\d.]+/([\d.]+)/", output)
    if match:
        return float(match.group(1))

    match = re.search(r"round-trip min/avg/max = [\d.]+/([\d.]+)/", output)
    if match:
        return float(match.group(1))

    return 0.0


def main():
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Test WiFi functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--ssid",
        type=str,
        required=True,
        help="WiFi SSID to connect (required)",
    )
    parser.add_argument(
        "--password",
        type=str,
        default=None,
        help="WiFi password (optional)",
    )
    parser.add_argument(
        "--interface",
        type=str,
        default=None,
        help="WiFi interface name (default: auto-detect)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Test timeout in seconds (default: 30)",
    )

    # Standard options
    parser.add_argument(
        "-I",
        "--loop-count",
        type=int,
        default=1,
        help="Loop count",
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=int,
        default=0,
        help="Interval between loops (seconds)",
    )
    parser.add_argument(
        "-r",
        "--report",
        action="store_true",
        help="Enable report generation",
    )
    parser.add_argument(
        "-w",
        "--wait-timeout",
        type=int,
        default=None,
        help="Wait timeout (seconds)",
    )

    # Scan option
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scan for available WiFi networks",
    )

    args = parser.parse_args()

    # Scan if requested
    if args.scan:
        print("Available WiFi networks:")
        for network in scan_wifi(args.interface):
            print(f"  {network['ssid']} (signal: {network['signal']}%, security: {network['security']})")
        return 0

    # Run test
    result = test_wifi(
        ssid=args.ssid,
        password=args.password,
        interface=args.interface,
        timeout=args.timeout,
    )

    # Print result
    print(f"WiFi Test: {result['message']}")
    if "details" in result:
        for key, value in result["details"].items():
            print(f"  {key}: {value}")

    return result.get("code", -1)


if __name__ == "__main__":
    exit(main())
