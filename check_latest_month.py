import requests
from datetime import datetime

SERVICE_KEY = "6be75af37c6693a24417c2ed2930e4bd4dd01dddf289552260ce8ce1daf43414"
BASE_URL = "https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList"

def check_month(yyyymm):
    params = {
        "serviceKey": SERVICE_KEY,
        "strtYymm": yyyymm,
        "endYymm": yyyymm,
        "hsSgn": "8542",  # 반도체 (데이터 있을 가능성 높음)
        "type": "xml"
    }
    r = requests.get(BASE_URL, params=params, timeout=10)
    has_data = "<item>" in r.text
    return has_data

print(f"오늘 날짜: {datetime.now().strftime('%Y-%m-%d')}")
print("관세청 API 최신 데이터 월 탐색 중...\n")

# 2025년 11월부터 최신까지 순서대로 확인
months_to_check = ["202511", "202512", "202601", "202602", "202603", "202604"]

for m in months_to_check:
    result = check_month(m)
    status = "[O] Data found" if result else "[X] No data"
    print(f"  {m[:4]}yr {m[4:]}mo: {status}")
