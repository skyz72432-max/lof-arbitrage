
"""
Debug script to check actual API response structure
"""
import requests
import json

url = "https://www.jisilu.cn/data/lof/hist_list/161126"
params = {
    '___jsl': 'LST___t',
    'rp': '50',
    'page': '1'
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
}

response = requests.get(url, params=params, headers=headers)
data = response.json()

print("📊 Full API Response Structure:")
print(json.dumps(data, indent=2, ensure_ascii=False))

# Check first row structure
if data.get('rows'):
    first_row = data['rows'][0]
    print("\n🔍 First row structure:")
    print(json.dumps(first_row, indent=2, ensure_ascii=False))
    
    if 'cell' in first_row:
        print("\n📋 All available columns in 'cell':")
        for key, value in first_row['cell'].items():
            print(f"  {key}: {value} ({type(value).__name__})")