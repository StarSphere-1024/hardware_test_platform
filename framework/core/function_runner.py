"""
Function runner for executing test functions.

Executes individual test functions with standardized parameter validation,
timeout handling, and result aggregation.

Function Runner - 执行单个测试函数
支持参数校验、超时处理、结果汇总
"""

import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
import inspect

from .status_codes import StatusCode


@dataclass
class FunctionResult:
    """
    Result of a function execution.

    函数执行结果
    """

    name: str                        # Function name
    code: int                        # Status code
    message: str                     # Human-readable message
    duration: float                  # Execution time in seconds
    details: Optional[Dict[str, Any]] = None  # Additional details

    @property
    def success(self) -> bool:
        """Check if function executed successfully."""
        return self.code == StatusCode.SUCCESS

    @property
    def is_retryable(self) -> bool:
        """Check if the error is retryable."""
        return StatusCode.is_retryable(self.code)


class FunctionRunner:
    """
    Runner for executing test functions.

    测试函数执行器

    Features:
    - Parameter validation
    - Timeout handling
    - Status code mapping
    - Result aggregation

    功能：
    - 参数校验
    - 超时处理
    - 状态码映射
    - 结果汇总
    """

    def __init__(self, functions_dir: str = "functions"):
        """
        Initialize the function runner.

        Args:
            functions_dir: Base directory for test functions
        """
        self.functions_dir = Path(functions_dir)
        self._loaded_functions: Dict[str, Callable] = {}

    def _find_function_script(self, name: str) -> Optional[Path]:
        """Find python script file for function name."""
        for module_dir in self.functions_dir.iterdir():
            if not module_dir.is_dir():
                continue
            candidate = module_dir / f"{name}.py"
            if candidate.exists():
                return candidate
        return None

    def _supports_cli_execution(self, script_path: Path) -> bool:
        """Check whether a function script exposes argparse-based CLI entrypoint."""
        try:
            content = script_path.read_text(encoding="utf-8")
        except Exception:
            return False
        return "if __name__ == \"__main__\"" in content and "argparse.ArgumentParser" in content

    def _params_to_cli_args(self, params: Dict[str, Any]) -> List[str]:
        """Convert dict params to long-form CLI args.

        Example:
            {"ip": "1.1.1.1", "enable": True} -> ["--ip", "1.1.1.1", "--enable"]
        """
        args: List[str] = []
        for key, value in params.items():
            normalized_key = key.replace("_", "-")
            option = f"--{normalized_key}"

            if isinstance(value, bool):
                if value:
                    args.append(option)
                continue

            if value is None:
                continue

            if isinstance(value, list):
                for item in value:
                    args.extend([option, str(item)])
                continue

            args.extend([option, str(value)])
        return args

    def _run_via_cli(
        self,
        script_path: Path,
        name: str,
        params: Dict[str, Any],
        timeout: Optional[int],
        start_time: float,
    ) -> FunctionResult:
        """Run function script as CLI process."""
        cli_args = self._params_to_cli_args(params)
        command = [sys.executable, str(script_path), *cli_args]

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return FunctionResult(
                name=name,
                code=StatusCode.TIMEOUT,
                message=f"Function '{name}' timed out after {timeout}s",
                duration=time.time() - start_time,
                details={"mode": "cli", "args": cli_args},
            )
        except Exception as e:
            return FunctionResult(
                name=name,
                code=StatusCode.FAILED,
                message=f"Function '{name}' failed: {e}",
                duration=time.time() - start_time,
                details={"mode": "cli", "args": cli_args},
            )

        return_code = completed.returncode
        normalized_code = return_code - 256 if return_code > 127 else return_code
        output_message = (completed.stdout or completed.stderr or "").strip().splitlines()
        message = output_message[-1] if output_message else (
            "Success" if normalized_code == 0 else f"CLI exited with code {normalized_code}"
        )

        return FunctionResult(
            name=name,
            code=normalized_code,
            message=message,
            duration=time.time() - start_time,
            details={
                "mode": "cli",
                "args": cli_args,
                "stdout": (completed.stdout or "").strip(),
                "stderr": (completed.stderr or "").strip(),
            },
        )

    def _run_via_import(
        self,
        func: Callable,
        name: str,
        params: Dict[str, Any],
        timeout: Optional[int],
        start_time: float,
    ) -> FunctionResult:
        """Run function by python import call (compatibility fallback)."""
        try:
            sig = inspect.signature(func)
            required_params = {
                p_name
                for p_name, param in sig.parameters.items()
                if param.default is inspect.Parameter.empty
                and p_name != "kwargs"
            }

            missing = required_params - set(params.keys())
            if missing:
                return FunctionResult(
                    name=name,
                    code=StatusCode.MISSING_PARAM,
                    message=f"Missing required parameters: {missing}",
                    duration=time.time() - start_time,
                )
        except Exception:
            pass

        try:
            if timeout:
                result = self._run_with_timeout(func, params, timeout)
            else:
                result = func(**params)

            if isinstance(result, int):
                code = result
                message = StatusCode(code).description
            elif isinstance(result, dict):
                code = result.get("code", StatusCode.SUCCESS)
                message = result.get("message", StatusCode(code).description)
            else:
                code = StatusCode.SUCCESS
                message = "Success"

            return FunctionResult(
                name=name,
                code=code,
                message=message,
                duration=time.time() - start_time,
                details=result if isinstance(result, dict) else None,
            )

        except subprocess.TimeoutExpired:
            return FunctionResult(
                name=name,
                code=StatusCode.TIMEOUT,
                message=f"Function '{name}' timed out after {timeout}s",
                duration=time.time() - start_time,
            )
        except Exception as e:
            return FunctionResult(
                name=name,
                code=StatusCode.FAILED,
                message=f"Function '{name}' failed: {e}",
                duration=time.time() - start_time,
            )

    def load_function(self, name: str) -> Optional[Callable]:
        """
        Load a test function by name.

        加载测试函数

        Args:
            name: Function name (e.g., "test_eth")

        Returns:
            Function callable or None if not found
        """
        if name in self._loaded_functions:
            return self._loaded_functions[name]

        # Try to find and import the function
        # Search in all subdirectories
        for module_dir in self.functions_dir.iterdir():
            if not module_dir.is_dir():
                continue

            func_file = module_dir / f"{name}.py"
            if func_file.exists():
                try:
                    # Import the module
                    import sys
                    if str(self.functions_dir.parent) not in sys.path:
                        sys.path.insert(0, str(self.functions_dir.parent))

                    module_name = f"functions.{module_dir.name}.{name}"
                    module = __import__(module_name, fromlist=[name])

                    # Get the main function (should have same name as file)
                    func = getattr(module, name, None)
                    if func and callable(func):
                        self._loaded_functions[name] = func
                        return func

                except Exception as e:
                    print(f"Error loading function {name}: {e}")
                    return None

        return None

    def run(
        self,
        name: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> FunctionResult:
        """
        Run a test function.

        执行测试函数

        Args:
            name: Function name
            params: Function parameters
            timeout: Timeout in seconds

        Returns:
            FunctionResult with execution details
        """
        start_time = time.time()
        params = params or {}

        script_path = self._find_function_script(name)
        if script_path and self._supports_cli_execution(script_path):
            return self._run_via_cli(script_path, name, params, timeout, start_time)

        # Load the function
        func = self.load_function(name)
        if not func:
            return FunctionResult(
                name=name,
                code=StatusCode.ENV_MISSING,
                message=f"Function '{name}' not found",
                duration=time.time() - start_time,
            )

        return self._run_via_import(func, name, params, timeout, start_time)

    def _run_with_timeout(
        self,
        func: Callable,
        params: Dict[str, Any],
        timeout: int,
    ) -> Any:
        """
        Run a function with timeout.

        带超时执行函数
        """
        # For now, simple timeout implementation
        # Can be enhanced with process-based timeout
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError(f"Function timed out after {timeout}s")

        # Set the signal handler
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)

        try:
            result = func(**params)
            return result
        finally:
            # Cancel the alarm and restore old handler
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    def get_help(self, name: str) -> Optional[str]:
        """
        Get help text for a function.

        获取函数帮助文本

        Args:
            name: Function name

        Returns:
            Help text or None if not found
        """
        func = self.load_function(name)
        if not func:
            return None

        doc = inspect.getdoc(func)
        if not doc:
            return None

        return doc

    def list_functions(self) -> List[str]:
        """
        List all available test functions.

        列出所有可用的测试函数

        Returns:
            List of function names
        """
        functions = []

        if not self.functions_dir.exists():
            return functions

        for module_dir in self.functions_dir.iterdir():
            if not module_dir.is_dir():
                continue

            for func_file in module_dir.glob("test_*.py"):
                func_name = func_file.stem
                functions.append(func_name)

        return sorted(functions)
