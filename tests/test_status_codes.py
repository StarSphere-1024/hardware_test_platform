"""
Tests for status_codes module.

测试状态码模块
"""
import pytest
from framework.core.status_codes import (
    StatusCode,
    SUCCESS,
    TIMEOUT,
    MISSING_PARAM,
    FAILED,
    ENV_MISSING,
    DEVICE_NOT_FOUND,
    DEVICE_ERROR,
    FILE_NOT_FOUND,
)


class TestStatusCodeEnum:
    """测试状态码枚举类"""

    def test_success_code_value(self):
        """测试成功状态码值"""
        assert StatusCode.SUCCESS == 0
        assert SUCCESS == 0

    def test_timeout_code_value(self):
        """测试超时状态码值"""
        assert StatusCode.TIMEOUT == 1
        assert TIMEOUT == 1

    def test_missing_param_code_value(self):
        """测试缺少参数状态码值"""
        assert StatusCode.MISSING_PARAM == 2
        assert MISSING_PARAM == 2

    def test_failed_code_value(self):
        """测试失败状态码值"""
        assert StatusCode.FAILED == -1
        assert FAILED == -1

    def test_env_missing_code_value(self):
        """测试环境缺失状态码值"""
        assert StatusCode.ENV_MISSING == -2
        assert ENV_MISSING == -2

    def test_device_not_found_code_value(self):
        """测试设备未找到状态码值"""
        assert StatusCode.DEVICE_NOT_FOUND == -101
        assert DEVICE_NOT_FOUND == -101

    def test_device_error_code_value(self):
        """测试设备错误状态码值"""
        assert StatusCode.DEVICE_ERROR == -102
        assert DEVICE_ERROR == -102

    def test_file_not_found_code_value(self):
        """测试文件未找到状态码值"""
        assert StatusCode.FILE_NOT_FOUND == -103
        assert FILE_NOT_FOUND == -103


class TestStatusCodeMethods:
    """测试状态码方法"""

    def test_is_success_true(self):
        """测试 is_success 返回 True 的情况"""
        assert StatusCode.is_success(0) is True
        assert StatusCode.is_success(StatusCode.SUCCESS) is True

    def test_is_success_false(self):
        """测试 is_success 返回 False 的情况"""
        assert StatusCode.is_success(1) is False
        assert StatusCode.is_success(-1) is False
        assert StatusCode.is_success(-101) is False

    def test_is_error_true(self):
        """测试 is_error 返回 True 的情况"""
        assert StatusCode.is_error(1) is True
        assert StatusCode.is_error(-1) is True
        assert StatusCode.is_error(-101) is True

    def test_is_error_false(self):
        """测试 is_error 返回 False 的情况"""
        assert StatusCode.is_error(0) is False
        assert StatusCode.is_error(StatusCode.SUCCESS) is False

    def test_is_retryable_timeout(self):
        """测试超时是否可重试"""
        assert StatusCode.is_retryable(StatusCode.TIMEOUT) is True

    def test_is_retryable_device_error(self):
        """测试设备错误是否可重试"""
        assert StatusCode.is_retryable(StatusCode.DEVICE_ERROR) is True

    def test_is_retryable_not_retryable(self):
        """测试不可重试的错误"""
        assert StatusCode.is_retryable(StatusCode.MISSING_PARAM) is False
        assert StatusCode.is_retryable(StatusCode.DEVICE_NOT_FOUND) is False
        assert StatusCode.is_retryable(StatusCode.SUCCESS) is False

    def test_description_en(self):
        """测试英文描述"""
        assert "Success" in StatusCode.SUCCESS.description
        assert "Timeout" in StatusCode.TIMEOUT.description
        assert "Missing" in StatusCode.MISSING_PARAM.description

    def test_description_zh(self):
        """测试中文描述"""
        assert "成功" in StatusCode.SUCCESS.description_zh
        assert "超时" in StatusCode.TIMEOUT.description_zh
        assert "缺少" in StatusCode.MISSING_PARAM.description_zh

    def test_unknown_status_code(self):
        """测试未知状态码的描述"""
        # 注意：StatusCode 枚举类对于无效值会抛出 ValueError
        # 这是预期行为，因为我们使用了 IntEnum
        import pytest
        with pytest.raises(ValueError):
            StatusCode(999)
