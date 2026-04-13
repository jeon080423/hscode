import pandas as pd

# ICT 주요 품목 매핑 (HS 코드 대분류 기준)
ICT_CATEGORIES = {
    "전자부품": ["8542", "8541", "8524", "8532", "8533", "8534", "8540", "8513"],
    "컴퓨터 및 주변기기": ["8471", "8473"],
    "정보통신응용기반기기": ["90", "84", "8508", "8509", "8516"], # 계측기, 사무기기, 가전제품(청소기, 전열기기 등)
    "방송장비": ["8525", "8528"],
    "통신장비": ["8517"],
    "음향 및 영상기기": ["8518", "8519", "8521", "8522", "8527"],
}

# 세부 품목 확장 (관세청 HS 코드 기준)
ICT_DETAIL_ITEMS = {
    "DRAM": "8542321010",
    "Flash 메모리": "8542321020",
    "마이크로컴포넌트": "8542311020",
    "Logics": "8542311010",
    "보조기억장치": "847170",
    "광전자": "854141",
    "기타 메모리반도체": "85423290",
    "반도체 개별소자": "8541",
    "아날로그IC, 디지털IC 부품": "854239",
    "계측기": "9030",
    "변성기": "850421",
    "아날로그 IC": "854233",
    "기타 디지털 IC": "854239",
    "LCD 패널": "852411",
    "OLED 패널": "852412",
    "실리콘웨이퍼": "381800",
    "센서": "854143",
    "PCB": "853400",
    "전자관": "8540",
    "냉장고": "8418",
    "세탁기": "8450",
    "에어컨": "8415",
    "전자레인지": "851650",
    "공기청정기": "842139",
    "진공청소기": "8508",
    "식기세척기": "842211",
    "가정용 선풍기": "841451",
    "정수기": "842121",
    "전기밥솥": "851660",
    "사무용기기": "8472",

    "컴퓨터부품": "847330",
    "데스크탑PC": "847141",
    "중대형컴퓨터": "847149",
    "노트북PC": "847130",
    "휴대폰": "851713", # 스마트폰
    "기지국 장비": "851761",
    "네트워크 장비": "851762",
    "TV 수상기": "852872",
    "디지털 카메라": "852581",
    "스피커": "851821",
    "헤드폰 및 이어폰": "851830",
    "디지털 영상 플레이어": "16220000",
    "빔 프로젝터": "16230000",
    "영상기기 부품": "16290000",
    "홈시어터 시스템": "16310000",
    "기타 음향 및 영상기기": "16900000",
}


class DataProcessor:
    # v1.1: Added YoY growth calculation support
    def __init__(self):
        pass

    def categorize_data(self, df):
        """
        HS 코드를 기반으로 대분류를 할당합니다.
        """
        if df is None or df.empty:
            return df

        def get_category(hs):
            hs_str = str(hs).replace('.', '')
            for cat, codes in ICT_CATEGORIES.items():
                if any(hs_str.startswith(code) for code in codes):
                    return cat
            return "기타 ICT"

        df['category'] = df['hs_code'].apply(get_category)
        return df

    def calculate_growth(self, current_df, prev_df, yoy_df=None):
        """
        당월 vs 전월(MoM) 및 당월 vs 전년동월(YoY) 증감률을 계산합니다.
        집계(aggregation) 이후 hs_code가 월별로 다를 수 있으므로 item_name 기준으로 merge합니다.
        """
        if current_df is None or prev_df is None:
            return current_df

        # 전월 데이터 병합 (MoM) - item_name 기준
        merged = pd.merge(current_df, prev_df[['item_name', 'exp_amount']],
                          on='item_name', suffixes=('_curr', '_prev'), how='left')
        merged['growth_amount'] = merged['exp_amount_curr'] - merged['exp_amount_prev'].fillna(0)
        merged['growth_rate'] = (merged['growth_amount'] / merged['exp_amount_prev'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)

        # 전년동월 데이터 병합 (YoY) - item_name 기준
        if yoy_df is not None and not yoy_df.empty:
            merged = pd.merge(merged, yoy_df[['item_name', 'exp_amount']],
                              on='item_name', how='left')
            merged = merged.rename(columns={'exp_amount': 'exp_amount_yoy'})
            merged['growth_amount_yoy'] = merged['exp_amount_curr'] - merged['exp_amount_yoy'].fillna(0)
            merged['growth_rate_yoy'] = (merged['growth_amount_yoy'] / merged['exp_amount_yoy'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
        else:
            merged['growth_rate_yoy'] = 0.0

        return merged

    def get_time_series_data(self, data_list):
        """
        여러 달의 데이터를 병합하여 시계열 데이터프레임을 생성합니다.
        data_list: List of DataFrames
        """
        if not data_list:
            return pd.DataFrame()

        combined = pd.concat(data_list, ignore_index=True)
        return combined

    def get_service_trade_data(self, months_list, ecos_client=None):
        """
        한국은행(BOK) 실측 데이터 또는 시뮬레이션을 통해 서비스 무역 데이터를 생성합니다.
        """
        # 실측 API 클라이언트가 제공된 경우 실제 호출 시도
        if ecos_client:
            start_month = min(months_list)
            end_month = max(months_list)
            df = ecos_client.fetch_service_trade_data(start_month, end_month)
            if df is not None and not df.empty:
                return df

        # API 실패 시 또는 클라이언트 없을 시 시뮬레이션 데이터 반환 (원활한 화면 구성을 위해)
        service_items = {
            "컴퓨터서비스(SW)": {"base": 800, "growth": 1.2},
            "정보서비스": {"base": 300, "growth": 1.1},
            "통통신서비스": {"base": 200, "growth": 1.05},
            "기타 지식서비스": {"base": 150, "growth": 1.08}
        }
        
        all_service_data = []
        for yyyymm in months_list:
            if not yyyymm or len(yyyymm) < 4:
                continue
            try:
                year = int(yyyymm[:4])
                month = int(yyyymm[4:])
            except (ValueError, IndexError):
                continue
            
            for item, specs in service_items.items():
                growth_factor = (year - 2020) * 50
                val = specs["base"] + growth_factor + (month * 10)
                import random
                val = val * random.uniform(0.95, 1.05)
                
                all_service_data.append({
                    "year_month": yyyymm,
                    "service_name": item,
                    "exp_amount": round(val, 1),
                    "imp_amount": round(val * 0.7, 1)
                })
        
        return pd.DataFrame(all_service_data)
