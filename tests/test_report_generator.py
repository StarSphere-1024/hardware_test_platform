"""
Tests for report_generator module.

测试报告生成器模块
"""
import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock

from framework.logging.report_generator import (
    ReportGenerator,
    ReportArtifact,
    status_code_descriptions,
)


class TestReportArtifact:
    """测试 ReportArtifact 类"""

    def test_create_artifact(self, temp_dir: Path):
        """测试创建报告产物"""
        text_path = temp_dir / "test.report"
        json_path = temp_dir / "test.report.json"

        artifact = ReportArtifact(text_report_path=text_path, json_report_path=json_path)

        assert artifact.text_report_path == text_path
        assert artifact.json_report_path == json_path


class TestReportGeneratorInit:
    """测试 ReportGenerator 初始化"""

    def test_init_creates_dir(self, temp_dir: Path):
        """测试初始化创建目录"""
        reports_dir = temp_dir / "reports"
        generator = ReportGenerator(reports_dir=str(reports_dir))

        assert generator.reports_dir.exists()
        assert generator.reports_dir.is_dir()


class TestReportGeneratorSanitize:
    """测试文件名清理"""

    def test_sanitize_normal(self):
        """测试清理正常字符串"""
        result = ReportGenerator._sanitize_filename_part("CM4")
        assert result == "CM4"

    def test_sanitize_with_special_chars(self):
        """测试清理带特殊字符的字符串"""
        result = ReportGenerator._sanitize_filename_part("CM4 测试")
        assert "CM4" in result
        assert "测试" not in result  # 中文字符被替换

    def test_sanitize_empty(self):
        """测试清理空字符串"""
        result = ReportGenerator._sanitize_filename_part("")
        assert result == "UNKNOWN"

    def test_sanitize_whitespace(self):
        """测试清理空白字符"""
        result = ReportGenerator._sanitize_filename_part("  test  ")
        assert result == "test"

    def test_sanitize_truncate(self):
        """测试截断长字符串"""
        long_string = "a" * 100
        result = ReportGenerator._sanitize_filename_part(long_string)
        assert len(result) <= 64


class TestReportGeneratorAtomicWrite:
    """测试原子写入"""

    def test_atomic_write_creates_file(self, temp_dir: Path):
        """测试原子写入创建文件"""
        file_path = temp_dir / "test.txt"
        content = "test content"

        ReportGenerator._atomic_write(file_path, content)

        assert file_path.exists()
        assert file_path.read_text() == content

    def test_atomic_write_no_temp_left(self, temp_dir: Path):
        """测试原子写入不留临时文件"""
        file_path = temp_dir / "test.txt"
        content = "test content"

        ReportGenerator._atomic_write(file_path, content)

        temp_files = list(temp_dir.glob("*.tmp"))
        assert len(temp_files) == 0


class TestReportGeneratorGenerate:
    """测试报告生成"""

    def test_generate_creates_files(self, temp_dir: Path):
        """测试生成创建文件"""
        reports_dir = temp_dir / "reports"
        generator = ReportGenerator(reports_dir=str(reports_dir))

        # 创建 mock fixture result
        mock_result = MagicMock()
        mock_result.fixture_name = "test_fixture"
        mock_result.status = "pass"
        mock_result.duration = 10.5
        mock_result.loop_count = 1
        mock_result.total_pass = 2
        mock_result.total_fail = 0
        mock_result.case_results = []

        mock_config = {
            "description": "Test fixture",
            "execution": "sequential",
            "stop_on_failure": False,
            "retry": 0,
            "retry_interval": 5,
            "loop": False,
            "loop_count": 1,
            "loop_interval": 0,
        }

        mock_global_config = {
            "product": {
                "sku": "TEST",
                "stage": "EVT",
            }
        }

        artifact = generator.generate(
            fixture_result=mock_result,
            fixture_config=mock_config,
            global_config=mock_global_config,
            sn="SN12345",
        )

        assert artifact.text_report_path.exists()
        assert artifact.json_report_path.exists()

    def test_generate_json_valid_structure(self, temp_dir: Path):
        """测试生成 JSON 有效结构"""
        reports_dir = temp_dir / "reports"
        generator = ReportGenerator(reports_dir=str(reports_dir))

        mock_result = MagicMock()
        mock_result.fixture_name = "test_fixture"
        mock_result.status = "pass"
        mock_result.duration = 10.5
        mock_result.loop_count = 1
        mock_result.total_pass = 2
        mock_result.total_fail = 0
        mock_result.case_results = []

        mock_config = {
            "description": "Test fixture",
            "execution": "sequential",
        }

        mock_global_config = {
            "product": {"sku": "TEST", "stage": "EVT"}
        }

        artifact = generator.generate(
            fixture_result=mock_result,
            fixture_config=mock_config,
            global_config=mock_global_config,
            sn="SN12345",
        )

        # 验证 JSON 结构
        with open(artifact.json_report_path, "r") as f:
            data = json.load(f)

        assert "metadata" in data
        assert "fixture" in data
        assert "summary" in data
        assert "cases" in data
        assert data["metadata"]["schema_version"] == "1.0"

    def test_generate_text_report_readable(self, temp_dir: Path):
        """测试生成文本报告可读"""
        reports_dir = temp_dir / "reports"
        generator = ReportGenerator(reports_dir=str(reports_dir))

        mock_result = MagicMock()
        mock_result.fixture_name = "test_fixture"
        mock_result.status = "pass"
        mock_result.duration = 10.5
        mock_result.loop_count = 1
        mock_result.total_pass = 2
        mock_result.total_fail = 0
        mock_result.case_results = []

        mock_config = {"description": "Test fixture"}
        mock_global_config = {"product": {"sku": "TEST", "stage": "EVT"}}

        artifact = generator.generate(
            fixture_result=mock_result,
            fixture_config=mock_config,
            global_config=mock_global_config,
            sn="SN12345",
        )

        # 验证文本报告内容
        content = artifact.text_report_path.read_text()
        assert "Hardware Test Platform" in content
        assert "test_fixture" in content
        assert "PASS" in content or "pass" in content


class TestReportGeneratorFilename:
    """测试报告文件名"""

    def test_filename_with_sn(self, temp_dir: Path):
        """测试带 SN 的文件名"""
        reports_dir = temp_dir / "reports"
        generator = ReportGenerator(reports_dir=str(reports_dir))

        mock_result = MagicMock()
        mock_result.fixture_name = "test"
        mock_result.status = "pass"
        mock_result.duration = 1.0
        mock_result.loop_count = 1
        mock_result.total_pass = 0
        mock_result.total_fail = 0
        mock_result.case_results = []

        mock_config = {}
        mock_global_config = {"product": {"sku": "CM4", "stage": "DVT"}}

        artifact = generator.generate(
            fixture_result=mock_result,
            fixture_config=mock_config,
            global_config=mock_global_config,
            sn="SN12345",
        )

        # 文件名应该包含 SN
        assert "CM4" in str(artifact.text_report_path)
        assert "SN12345" in str(artifact.text_report_path)

    def test_filename_with_stage(self, temp_dir: Path):
        """测试带阶段的文件名（无 SN）"""
        reports_dir = temp_dir / "reports"
        generator = ReportGenerator(reports_dir=str(reports_dir))

        mock_result = MagicMock()
        mock_result.fixture_name = "test"
        mock_result.status = "pass"
        mock_result.duration = 1.0
        mock_result.loop_count = 1
        mock_result.total_pass = 0
        mock_result.total_fail = 0
        mock_result.case_results = []

        mock_config = {}
        mock_global_config = {"product": {"sku": "CM4", "stage": "DVT"}}

        artifact = generator.generate(
            fixture_result=mock_result,
            fixture_config=mock_config,
            global_config=mock_global_config,
            sn=None,
        )

        # 文件名应该包含阶段
        assert "CM4" in str(artifact.text_report_path)
        assert "DVT" in str(artifact.text_report_path)

    def test_filename_with_status(self, temp_dir: Path):
        """测试带状态的文件名"""
        reports_dir = temp_dir / "reports"
        generator = ReportGenerator(reports_dir=str(reports_dir))

        mock_result_pass = MagicMock()
        mock_result_pass.fixture_name = "test"
        mock_result_pass.status = "pass"
        mock_result_pass.duration = 1.0
        mock_result_pass.loop_count = 1
        mock_result_pass.total_pass = 0
        mock_result_pass.total_fail = 0
        mock_result_pass.case_results = []

        mock_config = {}
        mock_global_config = {"product": {"sku": "CM4", "stage": "DVT"}}

        artifact = generator.generate(
            fixture_result=mock_result_pass,
            fixture_config=mock_config,
            global_config=mock_global_config,
        )

        # 文件名应该包含 pass
        assert "pass" in str(artifact.text_report_path).lower()


class TestStatusCodeDescriptions:
    """测试状态码描述"""

    def test_returns_dict(self):
        """测试返回字典"""
        descriptions = status_code_descriptions()
        assert isinstance(descriptions, dict)

    def test_has_status_codes(self):
        """测试包含状态码"""
        descriptions = status_code_descriptions()
        # 0 是 SUCCESS
        assert 0 in descriptions
        # -1 是 FAILED
        assert -1 in descriptions

    def test_has_en_and_zh(self):
        """测试包含中英文"""
        descriptions = status_code_descriptions()
        assert "en" in descriptions[0]
        assert "zh" in descriptions[0]
