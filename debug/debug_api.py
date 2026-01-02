"""
Debug script to find actual API endpoints for Jisilu LOF data
"""
import asyncio
import aiohttp
import logging
import json
import re
from datetime import date, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIFinder:
    """Find actual API endpoints by analyzing page structure"""
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://www.jisilu.cn'
        }
        self.session = aiohttp.ClientSession(headers=headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_page_content(self, url: str) -> str:
        """Get HTML content of the page"""
        try:
            async with self.session.get(url, timeout=10) as response:
                return await response.text()
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return ""
    
    async def extract_api_endpoints(self, lof_code: str = "161126"):
        """Extract API endpoints from HTML pages"""
        
        # Main LOF page
        urls_to_check = [
            f"https://www.jisilu.cn/data/lof/detail/{lof_code}",
            f"https://www.jisilu.cn/data/qdii/detail/{lof_code}",
            f"https://www.jisilu.cn/data/lof/",
            f"https://www.jisilu.cn/data/qdii/"
        ]
        
        endpoints = []
        
        for url in urls_to_check:
            logger.info(f"\n{'='*60}")
            logger.info(f"Analyzing: {url}")
            
            content = await self.get_page_content(url)
            if not content:
                continue
            
            # Look for JavaScript API calls
            api_patterns = [
                r'["\']([^"\']*api[^"\']*json[^"\']*)["\']',
                r'["\']([^"\']*data[^"\']*json[^"\']*)["\']',
                r'["\']([^"\']*fund[^"\']*json[^"\']*)["\']',
                r'["\']([^"\']*lof[^"\']*json[^"\']*)["\']',
                r'["\']([^"\']*qdii[^"\']*json[^"\']*)["\']',
                r'/data[^"\']*\.json[^"\']*',
                r'/ajax[^"\']*\.json[^"\']*',
                r'/api[^"\']*\.json[^"\']*',
            ]
            
            for pattern in api_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    logger.info(f"Found API pattern: {pattern}")
                    for match in matches[:5]:  # Show first 5 matches
                        logger.info(f"  - {match}")
                        endpoints.append(match)
            
            # Look for specific data endpoints
            if 'lof' in url.lower():
                # Try to find LOF-specific endpoints
                lof_patterns = [
                    r'/data/lof/[^"\']*',
                    r'/data/qdii/[^"\']*',
                    r'/ajax/lof[^"\']*',
                    r'/ajax/qdii[^"\']*',
                ]
                
                for pattern in lof_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        logger.info(f"Found LOF endpoint: {pattern}")
                        for match in matches[:3]:
                            logger.info(f"  - {match}")
                            endpoints.append(match)
        
        return list(set(endpoints))  # Remove duplicates
    
    async def test_json_endpoints(self, lof_code: str = "161126", test_date: date = None):
        """Test potential JSON endpoints"""
        if test_date is None:
            test_date = date.today() - timedelta(days=1)
        
        # Common Jisilu API patterns
        potential_endpoints = [
            # LOF endpoints
            f"https://www.jisilu.cn/data/lof/detail_hist/{lof_code}",
            f"https://www.jisilu.cn/data/lof/hist/{lof_code}",
            f"https://www.jisilu.cn/data/lof/detail_json/{lof_code}",
            f"https://www.jisilu.cn/data/lof/json/{lof_code}",
            f"https://www.jisilu.cn/ajax/lof/detail/{lof_code}",
            f"https://www.jisilu.cn/ajax/lof/history/{lof_code}",
            
            # QDII endpoints  
            f"https://www.jisilu.cn/data/qdii/detail_hist/{lof_code}",
            f"https://www.jisilu.cn/data/qdii/hist/{lof_code}",
            f"https://www.jisilu.cn/data/qdii/detail_json/{lof_code}",
            f"https://www.jisilu.cn/data/qdii/json/{lof_code}",
            f"https://www.jisilu.cn/ajax/qdii/detail/{lof_code}",
            f"https://www.jisilu.cn/ajax/qdii/history/{lof_code}",
            
            # Generic data endpoints
            f"https://www.jisilu.cn/data/fund/history/{lof_code}",
            f"https://www.jisilu.cn/data/fund/detail_json/{lof_code}",
            f"https://www.jisilu.cn/ajax/fund/history/{lof_code}",
            
            # With date parameters
            f"https://www.jisilu.cn/data/lof/detail/{lof_code}.json",
            f"https://www.jisilu.cn/data/qdii/detail/{lof_code}.json",
            f"https://www.jisilu.cn/data/fund/detail/{lof_code}.json",
        ]
        
        params_sets = [
            {'date': test_date.strftime('%Y-%m-%d')},
            {'trade_date': test_date.strftime('%Y-%m-%d')},
            {'day': test_date.strftime('%Y-%m-%d')},
            {'___jsl': 'LST___t', 'date': test_date.strftime('%Y-%m-%d')},
            {},
        ]
        
        working_endpoints = []
        
        for endpoint in potential_endpoints:
            logger.info(f"\nTesting: {endpoint}")
            
            for params in params_sets:
                try:
                    url = endpoint
                    async with self.session.get(url, params=params, timeout=10) as response:
                        content_type = response.headers.get('content-type', '')
                        
                        if 'json' in content_type:
                            try:
                                data = await response.json()
                                logger.info(f"✓ JSON found: {url} with params {params}")
                                logger.info(f"  Response keys: {list(data.keys())}")
                                working_endpoints.append({
                                    'url': str(response.url),
                                    'params': params,
                                    'data': data
                                })
                                return working_endpoints  # Return on first success
                            except:
                                pass
                        elif response.status == 200 and len(await response.text()) > 100:
                            # Check if it's JSON-like
                            text = await response.text()
                            try:
                                json.loads(text)
                                logger.info(f"✓ JSON-like response: {url}")
                                working_endpoints.append({
                                    'url': str(response.url),
                                    'params': params,
                                    'data': json.loads(text)
                                })
                                return working_endpoints
                            except:
                                pass
                        
                        if response.status != 404:
                            logger.info(f"  Status {response.status}, Content-Type: {content_type}")
                
                except Exception as e:
                    logger.debug(f"  Error: {e}")
        
        return working_endpoints
    
    async def analyze_page_structure(self):
        """Analyze the actual page structure"""
        lof_codes = ["161126", "501312", "164906"]
        
        for code in lof_codes[:1]:  # Test first code
            logger.info(f"\n{'='*80}")
            logger.info(f"Analyzing page structure for {code}")
            
            # Get the main page
            main_url = f"https://www.jisilu.cn/data/qdii/detail/{code}"
            content = await self.get_page_content(main_url)
            
            if content:
                # Look for JavaScript variables
                js_vars = re.findall(r'var\s+([^=]+)\s*=\s*([^;]+);', content)
                logger.info(f"Found {len(js_vars)} JavaScript variables")
                for var_name, var_value in js_vars[:10]:
                    logger.info(f"  {var_name.strip()} = {var_value.strip()}")
                
                # Look for data URLs
                data_urls = re.findall(r'["\']([^"\']*data[^"\']*["\']', content)
                logger.info(f"Found {len(data_urls)} potential data URLs")
                for url in data_urls[:10]:
                    logger.info(f"  {url}")
                
                # Look for AJAX calls
                ajax_patterns = [
                    r'\.ajax\([^)]*url["\']: *["\']([^"\']+)["\']',
                    r'\.getJSON\(["\']([^"\']+)["\']',
                    r'fetch\(["\']([^"\']+)["\']',
                ]
                
                for pattern in ajax_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        logger.info(f"Found AJAX pattern: {pattern}")
                        for match in matches:
                            logger.info(f"  - {match}")

async def main():
    async with APIFinder() as finder:
        print("🔍 Searching for Jisilu LOF API endpoints...")
        
        # Step 1: Extract endpoints from HTML
        endpoints = await finder.extract_api_endpoints("161126")
        print(f"\n📋 Found {len(endpoints)} potential endpoints")
        
        # Step 2: Test JSON endpoints
        results = await finder.test_json_endpoints("161126")
        if results:
            print(f"\n✅ Found working endpoints:")
            for result in results:
                print(f"  URL: {result['url']}")
                print(f"  Params: {result['params']}")
                print(f"  Data keys: {list(result['data'].keys())}")
        else:
            print("\n❌ No working JSON endpoints found")
        
        # Step 3: Analyze page structure
        await finder.analyze_page_structure()

if __name__ == "__main__":
    from datetime import timedelta
    asyncio.run(main())