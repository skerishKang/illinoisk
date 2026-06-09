#!/usr/bin/env python3
"""
illinoisK — 주식/시장 데이터베이스 초기화
실행: python3 scripts/init_db.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "DB", "illinoisK.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init():
    conn = get_db()
    cur = conn.cursor()

    # ── 시장 스냅샷 (WTI, Brent, 선물, 코인 실시간) ──
    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            captured_at TEXT NOT NULL,
            captured_kst TEXT NOT NULL,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            price REAL,
            change_pct REAL,
            source_url TEXT
        )
    """)

    # ── 뉴스 ──
    cur.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            captured_at TEXT NOT NULL,
            captured_kst TEXT NOT NULL,
            published_at TEXT,
            source TEXT,
            url TEXT,
            title TEXT NOT NULL,
            summary TEXT,
            category TEXT,
            region TEXT,
            keywords TEXT,
            market_impact TEXT
        )
    """)

    # ── 관심종목 ──
    cur.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            name TEXT,
            market TEXT,
            sector TEXT,
            reason TEXT,
            added_at TEXT DEFAULT (datetime('now', '+9 hours'))
        )
    """)

    # ── 분석/예측 노트 ──
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            created_kst TEXT NOT NULL,
            type TEXT NOT NULL,
            symbol TEXT,
            title TEXT,
            content TEXT,
            tags TEXT
        )
    """)

    # ── 예측 결과 트래킹 ──
    cur.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            created_kst TEXT NOT NULL,
            symbol TEXT,
            direction TEXT,
            target_price REAL,
            target_date TEXT,
            reason TEXT,
            outcome TEXT DEFAULT '미판정',
            outcome_date TEXT,
            outcome_note TEXT
        )
    """)

    conn.commit()
    conn.close()
    print(f"✅ DB 초기화 완료: {DB_PATH}")
    print(f"   테이블: market_snapshots, news, watchlist, notes, predictions")

if __name__ == "__main__":
    init()
