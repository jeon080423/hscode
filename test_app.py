from app import load_data
import os

try:
    if os.path.exists("data_cache.csv"):
        os.remove("data_cache.csv")
    print("Testing load_data without cache...")
    df = load_data(sim_mode=False)
    print("Loaded records:", len(df))
    if not df.empty:
        print("Error rows:", len(df[df['is_error'] == True]))
        if len(df[df['is_error'] == True]) > 0:
            print(df[df['is_error'] == True].head())
        else:
            print("Successfully loaded everything without errors.")
except Exception as e:
    import traceback
    traceback.print_exc()
