import pandas as pd
import data_processor
import datetime

dp = data_processor.DataProcessor()

# Mock data
data = []
# Create data for 202602, 202601, and 202502
months = ["202602", "202601", "202502"]
for m in months:
    data.append({
        "year_month": m,
        "hs_code": "8542321010",
        "item_name": "DRAM",
        "exp_amount": 1000 if m == "202602" else (800 if m == "202601" else 900)
    })

df = pd.DataFrame(data)

curr_df = df[df['year_month'] == "202602"]
prev_df = df[df['year_month'] == "202601"]
yoy_df = df[df['year_month'] == "202502"]

result = dp.calculate_growth(curr_df, prev_df, yoy_df)

print("Columns in result:", result.columns.tolist())
print("\nResult Data:")
print(result[['item_name', 'exp_amount_curr', 'exp_amount_prev', 'exp_amount_yoy', 'growth_rate', 'growth_rate_yoy']])

# Check if KeyError still exists in logic like app.py
try:
    row = result.iloc[0]
    mom = row['growth_rate']
    yoy = row['growth_rate_yoy']
    print("\nAccess check: SUCCESS")
    print(f"MoM: {mom:.1f}%, YoY: {yoy:.1f}%")
except Exception as e:
    print(f"\nAccess check: FAILED - {e}")
