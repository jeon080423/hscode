import requests
import xml.etree.ElementTree as ET
import pandas as pd
import datetime

# 공공데이터포털 서비스키 (관세청)
# 금일(4/7) 성공적으로 실측 데이터를 불러왔던 최신 키로 교체합니다.
CUSTOMS_SERVICE_KEY = "rWV9FTPXzoGfN0Cl232NYiSEKla0pPL9AH8q8DYJfPGGOYqCtrcCC2E7Lef6qnVLjojcUQxhMZ2D0+wMVVx/sA=="
CUSTOMS_BASE_URL = "http://apis.data.go.kr/1220000/Itemtrade/getitemtradeList"

# 한국은행 ECOS 서비스키 (제공받은 키 적용)
ECOS_SERVICE_KEY = "Q33UM6GK6QDQ46NEH83B"
ECOS_BASE_URL = "http://ecos.bok.or.kr/api/StatisticSearch"

class CustomsAPIClient:
    def __init__(self, service_key=CUSTOMS_SERVICE_KEY):
        self.service_key = service_key
        self.url = CUSTOMS_BASE_URL

    def fetch_monthly_data(self, year_month, hs_code):
        """관세청 GW API를 사용하여 특정 품목의 월별 실적을 가져옵니다."""
        try:
            unquoted_key = requests.utils.unquote(self.service_key)
            params = {
                "serviceKey": unquoted_key,
                "strtYymm": year_month,
                "endYymm": year_month,
                "hsSgn": hs_code
            }
            response = requests.get(self.url, params=params, timeout=15)
            if response.status_code == 200:
                return self.parse_xml(response.text, year_month, hs_code)
            else:
                return None, f"HTTP Error {response.status_code}"
        except Exception as e:
            return None, str(e)

    def parse_xml(self, xml_data, year_month, hs_code):
        try:
            root = ET.fromstring(xml_data)
            header = root.find('header')
            if header is not None:
                if header.findtext('resultCode') != '00':
                    return None, f"API Error: {header.findtext('resultMsg')}"

            items = []
            for item in root.findall('.//item'):
                hs_val = item.findtext('hsCode') or item.findtext('hsSgn')
                name_val = item.findtext('itemNm') or item.findtext('statItemNm')
                exp_val = item.findtext('expAmt') or item.findtext('expDlAmt') or '0'
                imp_val = item.findtext('impAmt') or item.findtext('impDlAmt') or '0'
                
                if hs_val:
                    items.append({
                        'year_month': year_month,
                        'hs_code': hs_val,
                        'item_name': name_val,
                        'exp_amount': float(str(exp_val).replace(',', '')),
                        'imp_amount': float(str(imp_val).replace(',', '')),
                    })
            return pd.DataFrame(items)
        except Exception as e:
            return None

class ECOSAPIClient:
    def __init__(self, service_key=ECOS_SERVICE_KEY):
        self.service_key = service_key
        self.base_url = ECOS_BASE_URL

    def fetch_service_trade_data(self, start_month, end_month):
        """
        한국은행 ECOS API를 통해 서비스 무역(BOP) 데이터를 가져오는 로직입니다.
        표코드: 102Y004 (국제수지 서비스)
        항목코드: 
          - S111 (컴퓨터 서비스)
          - S121 (정보 서비스)
          - S131 (통신 서비스)
        """
        # API 가이드: /api/StatisticSearch/[Key]/[Type]/[Language]/[Start]/[End]/[Table]/[Cycle]/[StartMonth]/[EndMonth]/[Item1]/...
        # M = Monthly
        results = []
        # 주요 ICT 서비스 항목 매핑
        items = {
            "S111": "컴퓨터서비스(SW)",
            "S121": "정보서비스",
            "S131": "통신서비스"
        }
        
        try:
            for code, name in items.items():
                url = f"{self.base_url}/{self.service_key}/xml/kr/1/100/102Y004/M/{start_month}/{end_month}/{code}/"
                response = requests.get(url, timeout=15)
                if response.status_code == 200:
                    df = self.parse_ecos_xml(response.text, name)
                    if df is not None:
                        results.append(df)
            
            if results:
                return pd.concat(results, ignore_index=True)
            return pd.DataFrame()
        except Exception as e:
            print(f"ECOS Error: {e}")
            return pd.DataFrame()

    def parse_ecos_xml(self, xml_data, service_name):
        try:
            root = ET.fromstring(xml_data)
            rows = []
            for row in root.findall('.//row'):
                rows.append({
                    'year_month': row.findtext('TIME'),
                    'service_name': service_name,
                    'exp_amount': float(row.findtext('DATA_VALUE')) # 국제수지는 보통 수출/수입이 별도 코드로 존재하나 여기서는 기본 실적으로 매핑
                })
            return pd.DataFrame(rows)
        except Exception:
            return None

if __name__ == "__main__":
    ecos = ECOSAPIClient()
    df = ecos.fetch_service_trade_data("202401", "202403")
    if not df.empty:
        print(df.head())
