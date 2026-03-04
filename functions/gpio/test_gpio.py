"""
GPIO test function.

Tests GPIO functionality including info, set, get, and mode operations.

GPIO 测试功能
包括信息、设置、获取和模式操作测试

Usage:
    test_gpio --pin <PIN> [options]

Options:
    --pin <PIN>: GPIO pin number (required)
    --mode <MODE>: GPIO mode (input/output, default: output)
    --value <VALUE>: Set GPIO value (0/1, optional)
    --timeout <seconds>: Test timeout (default: 10)

Examples:
    test_gpio --pin 17
    test_gpio --pin 17 --mode input
    test_gpio --pin 17 --mode output --value 1

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
from typing import Dict, Any, List, Optional


def test_gpio(
    pin: int,
    mode: str = "output",
    value: Optional[int] = None,
    timeout: int = 10,
) -> Dict[str, Any]:
    """
    Test GPIO functionality.

    测试 GPIO 功能

    Args:
        pin: GPIO pin number
        mode: GPIO mode (input/output)
        value: Value to set (0/1)
        timeout: Timeout in seconds

    Returns:
        Dictionary with code, message, and details
    """
    start_time = time.time()
    details: Dict[str, Any] = {
        "pin": pin,
        "mode": mode,
        "value": value,
    }

    # Check if GPIO is available
    gpio_chip = find_gpio_chip()
    if not gpio_chip:
        return {
            "code": -101,  # DEVICE_NOT_FOUND
            "message": "GPIO chip not found",
            "details": details,
        }

    details["gpio_chip"] = gpio_chip

    # Check if gpiochip device exists
    gpiochip_device = f"/dev/{gpio_chip}"
    if not os.path.exists(gpiochip_device):
        # Try using sysfs GPIO (older method)
        gpio_sysfs = f"/sys/class/gpio/gpio{pin}"
        if not os.path.exists(gpio_sysfs):
            # Try to export the GPIO
            try:
                with open("/sys/class/gpio/export", "w") as f:
                    f.write(str(pin))
                time.sleep(0.1)  # Wait for export
            except Exception:
                pass

        if not os.path.exists(gpio_sysfs):
            return {
                "code": -101,
                "message": f"GPIO pin {pin} not accessible",
                "details": details,
            }

    # Try to use libgpiod first (modern method)
    try:
        import lgpio
        result = _test_gpio_lgpiod(pin, mode, value, details)
    except ImportError:
        # Fallback to sysfs method
        result = _test_gpio_sysfs(pin, mode, value, details)

    if result["code"] != 0:
        return result

    duration = time.time() - start_time

    return {
        "code": 0,  # SUCCESS
        "message": f"GPIO {pin} test passed",
        "duration": round(duration, 2),
        "details": details,
    }


def _test_gpio_sysfs(
    pin: int,
    mode: str,
    value: Optional[int],
    details: Dict[str, Any],
) -> Dict[str, Any]:
    """Test GPIO using sysfs interface."""
    gpio_dir = f"/sys/class/gpio/gpio{pin}"

    try:
        # Set direction
        direction_file = f"{gpio_dir}/direction"
        if os.path.exists(direction_file):
            with open(direction_file, "w") as f:
                f.write(mode)
            details["direction_set"] = mode
        else:
            return {
                "code": -1,
                "message": f"Cannot access GPIO {pin} direction",
                "details": details,
            }

        # Set value if output mode and value provided
        if mode == "output" and value is not None:
            value_file = f"{gpio_dir}/value"
            if os.path.exists(value_file):
                with open(value_file, "w") as f:
                    f.write(str(value))
                details["value_set"] = value

                # Verify by reading back
                time.sleep(0.01)
                with open(value_file, "r") as f:
                    read_value = int(f.read().strip())
                details["value_read"] = read_value

                if read_value != value:
                    return {
                        "code": -1,
                        "message": f"GPIO value mismatch: expected {value}, got {read_value}",
                        "details": details,
                    }

        # Read value if input mode
        if mode == "input":
            value_file = f"{gpio_dir}/value"
            if os.path.exists(value_file):
                with open(value_file, "r") as f:
                    read_value = int(f.read().strip())
                details["value_read"] = read_value

    except Exception as e:
        return {
            "code": -102,  # DEVICE_ERROR
            "message": f"GPIO operation failed: {e}",
            "details": details,
        }

    return {
        "code": 0,
        "message": "Success",
        "details": details,
    }


def _test_gpio_lgpiod(
    pin: int,
    mode: str,
    value: Optional[int],
    details: Dict[str, Any],
) -> Dict[str, Any]:
    """Test GPIO using lgpio library."""
    try:
        import lgpio

        # Open chip
        chip = lgpio.gpiochip_open(0)

        # Request line
        lgpio.gpio_request_one(chip, pin, lgpio.LG_SET_OUTPUT if mode == "output" else lgpio.LG_SET_INPUT)

        if mode == "output" and value is not None:
            lgpio.gpio_write(chip, pin, value)
            details["value_set"] = value

            # Verify
            read_value = lgpio.gpio_read(chip, pin)
            details["value_read"] = read_value

            if read_value != value:
                lgpio.gpiochip_close(chip)
                return {
                    "code": -1,
                    "message": f"GPIO value mismatch: expected {value}, got {read_value}",
                    "details": details,
                }

        elif mode == "input":
            read_value = lgpio.gpio_read(chip, pin)
            details["value_read"] = read_value

        lgpio.gpiochip_close(chip)

    except Exception as e:
        return {
            "code": -102,
            "message": f"lgpio operation failed: {e}",
            "details": details,
        }

    return {
        "code": 0,
        "message": "Success",
        "details": details,
    }


def find_gpio_chip() -> Optional[str]:
    """
    Find available GPIO chip.

    查找可用 GPIO 芯片

    Returns:
        GPIO chip name or None
    """
    # Check for gpiochip devices
    chips = glob.glob("/dev/gpiochip*")
    if chips:
        return "gpiochip0"

    # Check sysfs GPIO
    if os.path.exists("/sys/class/gpio"):
        return "sysfs_gpio"

    return None


def list_gpio_pins() -> List[int]:
    """
    List available GPIO pins.

    列出可用 GPIO 引脚

    Returns:
        List of GPIO pin numbers
    """
    pins = []

    # Try sysfs method
    gpio_dir = "/sys/class/gpio"
    if os.path.exists(gpio_dir):
        for item in os.listdir(gpio_dir):
            if item.startswith("gpio"):
                try:
                    pins.append(int(item[4:]))
                except ValueError:
                    pass

    return sorted(pins)


def main():
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Test GPIO functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--pin",
        type=int,
        required=True,
        help="GPIO pin number (required)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["input", "output"],
        default="output",
        help="GPIO mode (default: output)",
    )
    parser.add_argument(
        "--value",
        type=int,
        choices=[0, 1],
        default=None,
        help="Set GPIO value (0/1, optional)",
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

    # List pins option
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available GPIO pins",
    )

    args = parser.parse_args()

    # List pins if requested
    if args.list:
        print("Available GPIO pins:")
        for pin in list_gpio_pins():
            print(f"  GPIO {pin}")
        return 0

    # Run test
    result = test_gpio(
        pin=args.pin,
        mode=args.mode,
        value=args.value,
        timeout=args.timeout,
    )

    # Print result
    print(f"GPIO Test: {result['message']}")
    if "details" in result:
        for key, value in result["details"].items():
            print(f"  {key}: {value}")

    return result.get("code", -1)


if __name__ == "__main__":
    exit(main())
