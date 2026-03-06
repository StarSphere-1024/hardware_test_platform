"""
Case runner for executing test cases.

A Case is a collection of test functions for a specific hardware module.
This runner loads case configurations from JSON files and executes the
defined functions in order.

Case Runner - 执行测试用例
从 JSON 配置加载并按顺序执行测试函数
"""

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .status_codes import StatusCode
from .function_runner import FunctionRunner, FunctionResult
from .result_store import ResultStore, TestResult
from framework.platform.board_profile import load_board_profile
import os
import shutil


@dataclass
class CaseResult:
    """
    Result of a case execution.

    用例执行结果
    """

    case_name: str
    module: str
    status: str  # "pass", "fail"
    duration: float
    function_results: List[FunctionResult]
    retry_count: int = 0
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.status == "pass"

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.function_results if r.success)

    @property
    def fail_count(self) -> int:
        return len(self.function_results) - self.pass_count


class CaseRunner:
    """
    Runner for executing test cases.

    测试用例执行器

    A Case consists of:
    - Case name and module
    - List of functions to execute
    - Execution mode (sequential/parallel)
    - Timeout and retry settings

    一个用例包括：
    - 用例名称和模块
    - 要执行的函数列表
    - 执行模式（串行/并行）
    - 超时和重试设置
    """

    def __init__(
        self,
        functions_dir: str = "functions",
        cases_dir: str = "cases",
    ):
        """
        Initialize the case runner.

        Args:
            functions_dir: Directory containing test functions
            cases_dir: Directory containing case configurations
        """
        self.functions_dir = Path(functions_dir)
        self.cases_dir = Path(cases_dir)
        self.function_runner = FunctionRunner(functions_dir)
        self.result_store = ResultStore()

    def load_case(self, case_path: str) -> Optional[Dict[str, Any]]:
        """
        Load a case configuration from JSON file.

        从 JSON 文件加载用例配置

        Args:
            case_path: Path to case JSON file or case name

        Returns:
            Case configuration dictionary or None
        """
        path = Path(case_path)

        # If just a name, try to find in cases_dir
        if not path.exists():
            if not path.suffix:
                path = self.cases_dir / f"{path}_case.json"
            else:
                path = self.cases_dir / path

        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                case_config = json.load(f)
                if isinstance(case_config, dict):
                    case_config["__case_id"] = path.stem
                return case_config
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading case {path}: {e}")
            return None


    def _is_interface_available(self, interface_type: str, candidate: str) -> bool:
        """Check whether an interface candidate is available on current OS."""
        if not candidate:
            return False

        if interface_type in {"eth", "wifi", "ble"}:
            return os.path.exists(f"/sys/class/net/{candidate}")

        if candidate.startswith("/dev/") or candidate.startswith("/sys/"):
            return os.path.exists(candidate)

        return os.path.exists(candidate)

    def _bind_interfaces(
        self,
        required_interfaces: Dict[str, Any],
        profile_interfaces: Dict[str, Any],
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Resolve required interfaces from board profile candidates."""
        resolved: Dict[str, Any] = {}

        for interface_type, request in required_interfaces.items():
            request = request if isinstance(request, dict) else {}
            select_mode = request.get("select", "auto")
            is_required = bool(request.get("required", False))

            if select_mode != "auto":
                selected = request.get("value")
                if selected:
                    resolved[interface_type] = selected
                    continue
                if is_required:
                    return (
                        False,
                        f"Interface '{interface_type}' requires explicit value for select={select_mode}",
                        resolved,
                    )
                continue

            candidates = profile_interfaces.get(interface_type, [])
            if not isinstance(candidates, list):
                candidates = []

            selected_candidate: Optional[str] = None
            for raw_candidate in candidates:
                candidate = str(raw_candidate)
                if self._is_interface_available(interface_type, candidate):
                    selected_candidate = candidate
                    break

            if selected_candidate is not None:
                resolved[interface_type] = selected_candidate
            elif is_required:
                return (
                    False,
                    f"No available interfaces found for type '{interface_type}'",
                    resolved,
                )

        return True, "", resolved

    def _render_templates(self, value: Any, resolved_context: Dict[str, Any]) -> Any:
        """Render ${interfaces.xxx} placeholders recursively."""
        if isinstance(value, str):
            pattern = re.compile(r"\$\{interfaces\.([A-Za-z0-9_\-]+)\}")

            def _replace(match: re.Match[str]) -> str:
                key = match.group(1)
                return str(resolved_context.get(key, match.group(0)))

            return pattern.sub(_replace, value)

        if isinstance(value, dict):
            return {k: self._render_templates(v, resolved_context) for k, v in value.items()}

        if isinstance(value, list):
            return [self._render_templates(item, resolved_context) for item in value]

        return value

    def _preflight(self, case_config: Dict[str, Any], profile: Dict[str, Any]) -> tuple[bool, str, Dict[str, Any]]:
        """
        Execute preflight checks and interface bindings.
        Returns: (success, error_msg, resolved_context)
        """
        case_name = str(case_config.get("case_name", ""))
        case_id = str(case_config.get("__case_id", ""))
        resolved_context: Dict[str, Any] = {}

        # 1. Check supported_cases
        supported_cases = profile.get("supported_cases", [])
        if isinstance(supported_cases, list) and supported_cases:
            supported = {str(item) for item in supported_cases}
            if case_name not in supported and case_id not in supported:
                return False, f"Case '{case_name or case_id}' is not in supported_cases", resolved_context

        # 2. Tools required
        tools = profile.get("tools_required", [])
        for tool in tools if isinstance(tools, list) else []:
            if not shutil.which(tool):
                return False, f"Required tool '{tool}' not found in system path", resolved_context

        # 3. Interface binding
        required_interfaces = case_config.get("required_interfaces", {})
        if not isinstance(required_interfaces, dict):
            required_interfaces = {}

        profile_interfaces = profile.get("interfaces", {})
        if not isinstance(profile_interfaces, dict):
            profile_interfaces = {}

        bind_ok, bind_msg, resolved = self._bind_interfaces(required_interfaces, profile_interfaces)
        if not bind_ok:
            return False, bind_msg, resolved

        return True, "", resolved

    def _execute_functions_once(
        self,
        functions: List[Dict[str, Any]],
        timeout: int,
        stop_on_failure: bool,
        resolved_context: Dict[str, Any],
    ) -> List[FunctionResult]:
        """Execute all enabled functions once with rendered params."""
        results: List[FunctionResult] = []

        for func_config in functions:
            func_name = func_config.get("name")
            if not func_name or not func_config.get("enabled", True):
                continue

            raw_params = func_config.get("params", {})
            params = raw_params.copy() if isinstance(raw_params, dict) else {}
            rendered_params = self._render_templates(params, resolved_context)

            result = self.function_runner.run(
                name=func_name,
                params=rendered_params,
                timeout=timeout,
            )
            results.append(result)

            if not result.success and stop_on_failure:
                break

        return results

    def run(
        self,
        case_config: Dict[str, Any],
        retry: Optional[int] = None,
        retry_interval: Optional[int] = None,
    ) -> CaseResult:
        """
        Run a test case.

        执行测试用例

        Args:
            case_config: Case configuration dictionary
            retry: Number of retries on failure
            retry_interval: Interval between retries (seconds)

        Returns:
            CaseResult with execution details
        """
        case_name = case_config.get("case_name", "unknown")
        module = case_config.get("module", "unknown")
        functions = case_config.get("functions", [])
        timeout = case_config.get("timeout", 60)
        _execution_mode = case_config.get("execution", "sequential")
        effective_retry = case_config.get("retry", 0) if retry is None else retry
        effective_retry_interval = (
            case_config.get("retry_interval", 5) if retry_interval is None else retry_interval
        )
        stop_on_failure = bool(case_config.get("stop_on_failure", False))

        start_time = time.time()
        function_results: List[FunctionResult] = []
        last_error: Optional[str] = None
        retry_count = 0

        # Execute function logic
        board_profile = load_board_profile() # auto detect current profile
        
        precheck = case_config.get("precheck", False)
        resolved_context = {}
        if precheck:
            success, msg, resolved_context = self._preflight(case_config, board_profile)
            if not success:
                self.result_store.write_failure(
                    module=module,
                    case_name=case_name,
                    duration=0.0,
                    error=f"Preflight failed: {msg}",
                    retry_count=0,
                    resolved_context=resolved_context
                )
                return CaseResult(case_name, module, "fail", 0.0, [], 0, msg)
                
        # Write running status
        self.result_store.write_running_status(module, case_name)

        max_attempts = max(int(effective_retry), 0) + 1
        for attempt in range(max_attempts):
            function_results = self._execute_functions_once(
                functions=functions,
                timeout=timeout,
                stop_on_failure=stop_on_failure,
                resolved_context=resolved_context,
            )

            all_passed = all(result.success for result in function_results)
            if all_passed:
                break

            failed_results = [result for result in function_results if not result.success]
            last_error = failed_results[-1].message if failed_results else "Unknown error"

            if attempt < max_attempts - 1:
                retry_count += 1
                time.sleep(max(int(effective_retry_interval), 0))

        duration = time.time() - start_time

        # Determine overall status
        all_passed = all(r.success for r in function_results)

        # Write final result
        if all_passed:
            final_status = "pass"
            self.result_store.write_success(
                module=module,
                case_name=case_name,
                duration=duration,
                details={
                    "pass_count": sum(1 for r in function_results if r.success),
                    "fail_count": sum(1 for r in function_results if not r.success),
                },
                resolved_context=resolved_context
            )
        else:
            final_status = "fail"
            failed_funcs = [fr for fr in function_results if not fr.success]
            last_error = failed_funcs[-1].message if failed_funcs else "Unknown error"

            self.result_store.write_failure(
                module=module,
                case_name=case_name,
                duration=duration,
                error=last_error,
                retry_count=retry_count,
                resolved_context=resolved_context
            )

        return CaseResult(
            case_name=case_name,
            module=module,
            status=final_status,
            duration=duration,
            function_results=function_results,
            retry_count=retry_count,
            error=last_error,
        )

    def run_from_file(
        self,
        case_path: str,
        retry: Optional[int] = None,
        retry_interval: Optional[int] = None,
    ) -> Optional[CaseResult]:
        """
        Run a case from a JSON file.

        从 JSON 文件运行用例

        Args:
            case_path: Path to case JSON file
            retry: Number of retries
            retry_interval: Retry interval

        Returns:
            CaseResult or None if case not found
        """
        case_config = self.load_case(case_path)
        if not case_config:
            return None

        return self.run(case_config, retry, retry_interval)
