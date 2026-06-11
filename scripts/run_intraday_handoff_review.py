#!/usr/bin/env python3
"""
Local handoff review CLI.

Reads a caller-provided local snapshot JSON file, builds a deterministic
handoff review packet, and prints the packet to stdout.

This script does not run a server, connect to external services, fetch market
data, call models, write files, or place orders.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from handoff_orchestrator import build_handoff_from_message


def load_snapshot(path: str) -> dict[str, Any]:
    """Load a local snapshot JSON file as a dictionary."""
    snapshot_path = Path(path)
    try:
        with snapshot_path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError as exc:
        raise SystemExit(f"snapshot file not found: {snapshot_path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"snapshot file is not valid JSON: {snapshot_path}: {exc}") from exc

    if not isinstance(value, dict):
        raise SystemExit("snapshot JSON root must be an object")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a local intraday handoff review packet from a snapshot JSON file."
    )
    parser.add_argument(
        "--snapshot",
        required=True,
        help="Path to a local snapshot JSON file.",
    )
    parser.add_argument(
        "--message",
        required=True,
        help="User review message, for example: 'HPSP 신호 왔어?'",
    )
    parser.add_argument(
        "--active-symbol",
        default=None,
        help="Optional active symbol fallback when the message has no symbol.",
    )
    parser.add_argument(
        "--current-model-answer",
        default=None,
        help="Optional existing answer text to check against packet guardrails.",
    )
    parser.add_argument(
        "--time-kst",
        default=None,
        help="Optional display/reference time such as 2026-06-11T10:35:00+09:00.",
    )
    parser.add_argument(
        "--snapshot-reference-time",
        default=None,
        help="Optional deterministic reference time for snapshot age checks.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    snapshot = load_snapshot(args.snapshot)
    result = build_handoff_from_message(
        {
            "message": args.message,
            "active_symbol": args.active_symbol,
            "snapshot": snapshot,
            "current_model_answer": args.current_model_answer,
            "time_kst": args.time_kst,
            "snapshot_reference_time": args.snapshot_reference_time,
        }
    )
    print(result.packet_markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
