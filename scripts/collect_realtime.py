#!/usr/bin/env python3
"""illinoisK 실시간 시세 수집기 - 트레이스 적용"""
import os
import sys
import json
import sqlite3
import requests
from datetime import datetime, timezone, timedelta

# ─── 트레이스 헬퍼 ───
sys.path.insert(0, os.path.dirname(__file__))
from trace_helper import new_trace, start_span, end_span, traced, inject_trace_env, span

KST = timezone(timedelta(hours=9))
BASE = "/mnt/g/Ddrive/BatangD/task/workdiary/illinoisK"
DB = os.path.join(BASE, "DB", "illinoisK.db")
RT = os.path.join(BASE, "realtime")
AK = "N248MlQKSoL6zY-dNF0jXEz09EE_nXrA77ev4XuscV8"
SK = "GXFAgPOeRKFOl94WRwhZWADwFlXhHSF6eOJtNBV2tZ4"

ST = [
    ("005930", "삼전자", "KOSPI"),
    ("000660", "SK하이닉스", "KOSPI"),
    ("005935", "삼전자우", "KOSPI"),
    ("058470", "리노공업", "KOSDAQ"),
    ("240810", "원익IPS", "KOSDAQ"),
    ("039030", "이오테크닉스", "KOSDAQ"),
    ("005290", "동진쎄미켐", "KOSDAQ"),
    ("095340", "ISC", "KOSDAQ"),
    ("131970", "두산테스나", "KOSDAQ"),
    ("403870", "HPSP", "KOSDAQ"),
    ("042700", "한미반도체", "KOSDAQ"),
    ("036930", "주성엔지니어링", "KOSDAQ"),
    # 확장 관심종목 (2026-06-06 추가)
    ("080220", "제주반도체", "KOSDAQ"),
    ("067310", "하나마이크론", "KOSDAQ"),
    ("007660", "이수페타시스", "KOSDAQ"),
    ("319660", "피에스케이", "KOSDAQ"),
    ("489790", "한화비전", "KOSDAQ"),
    ("353200", "대덕전자", "KOSDAQ"),
    ("281820", "케이씨텍", "KOSDAQ"),
    ("102710", "이엔에프테크놀로지", "KOSDAQ"),
    ("357780", "솔브레인", "KOSDAQ"),
    ("232140", "와이씨", "KOSDAQ"),
    ("039440", "에스티아이", "KOSDAQ"),
    ("098460", "고영", "KOSDAQ"),
    ("095610", "테스", "KOSDAQ"),
    ("084370", "유진테크", "KOSDAQ"),
    ("222800", "심텍", "KOSDAQ"),
    ("056190", "에스에프에이", "KOSDAQ"),
    ("101490", "에스앤에스텍", "KOSDAQ"),
    ("083450", "GST", "KOSDAQ"),
    ("183490", "코미코", "KOSDAQ"),
    ("036540", "SFA반도체", "KOSDAQ"),
    ("003160", "디아이", "KOSDAQ"),
    ("000990", "DB하이텍", "KOSPI"),
]


@traced("kiwoom-get-token", "키움 OAuth2 토큰 발급")
def get_token() -> str:
    r = requests.post(
        "https://api.kiwoom.com/oauth2/token",
        json={"grant_type": "client_credentials", "appkey": AK, "secretkey": SK},
        timeout=10,
    )
    return r.json().get("token", "")


@traced("kiwoom-ka10001", "단일 종목 현재가 조회 (ka10001)")
def fetch_price(token: str, code: str, suffix: str = "") -> dict | None:
    h = {
        "api-id": "ka10001",
        "authorization": f"Bearer {token}",
        "cont-yn": "N",
        "next-key": "",
        "Content-Type": "application/json;charset=UTF-8",
    }
    try:
        r = requests.post(
            "https://api.kiwoom.com/api/dostk/stkinfo",
            json={"stk_cd": f"{code}{suffix}"},
            headers=h,
            timeout=10,
        )
        d = r.json()
        if d.get("return_code") == 0:
            def pv(v):
                if not v:
                    return 0
                s = str(v).replace(",", "").replace("+", "").replace("-", "")
                try:
                    return int(float(s)) if s else 0
                except Exception:
                    return 0
            
            raw_price = str(d.get("cur_prc", "0"))
            is_negative = raw_price.startswith("-")
            pr = pv(raw_price)
            if is_negative and suffix == "_NX":
                # NXT 가격은 음수로 내려옴 (키움 관례) → 절대값이 실가
                pass  # pv()가 이미 절대값 반환
            try:
                fl = float(d.get("flu_rt", 0))
            except Exception:
                fl = 0.0
            return {"price": pr, "flu_rt": fl, "volume": pv(d.get("trde_qty")), "has_data": True}
        else:
            return {"has_data": False}
    except Exception:
        return {"has_data": False}


@traced("db-upsert-prices", "수집된 시세 DB 저장")
def upsert_prices(conn: sqlite3.Connection, rows: list[dict]) -> int:
    count = 0
    for row in rows:
        conn.execute(
            "INSERT OR IGNORE INTO stock_prices(captured_at,code,name,market,price,flu_rt,volume,source) VALUES(?,?,?,?,?,?,?,?)",
            (row["captured_at"], row["code"], row["name"], row["market"], row["price"], row["flu_rt"], row["volume"], row["source"]),
        )
        count += 1
    conn.commit()
    return count


def main():
    # 트레이스 시작
    trace_id = new_trace("collect-realtime")
    os.environ.update(inject_trace_env())  # 자식 프로세스 전파용
    
    now = datetime.now(KST)
    cap = now.isoformat()
    
    span_token = start_span("main-flow", "실시간 수집 메인 플로우 시작")
    
    token = get_token()
    if not token:
        end_span(span_token, "error", error="토큰 발급 실패")
        return
    
    all_rows = []
    
    # 09:00 이후엔 NXT(_NX) 호출 안 함 - 키움 _NX 피드 불완전함
    now_hm = now.strftime("%H:%M")
    is_regular = now_hm >= "09:00"
    markets = [("KRX", "")] if is_regular else [("KRX", ""), ("NXT", "_NX")]
    
    with span("collect-all-stocks", f"{len(ST)}종목 × {len(markets)}시장 수집") as span_obj:
        for code, name, market in ST:
            for src, suffix in markets:
                data = fetch_price(token, code, suffix)
                if data and data.get("has_data") and data["price"] > 0:
                    all_rows.append({
                        "captured_at": cap,
                        "code": code,
                        "name": name,
                        "market": market,
                        "price": data["price"],
                        "flu_rt": data["flu_rt"],
                        "volume": data["volume"],
                        "source": src,
                    })
                elif not (data and data.get("has_data")):
                    print(f"⚠️ SKIP {name}({code}) {src}{suffix}: has_data={data.get('has_data') if data else 'no response'}")
                elif data["price"] <= 0:
                    print(f"⚠️ SKIP {name}({code}) {src}{suffix}: price={data['price']}")
        span_obj["attrs"]["collected_count"] = len(all_rows)
    
    if all_rows:
        with span("save-to-db", f"DB 저장 + realtime/latest.json 갱신") as span_obj:
            conn = sqlite3.connect(DB)
            saved = upsert_prices(conn, all_rows)
            conn.close()
            
            os.makedirs(RT, exist_ok=True)
            with open(os.path.join(RT, "latest.json"), "w", encoding="utf-8") as f:
                json.dump({"captured_at": cap, "count": len(all_rows), "stocks": all_rows}, f, ensure_ascii=False)
            
            span_obj["attrs"]["saved_count"] = saved
            span_obj["attrs"]["json_updated"] = True
    
    end_span(span_token, "ok", collected=len(all_rows), saved=len(all_rows) if all_rows else 0)
    print(f"[{datetime.now(KST).strftime('%H:%M:%S')}] illinoisK: {len(all_rows)} pts (trace: {trace_id})")


if __name__ == "__main__":
    main()