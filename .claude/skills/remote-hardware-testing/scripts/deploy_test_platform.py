#!/usr/bin/env python3
"""Deploy hardware test platform to remote board through package_and_deploy_offline.py."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build and deploy hardware_test_platform to remote RK3576 board.",
    )
    parser.add_argument("--host", default=os.getenv("REMOTE_HOST", "192.168.100.91"))
    parser.add_argument("--user", default=os.getenv("REMOTE_USER", "seeed"))
    parser.add_argument("--password", default=os.getenv("REMOTE_PASS", "seeed"))
    parser.add_argument("--remote-dir", default=os.getenv("REMOTE_DIR", "/home/seeed/hardware_test"))
    parser.add_argument(
        "--as-root",
        action="store_true",
        help="Use root account for remote operations",
    )
    parser.add_argument(
        "--skip-venv",
        action="store_true",
        help="Reuse remote venv and skip venv creation",
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip dependency upload/install",
    )
    parser.add_argument(
        "--skip-package-install",
        action="store_true",
        help="Skip wheel build/upload/install and only sync workspace files",
    )
    parser.add_argument(
        "--fast-reuse",
        action="store_true",
        help="Shortcut for --skip-venv --skip-deps --skip-package-install",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if shutil.which("sshpass") is None:
        print("[ERROR] sshpass not found. Please install sshpass first.")
        return 2

    deploy_script_name = "package_and_deploy_offline.py"
    script_path = Path(__file__).resolve()
    search_roots = [Path.cwd().resolve(), *script_path.parents]

    deploy_script: Path | None = None
    repo_root: Path | None = None
    for root in search_roots:
        candidates = [
            root / deploy_script_name,
            root / "scripts" / deploy_script_name,
        ]
        for candidate in candidates:
            if candidate.exists():
                deploy_script = candidate
                repo_root = root
                break
        if deploy_script is not None:
            break

    if deploy_script is None or repo_root is None:
        print(f"[ERROR] deploy script not found: scripts/{deploy_script_name}")
        return 2

    cmd = [
        sys.executable,
        str(deploy_script),
        args.host,
        "root" if args.as_root else args.user,
        args.password,
        args.remote_dir,
    ]

    if args.skip_venv:
        cmd.append("--skip-venv")
    if args.skip_deps:
        cmd.append("--skip-deps")
    if args.skip_package_install:
        cmd.append("--skip-package-install")
    if args.fast_reuse:
        cmd.append("--fast-reuse")

    print("=" * 60)
    print("Remote deploy command")
    print("=" * 60)
    print(" ".join(cmd))

    result = subprocess.run(cmd, cwd=str(repo_root))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
