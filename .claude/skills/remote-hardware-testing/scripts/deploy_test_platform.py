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
        candidate = root / deploy_script_name
        if candidate.exists():
            deploy_script = candidate
            repo_root = root
            break

    if deploy_script is None or repo_root is None:
        print(f"[ERROR] deploy script not found: {Path.cwd().resolve() / deploy_script_name}")
        return 2

    cmd = [
        sys.executable,
        str(deploy_script),
        args.host,
        args.user,
        args.password,
        args.remote_dir,
    ]

    print("=" * 60)
    print("Remote deploy command")
    print("=" * 60)
    print(" ".join(cmd))

    result = subprocess.run(cmd, cwd=str(repo_root))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
