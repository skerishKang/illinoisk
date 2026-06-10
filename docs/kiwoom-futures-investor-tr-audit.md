# Kiwoom 선물/옵션 투자자별 매매동향 TR 후보 감사 문서

## 목적
`scripts/scan_golden_cross.py`의 `fetch_futures_frgn_inst()` 함수에 실제 Kiwoom REST API 연결 전, 사용 가능한 TR 후보를 정리하고 적용 가능성을 검토한다.

---

## 1. 현황 요약

| 항목 | 상태 |
|------|------|
| 현재 구현 | `fetch_futures_frgn_inst()` 스텁 — `{"frgn_net": 0, "inst_net": 0, "source": "unavailable"}` 반환 |
| 호출 위치 | `fetch_market_overview()` 내부 — 시장 개요 최상단에 외인/기관 선물 수급 표시 |
| 출력 위치 | `print_market_overview()` / `main()` 리포트 생성 — `[선물] 외인 순매수/순매도` 필드 포함 |
| 실제 API 호출 | 없음 (TODO 상태 유지) |
| 전략 문서 연동 | `strategies/박사님_RSI_2퍼_시스템.md` — 외인 선물 순매도 시 진입 기준 강화 규칙 반영됨 (PR #8) |

---

## 2. 후보 TR 리스트

### 2.1 opt10039 / opt10040 — 투자자별 매매동향 (주식/시장)

| TR 코드 | 명칭 | 설명 |
|---------|------|------|
| opt10039 | 투자자별 매매동향(일별) | 일자별 개인/외인/기관/기타 순매수 수량 제공 |
| opt10040 | 투자자별 매매동향(분별) | 분별 개인/외인/기관/기타 순매수 수량 제공 |

**적용 가능성 검토:**
- ✅ 주식시장(KOSPI/KOSDAQ) 개별 종목/업종/시장 전체에 대해 투자자별 수급 확인 가능
- ⚠️ **선물(KOSPI200) 직접 지원 여부 불확실** — 공식 문서 기준으로 주식시장 기준 TR로 분류됨
- ⚠️ `ka10010`(프로그램매매동향)과 혼동 주의 — `ka10010`은 주식 프로그램매매/차익/비차익 기준
- 🔍 **확인 필요**: REST API `dostk/chart`/`dostk/rkinfo` 엔드포인트에서 `tr_cd: "opt10039"`로 선물 지수(106F200 등) 조회 가능한지

**테스트 방법:**
```bash
curl -X POST https://api.kiwoom.com/api/dostk/rkinfo \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"tr_cd": "opt10039", "tr_cont": "N", "tr_cont_key": "", "input": {"stk_cd": "106F200"}}'
```
- `stk_cd`에 선물 종목코드(106F200 등) 넣었을 때 정상 응답 오는지 확인
- 응답에 `개인`, `외국인`, `기관`, `기타` 필드 포함되는지 확인

---

### 2.2 opt50001~opt50099 — 선물/옵션 계열

| TR 코드 | 명칭 | 설명 |
|---------|------|------|
| opt50001 | 선물/옵션 현재가 | 선물/옵션 실시간 현재가/체결량 |
| opt50002 | 선물/옵션 호가 | 선물/옵션 호가 잔량 |
| opt50003 | 선물/옵션 체결 | 선물/옵션 체결 내역 |
| opt50004 | 선물/옵션 투자자별 | **선물/옵션 투자자별 매매동향 (후보)** |
| opt50005 | 선물/옵션 미결제약정 | 미결제약정 수량/증감 |

**적용 가능성 검토:**
- ✅ **opt50004 "선물/옵션 투자자별"이 가장 유력** — 명칭상 선물/옵션 전용 투자자별 수급
- ⚠️ 실전 사용 사례(커뮤니티/공식문서) 드물어 응답 포맷 불확실
- ⚠️ KOSPI200 선물(106F200) 외에 미니선물, 옵션 등 구분 필요
- 🔍 **확인 필요**: REST API에서 `tr_cd: "opt50004"` 지원 여부, 입력 파라미터, 출력 필드

**테스트 방법:**
```bash
curl -X POST https://api.kiwoom.com/api/dostk/rkinfo \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"tr_cd": "opt50004", "tr_cont": "N", "tr_cont_key": "", "input": {"stk_cd": "106F200"}}'
```

---

### 2.3 ka10010 — 프로그램매매동향 (주식)

| TR 코드 | 명칭 | 설명 |
|---------|------|------|
| ka10010 | 프로그램매매동향 | 주식시장 프로그램 매매(차익/비차익) 순매수 |

**적용 가능성 검토:**
- ❌ **선물 외인/기관 수급 대용 불가** — 주식 프로그램매매 기준(차익/비차익)
- ❌ 외인/기관 구분 없이 "프로그램" 단일 주체로 집계
- ✅ 현재 `scan_golden_cross.py`에서 별도로 `fetch_program_batch()`로 조회 중 — **용도 다름**

---

### 2.4 기타 후보

| TR/엔드포인트 | 비고 |
|---------------|------|
| `dostk/futures` 계열 | 선물 전용 엔드포인트 존재 여부 확인 필요 (REST API 문서에 별도 섹션 있을 수 있음) |
| `kt10000` 계열 | 실시간(웹소켓) 수급 — 구현 복잡도 높음, polling 기반이면 REST 우선 |
| OpenAPI+ (COM/OCX) | 레거시 — REST API로 충분하면 비권장 |

---

## 3. 추천 검증 순서

| 순위 | TR/방법 | 이유 |
|------|---------|------|
| 1 | **opt50004** | 선물/옵션 전용 투자자별 매매동향 — 명칭상 정확히 일치 |
| 2 | **opt10039/10040 with 선물코드** | 주식 TR이나 선물코드 허용 시 가장 간단 |
| 3 | **실시간 웹소켓(kt10000 계열)** | REST 불가 시 대안, 구현 복잡 |
| 4 | **OpenAPI+ 레거시** | 최후 수단 |

---

## 4. 구현 시 고려사항

### 4.1 응답 파싱 표준화
```python
# 예상 응답 구조 (가정)
{
    "tr_cd": "opt50004",
    "rsp_cd": "00000",
    "output": {
        "frgn_net_buy": 12345,    # 외인 순매수
        "inst_net_buy": -5678,    # 기관 순매수 (음수=순매도)
        "indv_net_buy": -6667,    # 개인 순매수
        "etc_net_buy": 0,         # 기타
        "base_dt": "20260610",
        "base_tm": "153000"
    }
}
```

### 4.2 에러 처리
- 토큰 만료 → 자동 재발급 후 재시도
- TR 미지원/권한 없음 → `source="unavailable"` 유지, 로그 남김
- 응답 필드 누락 → 기본값 0, `source="partial"` 표기

### 4.3 레이트리밋
- 초당 5회 이하 권장 (Kiwoom REST API 공통)
- `scan_golden_cross.py` 실행 주기(장중 30분마다 1회)에 맞춰 1회 호출 → 문제 없음

### 4.4 캐싱/갱신 주기
- 장중: 5분~10분마다 갱신 (외인/기관 수급은 장중 변동 크지 않음)
- 장마감 후: 최종 확정값 1회 저장

---

## 5. 다음 단계

1. **실제 토큰으로 opt50004 테스트** (장중 또는 모의투자 환경)
2. 응답 포맷 확정 후 `fetch_futures_frgn_inst()` 구현
3. `source="opt50004"` 또는 `source="opt10039"` 등 실제 출처 표기
4. 단위 테스트 추가 (mock 응답 기반)

---

## 6. 변경 금지 사항 (이 PR 범위)

- ❌ `scripts/scan_golden_cross.py`에 실제 네트워크/API 호출 추가
- ❌ `fetch_futures_frgn_inst()` 반환값 변경 (여전히 `unavailable` 유지)
- ❌ 전략 로직/문서 수정 (`strategies/박사님_RSI_2퍼_시스템.md` 등)
- ❌ 다른 TR 호출 함수 추가

---

## 7. 참고 링크

- Kiwoom REST API 문서: https://api.kiwoom.com (인증 필요)
- 키움 OpenAPI+ 레거시 TR 매뉴얼: `opt10039`, `opt50004` 등 검색
- 커뮤니티 검증 사례: 키움증권 개발자 카페, GitHub `kiwoom-rest-api` 관련 레포

---

## 8. 메타데이터

| 항목 | 값 |
|------|-----|
| 작성일 | 2026-06-10 |
| 관련 PR | #7 (스크립트 stub), #8 (전략 문서) |
| 대상 함수 | `scripts/scan_golden_cross.py::fetch_futures_frgn_inst()` |
| 문서 경로 | `docs/kiwoom-futures-investor-tr-audit.md` |