"""
Fixtures for pytest test suite.

提供全局的 pytest fixtures 用于测试
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

import pytest


@pytest.fixture
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def test_data_dir(project_root: Path) -> Path:
    """Get the test data directory."""
    data_dir = project_root / "tests" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for testing."""
    temp = tempfile.mkdtemp(prefix="test_hardware_")
    yield Path(temp)
    # Cleanup
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def temp_dirs(temp_dir: Path) -> Dict[str, Path]:
    """Create standard test directories."""
    dirs = {
        "tmp": temp_dir / "tmp",
        "logs": temp_dir / "logs",
        "reports": temp_dir / "reports",
        "config": temp_dir / "config",
        "functions": temp_dir / "functions",
        "cases": temp_dir / "cases",
        "fixtures": temp_dir / "fixtures",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


@pytest.fixture
def mock_case_config() -> Dict[str, Any]:
    """Mock case configuration."""
    return {
        "case_name": "mock_eth_test",
        "description": "Mock Ethernet test case",
        "module": "eth",
        "functions": [
            {
                "name": "test_eth",
                "params": {"ip": "127.0.0.1", "count": 2},
                "enabled": True,
            }
        ],
        "execution": "sequential",
        "timeout": 30,
        "retry": 1,
        "retry_interval": 1,
    }


@pytest.fixture
def mock_fixture_config() -> Dict[str, Any]:
    """Mock fixture configuration."""
    return {
        "fixture_name": "mock_quick_test",
        "description": "Mock quick functional test",
        "cases": [
            "cases/eth_case.json",
            "cases/uart_case.json",
        ],
        "execution": "sequential",
        "stop_on_failure": False,
        "loop": False,
        "loop_count": 1,
        "loop_interval": 0,
        "retry": 1,
        "retry_interval": 1,
        "report_enabled": True,
        "upload_oss": False,
    }


@pytest.fixture
def mock_global_config() -> Dict[str, Any]:
    """Mock global configuration."""
    return {
        "product": {
            "sku": "MOCK",
            "stage": "EVT",
            "default_sn_for_test": "EVT",
            "engineer": "Test Engineer",
        },
        "runtime": {
            "default_retry": 1,
            "default_retry_interval": 1,
            "default_timeout": 30,
        },
    }


@pytest.fixture
def sample_test_function_py() -> str:
    """Sample test function code for dynamic loading tests."""
    return '''
"""Sample test function for testing."""
from typing import Dict, Any


def test_sample(param1: str = "default") -> Dict[str, Any]:
    """Sample test function."""
    return {
        "code": 0,
        "message": "Success",
        "details": {"param1": param1},
    }
'''
