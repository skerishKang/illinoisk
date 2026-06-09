#!/usr/bin/env python3
"""
Test Kiwoom API for volume comparison fields (동시간대 거래량비교)
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

APP_KEY = os.getenv("KIWOOM_APPKEY")
SECRET_KEY = os.getenv("KIWOOM_SECRETKEY")

def get_token():
    """Get Kiwoom access token"""
    url = "https://api.kiwoom.com/oauth2/token"
    data = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "secretkey": SECRET_KEY
    }
    r = requests.post(url, json=data, timeout=10)
    return r.json().get("token")

def call_ka10001(token, stk_cd):
    """Call ka10001 - 현재가"""
    url = "https://api.kiwoom.com/api/dostk/stkinfo"
    headers = {
        "api-id": "ka10001",
        "authorization": f"Bearer {token}",
        "cont-yn": "N",
        "next-key": "",
        "Content-Type": "application/json;charset=UTF-8"
    }
    body = {"stk_cd": stk_cd}
    r = requests.post(url, headers=headers, json=body, timeout=10)
    return r.json()

def call_ka10080(token, stk_cd, nmin="1", qrycnt="100", tic_scope="0"):
    """Call ka10080 - 분봉/일봉 차트"""
    url = "https://api.kiwoom.com/api/dostk/chart"
    headers = {
        "api-id": "ka10080",
        "authorization": f"Bearer {token}",
        "cont-yn": "N",
        "next-key": "",
        "Content-Type": "application/json;charset=UTF-8"
    }
    body = {
        "stk_cd": stk_cd,
        "nmin": nmin,
        "qrycnt": qrycnt,
        "tic_scope": tic_scope,
        "upd_stkpc_tp": "0"
    }
    r = requests.post(url, headers=headers, json=body, timeout=10)
    return r.json()

def call_ka10081(token, stk_cd, base_dt, qrycnt="100"):
    """Call ka10081 - 일봉 차트 (base_dt 필수)"""
    url = "https://api.kiwoom.com/api/dostk/chart"
    headers = {
        "api-id": "ka10081",
        "authorization": f"Bearer {token}",
        "cont-yn": "N",
        "next-key": "",
        "Content-Type": "application/json;charset=UTF-8"
    }
    body = {
        "stk_cd": stk_cd,
        "base_dt": base_dt,
        "qrycnt": qrycnt,
        "upd_stkpc_tp": "0"
    }
    r = requests.post(url, headers=headers, json=body, timeout=10)
    return r.json()

def main():
    token = get_token()
    print("=" * 80)
    print("TOKEN:", token[:20] + "...")
    print("=" * 80)
    
    # Test with SK하이닉스 (000660)
    stk_cd = "000660"
    
    print("\n" + "=" * 80)
    print("KA10001 - 현재가 (정규장)")
    print("=" * 80)
    result = call_ka10001(token, stk_cd)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    print("\n" + "=" * 80)
    print("KA10001 - 현재가 (NXT)")
    print("=" * 80)
    result_nx = call_ka10001(token, f"{stk_cd}_NX")
    print(json.dumps(result_nx, ensure_ascii=False, indent=2))
    
    print("\n" + "=" * 80)
    print("KA10080 - 1분봉 (최근 30개) - tic_scope=0 (일봉재구성)")
    print("=" * 80)
    result_1min = call_ka10080(token, stk_cd, nmin="1", qrycnt="30", tic_scope="0")
    print(json.dumps(result_1min, ensure_ascii=False, indent=2))
    
    print("\n" + "=" * 80)
    print("KA10081 - 일봉 (base_dt=20260607) - 전일 종가 기준")
    print("=" * 80)
    result_daily = call_ka10081(token, stk_cd, base_dt="20260607", qrycnt="10")
    print(json.dumps(result_daily, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
