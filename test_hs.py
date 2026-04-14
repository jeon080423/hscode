import xml.etree.ElementTree as ET
import requests

service_key = "6be75af37c6693a24417c2ed2930e4bd4dd01dddf289552260ce8ce1daf43414"
url = "https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList"

# Test HS Codes
codes_to_test = ['8540', '8542311020', '8542311010', '85423290']

def check_hs(code):
    params = {
        "serviceKey": service_key,
        "strtYymm": "202501",
        "endYymm": "202501",
        "hsSgn": code,
        "type": "xml"
    }
    r = requests.get(url, params=params)
    names = set()
    if r.status_code == 200:
        if "<item>" in r.text:
            root = ET.fromstring(r.text)
            for item in root.findall('.//item'):
                hs = item.findtext('hsSgn') or item.findtext('hsCode')
                name = item.findtext('statKor')
                if name and name != '-':
                    names.add(f"{hs}: {name}")
            return f"Success - Found items: {', '.join(names)}"
        else:
            return f"No Data - {r.text[:200]}"
    return f"HTTP {r.status_code}"

for c in codes_to_test:
    print(f"--- {c} ---")
    print(check_hs(c))
