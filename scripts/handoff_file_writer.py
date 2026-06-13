#!/usr/bin/env python3
"""
Local handoff packet path generator.

사람이 직접 로컬에서 handoff packet을 디스크에 저장할 경로를 결정하고
overwrite 여부를 안전하게 차단하는 helper들을 제공합니다.

이 모듈은 filesystem 상태를 바꾸지 않습니다. ``build_handoff_packet_path``는
순수하게 ``pathlib.Path`` 객체만 만들고, ``ensure_can_write_packet``은
부모 디렉토리와 파일의 존재 여부만 확인합니다. 실제 파일 쓰기는 호출자의
책임입니다 (이 모듈에서는 ``path.write_text(...)`` 등을 호출하지 않습니다).

사용 예시:

    from handoff_file_writer import (
        build_handoff_packet_path,
        ensure_can_write_packet,
        sanitize_filename_component,
    )

    path = build_handoff_packet_path(
        "handoff",
        "2026-06-13",
        "10:35",
        "HPSP",
        "signal review",
    )
    allowed, reason = ensure_can_write_packet(path, overwrite=False)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Tuple, Union


# filename component에 안전하지 않은 모든 문자를 '_'로 치환하기 위한 패턴.
# - ASCII alphanumeric, '_', '-', '.': 그대로 유지
# - 한글 (가-힣): 그대로 유지
# - 그 외 (공백, 슬래시, 백슬래시, 제어문자, 구두점, 따옴표 등): '_'로 바뀜
_SAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9가-힣._\-]+")
_RUN_OF_UNDERSCORES = re.compile(r"_+")


_DATE_KST_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_KST_COLON_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
_TIME_KST_COMPACT_PATTERN = re.compile(r"^([01]\d|2[0-3])([0-5]\d)$")


DEFAULT_SANITIZE_MAX_LENGTH = 64
DEFAULT_FILENAME_FALLBACK = "unavailable"


def sanitize_filename_component(
    value: Optional[str],
    *,
    fallback: str = DEFAULT_FILENAME_FALLBACK,
    max_length: int = DEFAULT_SANITIZE_MAX_LENGTH,
) -> str:
    """filename component로 안전하게 쓸 수 있도록 문자열을 정제한다.

    규칙:
    - ``None`` 또는 빈 문자열/공백만 있으면 ``fallback``을 반환한다.
    - 안전한 문자 (ASCII alphanumeric, ``_``, ``-``, ``.``, 한글)를 제외한
      모든 문자를 ``_``로 치환한다.
    - 연속된 ``_``는 한 글자로 합친다.
    - 앞뒤의 ``_``, ``.``, 공백을 제거한다.
    - 정제 후 빈 문자열이 되면 ``fallback``을 반환한다.
    - 결과는 ``max_length`` 글자에서 잘라낸다 (단순 slice).

    예시::

        sanitize_filename_component("HPSP") == "HPSP"
        sanitize_filename_component("a/b") == "a_b"
        sanitize_filename_component("") == "unavailable"
        sanitize_filename_component(None) == "unavailable"
        sanitize_filename_component("신호") == "신호"
        sanitize_filename_component("  test  ") == "test"
    """
    if value is None:
        return fallback

    sanitized = _SAFE_FILENAME_CHARS.sub("_", value)
    sanitized = _RUN_OF_UNDERSCORES.sub("_", sanitized)
    sanitized = sanitized.strip("_ .")

    if not sanitized:
        return fallback

    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized


def _normalize_time_kst(time_kst: str) -> str:
    """``HH:MM`` 또는 ``HHMM`` 형식의 시각을 ``HHMM`` 4자리로 정규화한다."""
    if not isinstance(time_kst, str):
        raise ValueError(
            "time_kst must be a string in 'HH:MM' or 'HHMM' format, "
            f"got {type(time_kst).__name__}"
        )

    match = _TIME_KST_COLON_PATTERN.match(time_kst)
    if match:
        return f"{match.group(1)}{match.group(2)}"

    match = _TIME_KST_COMPACT_PATTERN.match(time_kst)
    if match:
        return f"{match.group(1)}{match.group(2)}"

    raise ValueError(
        f"time_kst must be 'HH:MM' or 'HHMM' format (00:00-23:59), got {time_kst!r}"
    )


def build_handoff_packet_path(
    root_dir: Union[str, Path],
    date_kst: str,
    time_kst: str,
    symbol: Optional[str],
    purpose: Optional[str],
) -> Path:
    """deterministic handoff packet 경로를 생성한다 (filesystem 접근 없음).

    형식: ``<root_dir>/<YYYY-MM-DD>/<HHMM>-<symbol>-<purpose>.md``

    - ``date_kst``는 ``YYYY-MM-DD`` 형식이어야 한다 (그 외엔 ``ValueError``).
    - ``time_kst``는 ``HH:MM`` 또는 ``HHMM`` 형식이며 ``HHMM`` 4자리로 정규화된다.
    - ``symbol``과 ``purpose``는 ``sanitize_filename_component``로 정제된다.
    - 반환값은 ``pathlib.Path``이며 실제 filesystem 접근은 하지 않는다.
    """
    if not isinstance(date_kst, str) or not _DATE_KST_PATTERN.match(date_kst):
        raise ValueError(
            f"date_kst must be 'YYYY-MM-DD' format, got {date_kst!r}"
        )

    time_compact = _normalize_time_kst(time_kst)

    safe_symbol = sanitize_filename_component(symbol)
    safe_purpose = sanitize_filename_component(purpose)

    filename = f"{time_compact}-{safe_symbol}-{safe_purpose}.md"
    return Path(root_dir) / date_kst / filename


def ensure_can_write_packet(
    path: Union[str, Path],
    *,
    overwrite: bool = False,
) -> Tuple[bool, str]:
    """packet 경로에 쓸 수 있는지 확인한다 (실제 쓰기 없음).

    반환값: ``(allowed, reason)`` 튜플.
    - ``allowed=True``, ``reason="ok"``: 경로에 파일이 없고 overwrite=False인 경우
    - ``allowed=True``, ``reason="overwrite"``: 경로에 파일이 있지만 overwrite=True인 경우
    - ``allowed=False``, ``reason="exists"``: 경로에 파일이 있고 overwrite=False인 경우
    - ``allowed=False``, ``reason="parent_missing"``: 부모 디렉토리가 없거나 디렉토리가 아닌 경우

    부모 디렉토리가 없으면 overwrite와 무관하게 거부한다. 호출자가
    ``path.parent.mkdir(parents=True, exist_ok=True)``로 디렉토리를 만든 다음
    다시 호출해야 한다.
    """
    target = Path(path)
    parent = target.parent

    if not parent.exists() or not parent.is_dir():
        return (False, "parent_missing")

    if target.exists():
        if overwrite:
            return (True, "overwrite")
        return (False, "exists")

    return (True, "ok")


__all__ = [
    "build_handoff_packet_path",
    "ensure_can_write_packet",
    "sanitize_filename_component",
    "DEFAULT_FILENAME_FALLBACK",
    "DEFAULT_SANITIZE_MAX_LENGTH",
]
