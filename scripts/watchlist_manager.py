#!/usr/bin/env python3
"""
watchlist_manager.py — 관심종목 CRUD + 종목 검색 CLI
사용법:
  python3 scripts/watchlist_manager.py list
  python3 scripts/watchlist_manager.py search 삼성
  python3 scripts/watchlist_manager.py add 005930 --reason "대표 성장주"
  python3 scripts/watchlist_manager.py remove 3
  python3 scripts/watchlist_manager.py info 005930
  python3 scripts/watchlist_manager.py clear
"""
import sqlite3
import argparse
import sys
import os
from datetime import datetime, timezone, timedelta

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "DB", "illinoisK.db")
KST = timezone(timedelta(hours=9))


def _conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def fmt_dt(dt_str):
    # YYYY-MM-DD HH:MM:SS -> MM-DD HH:MM
    if not dt_str:
        return "-"
    return dt_str[5:16]  # MM-DD HH:MM


# ───────────────────── list ─────────────────────
def cmd_list(_):
    conn = _conn()
    rows = conn.execute(
        "SELECT id, symbol, name, market, sector, reason, added_at FROM watchlist ORDER BY added_at DESC"
    ).fetchall()
    conn.close()

    if not rows:
        print("watchlist가 비어 있습니다.")
        return

    header = f"{'ID':>4}  {'심볼':<8} {'이름':<12} {'시장':<8} {'업종':<12} {'추가일':<12} {'이유'}"
    print(header)
    print("-" * len(header))
    for r in rows:
        name = (r["name"] or "-")[:12]
        sector = (r["sector"] or "-")[:12]
        reason = (r["reason"] or "-")[:36]
        print(f"{r['id']:>4}  {r['symbol']:<8} {name:<12} {(r['market'] or '-'):<8} {sector:<12} {fmt_dt(r['added_at']):<12} {reason}")
    print(f"\n총 {len(rows)}개 관심종목")


# ───────────────────── search ─────────────────────
def cmd_search(args):
    keyword = args.keyword
    conn = _conn()
    # stock_list에서 이름 또는 코드로 LIKE 검색
    rows = conn.execute(
        """
        SELECT code, name, market, price, shares, market_cap, margin_rate
        FROM stock_list
        WHERE name LIKE ? OR code LIKE ?
        ORDER BY market_cap DESC
        LIMIT 20
        """,
        (f"%{keyword}%", f"%{keyword}%"),
    ).fetchall()
    conn.close()

    if not rows:
        print(f"'{keyword}' 에 해당하는 종목을 찾을 수 없습니다.")
        return

    header = f"{'코드':<8} {'이름':<16} {'시장':<8} {'주가':>10} {'시총(억)':>12} {'증거금':<6}"
    print(header)
    print("-" * len(header))
    for r in rows:
        mc = (r["market_cap"] or 0) // 100000000  # 억 단위
        print(f"{r['code']:<8} {(r['name'] or '-'):<16} {(r['market'] or '-'):<8} {(r['price'] or 0):>10,} {mc:>12,} {(r['margin_rate'] or '-'):<6}")
    print(f"\n총 {len(rows)}개 검색결과")


# ───────────────────── add ─────────────────────
def cmd_add(args):
    conn = _conn()

    # stock_list에서 symbol 조회 → 자동 채움
    stock = conn.execute(
        "SELECT name, market, price, margin_rate FROM stock_list WHERE code = ?",
        (args.symbol,),
    ).fetchone()

    name = args.name or (stock["name"] if stock else None)
    market = args.market or (stock["market"] if stock else None)
    sector = args.sector or (stock["margin_rate"] if stock else None)
    reason = args.reason or ""

    if not name:
        print(f"오류: 종목코드 {args.symbol}에 대한 정보가 stock_list에 없습니다. --name으로 직접 지정하세요.")
        sys.exit(1)

    # 중복 체크
    dup = conn.execute(
        "SELECT id FROM watchlist WHERE symbol = ?", (args.symbol,)
    ).fetchone()
    if dup:
        print(f"이미 watchlist에 존재합니다. (ID: {dup['id']})")
        sys.exit(1)

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO watchlist (symbol, name, market, sector, reason, added_at)
        VALUES (?, ?, ?, ?, ?, datetime('now', '+9 hours'))
        """,
        (args.symbol, name, market, sector, reason),
    )
    new_id = cur.lastrowid
    conn.commit()
    conn.close()

    print(f"✅ 추가 완료  ID: {new_id}  {name} ({args.symbol})")
    if reason:
        print(f"   이유: {reason}")


# ───────────────────── remove ─────────────────────
def cmd_remove(args):
    conn = _conn()
    row = conn.execute(
        "SELECT id, symbol, name FROM watchlist WHERE id = ?", (args.id,)
    ).fetchone()
    if not row:
        print(f"ID {args.id} 를 찾을 수 없습니다.")
        sys.exit(1)

    conn.execute("DELETE FROM watchlist WHERE id = ?", (args.id,))
    conn.commit()
    conn.close()
    print(f"🗑️  삭제 완료  ID {row['id']} — {row['name']} ({row['symbol']})")


# ───────────────────── info ─────────────────────
def cmd_info(args):
    conn = _conn()
    stock = conn.execute(
        "SELECT code, name, market, price, shares, market_cap, listed_date, margin_rate FROM stock_list WHERE code = ?",
        (args.symbol,),
    ).fetchone()

    wl = conn.execute(
        "SELECT id, reason, added_at FROM watchlist WHERE symbol = ?",
        (args.symbol,),
    ).fetchone()
    conn.close()

    if not stock:
        print(f"종목코드 {args.symbol} 를 stock_list에서 찾을 수 없습니다.")
        sys.exit(1)

    mc = (stock["market_cap"] or 0) // 100000000
    print(f"{'─'*50}")
    print(f"📌 {stock['name']}  ({stock['code']})")
    print(f"{'─'*50}")
    print(f"  시장:      {stock['market'] or '-'}")
    print(f"  주가:      {stock['price'] or 0:,} 원")
    print(f"  시총:      {mc:,} 억")
    print(f"  발행주:    {(stock['shares'] or 0):,} 주")
    print(f"  상장일:    {stock['listed_date'] or '-'}")
    print(f"  증거금:    {stock['margin_rate'] or '-'}")
    if wl:
        print(f"  ⭐ 관심등록: O  (ID {wl['id']}, {fmt_dt(wl['added_at'])})")
        if wl["reason"]:
            print(f"     이유: {wl['reason']}")
    else:
        print(f"  ⭐ 관심등록: X")
    print(f"{'─'*50}")


# ───────────────────── clear ─────────────────────
def cmd_clear(args):
    if not args.force:
        ans = input("watchlist 전체를 삭제할까요? [y/N]: ").strip().lower()
        if ans not in ("y", "yes"):
            print("취소되었습니다.")
            return
    conn = _conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM watchlist")
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    print(f"🗑️  {deleted}개 항목을 삭제했습니다.")


def main():
    parser = argparse.ArgumentParser(
        description="관심종목(watchlist) 관리 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python3 scripts/watchlist_manager.py list
  python3 scripts/watchlist_manager.py search 삼성
  python3 scripts/watchlist_manager.py add 005930 --reason "시총 1위 블루칩"
  python3 scripts/watchlist_manager.py info 005930
  python3 scripts/watchlist_manager.py remove 2
  python3 scripts/watchlist_manager.py clear --force
""",
    )
    sub = parser.add_subparsers(dest="command", help="명령")

    # list
    sub.add_parser("list", help="watchlist 전체 조회")

    # search
    p_search = sub.add_parser("search", help="stock_list에서 종목 검색 (이름/코드)")
    p_search.add_argument("keyword", help="검색어")

    # add
    p_add = sub.add_parser("add", help="watchlist에 종목 추가")
    p_add.add_argument("symbol", help="종목코드 (예: 005930)")
    p_add.add_argument("--name", help="종목명 (stock_list에 있으면 자동)")
    p_add.add_argument("--market", help="시장 (예: KOSPI)")
    p_add.add_argument("--sector", help="업종/섹터")
    p_add.add_argument("--reason", help="추가 이유")

    # remove
    p_rem = sub.add_parser("remove", help="ID로 watchlist 항목 삭제")
    p_rem.add_argument("id", type=int, help="삭제할 watchlist ID")

    # info
    p_info = sub.add_parser("info", help="특정 종목 상세 정보 + watchlist 여부")
    p_info.add_argument("symbol", help="종목코드")

    # clear
    p_clear = sub.add_parser("clear", help="watchlist 전체 삭제")
    p_clear.add_argument("--force", action="store_true", help="확인 없이 즉시 삭제")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "list": cmd_list,
        "search": cmd_search,
        "add": cmd_add,
        "remove": cmd_remove,
        "info": cmd_info,
        "clear": cmd_clear,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
