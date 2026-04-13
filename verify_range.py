import requests
from datetime import datetime, timedelta

SERVICE_KEY = "6be75af37c6693a24417c2ed2930e4bd4dd01dddf289552260ce8ce1daf43414"
BASE_URL = "https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList"

def check_range(start, end):
    print(f"\n[RANGE TEST] {start} to {end}")
    params = {
        "serviceKey": SERVICE_KEY,
        "strtYymm": start,
        "endYymm": end,
        "hsSgn": "8542",
        "type": "xml"
    }
    try:
        response = requests.get(BASE_URL, params=params, timeout=15)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            if "<item>" in response.text:
                print(">>> SUCCESS: Data found.")
            else:
                print(">>> EMPTY: No <item> tags.")
                if "<resultMsg>" in response.text:
                    msg = response.text.split("<resultMsg>")[1].split("</resultMsg>")[0]
                    print(f">>> API Msg: {msg}")
        else:
            print(f">>> ERROR: {response.text}")
    except Exception as e:
        print(f">>> Network Error: {e}")

# Test 1: Recent data (Feb 2026)
check_range("202602", "202602")

# Test 2: Full 14-month range (Jan 2025 to Feb 2026)
check_range("202501", "202602")

# Test 3: Large range (Jan 2024 to Feb 2026 - 26 months)
check_range("202401", "202602")
