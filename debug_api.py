import requests
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime, timedelta

# api_client에서 키 정보 가져오기 시도
try:
    from api_client import CUSTOMS_SERVICE_KEY, CUSTOMS_BASE_URL
except ImportError:
    CUSTOMS_SERVICE_KEY = "rWV9FTPXzoGfN0Cl232NYiSEKla0pPL9AH8q8DYJfPGGOYqCtrcCC2E7Lef6qnVLjojcUQxhMZ2D0+wMVVx/sA=="
    CUSTOMS_BASE_URL = "http://apis.data.go.kr/1220000/Itemtrade/getitemtradeList"

def debug_fetch(year_month, hs_code):
    print(f"\n[DEBUG] Fetching: Month={year_month}, HS={hs_code}")
    unquoted_key = requests.utils.unquote(CUSTOMS_SERVICE_KEY)
    params = {
        "serviceKey": unquoted_key,
        "strtYymm": year_month,
        "endYymm": year_month,
        "hsSgn": hs_code
    }
    try:
        response = requests.get(CUSTOMS_BASE_URL, params=params, timeout=15)
        print(f"Status Code: {response.status_code}")
        print("Raw Response Header (first 500 chars):")
        print(response.text[:500])
        
        if "<item>" in response.text:
            print(">>> SUCCESS: <item> tags found in response!")
            # 간단한 아이템 요약
            count = response.text.count("<item>")
            print(f">>> Item Count: {count}")
        else:
            print(">>> FAILURE: No <item> tags found.")
            if "<resultMsg>" in response.text:
                msg = response.text.split("<resultMsg>")[1].split("</resultMsg>")[0]
                print(f">>> API Message: {msg}")
    except Exception as e:
        print(f">>> Network/System Error: {e}")

def test_strategy(name, base_url, key_to_use, manual_url=False):
    print(f"\n[STRATEGY: {name}] Target: {base_url}")
    params = {
        "serviceKey": key_to_use,
        "strtYymm": "202512",
        "endYymm": "202512",
        "hsSgn": "8542"
    }
    try:
        if manual_url:
            # 매뉴얼 URL 구성 (requests의 자동 인코딩 방지)
            url = f"{base_url}?serviceKey={key_to_use}&strtYymm=202512&endYymm=202512&hsSgn=8542"
            response = requests.get(url, timeout=10)
        else:
            response = requests.get(base_url, params=params, timeout=10)
            
        print(f"Status: {response.status_code}")
        snippet = response.text[:400].replace('\n', '')
        print(f"Response: {snippet}")
        if "<item>" in response.text:
            print(">>> !!! SUCCESS !!! Data found.")
            return True
    except Exception as e:
        print(f"Error: {e}")
    return False

if __name__ == "__main__":
    raw_key = "rWV9FTPXzoGfN0Cl232NYiSEKla0pPL9AH8q8DYJfPGGOYqCtrcCC2E7Lef6qnVLjojcUQxhMZ2D0+wMVVx/sA=="
    decoded_key = requests.utils.unquote(raw_key)
    
    # 후보 URL
    url_items = "https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList"
    url_ict = "https://apis.data.go.kr/1220000/IctTrade/getIctTradeList"
    
    strategies = [
        ("Manual URL + Raw Key", url_items, raw_key, True),
        ("Manual URL + Decoded Key", url_items, decoded_key, True),
        ("Params + Decoded Key", url_items, decoded_key, False),
        ("ICT API + Manual Raw", url_ict, raw_key, True)
    ]
    
    for name, url, key, manual in strategies:
        if test_strategy(name, url, key, manual):
            print("\n[CONCLUSION] Use this successful strategy!")
            break
