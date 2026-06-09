#!/usr/bin/env python3
"""illinoisK 대시보드 서버 — DB 기반 웹 UI"""
import http.server, json, os, sqlite3, socketserver, urllib.parse, sys

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(DIR, "DB", "illinoisK.db")

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        p = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(p.query)

        if p.path == "/api/watchlist":
            return self._json(self.q("SELECT id,symbol,name,market,sector,reason,added_at FROM watchlist ORDER BY added_at DESC"))
        if p.path == "/api/search":
            kw = q.get("q",[""])[0]
            rows = self.q("SELECT code,name,market,price,shares,market_cap,margin_rate FROM stock_list WHERE name LIKE ? OR code LIKE ? ORDER BY market_cap DESC LIMIT 20", (f"%{kw}%",f"%{kw}%")) if kw else []
            for r in rows: r["market_cap_b"] = (r["market_cap"] or 0)//100000000
            return self._json(rows)
        if p.path == "/api/stock":
            code = q.get("code",[""])[0]
            s = self.q1("SELECT code,name,market,price,shares,market_cap,listed_date,margin_rate FROM stock_list WHERE code=?", (code,))
            w = self.q1("SELECT id,reason,added_at FROM watchlist WHERE symbol=?", (code,))
            if s: s["market_cap_b"] = (s["market_cap"] or 0)//100000000; s["watchlist"] = dict(w) if w else None
            return self._json(s)
        if p.path == "/api/market-snapshots":
            return self._json(self.q("SELECT * FROM market_snapshots ORDER BY category,name"))
        if p.path == "/api/news":
            return self._json(self.q("SELECT * FROM news ORDER BY published_at DESC LIMIT 20"))
        if p.path == "/api/add-watchlist":
            sym = q.get("symbol",[""])[0]
            if not sym: return self._json({"error":"symbol required"})
            conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
            if conn.execute("SELECT id FROM watchlist WHERE symbol=?",(sym,)).fetchone(): conn.close(); return self._json({"error":"already exists"})
            st = conn.execute("SELECT name,market,margin_rate FROM stock_list WHERE code=?",(sym,)).fetchone()
            n=st["name"] if st else sym; m=st["market"] if st else None; sc=st["margin_rate"] if st else None
            conn.execute("INSERT INTO watchlist(symbol,name,market,sector,reason,added_at) VALUES(?,?,?,?,?,datetime('now','+9 hours'))",(sym,n,m,sc,q.get("reason",[""])[0]))
            conn.commit(); conn.close()
            return self._json({"success":True,"name":n})
        if p.path == "/api/remove-watchlist":
            i = q.get("id",[None])[0]
            if i: conn=sqlite3.connect(DB_PATH); conn.execute("DELETE FROM watchlist WHERE id=?",(i,)); conn.commit(); conn.close()
            return self._json({"success":True})
        super().do_GET()
    def q(self,s,p=()):
        conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row
        r=[dict(r) for r in conn.execute(s,p).fetchall()]; conn.close(); return r
    def q1(self,s,p=()):
        conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row
        r=conn.execute(s,p).fetchone(); conn.close(); return dict(r) if r else None
    def _json(self,d):
        b=json.dumps(d,ensure_ascii=False,default=str).encode()
        self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin","*"); self.send_header("Content-Length",str(len(b)))
        self.end_headers(); self.wfile.write(b)
    def log_message(self,*a): pass

if __name__=="__main__":
    os.chdir(DIR)
    port=8898
    while True:
        try:
            s=socketserver.TCPServer(("0.0.0.0",port),Handler)
            break
        except OSError:
            port+=1
    print(f"🚀 http://localhost:{port}/dashboard.html  |  API: /api/watchlist /api/search?q=삼성 /api/market-snapshots")
    sys.stdout.flush()
    s.serve_forever()
