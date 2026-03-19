import pandas as pd

# ICT 주요 품목 HS 코드 매핑 (대분류 기준)
ICT_CATEGORIES = {
    "반도체": ["8541", "8542"],
    "컴퓨터 및 주변기기": ["8471", "8473"],
    "통신장비": ["8517"],
    "디스플레이": ["8524", "8528", "9013"],
    "이차전지": ["8506", "8507"],
    "ICT 소부장": ["8486", "8532", "8533", "8534", "3818"], # 소재/부품/장비
}

# 세부 품목 확장 (소재, 부품, 장비 포함 약 50개)
ICT_DETAIL_ITEMS = {
    "메모리 반도체": "854232", "시스템 반도체": "854231", "D램": "85423210", "플래시메모리": "85423220",
    "반도체 제조장비": "848620", "노광장비": "84862010", "식각장비": "84862020", "이온주입기": "84862030",
    "MLCC": "853224", "인쇄회로기판(PCB)": "853400", "연성PCB": "85340010", "다층PCB": "85340020",
    "제조용 화학물": "381800", "실리콘웨이퍼": "38180010", "포토레지스트": "370790", "블랭크마스크": "700600",
    "휴대폰": "851713", "스마트폰": "85171310", "휴대폰용 부품": "851771", "안테나": "85177110",
    "컴퓨터": "847130", "노트북": "84713010", "태블릿": "84713020", "SSD": "847170",
    "모니터": "852852", "OLED": "852491", "LCD": "852411", "디스플레이 부품": "901380",
    "이차전지": "850760", "리튬이온배터리": "85076010", "양극재": "282590", "음극재": "380110",
    "분리막": "392190", "전해액": "382499", "네트워크장비": "851762", "라우터": "85176210",
    "스위치": "85176220", "기지국장비": "851761", "방송장비": "852550", "카메라모듈": "852589",
    "광학렌즈": "900211", "센서": "903289", "전력반도체": "854129", "LED": "854141",
    "태양전지": "854142", "웨어러블기기": "85176290", "스마트워치": "85176291", "VR/AR기기": "85285210",
    "산업용 로봇": "847950", "서빙 로봇": "84795010"
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
            return "기타 ICT"

        df['category'] = df['hs_code'].apply(get_category)
        return df

    def calculate_growth(self, current_df, prev_df):
        """
        당월 vs 전월 증감률을 계산합니다.
        """
        if current_df is None or prev_df is None:
            return current_df
        
        # 품목별로 정렬 및 병합
        merged = pd.merge(current_df, prev_df[['hs_code', 'item_name', 'exp_amount']], 
                          on=['hs_code', 'item_name'], suffixes=('_curr', '_prev'), how='left')
        merged['growth_amount'] = merged['exp_amount_curr'] - merged['exp_amount_prev'].fillna(0)
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
