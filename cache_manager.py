import pandas as pd
import os
from datetime import datetime

CACHE_FILE = "data_cache.csv"

class CacheManager:
    @staticmethod
    def load_cache():
        if os.path.exists(CACHE_FILE):
            try:
                # dtype 설정으로 hs_code가 0으로 시작하는 경우 잘리는 현상 방지
                return pd.read_csv(CACHE_FILE, dtype={'year_month': str, 'hs_code': str, 'req_code': str})
            except Exception as e:
                print(f"Cache load error: {e}")
                return pd.DataFrame()
        return pd.DataFrame()

    @staticmethod
    def save_to_cache(df):
        if df is None or df.empty:
            return
            
        try:
            if os.path.exists(CACHE_FILE):
                existing_df = CacheManager.load_cache()
                if not existing_df.empty:
                    # 기존 캐시와 새 데이터를 합친 후 중복 제거 (req_code, year_month, hs_code 기준)
                    combined = pd.concat([existing_df, df], ignore_index=True)
                    combined = combined.drop_duplicates(subset=['req_code', 'year_month', 'hs_code'], keep='last')
                    combined.to_csv(CACHE_FILE, index=False)
                    return
            
            # 파일이 없거나 기존 데이터가 없는 경우 새로 저장
            df.to_csv(CACHE_FILE, index=False)
        except Exception as e:
            print(f"Cache save error: {e}")

    @staticmethod
    def get_missing_ranges(required_months, cached_months):
        """
        필요한 월과 캐시에 있는 월을 비교하여, 누락된 월들을 연속된 구간(Start, End)의 리스트로 반환합니다.
        예: ['202301', '202302', '202305'] -> [('202301', '202302'), ('202305', '202305')]
        """
        missing = sorted(list(set(required_months) - set(cached_months)))
        if not missing:
            return []

        ranges = []
        range_start = missing[0]
        prev = missing[0]

        for current in missing[1:]:
            # current가 prev의 바로 다음 달인지 확인
            try:
                prev_date = datetime.strptime(prev, "%Y%m")
                curr_date = datetime.strptime(current, "%Y%m")
                
                # 년월 계산에서 다음 달 구하기
                next_month = prev_date.month + 1
                next_year = prev_date.year
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                    
                expected_next = f"{next_year}{next_month:02d}"
                
                if current == expected_next:
                    prev = current
                else:
                    ranges.append((range_start, prev))
                    range_start = current
                    prev = current
            except Exception:
                # 파싱 에러 시 그냥 끊어줌
                ranges.append((range_start, prev))
                range_start = current
                prev = current
                
        ranges.append((range_start, prev))
        return ranges
