import requests, json, os

ENV = '/mnt/g/Ddrive/BatangD/task/workdiary/65stock/01_core/kiwoom_dashboard_clean/.env'
if not os.path.exists(ENV):
    raise SystemExit('.env not found: ' + ENV)

with open(ENV) as f:
    raw = f.read()

env_vars = {}
for line in raw.splitlines():
    line = line.strip()
    if not line or line.startswith('#'):
        continue
    if '=' in line:
        k, v = line.split('=', 1)
        env_vars[k.strip()] = v.strip()

APP_KEY = env_vars.get('APP_KEY')
SECRET_KEY=env_vars.get('SECRET_KEY')
print('APP_KEY found:', bool(APP_KEY), 'len:', len(APP_KEY) if APP_KEY else 0)
print('SECRET_KEY found:', bool(SECRET_KEY), 'len:', len(SECRET_KEY) if SECRET_KEY else 0)

if not APP_KEY or not SECRET_KEY:
    raise SystemExit('Missing credentials in .env')

r = requests.post('https://api.kiwoom.com/oauth2/token', json={
    'grant_type': 'client_credentials',
    'appkey': APP_KEY,
    'secretkey': SECRET_KEY
}, timeout=10)
token = r.json()['token']

headers = {
    'api-id': 'ka10095',
    'authorization': 'Bearer ' + token,
    'cont-yn': 'N',
    'next-key': '',
    'Content-Type': 'application/json;charset=UTF-8'
}

for code, name in [('001', 'KOSPI'), ('101', 'KOSDAQ')]:
    resp = requests.post('https://api.kiwoom.com/api/dostk/stkinfo',
                         json={'stk_cd': code}, headers=headers, timeout=10)
    d = resp.json()
    if d.get('return_code') == 0:
        row = d['atn_stk_infr'][0]
        def parse_price(s):
            s2 = s.replace(',', '').lstrip('+-')
            return int(s2) if s2 else 0
        prc = parse_price(row.get('cur_prc', '0'))
        flu = float(row.get('flu_rt', 0))
        pred = parse_price(row.get('pred_pre', '0'))
        high = parse_price(row.get('high_pric', '0'))
        low = parse_price(row.get('low_pric', '0'))
        opn = parse_price(row.get('open_pric', '0'))
        vol = int(row.get('trde_qty', 0))
        print(name + ': ' + format(prc, ',') + '원 (' + format(flu, '+.2f') + '%) | 시가 ' + format(opn, ',') + ' | 고가 ' + format(high, ',') + ' | 저가 ' + format(low, ',') + ' | 거래량 ' + format(vol, ','))
    else:
        print(name + ': API error')
