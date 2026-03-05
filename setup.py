#!/usr/bin/env python3
"""
Setup script for Hardware Test Platform.

硬件测试平台打包脚本
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = [
        line.strip() for line in requirements_path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="hardware-test-platform",
    version="1.0.0",
    author="Seeed Studio",
    description="Hardware Test Platform for RK3576 and other development boards",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(
        exclude=["venv", "tests", "*.tests", "*.tests.*", "tools", "doc", "docs"]
    ),
    package_data={
        "functions": ["**/*.json"],
        "cases": ["*.json"],
        "fixtures": ["*.json"],
        "config": ["*.json"],
    },
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "hardware-test=framework.logging.logger:main",
            "run_case=framework.cli.case_runner:main",
            "run_fixture=framework.cli.fixture_runner:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
