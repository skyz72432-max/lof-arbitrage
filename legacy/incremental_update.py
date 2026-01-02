
"""
Simple incremental data update script
Preserves existing historical data while adding new records
"""
import requests
import pandas as pd
import os
import json
import time
from datetime import datetime, timedelta

def load_existing_data(code):
    """Load existing data for a code"""
    filename = f"data/lof_{code}.csv"
    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename)
            df['price_dt'] = pd.to_datetime(df['price_dt'])
            return df
        except Exception as e:
            print(f"Error loading {code}: {e}")
    return pd.DataFrame()

def save_data(code, df):
    """Save updated data for a code"""
    filename = f"data/lof_{code}.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')

def fetch_new_data(code, days_back=1):
    """Fetch new data from API with T+1 handling"""
    url = f"https://www.jisilu.cn/data/lof/hist_list/{code}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    params = {
        '___jsl': 'LST___t',
        'rp': '50',
        'page': '1'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            rows = data.get('rows', [])
            
            if rows:
                records = []
                for row in rows:
                    cell = row['cell']
                    record = dict(cell)
                    record['code'] = code
                    
                    # Handle T+1 data delay: skip records with "-" discount_rt
                    if record.get('discount_rt') == "-":
                        continue
                        
                    records.append(record)
                
                new_df = pd.DataFrame(records)
                new_df['price_dt'] = pd.to_datetime(new_df['price_dt'])
                
                # Filter for recent days only
                if not new_df.empty:
                    cutoff_date = datetime.now() - timedelta(days=days_back*2)  # Allow buffer for T+1
                    new_df = new_df[new_df['price_dt'] >= cutoff_date]
                
                return new_df
        
        return pd.DataFrame()
        
    except Exception as e:
        print(f"Error fetching {code}: {e}")
        return pd.DataFrame()

def incremental_update(days_back=1):
    """Perform incremental update"""
    print(f"🔄 Starting incremental data update for {days_back} days...")
    
    # Read LOF codes
    try:
        # 获取当前脚本的绝对路径
        current_script_path = os.path.abspath(__file__)
        # 获取当前脚本所在目录
        current_script_dir = os.path.dirname(current_script_path)
        # 获取父目录
        parent_dir = os.path.dirname(current_script_dir)
        # 构建all_LOF.txt在父目录中的路径
        lof_file_path = os.path.join(parent_dir, 'all_LOF.txt')

        with open(lof_file_path, 'r', encoding='utf-8') as f:
            lof_codes = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("❌ all_LOF.txt not found")
        return
    
    total_new_records = 0
    updated_codes = 0
    
    for code in lof_codes:
        print(f"Processing {code}...")
        
        # Load existing data
        existing_df = load_existing_data(code)
        
        # Fetch new data
        new_df = fetch_new_data(code)
        
        if new_df.empty:
            print(f"  No new data for {code}")
            continue
        
        # Merge data, avoiding duplicates
        if not existing_df.empty:
            # Remove any existing records with same date
            existing_dates = set(existing_df['price_dt'])
            new_df = new_df[~new_df['price_dt'].isin(existing_dates)]
            
            if not new_df.empty:
                # Combine and sort
                combined_df = pd.concat([existing_df, new_df])
                combined_df = combined_df.sort_values('price_dt').reset_index(drop=True)
                save_data(code, combined_df)
                print(f"  Added {len(new_df)} new records, total: {len(combined_df)}")
                total_new_records += len(new_df)
                updated_codes += 1
            else:
                print(f"  No new records for {code}")
        else:
            # No existing data, save new data
            new_df = new_df.sort_values('price_dt').reset_index(drop=True)
            save_data(code, new_df)
            print(f"  Created new file with {len(new_df)} records")
            total_new_records += len(new_df)
            updated_codes += 1
        
        # Small delay to be respectful
        time.sleep(0.5)
    
    print(f"\n✅ Update complete!")
    print(f"📊 Updated {updated_codes} codes")
    print(f"📈 Added {total_new_records} new records")
    
    # Show summary
    total_records = 0
    for code in lof_codes:
        filename = f"data/lof_{code}.csv"
        if os.path.exists(filename):
            try:
                df = pd.read_csv(filename)
                total_records += len(df)
            except:
                pass
    
    print(f"📋 Total records across all LOFs: {total_records}")

if __name__ == "__main__":
    import sys
    days = 2 if len(sys.argv) > 1 and sys.argv[1] == "--days" else 1
    incremental_update(days)