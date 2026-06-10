#!/usr/bin/env python3
"""
scan_golden_cross.py futures investor stub regression tests.

Run:
  python3 tests/test_scan_golden_cross_futures_stub.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

from scan_golden_cross import fetch_futures_frgn_inst


def test_futures_stub_returns_unavailable():
    """fetch_futures_frgn_inst must stay unavailable until a verified data source exists."""
    print("테스트 1: fetch_futures_frgn_inst unavailable stub")

    result = fetch_futures_frgn_inst("dummy-token")

    assert result == {
        "frgn_net": 0,
        "inst_net": 0,
        "source": "unavailable",
    }, f"unexpected futures stub result: {result}"

    print("  ✓ unavailable stub result locked")
    return True


def test_futures_stub_ignores_token_value():
    """The current stub must not depend on token value or token availability."""
    print("\n테스트 2: fetch_futures_frgn_inst token-independent")

    none_result = fetch_futures_frgn_inst(None)
    empty_result = fetch_futures_frgn_inst("")
    dummy_result = fetch_futures_frgn_inst("dummy-token")

    assert none_result == dummy_result, "None token changed stub result"
    assert empty_result == dummy_result, "empty token changed stub result"

    print("  ✓ token value does not affect unavailable stub")
    return True


def run_all_tests():
    print("=" * 60)
    print("scan_golden_cross.py futures stub tests")
    print("=" * 60)

    tests = [
        test_futures_stub_returns_unavailable,
        test_futures_stub_ignores_token_value,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as exc:
            failed += 1
            print(f"  ✗ 실패: {exc}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"결과: {passed}개 통과, {failed}개 실패")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
