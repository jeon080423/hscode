import requests
import xml.etree.ElementTree as ET
import pandas as pd
import datetime

# 공공데이터포털 서비스키 (이전 프로젝트에서 가져옴)
SERVICE_KEY = "6be75af37c6693a24417c2ed2930e4bd4dd01dddf289552260ce8ce1daf43414"
BASE_URL = "http://openapi.customs.go.kr/openapi/service/newSidoItemInoutExtStatis/getSidoItemInoutExtStatis" # 예시 URL, 실제 명칭 확인 필요

class CustomsAPIClient:
    def __init__(self, service_key=SERVICE_KEY):
        self.service_key = service_key
        # 실제 "품목별 수출입실적" API 엔드포인트
        self.url = "http://openapi.customs.go.kr/openapi/service/newSidoItemInoutExtStatis/getSidoItemInoutExtStatis"
        # 또는 관세청_품목별 수출입실적 GW
        self.gw_url = "http://openapi.customs.go.kr/openapi/service/newSidoItemInoutExtStatis/getIptExpItemQuatGW"

    def fetch_monthly_data(self, year_month, hs_code=None):
        """
        특정 년월의 수출입 실적을 조회합니다.
        year_month: YYYYMM 형식
        """
        params = {
            'serviceKey': self.service_key,
            'searchBgnDe': year_month,
            'searchEndDe': year_month,
        }
        if hs_code:
            params['hsSbc'] = hs_code # 품목코드

        try:
            response = requests.get(self.gw_url, params=params, timeout=15)
            if response.status_code == 200:
                return self._parse_xml(response.text, year_month)
            else:
                print(f"Error AI: {response.status_code}")
                return None
        except Exception as e:
            print(f"Exception: {e}")
            return None

    def _parse_xml(self, xml_data, year_month):
        try:
            root = ET.fromstring(xml_data)
            items = []
            for item in root.findall('.//item'):
                items.append({
                    'year_month': year_month,
                    'hs_code': item.findtext('hsSbc'),
                    'item_name': item.findtext('statItemNm'),
                    'exp_amount': float(item.findtext('expDlAmout', 0)), # 수출금액
                    'imp_amount': float(item.findtext('impDlAmout', 0)), # 수입금액
                    'trade_balance': float(item.findtext('trbalAlAmout', 0)), # 무역수지
                })
            return pd.DataFrame(items)
        except Exception as e:
            print(f"Parsing Error: {e}")
            return None

if __name__ == "__main__":
    client = CustomsAPIClient()
    # 테스트 조회 (예: 202401)
    df = client.fetch_monthly_data("202401")
    if df is not None:
        print(df.head())
