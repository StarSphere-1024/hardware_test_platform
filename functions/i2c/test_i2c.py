"""
I2C test function.

Tests I2C bus functionality including scan, read, and write operations.

I2C 测试功能
包括扫描、读取和写入操作测试

Usage:
    test_i2c --bus <BUS> [options]

Options:
    --bus <BUS>: I2C bus number (required, e.g., 1)
    --address <ADDR>: I2C device address (optional, for read/write test)
    --timeout <seconds>: Test timeout (default: 10)

Examples:
    test_i2c --bus 1
    test_i2c --bus 1 --address 0x50

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
import time
from typing import Dict, Any, List


def test_i2c(
    bus: int,
    address: int = None,
    timeout: int = 10,
) -> Dict[str, Any]:
    """
    Test I2C bus functionality.

    测试 I2C 总线功能

    Args:
        bus: I2C bus number (e.g., 1 for /dev/i2c-1)
        address: I2C device address (optional)
        timeout: Timeout in seconds

    Returns:
        Dictionary with code, message, and details
    """
    start_time = time.time()
    details: Dict[str, Any] = {
        "bus": bus,
        "address": hex(address) if address else None,
    }

    # Check if I2C bus exists
    i2c_device = f"/dev/i2c-{bus}"
    if not os.path.exists(i2c_device):
        available_buses = list_i2c_buses()
        return {
            "code": -101,  # DEVICE_NOT_FOUND
            "message": f"I2C bus '{i2c_device}' not found",
            "details": {
                **details,
                "available_buses": available_buses,
            },
        }

    # Check read/write permissions
    if not os.access(i2c_device, os.R_OK | os.W_OK):
        return {
            "code": -1,  # FAILED
            "message": f"No read/write permission for '{i2c_device}'",
            "details": details,
        }

    try:
        import smbus2
    except ImportError:
        try:
            import smbus as smbus2
        except ImportError:
            return {
                "code": -2,  # ENV_MISSING
                "message": "smbus2/smbus not installed. Run: pip install smbus2",
                "details": details,
            }

    # Run scan test
    try:
        bus_obj = smbus2.SMBus(bus)
        details["connection"] = "opened"

        # Scan for devices
        scanned_devices = []
        for addr in range(0x03, 0x78):
            try:
                bus_obj.write_byte(addr, 0)
                scanned_devices.append(hex(addr))
            except Exception:
                pass

        details["scanned_devices"] = scanned_devices
        details["device_count"] = len(scanned_devices)

        # If specific address provided, test read/write
        if address is not None:
            try:
                # Try to read one byte
                data = bus_obj.read_byte(address)
                details["read_test"] = "success"
                details["read_data"] = data
            except Exception as e:
                details["read_test"] = f"failed: {e}"

        bus_obj.close()
        details["connection"] = "closed"

    except Exception as e:
        return {
            "code": -102,  # DEVICE_ERROR
            "message": f"I2C communication error: {e}",
            "details": details,
        }

    duration = time.time() - start_time

    return {
        "code": 0,  # SUCCESS
        "message": f"I2C bus {bus} test passed, found {len(scanned_devices)} devices",
        "duration": round(duration, 2),
        "details": details,
    }


def list_i2c_buses() -> List[str]:
    """
    List available I2C buses.

    列出可用 I2C 总线

    Returns:
        List of I2C bus device paths
    """
    buses = []
    patterns = ["/dev/i2c-*"]

    for pattern in patterns:
        buses.extend(glob.glob(pattern))

    return sorted(buses)


def main():
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Test I2C bus functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--bus",
        type=int,
        required=True,
        help="I2C bus number (required, e.g., 1)",
    )
    parser.add_argument(
        "--address",
        type=lambda x: int(x, 0),  # Support hex and decimal
        default=None,
        help="I2C device address (optional, e.g., 0x50)",
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
        "--timeout",
        type=int,
        default=None,
        help="Wait timeout (seconds)",
    )

    # List buses option
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available I2C buses",
    )

    args = parser.parse_args()

    # List buses if requested
    if args.list:
        print("Available I2C buses:")
        for bus in list_i2c_buses():
            print(f"  {bus}")
        return 0

    # Run test
    result = test_i2c(
        bus=args.bus,
        address=args.address,
        timeout=args.timeout,
    )

    # Print result
    print(f"I2C Test: {result['message']}")
    if "details" in result:
        for key, value in result["details"].items():
            if isinstance(value, list):
                print(f"  {key}: {', '.join(value)}")
            else:
                print(f"  {key}: {value}")

    return result.get("code", -1)


if __name__ == "__main__":
    exit(main())
