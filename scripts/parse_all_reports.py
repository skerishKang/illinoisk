#!/usr/bin/env python3
"""
분기보고서 파싱 v6 — Universal parser
- 원/천원/백만원 단위 자동 감지
- inline format 지원 (피에스케이 style)
- 글머리(ㆍ) 무시
"""
import os, re

BASE = "/mnt/g/Ddrive/BatangD/task/workdiary/illinoisK"
REPORTS = os.path.join(BASE, "분기보고서")
STOCKS = os.path.join(BASE, "stock")

TICKERS = {
    "HPSP":"403870","ISC":"095340","대덕전자":"353200","동진쎄미켐":"005290",
    "두산테스나":"131970","리노공업":"058470","솔브레인":"357780","심텍":"222800",
    "에스티아이":"039440","에스에프에이":"056190","와이씨":"232140","원익IPS":"240810",
    "이수페타시스":"007660","이오테크닉스":"039030","제주반도체":"080220",
    "주성엔지니어링":"036930","하나마이크론":"067310","한미반도체":"042700",
    "한화비전":"489790","피에스케이":"319660","SFA반도체":"036540",
}
CATEGORIES = {
    "HPSP":"반도체 장비(고압산화)","ISC":"반도체 테스트 소켓","대덕전자":"반도체 PCB/기판",
    "동진쎄미켐":"반도체·디스플레이 소재","두산테스나":"반도체 테스트 서비스",
    "리노공업":"반도체 테스트 소켓","솔브레인":"반도체·디스플레이 소재","심텍":"반도체 PCB/기판",
    "에스티아이":"반도체·디스플레이 장비","에스에프에이":"반도체·디스플레이 장비",
    "와이씨":"반도체 장비","원익IPS":"반도체 증착 장비","이수페타시스":"반도체 PCB/기판",
    "이오테크닉스":"반도체 레이저 장비","제주반도체":"반도체 유통·솔루션",
    "주성엔지니어링":"반도체·디스플레이 장비","하나마이크론":"반도체 패키징·테스트",
    "한미반도체":"반도체 장비","한화비전":"보안·영상솔루션","피에스케이":"반도체 장비(플라즈마)",
    "SFA반도체":"반도체 조립·검사(OSAT)",
}

# Labels we're looking for → data keys
LABELS_IS = [
    ("매출액", "매출액_1Q"), ("수익", "매출액_1Q"),
    ("영업이익", "영업이익_1Q"),
    ("당기순이익", "분기순이익_1Q"), ("분기순이익", "분기순이익_1Q"),
    ("연결총당기순이익", "분기순이익_1Q"),
    ("기본주당순이익", "EPS_1Q"), ("기본주당순손익", "EPS_1Q"),
    ("기본주당이익", "EPS_1Q"), ("주당순이익", "EPS_1Q"),
]
LABELS_BS = [
    ("자산총계", "자산총계_1Q"),
    ("부채총계", "부채총계_1Q"),
    ("자본총계", "자본총계_1Q"),
    ("현금및현금성자산", "현금성자산_1Q"),
]

def cn(s):
    s = s.strip().replace(',','').replace(' ','').replace('ㆍ','')
    if not s: return None
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
    try: return int(s)
    except:
        try: return float(s)
        except: return None

def fmt(v):
    if v is None: return "—"
    b = v / 1e8
    return f"{b:,.0f}억" if abs(b) >= 100 else f"{b:,.1f}억"

def find_summary_section(lines):
    """Find the 요약재무정보 section, return start index"""
    for i, line in enumerate(lines):
        if i < 30: continue
        if "요약연결재무정보" in line or (line.strip() == "1. 요약재무정보" and "재무상태표" not in line):
            return i
    return -1

def detect_multiplier(lines, start):
    """Detect unit multiplier: 원=1, 백만원=1e6, 천원=1e3"""
    for i in range(start, min(start+30, len(lines))):
        if "천원" in lines[i] or "천원" in lines[i]:
            return 1_000
    for i in range(start, min(start+30, len(lines))):
        if "백만원" in lines[i]:
            return 1_000_000
    return 1  # 원

def get_nums_on_line(line):
    """Extract all numbers from a single line"""
    vals = []
    for token in re.findall(r'\(?[\d,]+\)?', line):
        v = cn(token)
        if v is not None:
            vals.append(v)
    return vals

def parse_report_v2(text):
    """Universal report parser"""
    lines = text.split('\n')
    data = {}
    
    s = find_summary_section(lines)
    if s < 0: return data
    
    mult = detect_multiplier(lines, s)
    
    # Split the section into BS part (before 수익/매출액) and IS part 
    # First collect all keywords we find with their first value
    found = {}
    
    is_section_start = False
    
    # Combine all labels
    all_labels = LABELS_BS + LABELS_IS
    
    for i in range(s, min(s+500, len(lines))):
        raw = lines[i]
        stripped = raw.strip().lstrip('ㆍ·')  # Remove bullet
        
        # Skip non-data lines
        if not stripped:
            continue
        if stripped.startswith('[') or stripped.startswith('('):
            continue
        if "요약" in stripped or "구분" in stripped:
            continue
        if "(단위" in stripped:
            continue
        if "제" in stripped and ("기" in stripped or "분기" in stripped):
            if get_nums_on_line(stripped) == []:
                continue
        
        # Check for section transition: IS section has "매출액" or "수익" or year headers
        if stripped in ("매출액", "수익", "영업이익"):
            is_section_start = True
        
        # Try to match each label
        for label, key in all_labels:
            if key in found:
                continue  # Already found this key
            
            # Exact match or label without bullet
            match_label = stripped.replace('ㆍ', '').replace('·', '')
            if match_label != label:
                continue
            
            # Now find the value
            # Format 1: label on own line, value on next non-empty line
            v = None
            for j in range(i+1, min(i+10, len(lines))):
                nums = get_nums_on_line(lines[j])
                # Find first number that's not a year (2025, 2026, etc.)
                for n in nums:
                    if abs(n) > 10000 or abs(n) < 1000:  # Not a year-like number
                        v = n
                        break
                if v is not None:
                    break
            
            if v is None:
                # Format 2: inline - label and value on same line
                parts = raw.split()
                for part in parts:
                    pv = cn(part)
                    if pv is not None and abs(pv) > 10000:
                        # Multiple values found, take first large one
                        v = pv
                        break
                # If still none, take any number from this line
                if v is None:
                    nums = get_nums_on_line(raw)
                    for n in nums:
                        if abs(n) > 1000 and (abs(n) < 1000 or abs(n) > 2025 or abs(n) < 2024):
                            v = n
                            break
            
            if v is not None:
                # Apply unit multiplier
                if key != 'EPS_1Q':  # EPS doesn't need conversion (already in 원)
                    v = v * mult
                found[key] = v
                break
    
    return found

def parse_biz_overview(text):
    lines = text.split('\n')
    result = []
    in_biz = False
    for i, line in enumerate(lines):
        if "1. 사업의 개요" in line:
            in_biz = True
            continue
        if not in_biz: continue
        if "2. 주요 제품" in line or "3. 원재료" in line: break
        if i > 2000: break
        s = line.strip()
        if s and len(s) > 5 and "전자공시시스템" not in s and "Page" not in s:
            result.append(s)
    return '\n'.join(result)[:1200]

def main():
    report_files = [f for f in os.listdir(REPORTS) if f.endswith('.txt') and f != 'generate_ticker_docs.py']
    
    seen = set()
    order = []
    for fname in sorted(report_files):
        m = re.match(r'\[(.+?)\]분기보고서', fname)
        if m and m.group(1).strip() not in seen:
            seen.add(m.group(1).strip())
            order.append((m.group(1).strip(), fname))
    
    total = len(order)
    ok = 0
    for idx, (name, fname) in enumerate(order):
        fpath = os.path.join(REPORTS, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                text = f.read()
        except:
            print(f"  ❌ {name}: 파일 읽기 실패")
            continue
        if len(text) < 1000:
            print(f"  ⚠️  {name}: 너무 짧음")
            continue
        
        data = parse_report_v2(text)
        biz = parse_biz_overview(text)
        n = len([k for k,v in data.items() if v])
        category = CATEGORIES.get(name, "반도체")
        
        fin_rows = []
        for label, key in [
            ("매출액",'매출액_1Q'),("영업이익",'영업이익_1Q'),
            ("분기순이익",'분기순이익_1Q'),
            ("EPS",'EPS_1Q'),
            ("자산총계",'자산총계_1Q'),("부채총계",'부채총계_1Q'),
            ("자본총계",'자본총계_1Q'),("현금성자산",'현금성자산_1Q'),
        ]:
            v = data.get(key)
            if key == 'EPS_1Q':
                fin_rows.append((label, f"{v:,}원" if v else "—"))
            else:
                fin_rows.append((label, fmt(v)))
        
        rev, op, ni = data.get('매출액_1Q'), data.get('영업이익_1Q'), data.get('분기순이익_1Q')
        equity, debt = data.get('자본총계_1Q'), data.get('부채총계_1Q')
        if rev and op: fin_rows.append(("영업이익률",f"{op/rev*100:.1f}%"))
        if rev and ni: fin_rows.append(("순이익률",f"{ni/rev*100:.1f}%"))
        if debt and equity: fin_rows.append(("부채비율",f"{debt/equity*100:.1f}%"))
        
        fin_table = "\n".join(f"| {k} | {v} |" for k,v in fin_rows)
        ticker = TICKERS.get(name, "??????")
        
        output = f"""# {name} ({ticker}) — 기업 개요

> **업종:** {category}
> **분기보고서:** {fname}
> **분석일시:** 2026-06-05

## 1. 사업 개요

{biz if biz else '(정보 없음)'}

## 2. 요약 재무 (2026년 1분기)

| 항목 | 값 |
|:----|:----:|
{fin_table}

---

> ※ 요약재무정보 섹션 자동 추출
"""
        sdir = os.path.join(STOCKS, name)
        os.makedirs(sdir, exist_ok=True)
        opath = os.path.join(sdir, f"{name}-overview.md")
        with open(opath, 'w', encoding='utf-8') as f:
            f.write(output.strip())
        for dtype in ['levels','trades','index']:
            dp = os.path.join(sdir, f"{name}-{dtype}.md")
            if not os.path.exists(dp):
                with open(dp, 'w', encoding='utf-8') as f:
                    f.write(f"# {name} — {dtype}\n\n> 자동 생성 (2026-06-05)\n\n준비 중...\n")
        
        print(f"  [{idx+1}/{total}] {name:12s}: {n:2d}개 | 매출 {fmt(rev):>10s} | 영업익 {fmt(op):>10s} | 순이익 {fmt(ni):>10s}")
        if n >= 4: ok += 1
    
    print(f"\n{'='*60}")
    print(f"📊 완료! {ok}/{total}")

if __name__ == '__main__':
    main()
