#!/usr/bin/env python3
"""
``scripts/handoff_file_writer.py`` 회귀 테스트.

이 슬라이스는 실제 ``handoff/`` 디렉토리에 쓰지 않고, ``tempfile.TemporaryDirectory()``로
생성한 임시 경로에서 path generator와 overwrite guard의 동작만 검증한다.

실행:
  python3 tests/test_handoff_file_writer.py
"""
import sys
import tempfile
from pathlib import Path

# scripts/ 안의 sibling 모듈 import 지원
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from handoff_file_writer import (  # noqa: E402
    DEFAULT_FILENAME_FALLBACK,
    build_handoff_packet_path,
    ensure_can_write_packet,
    sanitize_filename_component,
)


def test_sanitize_filename_component_handles_safe_unsafe_and_blank():
    """안전한 문자는 통과시키고, 안전하지 않은 문자는 '_'로 치환하며,
    blank 값은 fallback으로 대체한다."""
    print("\n테스트 1: sanitize_filename_component — safe/unsafe/blank")

    safe_cases = [
        ("HPSP", "HPSP"),
        ("abc_123", "abc_123"),
        ("abc-123", "abc-123"),
        ("abc.123", "abc.123"),
        ("KRX-HPSP", "KRX-HPSP"),
    ]
    for raw, expected in safe_cases:
        got = sanitize_filename_component(raw)
        assert got == expected, (
            f"safe value가 그대로 보존되지 않음: input={raw!r}, "
            f"got={got!r}, expected={expected!r}"
        )

    unsafe_cases = [
        ("a/b", "a_b"),
        ("a\\b", "a_b"),
        ("a:b", "a_b"),
        ("a*b", "a_b"),
        ("a?b", "a_b"),
        ("a<b", "a_b"),
        ('a"b', "a_b"),
        ("a|b", "a_b"),
        ("a  b", "a_b"),  # 공백 연속 -> 단일 '_'
        ("\tname", "name"),
    ]
    for raw, expected in unsafe_cases:
        got = sanitize_filename_component(raw)
        assert got == expected, (
            f"unsafe value 정제 실패: input={raw!r}, "
            f"got={got!r}, expected={expected!r}"
        )

    blank_cases = [
        ("", DEFAULT_FILENAME_FALLBACK),
        ("   ", DEFAULT_FILENAME_FALLBACK),
        (".", DEFAULT_FILENAME_FALLBACK),
        ("..", DEFAULT_FILENAME_FALLBACK),
        ("///", DEFAULT_FILENAME_FALLBACK),
    ]
    for raw, expected in blank_cases:
        got = sanitize_filename_component(raw)
        assert got == expected, (
            f"blank value가 fallback으로 대체되지 않음: input={raw!r}, "
            f"got={got!r}, expected={expected!r}"
        )

    assert sanitize_filename_component(None) == DEFAULT_FILENAME_FALLBACK, (
        "None이 fallback으로 대체되지 않음"
    )

    assert sanitize_filename_component("test", fallback="missing") == "test", (
        "custom fallback이 정상 입력에 영향을 줌"
    )
    assert sanitize_filename_component("", fallback="missing") == "missing", (
        "custom fallback이 blank 입력에 적용되지 않음"
    )

    print(f"  ✓ safe/unsafe/blank {len(safe_cases) + len(unsafe_cases) + len(blank_cases) + 3}개 케이스 통과")
    return True


def test_sanitize_filename_component_handles_korean_unicode_and_truncation():
    """한글/unicode는 보존하고, max_length 초과 시 잘라낸다."""
    print("\n테스트 2: sanitize_filename_component — 한글/unicode/길이 제한")

    korean_cases = [
        ("신호", "신호"),
        ("진입", "진입"),
        ("손절", "손절"),
        ("signal review", "signal_review"),
        ("신호_review", "신호_review"),
        ("hello-신호-2026", "hello-신호-2026"),
    ]
    for raw, expected in korean_cases:
        got = sanitize_filename_component(raw)
        assert got == expected, (
            f"한글/혼합 케이스 정제 실패: input={raw!r}, "
            f"got={got!r}, expected={expected!r}"
        )

    long_raw = "a" * 200
    got_default = sanitize_filename_component(long_raw)
    assert len(got_default) == 64, (
        f"기본 max_length=64로 truncation되지 않음: got len={len(got_default)}"
    )
    assert got_default == "a" * 64, "truncation 결과가 단순 slice와 다름"

    got_custom = sanitize_filename_component(long_raw, max_length=10)
    assert len(got_custom) == 10, (
        f"custom max_length=10이 적용되지 않음: got len={len(got_custom)}"
    )

    long_unsafe = "a/b" * 100  # 500자이지만 unsafe로 '_' 포함됨
    got_unsafe = sanitize_filename_component(long_unsafe, max_length=20)
    assert len(got_unsafe) <= 20, (
        f"unsafe+긴 입력이 max_length로 truncation되지 않음: got len={len(got_unsafe)}"
    )

    print(f"  ✓ 한글/unicode 보존 + truncation 동작 확인")
    return True


def test_build_handoff_packet_path_normalizes_time_and_sanitizes_components():
    """``build_handoff_packet_path``가 time을 HHMM으로 정규화하고
    symbol/purpose를 sanitize한 deterministic path를 만든다."""
    print("\n테스트 3: build_handoff_packet_path — 정규화/sanitize")

    path = build_handoff_packet_path(
        root_dir="handoff",
        date_kst="2026-06-13",
        time_kst="10:35",
        symbol="HPSP",
        purpose="signal review",
    )
    expected = Path("handoff") / "2026-06-13" / "1035-HPSP-signal_review.md"
    assert path == expected, (
        f"path가 기대값과 다름: got={path!r}, expected={expected!r}"
    )
    assert isinstance(path, Path), f"반환값이 Path가 아님: {type(path).__name__}"

    path_compact = build_handoff_packet_path(
        root_dir="/tmp/handoff",
        date_kst="2026-06-13",
        time_kst="1035",
        symbol="HPSP",
        purpose="entry",
    )
    expected_compact = Path("/tmp/handoff") / "2026-06-13" / "1035-HPSP-entry.md"
    assert path_compact == expected_compact, (
        f"compact time 입력이 HHMM 4자리로 정규화되지 않음: got={path_compact!r}"
    )

    path_unsafe = build_handoff_packet_path(
        root_dir="handoff",
        date_kst="2026-06-13",
        time_kst="10:35",
        symbol="HPSP/test",
        purpose="a:b?c",
    )
    assert path_unsafe.name == "1035-HPSP_test-a_b_c.md", (
        f"symbol/purpose sanitize가 path에 반영되지 않음: {path_unsafe.name!r}"
    )

    path_korean = build_handoff_packet_path(
        root_dir="handoff",
        date_kst="2026-06-13",
        time_kst="10:35",
        symbol="HPSP",
        purpose="신호 리뷰",
    )
    assert path_korean.name == "1035-HPSP-신호_리뷰.md", (
        f"한글 purpose sanitize 결과가 잘못됨: {path_korean.name!r}"
    )

    path_root = build_handoff_packet_path(
        root_dir=Path("/abs/handoff"),
        date_kst="2026-06-13",
        time_kst="00:00",
        symbol="X",
        purpose="Y",
    )
    assert path_root == Path("/abs/handoff") / "2026-06-13" / "0000-X-Y.md", (
        f"Path 입력 root_dir가 정상 처리되지 않음: {path_root!r}"
    )

    print(f"  ✓ time 정규화 + symbol/purpose sanitize + Path root 모두 통과")
    return True


def test_build_handoff_packet_path_validates_date_and_time_format():
    """잘못된 date/time 형식은 ``ValueError``로 거부된다."""
    print("\n테스트 4: build_handoff_packet_path — date/time 검증")

    invalid_dates = [
        "2026/06/13",
        "26-06-13",
        "2026-6-13",
        "2026-06-13 ",
        " 2026-06-13",
        "",
    ]
    for bad in invalid_dates:
        try:
            build_handoff_packet_path(
                root_dir="handoff",
                date_kst=bad,
                time_kst="10:35",
                symbol="HPSP",
                purpose="entry",
            )
        except ValueError:
            pass
        else:
            raise AssertionError(
                f"잘못된 date_kst={bad!r}이 거부되지 않음"
            )

    invalid_times = [
        "25:00",
        "10:60",
        "9:35",
        "100:35",
        "10-35",
        "abc",
        "",
        "10:35:00",
    ]
    for bad in invalid_times:
        try:
            build_handoff_packet_path(
                root_dir="handoff",
                date_kst="2026-06-13",
                time_kst=bad,
                symbol="HPSP",
                purpose="entry",
            )
        except ValueError:
            pass
        else:
            raise AssertionError(
                f"잘못된 time_kst={bad!r}이 거부되지 않음"
            )

    try:
        build_handoff_packet_path(
            root_dir="handoff",
            date_kst="2026-06-13",
            time_kst=12345,  # type: ignore[arg-type]
            symbol="HPSP",
            purpose="entry",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("time_kst에 문자열이 아닌 입력이 거부되지 않음")

    print(f"  ✓ 잘못된 date {len(invalid_dates)}건 + time {len(invalid_times) + 1}건 모두 ValueError")
    return True


def test_build_handoff_packet_path_uses_fallback_for_blank_components():
    """symbol/purpose가 blank면 filename component에 fallback이 들어간다."""
    print("\n테스트 5: build_handoff_packet_path — blank component fallback")

    for blank_symbol in ["", None, "   ", "///"]:
        path = build_handoff_packet_path(
            root_dir="handoff",
            date_kst="2026-06-13",
            time_kst="10:35",
            symbol=blank_symbol,
            purpose="entry",
        )
        assert f"-{DEFAULT_FILENAME_FALLBACK}-" in path.name, (
            f"blank symbol이 fallback으로 대체되지 않음: symbol={blank_symbol!r}, "
            f"path={path.name!r}"
        )

    for blank_purpose in ["", None, "..", ".."]:
        path = build_handoff_packet_path(
            root_dir="handoff",
            date_kst="2026-06-13",
            time_kst="10:35",
            symbol="HPSP",
            purpose=blank_purpose,
        )
        assert path.name.endswith(f"-{DEFAULT_FILENAME_FALLBACK}.md"), (
            f"blank purpose가 fallback으로 대체되지 않음: purpose={blank_purpose!r}, "
            f"path={path.name!r}"
        )

    print("  ✓ blank symbol/purpose → fallback 삽입 확인")
    return True


def test_ensure_can_write_packet_allows_when_path_does_not_exist():
    """``tempfile.TemporaryDirectory()``에서 path가 없으면 ``(True, 'ok')``."""
    print("\n테스트 6: ensure_can_write_packet — path 없으면 허용")

    with tempfile.TemporaryDirectory() as tmp:
        date_dir = Path(tmp) / "2026-06-13"
        date_dir.mkdir()
        packet = date_dir / "1035-HPSP-entry.md"
        allowed, reason = ensure_can_write_packet(packet)
        assert allowed is True, f"없는 path가 거부됨: reason={reason!r}"
        assert reason == "ok", f"reason이 'ok'가 아님: {reason!r}"

        allowed, reason = ensure_can_write_packet(packet, overwrite=True)
        assert allowed is True, f"overwrite=True가 없는 path에 거부됨"
        assert reason == "ok", f"reason이 'ok'가 아님: {reason!r}"

    print("  ✓ 임시 디렉토리에서 없는 path는 overwrite 무관하게 (True, 'ok')")
    return True


def test_ensure_can_write_packet_denies_existing_unless_overwrite():
    """파일이 이미 있으면 ``overwrite=False``에서 거부, ``overwrite=True``에서 허용."""
    print("\n테스트 7: ensure_can_write_packet — existing file overwrite guard")

    with tempfile.TemporaryDirectory() as tmp:
        packet = Path(tmp) / "1035-HPSP-entry.md"
        packet.write_text("dummy", encoding="utf-8")

        allowed, reason = ensure_can_write_packet(packet)
        assert allowed is False, f"기존 파일이 overwrite=False에서 허용됨: reason={reason!r}"
        assert reason == "exists", f"reason이 'exists'가 아님: {reason!r}"

        allowed, reason = ensure_can_write_packet(packet, overwrite=True)
        assert allowed is True, f"overwrite=True가 기존 파일에 거부됨: reason={reason!r}"
        assert reason == "overwrite", f"reason이 'overwrite'가 아님: {reason!r}"

    print("  ✓ overwrite=False → 거부, overwrite=True → 허용")
    return True


def test_ensure_can_write_packet_denies_when_parent_missing():
    """부모 디렉토리가 없으면 overwrite와 무관하게 거부된다."""
    print("\n테스트 8: ensure_can_write_packet — parent_missing")

    with tempfile.TemporaryDirectory() as tmp:
        missing_parent = Path(tmp) / "does-not-exist" / "1035-HPSP-entry.md"
        allowed, reason = ensure_can_write_packet(missing_parent)
        assert allowed is False, f"없는 부모 경로가 허용됨"
        assert reason == "parent_missing", f"reason이 'parent_missing'이 아님: {reason!r}"

        allowed, reason = ensure_can_write_packet(missing_parent, overwrite=True)
        assert allowed is False, "overwrite=True도 없는 부모 경로에 허용됨"
        assert reason == "parent_missing", f"reason이 'parent_missing'이 아님: {reason!r}"

        file_instead_of_dir = Path(tmp) / "regular_file"
        file_instead_of_dir.write_text("blocker", encoding="utf-8")
        blocked = file_instead_of_dir / "1035-HPSP-entry.md"
        allowed, reason = ensure_can_write_packet(blocked)
        assert allowed is False, "파일이 부모인 경로가 허용됨"
        assert reason == "parent_missing", (
            f"파일이 부모인 경우 reason이 'parent_missing'이 아님: {reason!r}"
        )

    print("  ✓ parent_missing/parent-is-file 둘 다 거부 확인")
    return True


def run_all_tests():
    """모든 테스트 실행."""
    print("=" * 60)
    print("handoff_file_writer.py 회귀 테스트")
    print("=" * 60)

    tests = [
        test_sanitize_filename_component_handles_safe_unsafe_and_blank,
        test_sanitize_filename_component_handles_korean_unicode_and_truncation,
        test_build_handoff_packet_path_normalizes_time_and_sanitizes_components,
        test_build_handoff_packet_path_validates_date_and_time_format,
        test_build_handoff_packet_path_uses_fallback_for_blank_components,
        test_ensure_can_write_packet_allows_when_path_does_not_exist,
        test_ensure_can_write_packet_denies_existing_unless_overwrite,
        test_ensure_can_write_packet_denies_when_parent_missing,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            if t():
                passed += 1
            else:
                failed += 1
        except AssertionError as e:
            print(f"  ✗ AssertionError: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ 예외 발생: {type(e).__name__}: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"결과: {passed}개 통과, {failed}개 실패")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
