"""
USB test function.

Tests USB port functionality including device detection and speed test.

USB 测试功能
包括设备检测和速度测试

Usage:
    test_usb [options]

Options:
    --port <PORT>: USB port number (optional)
    --speed-test: Enable speed test (requires USB storage)
    --timeout <seconds>: Test timeout (default: 10)

Examples:
    test_usb
    test_usb --speed-test

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
from typing import Dict, Any, List


def test_usb(
    port: int = None,
    speed_test: bool = False,
    timeout: int = 10,
) -> Dict[str, Any]:
    """
    Test USB port functionality.

    测试 USB 端口功能

    Args:
        port: USB port number (optional)
        speed_test: Whether to run speed test
        timeout: Timeout in seconds

    Returns:
        Dictionary with code, message, and details
    """
    start_time = time.time()
    details: Dict[str, Any] = {
        "port": port,
        "speed_test": speed_test,
    }

    # Detect USB devices
    usb_devices = detect_usb_devices()
    details["usb_devices"] = usb_devices
    details["device_count"] = len(usb_devices)

    if not usb_devices:
        return {
            "code": -101,  # DEVICE_NOT_FOUND
            "message": "No USB devices detected",
            "details": details,
        }

    # If specific port requested, check if it exists
    if port is not None:
        if port >= len(usb_devices):
            return {
                "code": -101,
                "message": f"USB port {port} not found",
                "details": details,
            }

    # Run speed test if requested
    if speed_test:
        speed_result = _run_usb_speed_test()
        details["speed_test"] = speed_result

    duration = time.time() - start_time

    return {
        "code": 0,  # SUCCESS
        "message": f"USB test passed, found {len(usb_devices)} devices",
        "duration": round(duration, 2),
        "details": details,
    }


def detect_usb_devices() -> List[Dict[str, Any]]:
    """
    Detect connected USB devices.

    检测连接的 USB 设备

    Returns:
        List of USB device information
    """
    devices = []

    # Method 1: Using lsusb
    try:
        result = subprocess.run(
            "lsusb",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line:
                    devices.append({
                        "type": "lsusb",
                        "description": line.strip(),
                    })
    except Exception:
        pass

    # Method 2: Check /dev/sd* devices
    if not devices:
        storage_devices = glob.glob("/dev/sd[a-z]")
        for dev in storage_devices:
            devices.append({
                "type": "storage",
                "device": dev,
            })

    # Method 3: Check USB bus topology
    try:
        result = subprocess.run(
            "lsusb -t 2>/dev/null | grep -v '^/'",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            devices.append({
                "type": "topology",
                "topology": result.stdout.strip(),
            })
    except Exception:
        pass

    return devices


def _run_usb_speed_test() -> Dict[str, Any]:
    """
    Run USB storage speed test.

    运行 USB 存储速度测试

    Returns:
        Speed test results
    """
    result = {
        "status": "not_run",
        "write_speed": None,
        "read_speed": None,
    }

    # Find a writable USB storage device
    usb_mount = _find_usb_mount()
    if not usb_mount:
        result["status"] = "no_mount_found"
        return result

    try:
        test_file = os.path.join(usb_mount, ".usb_speed_test")
        test_size = "10M"  # 10MB test file

        # Write test
        write_result = subprocess.run(
            f"dd if=/dev/zero of={test_file} bs={test_size} count=1 conv=fdatasync 2>&1",
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if write_result.returncode == 0:
            result["write_speed"] = _parse_dd_speed(write_result.stderr)
            result["status"] = "success"

        # Read test (clear cache first)
        subprocess.run("sync && echo 3 > /proc/sys/vm/drop_caches", shell=True)
        read_result = subprocess.run(
            f"dd if={test_file} of=/dev/null bs={test_size} 2>&1",
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if read_result.returncode == 0:
            result["read_speed"] = _parse_dd_speed(read_result.stderr)

        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)

    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
    except Exception as e:
        result["status"] = f"error: {e}"

    return result


def _find_usb_mount() -> str:
    """Find a USB mount point."""
    # Common USB mount locations
    usb_mounts = [
        "/media",
        "/mnt/usb",
        "/run/media",
    ]

    for mount_base in usb_mounts:
        if os.path.exists(mount_base):
            # Check for subdirectories
            try:
                for item in os.listdir(mount_base):
                    item_path = os.path.join(mount_base, item)
                    if os.path.isdir(item_path):
                        # Check if writable
                        test_file = os.path.join(item_path, ".write_test")
                        try:
                            with open(test_file, "w") as f:
                                f.write("test")
                            os.remove(test_file)
                            return item_path
                        except Exception:
                            pass
            except Exception:
                pass

    return ""


def _parse_dd_speed(output: str) -> float:
    """Parse dd speed output."""
    import re

    # Look for speed pattern (e.g., "10.5 MB/s" or "10.5MB/s")
    match = re.search(r"([\d.]+)\s*MB/s", output)
    if match:
        return float(match.group(1))

    # Look for bytes per second
    match = re.search(r"([\d.]+)\s*bytes/sec", output)
    if match:
        return float(match.group(1)) / (1024 * 1024)

    return 0.0


def main():
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Test USB functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="USB port number (optional)",
    )
    parser.add_argument(
        "--speed-test",
        action="store_true",
        help="Enable speed test",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Test timeout in seconds (default: 10)",
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

    # List devices option
    parser.add_argument(
        "--list",
        action="store_true",
        help="List USB devices",
    )

    args = parser.parse_args()

    # List devices if requested
    if args.list:
        print("USB devices:")
        for dev in detect_usb_devices():
            if "description" in dev:
                print(f"  {dev['description']}")
            elif "device" in dev:
                print(f"  {dev['device']}")
        return 0

    # Run test
    result = test_usb(
        port=args.port,
        speed_test=args.speed_test,
        timeout=args.timeout,
    )

    # Print result
    print(f"USB Test: {result['message']}")
    if "details" in result:
        for key, value in result["details"].items():
            if key == "usb_devices":
                print(f"  {key}: {len(value)} devices found")
            elif isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")

    return result.get("code", -1)


if __name__ == "__main__":
    exit(main())
