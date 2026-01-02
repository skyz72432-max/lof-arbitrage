"""
Debug script to test the correct API endpoints
"""
import asyncio
import aiohttp
import json
import logging
from datetime import date, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_correct_endpoints():
    """Test the correct Jisilu API endpoints"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://www.jisilu.cn'
    }
    
    test_code = "161126"
    test_date = date.today() - timedelta(days=1)
    
    # Correct endpoints based on debug findings
    correct_endpoints = [
        "/data/lof/hist_list/",
        "/data/qdii/hist_list/",
        "/data/lof/detail_list/",
        "/data/qdii/detail_list/",
        "/ajax/lof/hist_list/",
        "/ajax/qdii/hist_list/",
    ]
    
    params_sets = [
        {'___jsl': 'LST___t'},
        {'is_search': '1', 'rp': '50'},
        {'rp': '50', 'page': '1'},
        {},
    ]
    
    async with aiohttp.ClientSession(headers=headers) as session:
        for endpoint in correct_endpoints:
            full_url = f"https://www.jisilu.cn{endpoint}{test_code}"
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing: {full_url}")
            
            for params in params_sets:
                try:
                    async with session.get(full_url, params=params, timeout=10) as response:
                        content_type = response.headers.get('content-type', '')
                        logger.info(f"Status: {response.status}")
                        logger.info(f"Content-Type: {content_type}")
                        
                        if response.status == 200:
                            text = await response.text()
                            
                            # Try to parse as JSON
                            try:
                                data = json.loads(text)
                                logger.info(f"✅ SUCCESS! JSON response")
                                logger.info(f"Keys: {list(data.keys())}")
                                
                                # Check for data structure
                                if 'rows' in data:
                                    logger.info(f"Rows: {len(data['rows'])} records")
                                    if data['rows']:
                                        logger.info(f"First row: {data['rows'][0]}")
                                elif 'data' in data:
                                    logger.info(f"Data: {len(data['data'])} records")
                                elif 'cells' in data:
                                    logger.info(f"Cells: {len(data['cells'])} records")
                                
                                return {
                                    'url': str(response.url),
                                    'params': params,
                                    'data': data
                                }
                                
                            except json.JSONDecodeError:
                                logger.info(f"❌ Not JSON: {text[:200]}...")
                        else:
                            logger.info(f"❌ HTTP {response.status}")
                
                except Exception as e:
                    logger.error(f"Error: {e}")
    
    return None

async def test_specific_date_endpoint():
    """Test specific date-based endpoints"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    test_code = "161126"
    test_date = date.today() - timedelta(days=1)
    
    # Test the specific endpoints that were found
    specific_endpoints = [
        # These are the actual Jisilu API endpoints
        f"https://www.jisilu.cn/data/lof/detail_list/{test_code}",
        f"https://www.jisilu.cn/data/qdii/detail_list/{test_code}",
        f"https://www.jisilu.cn/data/lof/hist_list/{test_code}",
        f"https://www.jisilu.cn/data/qdii/hist_list/{test_code}",
        
        # With parameters
        f"https://www.jisilu.cn/data/qdii/detail_list/{test_code}",
        f"https://www.jisilu.cn/data/lof/detail_list/{test_code}",
    ]
    
    params = {
        '___jsl': 'LST___t',
        'rp': '50',
        'page': '1'
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        for endpoint in specific_endpoints:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing specific: {endpoint}")
            
            try:
                async with session.get(endpoint, params=params, timeout=10) as response:
                    logger.info(f"Status: {response.status}")
                    
                    if response.status == 200:
                        text = await response.text()
                        
                        # Check if it's JSON
                        if text.strip().startswith('{') or text.strip().startswith('['):
                            try:
                                data = json.loads(text)
                                logger.info(f"✅ JSON FOUND!")
                                logger.info(f"Keys: {list(data.keys())}")
                                
                                if 'rows' in data:
                                    logger.info(f"Rows count: {len(data.get('rows', []))}")
                                    if data.get('rows'):
                                        logger.info(f"Sample row: {data['rows'][0]}")
                                        
                                return {
                                    'endpoint': endpoint,
                                    'params': params,
                                    'data': data
                                }
                                
                            except json.JSONDecodeError:
                                logger.info(f"❌ Not valid JSON: {text[:200]}...")
                        else:
                            logger.info(f"❌ Not JSON: {text[:200]}...")
                            
            except Exception as e:
                logger.error(f"Error: {e}")
    
    return None

async def main():
    print("🔍 Testing correct Jisilu LOF endpoints...")
    
    # Test 1: General endpoints
    result1 = await test_correct_endpoints()
    if result1:
        print(f"\n🎉 Found working endpoint: {result1['url']}")
        return result1
    
    # Test 2: Specific endpoints
    result2 = await test_specific_date_endpoint()
    if result2:
        print(f"\n🎉 Found working endpoint: {result2['endpoint']}")
        return result2
    
    print("\n❌ No working endpoints found")
    return None

if __name__ == "__main__":
    asyncio.run(main())