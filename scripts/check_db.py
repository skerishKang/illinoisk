#!/usr/bin/env python3
"""illinoisK — DB 내용 확인"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "DB", "illinoisK.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

for table in ['market_snapshots', 'news', 'notes', 'watchlist', 'predictions']:
    row = conn.execute(f'SELECT count(*) as c FROM {table}').fetchone()
    print(f'📊 {table}: {row["c"]}건')

print()
print('=== market_snapshots ===')
for r in conn.execute('SELECT name, category, price, change_pct FROM market_snapshots'):
    chg = f'{r["change_pct"]:+.2f}%' if r["change_pct"] else '-'
    print(f'  {r["name"]:12s} ({r["category"]:4s}) → ${r["price"]:<10} {chg}')

print()
print('=== news (source별) ===')
for r in conn.execute('SELECT source, title FROM news ORDER BY published_at DESC'):
    print(f'  [{r["source"]}] {r["title"][:50]}')

print()
print('=== notes ===')
for r in conn.execute('SELECT type, title FROM notes'):
    print(f'  [{r["type"]}] {r["title"]}')

conn.close()