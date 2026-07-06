import requests
url='http://localhost:8000/parkhaus/NP12/prognose'
params={'horizon_minutes':480}
try:
    r=requests.get(url, params=params, timeout=30)
    print('STATUS', r.status_code)
    print(r.headers)
    print(r.text)
except Exception as e:
    print('ERR', type(e).__name__, e)
