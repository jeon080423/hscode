import requests
import xml.etree.ElementTree as ET
import pandas as pd
import datetime

import streamlit as st

# 서비스키 로드 함수
def get_secret(key_name, default_value=""):
    try:
        if key_name in st.secrets:
            return st.secrets[key_name]
    except Exception:
        pass
    return default_value

# 공공데이터포털 서비스키 (관세청)
CUSTOMS_SERVICE_KEY = get_secret("CUSTOMS_SERVICE_KEY", "6be75af37c6693a24417c2ed2930e4bd4dd01dddf289552260ce8ce1daf43414")
# 관세청_품목별 수출입실적(GW) 정식 서비스 엔드포인트
CUSTOMS_BASE_URL = "https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList"

# 한국은행 ECOS 서비스키
ECOS_SERVICE_KEY = get_secret("ECOS_SERVICE_KEY", "Q33UM6GK6QDQ46NEH83B")
ECOS_BASE_URL = "http://ecos.bok.or.kr/api/StatisticSearch"

class CustomsAPIClient:
    def __init__(self, service_key=CUSTOMS_SERVICE_KEY):
        self.service_key = service_key
        self.url = CUSTOMS_BASE_URL

    def fetch_monthly_data(self, start_month, end_month, hs_code):
        """기간별 품목 수출입 실적을 조회합니다."""
        try:
            unquoted_key = requests.utils.unquote(self.service_key)
            params = {
                "serviceKey": unquoted_key,
                "strtYymm": start_month,
                "endYymm": end_month,
                "hsSgn": hs_code,
                "type": "xml"
            }
            response = requests.get(self.url, params=params, timeout=15)
            if response.status_code == 200:
                if "<item>" in response.text:
                    result, err = self.parse_xml(response.text)
                    return result, err
                elif "resultCode" in response.text:
                    # 에러 태그 파싱 시도
                    _, err = self.parse_xml(response.text)
                    return pd.DataFrame(), err or "No Data"
                else:
                    return pd.DataFrame(), "Empty Response"
            else:
                return None, f"HTTP {response.status_code}"
        except Exception as e:
            return None, str(e)

    def parse_xml(self, xml_data):
        try:
            root = ET.fromstring(xml_data)
            header = root.find('header')
            if header is not None:
                if header.findtext('resultCode') != '00':
                    return None, f"API Error: {header.findtext('resultMsg')}"

            items = []
            for item in root.findall('.//item'):
                # XML 태그 바리에이션 대응 (신규 키 규격 포함)
                stat_month = (item.findtext('statYymm') or 
                              item.findtext('year') or "").replace('.', '') # 2024.12 -> 202412
                
                hs_val = item.findtext('hsSgn') or item.findtext('hsCode')
                
                name_val = (item.findtext('statItemNm') or 
                            item.findtext('itemNm') or 
                            item.findtext('statKor'))
                
                exp_val = (item.findtext('expDlAmt') or 
                           item.findtext('expAmt') or 
                           item.findtext('expDlr') or '0')
                
                imp_val = (item.findtext('impDlAmt') or 
                           item.findtext('impAmt') or 
                           item.findtext('impDlr') or '0')
                
                if hs_val and stat_month:
                    items.append({
                        'year_month': stat_month[:6],
                        'hs_code': hs_val,
                        'item_name': name_val,
                        'exp_amount': float(str(exp_val).replace(',', '')),
                        'imp_amount': float(str(imp_val).replace(',', '')),
                    })
            return pd.DataFrame(items), None
        except Exception as e:
            return None, str(e)

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
