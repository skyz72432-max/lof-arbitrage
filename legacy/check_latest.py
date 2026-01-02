
"""
Quick check to verify latest data availability
"""
import pandas as pd
import os
import glob

def check_latest_data():
    """Check latest dates across all LOF files"""
    csv_files = glob.glob('data/lof_*.csv')
    
    latest_dates = {}
    total_records = 0
    
    for file in csv_files:
        code = file.replace('data/lof_', '').replace('.csv', '')
        try:
            df = pd.read_csv(file)
            df['price_dt'] = pd.to_datetime(df['price_dt'])
            latest_date = df['price_dt'].max()
            record_count = len(df)
            latest_dates[code] = {
                'latest_date': latest_date.strftime('%Y-%m-%d'),
                'record_count': record_count
            }
            total_records += record_count
        except Exception as e:
            print(f"Error reading {file}: {e}")
    
    # Sort by latest date
    sorted_dates = sorted(latest_dates.items(), key=lambda x: x[1]['latest_date'], reverse=True)
    
    print("📊 Latest data summary:")
    print("=" * 50)
    
    # Show first 10 entries
    for code, info in sorted_dates[:10]:
        print(f"{code}: {info['latest_date']} ({info['record_count']} records)")
    
    print("=" * 50)
    print(f"Total LOFs: {len(latest_dates)}")
    print(f"Total records: {total_records}")
    
    # Check if any have data beyond July 22
    july_22_count = sum(1 for _, info in latest_dates.items() if info['latest_date'] >= '2025-07-22')
    july_23_count = sum(1 for _, info in latest_dates.items() if info['latest_date'] >= '2025-07-23')
    
    print(f"LOFs with July 22+ data: {july_22_count}")
    print(f"LOFs with July 23+ data: {july_23_count}")

if __name__ == "__main__":
    check_latest_data()