import data_processor
import pandas as pd
import datetime
import math
import time

def load_data_mock(months=132):
    end_date = datetime.datetime.now()
    dates = [(end_date - datetime.timedelta(days=30*i)).strftime("%Y%m") for i in range(months)]
    dates.sort()

    all_data = []
    items_list = list(data_processor.ICT_DETAIL_ITEMS.items())
    processor = data_processor.DataProcessor()

    for d in dates:
        year = int(d) // 100
        month = int(d) % 100
        growth_factor = (year - 2015) * 150
        df_month = pd.DataFrame({
            'year_month': d,
            'hs_code': [x[1] for x in items_list],
            'item_name': [x[0] for x in items_list],
            'exp_amount': [
                max(50,
                    int((abs(hash(x[0])) % 3000) + 200)
                    + growth_factor * (0.5 + (abs(hash(x[0])) % 100) / 100.0)
                    + int(300 * math.sin((month + (abs(hash(x[0])) % 6)) * math.pi / 6))
                    + month * (3 + (abs(hash(x[0])) % 15))
                )
                for x in items_list
            ],
            'imp_amount': [100 + (hash(x[0]) % 500) for x in items_list],
            'trade_balance': [0] * len(items_list)
        })
        df_month['trade_balance'] = df_month['exp_amount'] - df_month['imp_amount']
        all_data.append(df_month)

    combined = pd.concat(all_data, ignore_index=True)
    combined = processor.categorize_data(combined)
    return combined

start = time.time()
df = load_data_mock(132)
print(f"Loading 132 months took: {time.time()-start:.2f}s")
print(f"Total rows: {len(df)}")
