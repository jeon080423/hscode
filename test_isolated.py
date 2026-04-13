from cache_manager import CacheManager
from api_client import CustomsAPIClient
from datetime import datetime, timedelta
import pandas as pd

end_date = datetime.now() - timedelta(days=30)
main_start_date = end_date - timedelta(days=31*11) # 약 12개월
curr_d = main_start_date.replace(day=1)
req_months = []
while curr_d <= end_date:
    req_months.append(curr_d.strftime("%Y%m"))
    if curr_d.month == 12:
        curr_d = curr_d.replace(year=curr_d.year + 1, month=1)
    else:
        curr_d = curr_d.replace(month=curr_d.month + 1)
        
yoy_target_date = end_date - timedelta(days=366)
yoy_target_month = yoy_target_date.strftime("%Y%m")
if yoy_target_month not in req_months:
    req_months.append(yoy_target_month)
req_months = sorted(list(set(req_months)))

missing_ranges = CacheManager.get_missing_ranges(req_months, [])
print("Missing ranges:", missing_ranges)

client = CustomsAPIClient()
code = '8542321010'
for start_m, end_m in missing_ranges:
    print(f"Fetching: {start_m} ~ {end_m}")
    df, err = client.fetch_monthly_data(start_m, end_m, code)
    if err:
        print("ERROR:", err)
    else:
        print("SUCCESS:", len(df))
