"""
Direct test of the Jisilu API endpoint
"""
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)

def test_direct_request():
    """Test direct HTTP request"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    test_code = "161126"
    url = f"https://www.jisilu.cn/data/lof/hist_list/{test_code}"
    params = {
        '___jsl': 'LST___t',
        'rp': '50',
        'page': '1'
    }
    
    print(f"Testing: {url}")
    print(f"Params: {params}")
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ SUCCESS!")
                print(f"Keys: {list(data.keys())}")
                
                if 'rows' in data:
                    print(f"Rows: {len(data['rows'])}")
                    if data['rows']:
                        print(f"Sample: {data['rows'][0]}")
                        
                        # Save sample
                        with open(f"sample_{test_code}.json", "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        print(f"Saved sample to sample_{test_code}.json")
                        
                        return data
                        
            except json.JSONDecodeError as e:
                print(f"❌ JSON Error: {e}")
                print(f"Response: {response.text[:500]}...")
        else:
            print(f"❌ HTTP {response.status_code}")
            print(f"Response: {response.text[:500]}...")
            
    except Exception as e:
        print(f"❌ Request Error: {e}")
    
    return None

if __name__ == "__main__":
    print("🧪 Testing direct Jisilu API access...")
    result = test_direct_request()
    
    if result:
        print(f"\n🎉 Successfully fetched {len(result.get('rows', []))} records")
    else:
        print("\n❌ Failed to fetch data")