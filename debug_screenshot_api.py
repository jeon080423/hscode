import requests

# Information from user's screenshot
SERVICE_KEY = "6be75af37c6693a24417c2ed2930e4bd4dd01dddf289552260ce8ce1daf43414"
END_POINT = "https://apis.data.go.kr/1220000/Itemtrade"

def test_endpoint(url):
    print(f"\n[TESTING] URL: {url}")
    params = {
        "serviceKey": SERVICE_KEY,
        "strtYymm": "202401",
        "endYymm": "202401",
        "hsSgn": "8542",
        "type": "xml"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response (first 500): {response.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")

# Strategy 1: The endpoint exactly as shown in the screenshot
test_endpoint(END_POINT)

# Strategy 2: Appending /getItemtradeList (current code style)
test_endpoint(END_POINT + "/getItemtradeList")

# Strategy 3: Lowercase variant
test_endpoint(END_POINT.lower() + "/getitemtradeList")
