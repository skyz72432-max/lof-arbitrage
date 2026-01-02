"""
Simple test with working endpoint
"""
import requests
import json
import pandas as pd
from datetime import date, timedelta

# Test a few LOF codes
codes = ["161126", "501312", "164906"]

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

def fetch_and_save_lof(code):
    """Fetch and save LOF data"""
    url = f"https://www.jisilu.cn/data/lof/hist_list/{code}"
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract rows
            rows = data.get('rows', [])
            
            if rows:
                # Convert to dataframe
                records = []
                for row in rows:
                    cell = row['cell']
                    record = {
                        'code': code,
                        'date': cell.get('price_dt'),
                        'nav': cell.get('net_value'),
                        'price': cell.get('price'),
                        'premium': cell.get('discount_rt'),
                        'volume': cell.get('amount'),
                        'turnover': cell.get('amount'),
                        'est_val': cell.get('est_val')
                    }
                    records.append(record)
                
                df = pd.DataFrame(records)
                
                # Save to CSV
                filename = f"data/lof_{code}.csv"
                df.to_csv(filename, index=False, encoding='utf-8-sig')
                print(f"✅ Saved {len(records)} records for {code} to {filename}")
                return len(records)
            else:
                print(f"⚠️ No data for {code}")
                return 0
        else:
            print(f"❌ HTTP {response.status_code} for {code}")
            return 0
            
    except Exception as e:
        print(f"❌ Error for {code}: {e}")
        return 0

if __name__ == "__main__":
    print("🧪 Testing corrected scraper with working endpoints...")
    
    total_records = 0
    for code in codes:
        count = fetch_and_save_lof(code)
        total_records += count
    
    print(f"\n🎯 Total: {total_records} records saved across {len(codes)} LOFs")