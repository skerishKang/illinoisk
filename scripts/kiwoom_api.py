#!/usr/bin/env python3
"""키움 REST API 설정 — 키값은 이 파일에서만 참조, 채팅에 출력 금지"""
import json
import os
import subprocess
import sys

# ─── 트레이스 헬퍼 ───
sys.path.insert(0, os.path.dirname(__file__))
from trace_helper import new_trace, traced, start_span, end_span, span, inject_trace_env

# 키 파일 위치 (절대 채팅/로그에 값 노출 금지)
APPKEY_FILE = "/mnt/g/Ddrive/BatangD/task/workdiary/65stock/keys/appkey.txt"
SECRETKEY_FILE = "/mnt/g/Ddrive/BatangD/task/workdiary/65stock/keys/secretkey.txt"

# 실제 키움 API 접속 도메인 (실전)
BASE_URL = "https://api.kiwoom.com"


@traced("kiwoom-load-keys", "앱키/시크릿키 파일 로드")
def load_keys():
    with open(APPKEY_FILE) as f:
        appkey = f.read().strip()
    with open(SECRETKEY_FILE) as f:
        secretkey = f.read().strip()
    return appkey, secretkey


@traced("kiwoom-get-token", "OAuth2 토큰 발급 (curl)")
def get_token():
    """OAuth2 토큰 발급"""
    appkey, secretkey = load_keys()
    r = subprocess.run(
        ['curl', '-s', '-X', 'POST', f'{BASE_URL}/oauth2/token',
         '-H', 'Content-Type: application/json',
         '-d', json.dumps({"grant_type":"client_credentials","appkey":appkey,"secretkey":secretkey})],
        capture_output=True, text=True, timeout=15)
    data = json.loads(r.stdout)
    if data.get("return_code") != 0:
        raise Exception(f"토큰 발급 실패: {data.get('return_msg')}")
    return data["token"].strip()


@traced("kiwoom-ka10080", "분봉 차트 조회 ka10080 (curl)")
def fetch_chart(code, tick_scope="30"):
    """분봉 차트 조회 (ka10080)"""
    with span("kiwoom-get-token", "차트 조회용 토큰 발급"):
        token = get_token()
    
    r = subprocess.run(
        ['curl', '-s', '-X', 'POST', f'{BASE_URL}/api/dostk/chart',
         '-H', f'Authorization: Bearer {token}',
         '-H', 'Content-Type: application/json;charset=UTF-8',
         '-H', 'api-id: ka10080',
         '-d', json.dumps({"stk_cd": code, "tic_scope": tick_scope, "upd_stkpc_tp": "1"})],
        capture_output=True, text=True, timeout=15)
    return json.loads(r.stdout)


if __name__ == "__main__":
    # 트레이스 시작
    trace_id = new_trace("kiwoom-api-test")
    os.environ.update(inject_trace_env())
    
    # 간단 테스트
    token = get_token()
    print(f"토큰 발급 성공: {token[:20]}...")
    data = fetch_chart("005930", "30")
    rows = data.get("stk_min_pole_chart_qry", [])
    print(f"삼성전자 30분봉: {len(rows)}개 데이터 포인트")
