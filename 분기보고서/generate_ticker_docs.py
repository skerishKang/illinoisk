import os, re

WORKDIR = "/mnt/g/Ddrive/BatangD/task/workdiary/illinoisK/분기보고서"
DOCDIR = "/root/.hermes/memory_documents/stock/tickers"

def extract_section(lines, start_marker, end_markers=None, max_lines=300):
    result = []
    capture = False
    count = 0
    for line in lines:
        if start_marker in line and not capture:
            capture = True
            continue
        if capture:
            if end_markers and any(m in line for m in end_markers):
                break
            result.append(line.strip())
            count += 1
            if count > max_lines:
                break
    return '\n'.join(result)

def extract_financial_summary(text):
    data = {}
    patterns = {
        '매출액': r'매출액\s*\n\s*(\d[\d,]*)\s*\n\s*(\d[\d,]*)',
        '영업이익': r'영업이익\(손실\)\s*\n\s*(\d[\d,]*)\s*\n\s*(\d[\d,]*)',
        '당기순이익': r'연결당기순이익\(손실\)\s*\n\s*(\d[\d,]*)\s*\n\s*(\d[\d,]*)',
        '자산총계': r'자산총계\s*\n\s*(\d[\d,]*)\s*\n\s*(\d[\d,]*)',
        '부채총계': r'부채총계\s*\n\s*(\d[\d,]*)\s*\n\s*(\d[\d,]*)',
        '자본총계': r'자본총계\s*\n\s*(\d[\d,]*)\s*\n\s*(\d[\d,]*)',
    }
    for key, pat in patterns.items():
        m = re.search(pat, text)
        if m:
            data[key] = (m.group(1), m.group(2) if m.lastindex >= 2 else None)
    return data

txt_files = sorted([f for f in os.listdir(WORKDIR) if f.endswith('.txt')])
already_have = ['ISC', '이오테크닉스']

for tf in txt_files:
    company_match = re.match(r'\[(.+?)\]', tf)
    if company_match:
        company_name = company_match.group(1)
    else:
        continue
    
    if company_name in already_have:
        print(f"SKIP: {company_name}")
        continue
    
    filepath = os.path.join(WORKDIR, tf)
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        text = f.read()
    
    lines = text.split('\n')
    biz_overview = extract_section(lines, '사업의 개요', ['재무에 관한 사항', 'III.', 'Ⅲ.'])
    products = extract_section(lines, '주요 제품 및 서비스', ['원재료', 'III.', 'Ⅲ.'])
    rd = extract_section(lines, '연구개발활동', ['재무', 'III.', 'Ⅲ.', 'IV.', 'Ⅳ.'])
    fin = extract_financial_summary(text)
    
    # Clean company name for filename
    safe_name = company_name.replace(' ', '')
    doc_name = f"{safe_name}.md"
    
    biz_lines = biz_overview.split('\n')
    biz_clean = [bl.strip() for bl in biz_lines if bl.strip() and len(bl.strip()) > 5 
                 and '전자공시' not in bl and 'Page' not in bl and 'dart.fss' not in bl]
    
    md = f"""---
created: 2026-06-02
updated: 2026-06-02
tags: [{company_name}, 분기보고서, 2026.1Q]
source: 제33기 분기보고서 (2026.05.15)
---

# {company_name} — 기업 개요

**출처:** 제33기 분기보고서 (2026.05.15, 2026.1Q 기준)

## 사업 개요
"""
    if biz_clean:
        md += '\n'.join(biz_clean[:30]) + '\n\n'
    else:
        md += "(사업 개요 내용 없음)\n\n"
    
    md += "## 재무 현황 (연결, 백만원)\n\n"
    if fin:
        md += "| 구분 | 2026.1Q | 2025 |\n|---|---:|---:|\n"
        for key in ['매출액', '영업이익', '당기순이익', '자산총계', '부채총계', '자본총계']:
            if key in fin:
                md += f"| {key} | {fin[key][0]} | {fin[key][1] if fin[key][1] else '-'} |\n"
    else:
        md += "(재무 데이터 미추출 - 수동 확인 필요)\n"
    
    prod_clean = [pl.strip() for pl in products.split('\n') if pl.strip() and len(pl.strip()) > 3 
                  and 'Page' not in pl and 'dart' not in pl and '전자공시' not in pl]
    if prod_clean and len(prod_clean) > 2:
        md += "\n## 주요 제품\n"
        md += '\n'.join(prod_clean[:10]) + '\n'
    
    doc_path = os.path.join(DOCDIR, doc_name)
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(md)
    
    print(f"OK: {company_name}")

print("\nDONE")
