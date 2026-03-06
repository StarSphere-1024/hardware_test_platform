#!/usr/bin/env python3
"""
Deploy with strictly local dependency packages to remote RK3576 board.

This script will NOT download dependencies from network. It only uses local
dependency artifacts from `wheels/` or `wheels_source/`.

Usage:
    python scripts/package_and_deploy_offline.py <host> <user> <password> [remote_dir]
    python scripts/package_and_deploy_offline.py <host> <user> <password> [remote_dir] --skip-venv --skip-deps
"""

import argparse
import os
import subprocess
import sys
import shutil
import re
from pathlib import Path


DEPENDENCIES = [
    'pytest',
    'pytest-json-report',
    'pytest-metadata',
    'pyserial',
    'rich',
    'iniconfig',
    'pluggy',
    'packaging',
    'pygments',
    'mdurl',
    'markdown-it-py',
]


def _canonical_package_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _extract_package_name(filename: str) -> str | None:
    match = re.match(r"^([A-Za-z0-9_.-]+?)-\d", filename)
    if not match:
        return None
    return _canonical_package_name(match.group(1))


def _is_usable_wheel(file_name: str) -> bool:
    # Accept only architecture-agnostic wheels for remote board compatibility
    return file_name.endswith(".whl") and "none-any.whl" in file_name


def prepare_local_dependencies() -> list[Path]:
    """Resolve dependency artifacts from local cache only (no download)."""
    print("=" * 60)
    print("Preparing local dependencies (offline, no download)...")
    print("=" * 60)

    search_dirs = [Path("wheels"), Path("wheels_source")]
    available_by_pkg: dict[str, list[Path]] = {}

    for dep_dir in search_dirs:
        if not dep_dir.exists():
            continue
        for artifact in dep_dir.iterdir():
            if not artifact.is_file():
                continue
            name = artifact.name
            if not (name.endswith(".whl") or name.endswith(".tar.gz") or name.endswith(".zip")):
                continue
            pkg_name = _extract_package_name(name)
            if not pkg_name:
                continue
            available_by_pkg.setdefault(pkg_name, []).append(artifact)

    selected_files: list[Path] = []
    missing: list[str] = []

    for dep in DEPENDENCIES:
        key = _canonical_package_name(dep)
        candidates = available_by_pkg.get(key, [])
        if not candidates:
            missing.append(dep)
            continue

        universal_wheels = [item for item in candidates if _is_usable_wheel(item.name)]
        if universal_wheels:
            selected = sorted(universal_wheels)[0]
        else:
            source_pkgs = [item for item in candidates if item.name.endswith(".tar.gz") or item.name.endswith(".zip")]
            if source_pkgs:
                selected = sorted(source_pkgs)[0]
            else:
                missing.append(dep)
                continue

        selected_files.append(selected)
        print(f"  Using local artifact for {dep}: {selected}")

    if missing:
        print("[ERROR] Missing local dependency artifacts:")
        for dep in missing:
            print(f"  - {dep}")
        print("Please prepare local packages in wheels/ or wheels_source/ before deployment.")
        return []

    print(f"Prepared {len(selected_files)} local dependency artifacts")
    return selected_files


def build_package():
    """Build the hardware test platform package."""
    print("=" * 60)
    print("Building hardware test platform package...")
    print("=" * 60)

    dist_dir = Path("dist")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
        print(f"Cleaned {dist_dir}")

    build_dir = Path("build")
    if build_dir.exists():
        shutil.rmtree(build_dir)
        print(f"Cleaned {build_dir}")

    result = subprocess.run(
        [sys.executable, "setup.py", "bdist_wheel"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Build failed: {result.stderr}")
        return None

    wheels = list(dist_dir.glob("*.whl"))
    if wheels:
        wheel_path = wheels[0]
        print(f"Package built: {wheel_path}")
        return wheel_path

    print("No wheel file found")
    return None


def deploy_package(
    host: str,
    user: str,
    password: str,
    wheel_path: Path | None,
    dependency_files: list[Path],
    remote_dir: str,
    skip_venv: bool = False,
    skip_deps: bool = False,
    skip_package_install: bool = False,
):
    """Deploy package and dependencies to remote host."""
    os.environ['SSHPASS'] = password

    print("=" * 60)
    print(f"Deploying to {host}:{remote_dir}")
    print("=" * 60)

    venv_path = f"{remote_dir}/venv"

    try:
        # Create remote directory
        print(f"Creating remote directory: {remote_dir}...")
        mkdir_cmd = f'mkdir -p {remote_dir}'
        if not skip_deps:
            mkdir_cmd += f' {remote_dir}/local_deps'
        subprocess.run([
            'sshpass', '-e', 'ssh',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'ConnectTimeout=5',
            f'{user}@{host}',
            mkdir_cmd
        ], check=True)

        # Upload main package
        if not skip_package_install:
            if not wheel_path:
                print("[ERROR] wheel_path is required when package installation is enabled")
                return False
            print(f"Uploading package: {wheel_path.name}...")
            subprocess.run([
                'sshpass', '-e', 'scp',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'ConnectTimeout=5',
                str(wheel_path),
                f'{user}@{host}:{remote_dir}/'
            ], check=True)
        else:
            print("Skipping package upload/install (--skip-package-install)")

        # Upload local dependencies
        if not skip_deps:
            print("Uploading local dependencies...")
            wheel_count = 0
            for wheel in dependency_files:
                print(f"  Uploading {wheel.name}...")
                subprocess.run([
                    'sshpass', '-e', 'scp',
                    '-o', 'StrictHostKeyChecking=no',
                    '-o', 'ConnectTimeout=5',
                    str(wheel),
                    f'{user}@{host}:{remote_dir}/local_deps/'
                ], check=True)
                wheel_count += 1

            print(f"Uploaded {wheel_count} dependency files")
        else:
            print("Skipping dependency upload/install (--skip-deps)")

        # Create/reuse virtual environment on remote
        if not skip_venv:
            print("Creating virtual environment on remote...")
            result = subprocess.run([
                'sshpass', '-e', 'ssh',
                '-o', 'StrictHostKeyChecking=no',
                f'{user}@{host}',
                f'python3 -m venv {venv_path}'
            ], capture_output=True, text=True)

            if result.returncode != 0:
                print(f"Failed to create venv: {result.stderr}")
                return False

            print("Virtual environment created!")
        else:
            print("Reusing existing virtual environment (--skip-venv)")
            result = subprocess.run([
                'sshpass', '-e', 'ssh',
                '-o', 'StrictHostKeyChecking=no',
                f'{user}@{host}',
                f'test -x {venv_path}/bin/python'
            ], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"[ERROR] Remote venv not found at {venv_path}. Remove --skip-venv or create it first.")
                return False

        # Install build tools on remote (if needed)
        print("Checking for build tools on remote...")
        result = subprocess.run([
            'sshpass', '-e', 'ssh',
            '-o', 'StrictHostKeyChecking=no',
            f'{user}@{host}',
            'which gcc'
        ], capture_output=True, text=True)

        has_gcc = result.returncode == 0
        print(f"GCC available: {has_gcc}")

        # Install dependencies from local artifacts only (offline)
        if not skip_deps:
            print("Installing dependencies from local artifacts (offline)...")
            dep_install_cmd = (
                f'{venv_path}/bin/pip install --no-index --find-links={remote_dir}/local_deps '
                f'--no-cache-dir --no-build-isolation ' + " ".join(DEPENDENCIES)
            )
            result = subprocess.run([
                'sshpass', '-e', 'ssh',
                '-o', 'StrictHostKeyChecking=no',
                f'{user}@{host}',
                dep_install_cmd
            ], capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                print("[ERROR] Local dependency install failed (no network download allowed)")
                print(f"Error: {result.stderr[:500]}")
                print(f"Output: {result.stdout[:500]}")
                return False
            else:
                print("Dependencies installed!")

        # Install the main package
        if not skip_package_install:
            if not wheel_path:
                print("[ERROR] wheel_path is required when package installation is enabled")
                return False
            print("Installing hardware_test_platform...")
            result = subprocess.run([
                'sshpass', '-e', 'ssh',
                '-o', 'StrictHostKeyChecking=no',
                f'{user}@{host}',
                f'{venv_path}/bin/pip install --no-deps {remote_dir}/{wheel_path.name}'
            ], capture_output=True, text=True)

            if result.returncode != 0:
                print(f"Failed to install package: {result.stderr}")
                return False

            print("Package installed!")

        # Deploy test files
        print("Deploying workspace files (framework, functions, cases, fixtures, config, bin)...")
        for dir_name in ['framework', 'functions', 'cases', 'fixtures', 'config', 'bin']:
            local_dir = Path(dir_name)
            if local_dir.exists():
                print(f"  Deploying {dir_name}...")
                subprocess.run([
                    'sshpass', '-e', 'scp',
                    '-o', 'StrictHostKeyChecking=no',
                    '-o', 'ConnectTimeout=5',
                    '-r',
                    f'{local_dir}/',
                    f'{user}@{host}:{remote_dir}/'
                ], check=True)

        # Verify installation
        print("Verifying installation...")
        result = subprocess.run([
            'sshpass', '-e', 'ssh',
            '-o', 'StrictHostKeyChecking=no',
            f'{user}@{host}',
            f'{venv_path}/bin/python -c "import framework; print(\'framework version:\', framework.__version__)"'
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print(f"Verification: {result.stdout.strip()}")
        else:
            print(f"Verification failed: {result.stderr}")

        # Verify installed CLI entry points (generated by wheel)
        print("Verifying CLI entry points (run_case/run_fixture)...")
        result = subprocess.run([
            'sshpass', '-e', 'ssh',
            '-o', 'StrictHostKeyChecking=no',
            f'{user}@{host}',
            f'{venv_path}/bin/run_case --help >/dev/null && {venv_path}/bin/run_fixture --help >/dev/null && echo CLI_OK'
        ], capture_output=True, text=True)

        if result.returncode == 0 and 'CLI_OK' in result.stdout:
            print("CLI verification: run_case/run_fixture available")
        else:
            print(f"CLI verification failed: {result.stderr or result.stdout}")

        # Check pytest installation
        result = subprocess.run([
            'sshpass', '-e', 'ssh',
            '-o', 'StrictHostKeyChecking=no',
            f'{user}@{host}',
            f'{venv_path}/bin/pytest --version'
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print(f"pytest: {result.stdout.strip()}")
        else:
            print(f"pytest not available: {result.stderr[:200]}")

        # List installed packages
        print("Installed packages:")
        result = subprocess.run([
            'sshpass', '-e', 'ssh',
            '-o', 'StrictHostKeyChecking=no',
            f'{user}@{host}',
            f'{venv_path}/bin/pip list'
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print(result.stdout)

        print("=" * 60)
        print("Deployment complete!")
        print("=" * 60)

        return True

    except subprocess.CalledProcessError as e:
        print(f"Deployment failed: {e}")
        return False
    except subprocess.TimeoutExpired:
        print("Deployment timed out")
        return False
    finally:
        if 'SSHPASS' in os.environ:
            del os.environ['SSHPASS']


def main():
    parser = argparse.ArgumentParser(
        description="Offline deploy package to remote board with optional reuse mode"
    )
    parser.add_argument("host")
    parser.add_argument("user")
    parser.add_argument("password")
    parser.add_argument("remote_dir", nargs="?", default="/home/seeed/hardware_test")
    parser.add_argument(
        "--skip-venv",
        action="store_true",
        help="Reuse existing remote venv, skip 'python3 -m venv'",
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip dependency upload and pip install from local_deps",
    )
    parser.add_argument(
        "--skip-package-install",
        action="store_true",
        help="Skip wheel build/upload/install, only sync workspace files",
    )
    parser.add_argument(
        "--fast-reuse",
        action="store_true",
        help="Shortcut: --skip-venv --skip-deps --skip-package-install",
    )

    args = parser.parse_args()

    skip_venv = args.skip_venv or args.fast_reuse
    skip_deps = args.skip_deps or args.fast_reuse
    skip_package_install = args.skip_package_install or args.fast_reuse

    wheel_path: Path | None = None
    if not skip_package_install:
        wheel_path = build_package()
        if not wheel_path:
            print("Build failed!")
            sys.exit(1)
    else:
        print("Skipping wheel build (--skip-package-install or --fast-reuse)")

    dependency_files: list[Path] = []
    if not skip_deps:
        dependency_files = prepare_local_dependencies()
        if not dependency_files:
            print("Local dependency preparation failed!")
            sys.exit(1)
    else:
        print("Skipping local dependency preparation (--skip-deps or --fast-reuse)")

    # Deploy to remote
    success = deploy_package(
        args.host,
        args.user,
        args.password,
        wheel_path,
        dependency_files,
        args.remote_dir,
        skip_venv=skip_venv,
        skip_deps=skip_deps,
        skip_package_install=skip_package_install,
    )
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
