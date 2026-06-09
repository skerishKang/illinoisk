#!/usr/bin/env python3
"""
Phase 2: 전종목 overview.md 생성/보정
Phase 3: stock-index.md 생성
"""
import os, re, json

PDF_DIR = "/mnt/g/Ddrive/BatangD/task/workdiary/illinoisK/분기보고서/"
STOCK_DIR = "/mnt/g/Ddrive/BatangD/task/workdiary/illinoisK/stock/"

# 종목 매핑: {종목명: (티커, 업종)}
TICKER_MAP = {
    "DB하이텍":         ("000990", "파운드리"),
    "GST":              ("083450", "검사장비"),
    "고영":             ("098460", "3D검사"),
    "디아이":           ("003160", "반도체장비"),
    "에스앤에스텍":     ("101490", "마스크"),
    "에스에프에이":     ("056190", "장비"),
    "에스티아이":       ("039440", "장비"),
    "유진테크":         ("084370", "장비"),
    "이엔에프테크놀로지": ("102710", "소재"),
    "케이씨텍":         ("281820", "장비"),
    "SFA반도체":        ("036540", "조립검사"),
    "피에스케이":       ("319660", "장비"),
    "하나마이크론":     ("067310", "패키징테스트"),
    "한화비전":         ("489790", "보안"),
    "HPSP":             ("403870", "장비"),
    "ISC":              ("095340", "소켓"),
    "대덕전자":         ("353200", "PCB"),
    "동진쎄미켐":       ("005290", "소재"),
    "두산테스나":       ("131970", "테스트서비스"),
    "리노공업":         ("058470", "소켓"),
    "솔브레인":         ("357780", "소재"),
    "심텍":             ("222800", "PCB"),
    "와이씨":           ("232140", "장비"),
    "원익IPS":          ("240810", "장비"),
    "이수페타시스":     ("007660", "PCB"),
    "이오테크닉스":     ("039030", "장비"),
    "제주반도체":       ("080220", "유통"),
    "주성엔지니어링":   ("036930", "장비"),
    "한미반도체":       ("042700", "장비"),
}

def find_txt_for_stock(name):
    """Find the TXT file for a stock in PDF_DIR"""
    for f in os.listdir(PDF_DIR):
        if not f.endswith('.txt'): continue
        if f.startswith(f'[{name}]'):
            return os.path.join(PDF_DIR, f)
    return None

def extract_financial_data(text):
    """Extract financial data from 요약재무정보 section"""
    data = {}
    
    # Find the 요약재무정보 section - skip TOC, find the one with actual table content
    idx1 = text.find("1. 요약재무정보")
    if idx1 == -1:
        idx1 = text.find("요약재무정보")
    if idx1 == -1:
        return {}, 1
    
    # Find 2nd occurrence (the actual section, not TOC)
    idx2 = text.find("1. 요약재무정보", idx1 + 10)
    if idx2 == -1:
        # Try without the "1. " prefix
        idx2 = text.find("요약재무정보", idx1 + 10)
    if idx2 == -1:
        idx2 = idx1  # fallback to first
    
    # Determine search range - go up to next major section or 15000 chars
    section_end = min(idx2 + 15000, len(text))
    # Try to find the end of this section (next major section like "2. " or "II. ")
    end_match = re.search(r'\n(?=2\.\s|II\.\s|\n\d\.\s)', text[idx2+100:section_end])
    if end_match:
        section_end = min(section_end, idx2 + 100 + end_match.start() + 100)
    section = text[idx2:section_end]
    
    # Check if 연결 (consolidated) section exists
    # The subsection might be "요약재무정보(연결)", "요약 연결재무정보", "연결재무제표" etc.
    conn_idx = section.find("요약재무정보(연결)")
    if conn_idx == -1:
        conn_idx = section.find("요약 연결재무정보")
    if conn_idx == -1:
        conn_idx = section.find("요약연결재무정보")
    if conn_idx == -1:
        # Look for "가. " section header
        conn_idx = re.search(r'가\.\s*(?:요약\s*)?연결', section)
        if conn_idx:
            conn_idx = conn_idx.start()
    if conn_idx == -1:
        conn_idx = 0  # use the section as is
    
    sub = section[conn_idx:]
    
    # Determine unit - supports (단위:백만원) and [단위 : 백만원] formats
    # Search in entire sub section (unit line can be far from start)
    unit_match = re.search(r'[(\[]\s*단위\s*[:：]\s*([^)\]]+)[)\]]', sub[:2000])
    unit_str = unit_match.group(1).strip() if unit_match else ""
    if not unit_str:
        # Try "단위 : " format more broadly
        unit_match2 = re.search(r'단위\s*[:：]\s*([^\s)\]]+)', sub[:2000])
        if unit_match2:
            unit_str = unit_match2.group(1).strip()
    
    # Parse multiplier from unit
    multiplier = 1  # default: 원
    if '백만원' in unit_str:
        multiplier = 1_000_000
    elif '천원' in unit_str:
        multiplier = 1_000
    elif '억원' in unit_str:
        multiplier = 100_000_000
    
    # Define patterns for extraction
    # Format: label on one line, value on next line(s), first numeric value is current period
    # Handle: "매출액\n374,629" or "[매출액]\n374,629" or "매출액]\n374,629"
    # Also handle double newlines: "매출액\n\n374,629" or spaces: "매출액              374,629"
    patterns = [
        ("매출액", r'(?:수익\()?매출액[\]\[\)]?\n+\s*\(?([\d,]+)'),
        ("영업이익", r'영업이익(?:\(영업손실\))?[\]\[\)]?\n+\s*\(?(-?[\d,]+)'),
        ("당기순이익", r'(?:당기순이익|연결당기순이익)(?:\(손실\))?[\]\[\)]?\n+\s*\(?(-?[\d,]+)'),
        ("EPS", r'기본주당이익[\]\[\)]?\n+\s*\(?([\d,]+)'),
        ("자산총계", r'자산총계[\]\[\)]?\n+\s*\(?([\d,]+)'),
        ("부채총계", r'부채총계[\]\[\)]?\n+\s*\(?([\d,]+)'),
        ("자본총계", r'자본총계[\]\[\)]?\n+\s*\(?([\d,]+)'),
        ("현금성자산", r'현금(?:및현금)?성자산[\]\[\)]?\n+\s*\(?([\d,]+)'),
    ]
    
    for key, pattern in patterns:
        m = re.search(pattern, sub)
        if m:
            val_str = m.group(1).replace(',', '')
            try:
                val = int(val_str)
                data[key] = val
            except:
                pass
    
    # Handle negative values in parentheses: (6,177,693) -> -6177693
    for key in ["영업이익", "당기순이익"]:
        if key not in data:
            label_map = {"영업이익": "영업이익", "당기순이익": "(?:당기순이익|연결당기순이익)"}
            pattern = label_map[key]
            # Try with parentheses for negative values
            m = re.search(pattern + r'[\]\[]?\n+\s*\(([\d,]+)\)', sub)
            if m:
                val_str = '-' + m.group(1).replace(',', '')
                try:
                    data[key] = int(val_str)
                except:
                    pass
    
    # Fallback: same-line format (label then value separated by spaces, no newline)
    if not data.get("매출액"):
        for label, key in [("매출액", "매출액"), ("영업이익", "영업이익"), ("당기순이익", "당기순이익"),
                           ("자산총계", "자산총계"), ("부채총계", "부채총계"), ("자본총계", "자본총계"),
                           ("현금및현금성자산", "현금성자산"), ("기본주당이익", "EPS")]:
            if key in data:
                continue
            m = re.search(label + r'[\]\[]?\s{2,}([\d,]+)', sub[:3000])
            if m:
                val_str = m.group(1).replace(',', '')
                try:
                    data[key] = int(val_str)
                except:
                    pass
    
    return data, multiplier

def format_value_억(val, multiplier):
    """Convert raw number to 억 unit string"""
    if val is None:
        return "—"
    actual = val * multiplier
    # Convert to 억 (100,000,000)
    in_ok = actual / 100_000_000
    return f"{in_ok:,.0f}억"

def format_value_원(val, multiplier):
    """Convert raw number to 원 string for EPS"""
    if val is None:
        return "—"
    actual = val * multiplier
    return f"{actual:,}원"

def extract_biz_overview(text):
    """Extract 사업의 개요 section (2nd occurrence of '1. 사업의 개요')"""
    # Find the TOC occurrence first, then the actual section
    idx1 = text.find("1. 사업의 개요")
    if idx1 == -1:
        return "(정보 없음)"
    
    # Find 2nd occurrence (the actual section, not TOC)
    idx2 = text.find("1. 사업의 개요", idx1 + 10)
    if idx2 == -1:
        # No 2nd occurrence, use the first one
        idx2 = idx1
    
    # Find start of actual content (skip the heading line)
    content_start = idx2
    nl = text.find('\n', content_start)
    if nl != -1:
        content_start = nl + 1
    
    # Find where this section ends - look for next major section
    # Look for "2." or "II." or "전자공시시스템" markers
    end_markers = [
        r'\n2\.', r'\nII\.', r'전자공시시스템', r'\n3\.',
        r'\nIII\.', r'\n\[표지\]', r'\n\[주의\]'
    ]
    
    content_end = len(text)
    for marker in end_markers:
        m = re.search(marker, text[idx2 + 10:])
        if m:
            candidate = idx2 + 10 + m.start()
            if candidate < content_end and candidate > content_start + 50:
                content_end = candidate
    
    overview_text = text[content_start:content_end].strip()
    
    # Clean up
    # Remove page markers like "전자공시시스템 dart.fss.or.kr Page N"
    overview_text = re.sub(r'전자공시시스템\s+dart\.fss\.or\.kr\s+Page\s+\d+', '', overview_text)
    
    # Remove section headers like "가. 산업의 특성" etc if they appear
    # But keep the content
    
    if len(overview_text) < 50:
        return "(정보 없음)"
    
    return overview_text

def write_overview(stock_name, ticker, category, txt_path):
    """Write {stockname}-overview.md"""
    with open(txt_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Extract financial data
    fin_data, multiplier = extract_financial_data(text)
    
    # Extract business overview
    biz_text = extract_biz_overview(text)
    
    # Calculate derived values
    매출 = fin_data.get("매출액")
    영업이익 = fin_data.get("영업이익")
    순이익 = fin_data.get("당기순이익")
    eps = fin_data.get("EPS")
    자산 = fin_data.get("자산총계")
    부채 = fin_data.get("부채총계")
    자본 = fin_data.get("자본총계")
    현금 = fin_data.get("현금성자산")
    
    # Calculate ratios
    if 매출 and 영업이익:
        영업이익률 = (영업이익 * multiplier) / (매출 * multiplier) * 100
        영업이익률_str = f"{영업이익률:.1f}%"
    else:
        영업이익률_str = "—"
    
    if 매출 and 순이익:
        순이익률 = (순이익 * multiplier) / (매출 * multiplier) * 100
        순이익률_str = f"{순이익률:.1f}%"
    else:
        순이익률_str = "—"
    
    if 부채 and 자본 and 자본 > 0:
        부채비율 = (부채 * multiplier) / (자본 * multiplier) * 100
        부채비율_str = f"{부채비율:.1f}%"
    else:
        부채비율_str = "—"
    
    # Build overview content
    txt_filename = os.path.basename(txt_path)
    
    lines = []
    lines.append(f"# {stock_name} ({ticker}) — 기업 개요\n")
    lines.append(f"> **업종:** {category}")
    lines.append(f"> **분기보고서:** {txt_filename}")
    lines.append(f"> **분석일시:** 2026-06-05\n")
    lines.append("## 1. 사업 개요\n")
    
    # Format biz overview - preserve line breaks but limit to first 1500 chars for readability
    if len(biz_text) > 2000:
        biz_short = biz_text[:2000] + "\n\n*(... 이하 생략 ...)*"
    else:
        biz_short = biz_text
    
    # Format biz text with proper line breaks
    biz_formatted = biz_short.replace('\n', '\n ')
    lines.append(biz_formatted)
    lines.append("")
    
    lines.append("## 2. 요약 재무 (2026년 1분기)\n")
    lines.append("| 항목 | 값 |")
    lines.append("|:----|:----:|")
    lines.append(f"| 매출액 | {format_value_억(매출, multiplier) if 매출 else '—'} |")
    lines.append(f"| 영업이익 | {format_value_억(영업이익, multiplier) if 영업이익 else '—'} |")
    lines.append(f"| 분기순이익 | {format_value_억(순이익, multiplier) if 순이익 else '—'} |")
    if eps is not None:
        # EPS is already in 원 (per share value, not affected by table unit)
        lines.append(f"| EPS | {eps:,}원 |")
    else:
        lines.append(f"| EPS | — |")
    lines.append(f"| 자산총계 | {format_value_억(자산, multiplier) if 자산 else '—'} |")
    lines.append(f"| 부채총계 | {format_value_억(부채, multiplier) if 부채 else '—'} |")
    lines.append(f"| 자본총계 | {format_value_억(자본, multiplier) if 자본 else '—'} |")
    lines.append(f"| 현금성자산 | {format_value_억(현금, multiplier) if 현금 else '—'} |")
    lines.append(f"| 영업이익률 | {영업이익률_str} |")
    lines.append(f"| 순이익률 | {순이익률_str} |")
    lines.append(f"| 부채비율 | {부채비율_str} |")
    lines.append("")
    lines.append("---\n")
    lines.append("> ※ 요약연결재무정보 직접 추출")
    
    return '\n'.join(lines), (stock_name, ticker, category, 
                              format_value_억(매출, multiplier) if 매출 else '—',
                              format_value_억(영업이익, multiplier) if 영업이익 else '—',
                              format_value_억(순이익, multiplier) if 순이익 else '—',
                              f"{eps:,}원" if eps else '—',
                              영업이익률_str, 순이익률_str, 부채비율_str)

def write_index_md(stock_dir, stock_name, ticker, category):
    """Write {stockname}-index.md if not exists"""
    index_path = os.path.join(stock_dir, f"{stock_name}-index.md")
    if os.path.exists(index_path):
        return False
    content = f"""# 📊 {stock_name} ({ticker}) — 문서 인덱스

**코드:** {ticker} | **시장:** KOSDAQ | **업종:** {category}

| 문서 | 내용 |
|:----|:------|
| [개요]({stock_name}-overview.md) | 기업 정보, 사업 개요 |
| [레벨]({stock_name}-levels.md) | 지지/저항 레벨 |
| [매매 기록]({stock_name}-trades.md) | 매매 판단 기록 |
"""
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True

def write_levels_md(stock_dir, stock_name, ticker):
    """Write {stockname}-levels.md if not exists"""
    levels_path = os.path.join(stock_dir, f"{stock_name}-levels.md")
    if os.path.exists(levels_path):
        return False
    content = f"""# {stock_name} ({ticker}) — 가격 레벨
*최종 업데이트: 2026-06-05*
## 현재가
- **2026-06-05 현재:** 추후 업데이트
## 주요 레벨
| 구분 | 가격 | 비고 |
|:----|:---:|:-----|
| **관측 최고가** | — | |
| **관측 최저가** | — | |
## 비고
- 가격 레벨은 추후 업데이트 예정
"""
    with open(levels_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True

def write_trades_md(stock_dir, stock_name, ticker):
    """Write {stockname}-trades.md if not exists"""
    trades_path = os.path.join(stock_dir, f"{stock_name}-trades.md")
    if os.path.exists(trades_path):
        return False
    content = f"""# {stock_name} ({ticker}) — 매매 판단 기록

*최종 업데이트: 2026-06-05*

---

## 매매 기록

아직 매매 내역이 없습니다. 거래가 발생하면 이 파일에 기록합니다.

---

### 작성 양식

```
## YYYY-MM-DD (요일)

| 구분 | 내용 |
|:----|:------|
| **매수가** | 000,000 |
| **매도가** | 000,000 |
| **수익률** | +0.0% |
| **전략** | 전략명 |

**판단 근거:** ...
```
"""
    with open(trades_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True

def write_stock_index(all_data):
    """Write stock-index.md"""
    # Sort by 매출액 descending
    def sort_key(d):
        val_str = d[3]  # 매출액 string like "3746억"
        try:
            val = float(val_str.replace('억', '').replace(',', '').replace('—', '0'))
        except:
            val = 0
        return -val
    
    sorted_data = sorted(all_data, key=sort_key)
    
    lines = []
    lines.append("# 📊 종목별 문서 인덱스\n")
    lines.append("**분기보고서 기반 업데이트: 2026-06-05**\n")
    lines.append("---\n")
    lines.append(f"## 전체 종목 ({len(sorted_data)}개)\n")
    lines.append("| # | 종목명 | 코드 | 매출액 | 영업이익 | 순이익 | EPS | 영업이익률 | 순이익률 | 부채비율 |")
    lines.append("|:---:|:------|:---:|:-----:|:-------:|:-----:|:---:|:---------:|:--------:|:--------:|")
    
    for i, (name, ticker, category, rev, op, ni, eps, opm, npm, dr) in enumerate(sorted_data, 1):
        lines.append(f"| {i} | [{name}]({name}/{name}-index.md) | {ticker} | {rev} | {op} | {ni} | {eps} | {opm} | {npm} | {dr} |")
    
    lines.append("")
    lines.append("---\n")
    lines.append("*자동 업데이트: 2026-06-05*")
    
    return '\n'.join(lines)

def main():
    results = {
        "overview_created": [],
        "overview_updated": [],
        "overview_skipped": [],
        "missing_txt": [],
        "index_created": [],
        "levels_created": [],
        "trades_created": [],
        "issues": [],
    }
    
    all_data = []
    
    for stock_name, (ticker, category) in sorted(TICKER_MAP.items()):
        print(f"\n=== {stock_name} ({ticker}) ===")
        
        # Find TXT file
        txt_path = find_txt_for_stock(stock_name)
        if not txt_path:
            print(f"  ⚠ TXT 파일 없음")
            results["missing_txt"].append(stock_name)
            results["issues"].append(f"{stock_name}: 분기보고서 TXT 파일 없음")
            # Still add to index with placeholder
            all_data.append((stock_name, ticker, category, '—', '—', '—', '—', '—', '—', '—'))
            continue
        
        print(f"  TXT: {os.path.basename(txt_path)}")
        
        # Prepare stock directory
        stock_dir = os.path.join(STOCK_DIR, stock_name)
        os.makedirs(stock_dir, exist_ok=True)
        
        overview_path = os.path.join(stock_dir, f"{stock_name}-overview.md")
        
        # Generate overview content
        overview_content, fin_data = write_overview(stock_name, ticker, category, txt_path)
        all_data.append(fin_data)
        
        # Check if overview already exists and compare
        if os.path.exists(overview_path):
            with open(overview_path, 'r', encoding='utf-8') as f:
                existing = f.read()
            if existing == overview_content:
                results["overview_skipped"].append(stock_name)
                print(f"  overview: 변경 없음 (skip)")
            else:
                with open(overview_path, 'w', encoding='utf-8') as f:
                    f.write(overview_content)
                results["overview_updated"].append(stock_name)
                print(f"  overview: 업데이트 완료")
        else:
            with open(overview_path, 'w', encoding='utf-8') as f:
                f.write(overview_content)
            results["overview_created"].append(stock_name)
            print(f"  overview: 새로 생성 완료")
        
        # Create index.md, levels.md, trades.md if not exist
        if write_index_md(stock_dir, stock_name, ticker, category):
            results["index_created"].append(stock_name)
            print(f"  index.md: 새로 생성")
        
        if write_levels_md(stock_dir, stock_name, ticker):
            results["levels_created"].append(stock_name)
            print(f"  levels.md: 새로 생성")
        
        if write_trades_md(stock_dir, stock_name, ticker):
            results["trades_created"].append(stock_name)
            print(f"  trades.md: 새로 생성")
    
    # Write stock-index.md
    index_content = write_stock_index(all_data)
    index_path = os.path.join(STOCK_DIR, "stock-index.md")
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_content)
    print(f"\n=== stock-index.md 업데이트 완료 ({len(all_data)}개 종목) ===")
    
    # Print summary
    print("\n" + "="*60)
    print("작업 요약")
    print("="*60)
    print(f"overview 생성: {len(results['overview_created'])}개")
    for n in results['overview_created']:
        print(f"  + {n}")
    print(f"overview 업데이트: {len(results['overview_updated'])}개")
    for n in results['overview_updated']:
        print(f"  ~ {n}")
    print(f"overview 변경없음: {len(results['overview_skipped'])}개")
    print(f"index.md 생성: {len(results['index_created'])}개")
    print(f"levels.md 생성: {len(results['levels_created'])}개")  
    print(f"trades.md 생성: {len(results['trades_created'])}개")
    
    if results['issues']:
        print(f"\n⚠ 문제 종목: {len(results['issues'])}개")
        for issue in results['issues']:
            print(f"  ! {issue}")
    
    # Save results for Phase 4 report
    with open(os.path.join(STOCK_DIR, ".phase2_results.json"), 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Also save all_data for stock-index table
    all_data_json = []
    for d in all_data:
        all_data_json.append({
            "name": d[0], "ticker": d[1], "category": d[2],
            "매출액": d[3], "영업이익": d[4], "순이익": d[5], "EPS": d[6],
            "영업이익률": d[7], "순이익률": d[8], "부채비율": d[9]
        })
    with open(os.path.join(STOCK_DIR, ".phase2_all_data.json"), 'w', encoding='utf-8') as f:
        json.dump(all_data_json, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
