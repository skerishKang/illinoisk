# 🔑 키움증권 REST API

## 인증 정보

API 키는 `AGENTS.md` 참조. (단일 진실 공급원)

## 토큰 발급

```python
POST https://api.kiwoom.com/oauth2/token
{"grant_type":"client_credentials", "appkey": APP_KEY, "secretkey": SECRET_KEY}
→ token (24h 유효)
```

## API Endpoints

| API | URI | 용도 |
|:---|:----|:------|
| ka10001 | `/api/dostk/stkinfo` | 현재가 (KRX + NXT) |
| ka10002 | `/api/dostk/stkinfo` | 거래원 (신한/키움) |
| ka10004 | `/api/dostk/mrkcond` | 호가 (10단계) |
| ka10095 | `/api/dostk/stkinfo` | 지수 (001=KOSPI, 101=KOSDAQ) |
| ka10008 | `/api/dostk/frgnistt` | 외국인 매매동향 |
| ka10080 | `/api/dostk/chart` | 분봉 차트 |

## NXT 데이터 (중요!)

NXT 데이터는 `stk_cd` 뒤에 `_NX` 붙임:
```python
# KRX
{"stk_cd": "005930"}
# NXT
{"stk_cd": "005930_NX"}
```

**동작 패턴:**
- 08:00~08:30: cur_prc=0 (아직 체결 없음)
- 08:30~09:00: 실제 프리장 가격 리턴
- 09:00~: 정규장과 동일

## 가격 파싱

모든 가격 필드(cur_prc, high_pric, low_pric, open_pric)는 `+`/`-` 접두사 있음.
```python
raw = str(data.get("cur_prc","0")).replace(",","")
if raw.startswith("-") or raw.startswith("+"):
    price = int(raw[1:]) if raw[1:] else 0
is_down = raw.startswith("-")
```
