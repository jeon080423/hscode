import pandas as pd

# ICT 주요 품목 HS 코드 매핑 (대분류 기준)
ICT_CATEGORIES = {
    "반도체": ["8541", "8542"],
    "컴퓨터 및 주변기기": ["8471", "8473"],
    "통신장비": ["8517"],
    "디스플레이": ["8524", "8528", "9013"],
    "이차전지": ["8506", "8507"],
    "기타 ICT": ["84", "85", "90"] # 하위 제외한 나머지 (간략화)
}

# 세부 품목 예시 (박스/카드용)
ICT_DETAIL_ITEMS = {
    "메모리 반도체": "854232",
    "시스템 반도체": "854231",
    "휴대폰": "851713", # 851712/851713
    "SSD/HDD": "847170",
    "OLED": "852491", # Display 예시
}

class DataProcessor:
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
            return "기타"

        df['category'] = df['hs_code'].apply(get_category)
        return df

    def calculate_growth(self, current_df, prev_df):
        """
        당월 vs 전월 증감률을 계산합니다.
        """
        if current_df is None or prev_df is None:
            return None
        
        # 품목명/HS코드 기준으로 병합
        merged = pd.merge(current_df, prev_df, on=['hs_code', 'item_name'], suffixes=('_curr', '_prev'), how='left')
        merged['growth_amount'] = merged['exp_amount_curr'] - merged['exp_amount_prev']
        merged['growth_rate'] = (merged['growth_amount'] / merged['exp_amount_prev'] * 100).fillna(0)
        
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
