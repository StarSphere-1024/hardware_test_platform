#!/usr/bin/env python3
"""
Deploy with strictly local dependency packages to remote RK3576 board.

This script will NOT download dependencies from network. It only uses local
dependency artifacts from `wheels/` or `wheels_source/`.

Usage:
    python package_and_deploy_offline.py <host> <user> <password> [remote_dir]
"""

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


def deploy_package(host: str, user: str, password: str, wheel_path: Path, dependency_files: list[Path], remote_dir: str):
    """Deploy package and dependencies to remote host."""
    os.environ['SSHPASS'] = password

    print("=" * 60)
    print(f"Deploying to {host}:{remote_dir}")
    print("=" * 60)

    venv_path = f"{remote_dir}/venv"

    try:
        # Create remote directory
        print(f"Creating remote directory: {remote_dir}...")
        subprocess.run([
            'sshpass', '-e', 'ssh',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'ConnectTimeout=5',
            f'{user}@{host}',
            f'mkdir -p {remote_dir} {remote_dir}/local_deps'
        ], check=True)

        # Upload main package
        print(f"Uploading package: {wheel_path.name}...")
        subprocess.run([
            'sshpass', '-e', 'scp',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'ConnectTimeout=5',
            str(wheel_path),
            f'{user}@{host}:{remote_dir}/'
        ], check=True)

        # Upload local dependencies
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

        print(f"Uploaded {wheel_count} files")

        # Create virtual environment on remote
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
        print(f"Installing hardware_test_platform...")
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
        print("Deploying test files (functions, cases, fixtures)...")
        for dir_name in ['functions', 'cases', 'fixtures']:
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
    if len(sys.argv) < 4:
        print("Usage: package_and_deploy_offline.py <host> <user> <password> [remote_dir]")
        sys.exit(1)

    host = sys.argv[1]
    user = sys.argv[2]
    password = sys.argv[3]
    remote_dir = sys.argv[4] if len(sys.argv) > 4 else '/home/seeed/hardware_test'

    # Build package
    wheel_path = build_package()
    if not wheel_path:
        print("Build failed!")
        sys.exit(1)

    # Prepare local dependencies only (no download)
    dependency_files = prepare_local_dependencies()
    if not dependency_files:
        print("Local dependency preparation failed!")
        sys.exit(1)

    # Deploy to remote
    success = deploy_package(host, user, password, wheel_path, dependency_files, remote_dir)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
