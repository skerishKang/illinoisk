#!/usr/bin/env python3
"""
Run the local regression checks for illinoisk.

This runner intentionally uses only local checks. It must not require Kiwoom
credentials, network access, or live market API calls.

Run:
  python3 tests/run_all.py
"""
import subprocess
import sys
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]


CHECKS = [
    [sys.executable, "-m", "py_compile", "scripts/scan_golden_cross.py"],
    [sys.executable, "-m", "py_compile", "scripts/discord_trigger_router.py"],
    [sys.executable, "tests/test_save_conversation_import.py"],
    [sys.executable, "tests/test_scan_golden_cross_futures_stub.py"],
    [sys.executable, "tests/test_discord_trigger_router.py"],
]


def run_check(cmd):
    print("\n$ " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=BASE)
    return result.returncode == 0


def main():
    print("=" * 60)
    print("illinoisk local regression checks")
    print("=" * 60)

    passed = 0
    failed = 0

    for cmd in CHECKS:
        if run_check(cmd):
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print(f"결과: {passed}개 통과, {failed}개 실패")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
