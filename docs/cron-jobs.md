# ⏰ 크론 작업

*모든 크론은 DeepSeek 사용, workdir=illinoisK 설정*

## 작업 목록

| 시간 | 작업 | 전달 | 비고 |
|:----:|:-----|:----:|:-----|
| 07:00 | 🇺🇸 미국장 요약 | origin | S&P, 나스닥, WTI, 환율 |
| 07:30 | 📋 매매준비 | origin | context_from 3개 |
| **08:30** | **📊 NXT 동시호가 체크** | **origin** | **12종목 NXT + 테마** |
| **09:01** | **🏁 정규장 오픈체크** | **origin** | **12종목 KRX + 거래원** |
| 매분 | 📡 실시간 수집 | local (no_agent) | DB에 시세 저장 |
| 15:40 | 📊 일일 매매 복기 | origin | session_search |
| 21:00 | 🇰🇷 국장 마감 정리 | origin | 지수, 수급, NXT |

## 컨텍스트 체이닝

```
전날 15:40 📊 매매복기 ──┐
전날 21:00 🇰🇷 국장마감  ──┤  context_from
오늘 07:00 🇺🇸 미국장요약──┘       ↓
                         오늘 07:30 📋 매매준비
```

## ⚠️ 중요: Kiwoom API 크론 = 두 스킬 필수

Kiwoom API 호출하는 크론은 반드시:
```python
skills: ["stock-market-analysis", "kiwoom-stock-api"]
```

`kiwoom-stock-api` 빠지면 180초 타임아웃 실패 (2026-05-29 실제 사례).

## 실시간 수집기

- 스크립트: `illinoisK_collect.py` (in `~/.hermes/scripts/`)
- 1분마다 12종목 KRX+NXT 수집 → DB 저장 + latest.json 갱신
- no_agent 모드 (LLM 사용 안 함, 빠름)
