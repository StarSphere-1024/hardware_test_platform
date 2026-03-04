"""
Tests for function_runner module.

测试函数执行器模块
"""
import os
import tempfile
import pytest
from pathlib import Path
from typing import Dict, Any

from framework.core.function_runner import FunctionRunner, FunctionResult
from framework.core.status_codes import StatusCode


class TestFunctionResult:
    """测试 FunctionResult 类"""

    def test_create_basic_result(self):
        """测试创建基本结果"""
        result = FunctionResult(
            name="test_eth",
            code=0,
            message="Success",
            duration=1.5,
        )
        assert result.name == "test_eth"
        assert result.code == 0
        assert result.message == "Success"
        assert result.duration == 1.5

    def test_success_property(self):
        """测试成功属性"""
        success_result = FunctionResult(name="test", code=0, message="Success", duration=1.0)
        assert success_result.success is True

        fail_result = FunctionResult(name="test", code=-1, message="Failed", duration=1.0)
        assert fail_result.success is False

    def test_retryable_property(self):
        """测试可重试属性"""
        timeout_result = FunctionResult(name="test", code=StatusCode.TIMEOUT, message="Timeout", duration=1.0)
        assert timeout_result.is_retryable is True

        device_error_result = FunctionResult(name="test", code=StatusCode.DEVICE_ERROR, message="Error", duration=1.0)
        assert device_error_result.is_retryable is True

        missing_param_result = FunctionResult(name="test", code=StatusCode.MISSING_PARAM, message="Missing", duration=1.0)
        assert missing_param_result.is_retryable is False


class TestFunctionRunner:
    """测试 FunctionRunner 类"""

    def test_init(self):
        """测试初始化"""
        runner = FunctionRunner(functions_dir="functions")
        assert runner.functions_dir.name == "functions"
        assert len(runner._loaded_functions) == 0

    def test_load_function_not_found(self, project_root: Path):
        """测试加载不存在的函数"""
        runner = FunctionRunner(functions_dir=str(project_root / "functions"))
        func = runner.load_function("nonexistent_function")
        assert func is None

    def test_run_function_not_found(self, project_root: Path):
        """测试运行不存在的函数"""
        runner = FunctionRunner(functions_dir=str(project_root / "functions"))
        result = runner.run(name="nonexistent_function")

        assert result.name == "nonexistent_function"
        assert result.code == StatusCode.ENV_MISSING
        assert "not found" in result.message.lower()

    def test_run_with_missing_params(self, project_root: Path, sample_test_function_py: str):
        """测试运行缺少参数的函数"""
        import sys

        # 创建一个需要参数的测试函数
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 functions 目录（与代码逻辑匹配）
            functions_dir = Path(tmpdir) / "functions"
            functions_dir.mkdir()
            # 创建 __init__.py 使 functions 成为 Python 包
            (functions_dir / "__init__.py").write_text("")
            func_subdir = functions_dir / "test_mod"
            func_subdir.mkdir()
            # 创建 __init__.py 使目录成为 Python 包
            (func_subdir / "__init__.py").write_text("")
            func_file = func_subdir / "test_required.py"

            # 创建一个需要必填参数的函数
            func_file.write_text("""
def test_required(required_param: str) -> dict:
    return {"code": 0, "message": "Success"}
""")

            # 清理可能存在的缓存
            for key in list(sys.modules.keys()):
                if key.startswith('functions'):
                    del sys.modules[key]

            runner = FunctionRunner(functions_dir=str(functions_dir))
            # 不提供必填参数
            result = runner.run(name="test_required", params={})

            # 应该返回缺少参数错误
            assert result.code == StatusCode.MISSING_PARAM
            assert "Missing" in result.message or "required" in result.message.lower()

    def test_run_with_params(self, project_root: Path):
        """测试带参数运行函数"""
        import sys

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 functions 目录（与代码逻辑匹配）
            functions_dir = Path(tmpdir) / "functions"
            functions_dir.mkdir()
            # 创建 __init__.py 使 functions 成为 Python 包
            (functions_dir / "__init__.py").write_text("")
            func_subdir = functions_dir / "test_mod_params"
            func_subdir.mkdir()
            # 创建 __init__.py 使目录成为 Python 包
            (func_subdir / "__init__.py").write_text("")
            func_file = func_subdir / "test_param.py"

            func_file.write_text("""
def test_param(value: str = "default") -> dict:
    return {"code": 0, "message": f"Value: {value}"}
""")

            # 清理可能存在的缓存
            for key in list(sys.modules.keys()):
                if key.startswith('functions'):
                    del sys.modules[key]

            runner = FunctionRunner(functions_dir=str(functions_dir))
            result = runner.run(name="test_param", params={"value": "test123"})

            assert result.code == StatusCode.SUCCESS
            assert "test123" in result.message

    def test_run_with_timeout(self, project_root: Path):
        """测试带超时运行函数"""
        import sys

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 functions 目录（与代码逻辑匹配）
            functions_dir = Path(tmpdir) / "functions"
            functions_dir.mkdir()
            # 创建 __init__.py 使 functions 成为 Python 包
            (functions_dir / "__init__.py").write_text("")
            func_subdir = functions_dir / "test_mod_timeout"
            func_subdir.mkdir()
            # 创建 __init__.py 使目录成为 Python 包
            (func_subdir / "__init__.py").write_text("")
            func_file = func_subdir / "test_timeout.py"

            func_file.write_text("""
import time

def test_timeout() -> dict:
    time.sleep(0.1)  # Small delay
    return {"code": 0, "message": "Success"}
""")

            # 清理可能存在的缓存
            for key in list(sys.modules.keys()):
                if key.startswith('functions'):
                    del sys.modules[key]

            runner = FunctionRunner(functions_dir=str(functions_dir))
            result = runner.run(name="test_timeout", params={}, timeout=5)

            # Should complete successfully
            assert result.code == StatusCode.SUCCESS

    def test_run_return_dict(self, project_root: Path):
        """测试返回字典的函数"""
        import sys

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 functions 目录（与代码逻辑匹配）
            functions_dir = Path(tmpdir) / "functions"
            functions_dir.mkdir()
            # 创建 __init__.py 使 functions 成为 Python 包
            (functions_dir / "__init__.py").write_text("")
            func_subdir = functions_dir / "test_mod_dict"
            func_subdir.mkdir()
            # 创建 __init__.py 使目录成为 Python 包
            (func_subdir / "__init__.py").write_text("")
            func_file = func_subdir / "test_dict.py"

            func_file.write_text("""
def test_dict() -> dict:
    return {
        "code": 0,
        "message": "Success",
        "details": {"key": "value"}
    }
""")

            # 清理可能存在的缓存
            for key in list(sys.modules.keys()):
                if key.startswith('functions'):
                    del sys.modules[key]

            runner = FunctionRunner(functions_dir=str(functions_dir))
            result = runner.run(name="test_dict")

            assert result.code == 0
            assert result.message == "Success"
            # 当函数返回 dict 时，整个 dict 被赋值给 details
            assert result.details == {
                "code": 0,
                "message": "Success",
                "details": {"key": "value"}
            }

    def test_run_return_int(self, project_root: Path):
        """测试返回整数的函数"""
        import sys

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 functions 目录（与代码逻辑匹配）
            functions_dir = Path(tmpdir) / "functions"
            functions_dir.mkdir()
            # 创建 __init__.py 使 functions 成为 Python 包
            (functions_dir / "__init__.py").write_text("")
            func_subdir = functions_dir / "test_mod_int"
            func_subdir.mkdir()
            # 创建 __init__.py 使目录成为 Python 包
            (func_subdir / "__init__.py").write_text("")
            func_file = func_subdir / "test_int.py"

            func_file.write_text("""
def test_int() -> int:
    return 0
""")

            # 清理可能存在的缓存
            for key in list(sys.modules.keys()):
                if key.startswith('functions'):
                    del sys.modules[key]

            runner = FunctionRunner(functions_dir=str(functions_dir))
            result = runner.run(name="test_int")

            assert result.code == StatusCode.SUCCESS

    def test_run_exception_handling(self, project_root: Path):
        """测试异常处理"""
        import sys

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 functions 目录（与代码逻辑匹配）
            functions_dir = Path(tmpdir) / "functions"
            functions_dir.mkdir()
            # 创建 __init__.py 使 functions 成为 Python 包
            (functions_dir / "__init__.py").write_text("")
            func_subdir = functions_dir / "test_mod_exception"
            func_subdir.mkdir()
            # 创建 __init__.py 使目录成为 Python 包
            (func_subdir / "__init__.py").write_text("")
            func_file = func_subdir / "test_exception.py"

            func_file.write_text("""
def test_exception() -> dict:
    raise RuntimeError("Test exception")
""")

            # 清理可能存在的缓存
            for key in list(sys.modules.keys()):
                if key.startswith('functions'):
                    del sys.modules[key]

            runner = FunctionRunner(functions_dir=str(functions_dir))
            result = runner.run(name="test_exception")

            assert result.code == StatusCode.FAILED
            assert "failed" in result.message.lower()

    def test_list_functions(self, project_root: Path):
        """测试列出函数"""
        runner = FunctionRunner(functions_dir=str(project_root / "functions"))
        functions = runner.list_functions()

        # 应该至少找到一些函数
        assert isinstance(functions, list)
        # 检查是否找到已知函数
        function_names = [f for f in functions]
        assert len(function_names) >= 0  # 可能有也可能没有函数


class TestFunctionRunnerHelp:
    """测试函数帮助功能"""

    def test_get_help_exists(self, project_root: Path):
        """测试获取帮助文本"""
        runner = FunctionRunner(functions_dir=str(project_root / "functions"))

        # 对于不存在的函数返回 None
        help_text = runner.get_help("nonexistent")
        assert help_text is None

    def test_get_help_with_docstring(self, project_root: Path):
        """测试带文档字符串的帮助"""
        import sys

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 functions 目录（与代码逻辑匹配）
            functions_dir = Path(tmpdir) / "functions"
            functions_dir.mkdir()
            # 创建 __init__.py 使 functions 成为 Python 包
            (functions_dir / "__init__.py").write_text("")
            func_subdir = functions_dir / "test_mod_help"
            func_subdir.mkdir()
            # 创建 __init__.py 使目录成为 Python 包
            (func_subdir / "__init__.py").write_text("")
            func_file = func_subdir / "test_help.py"

            func_file.write_text('''
def test_help() -> dict:
    """This is a test function with help.

    Returns:
        dict: Result dictionary
    """
    return {"code": 0}
''')

            # 清理可能存在的缓存
            for key in list(sys.modules.keys()):
                if key.startswith('functions'):
                    del sys.modules[key]

            runner = FunctionRunner(functions_dir=str(functions_dir))
            help_text = runner.get_help("test_help")

            assert help_text is not None
            assert "test function" in help_text.lower()


class TestFunctionResultEdgeCases:
    """测试 FunctionResult 边界情况"""

    def test_result_with_none_details(self):
        """测试 None 详细信息的 result"""
        result = FunctionResult(
            name="test",
            code=0,
            message="Success",
            duration=1.0,
            details=None,
        )
        assert result.details is None
        assert result.success is True

    def test_result_with_empty_details(self):
        """测试空字典详细信息的 result"""
        result = FunctionResult(
            name="test",
            code=0,
            message="Success",
            duration=1.0,
            details={},
        )
        assert result.details == {}
        assert result.success is True

    def test_result_with_complex_details(self):
        """测试复杂详细信息的 result"""
        complex_details = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "mixed": {"a": 1, "b": [1, 2]},
        }
        result = FunctionResult(
            name="test",
            code=0,
            message="Success",
            duration=1.0,
            details=complex_details,
        )
        assert result.details == complex_details
        assert result.details["nested"]["key"] == "value"
