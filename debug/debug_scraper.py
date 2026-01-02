"""
Debug script for LOF scraper
Tests individual components to identify issues
"""
import asyncio
import aiohttp
import logging
import json
from datetime import datetime, date, timedelta
import pandas as pd

from config import Config

class DebugScraper:
    """Debug version of scraper with detailed logging"""
    
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Add console handler for debug output
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console.setFormatter(formatter)
        self.logger.addHandler(console)
    
    async def test_connection(self):
        """Test basic connectivity to Jisilu"""
        self.logger.info("Testing connection to Jisilu...")
        
        async with aiohttp.ClientSession(headers=self.config.get_headers()) as session:
            try:
                # Test base URL
                async with session.get(self.config.BASE_URL, timeout=10) as response:
                    self.logger.info(f"Base URL status: {response.status}")
                    content = await response.text()
                    self.logger.info(f"Response size: {len(content)} bytes")
                    
                    # Check if we can access LOF pages
                    if "集思录" in content or "jisilu" in content.lower():
                        self.logger.info("✓ Successfully connected to Jisilu")
                        return True
                    else:
                        self.logger.error("✗ Unexpected response content")
                        return False
                        
            except Exception as e:
                self.logger.error(f"✗ Connection failed: {e}")
                return False
    
    async def test_lof_endpoint(self, lof_code: str = "161126"):
        """Test LOF endpoint with detailed logging"""
        self.logger.info(f"Testing LOF endpoint for code: {lof_code}")
        
        url = f"{self.config.LOF_DETAIL_URL}{lof_code}"
        params = {
            '___jsl': 'LST___t',
            'date': date.today().strftime('%Y-%m-%d')
        }
        
        self.logger.info(f"URL: {url}")
        self.logger.info(f"Params: {params}")
        
        async with aiohttp.ClientSession(headers=self.config.get_headers()) as session:
            try:
                async with session.get(url, params=params, timeout=10) as response:
                    self.logger.info(f"Response status: {response.status}")
                    self.logger.info(f"Response headers: {dict(response.headers)}")
                    
                    content = await response.text()
                    self.logger.info(f"Response size: {len(content)} bytes")
                    
                    # Try to parse as JSON
                    try:
                        data = json.loads(content)
                        self.logger.info("✓ JSON response received")
                        self.logger.info(f"Response keys: {list(data.keys())}")
                        
                        # Look for actual data
                        if 'cells' in data:
                            cells = data.get('cells', [])
                            self.logger.info(f"Found {len(cells)} cells")
                            if cells:
                                self.logger.info(f"First cell: {cells[0]}")
                        else:
                            self.logger.warning("No 'cells' found in response")
                            
                        return data
                        
                    except json.JSONDecodeError:
                        self.logger.error("✗ Invalid JSON response")
                        self.logger.info(f"First 500 chars: {content[:500]}")
                        return None
                        
            except Exception as e:
                self.logger.error(f"✗ Request failed: {e}")
                return None
    
    async def test_multiple_codes(self):
        """Test multiple LOF codes"""
        codes = Config.get_lof_codes()[:3]  # Test first 3 codes
        results = {}
        
        for code in codes:
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"Testing code: {code}")
            
            data = await self.test_lof_endpoint(code)
            results[code] = data
            
            if data and 'cells' in data:
                cells = data.get('cells', [])
                self.logger.info(f"✓ {code}: {len(cells)} records found")
            else:
                self.logger.warning(f"✗ {code}: No valid data")
        
        return results
    
    async def test_date_range(self, lof_code: str = "161126"):
        """Test different date ranges"""
        dates = [
            date.today() - timedelta(days=i) 
            for i in range(1, 6)  # Test last 5 days
        ]
        
        self.logger.info(f"Testing date ranges for {lof_code}")
        
        async with aiohttp.ClientSession(headers=self.config.get_headers()) as session:
            for test_date in dates:
                url = f"{self.config.LOF_DETAIL_URL}{lof_code}"
                params = {
                    '___jsl': 'LST___t',
                    'date': test_date.strftime('%Y-%m-%d')
                }
                
                try:
                    async with session.get(url, params=params, timeout=10) as response:
                        content = await response.text()
                        try:
                            data = json.loads(content)
                            cells = data.get('cells', [])
                            self.logger.info(f"{test_date}: {len(cells)} records")
                        except:
                            self.logger.warning(f"{test_date}: No valid JSON")
                            
                except Exception as e:
                    self.logger.error(f"{test_date}: Error - {e}")
    
    async def analyze_jisilu_structure(self):
        """Try to understand Jisilu's actual structure"""
        self.logger.info("Analyzing Jisilu structure...")
        
        # Test different possible endpoints
        possible_endpoints = [
            "https://www.jisilu.cn/data/lof/detail/",
            "https://www.jisilu.cn/data/qdii/detail/",
            "https://www.jisilu.cn/data/etf/detail/",
            "https://www.jisilu.cn/data/fund/detail/",
        ]
        
        test_code = "161126"
        test_date = date.today() - timedelta(days=1)
        
        async with aiohttp.ClientSession(headers=self.config.get_headers()) as session:
            for endpoint in possible_endpoints:
                self.logger.info(f"\nTesting endpoint: {endpoint}")
                
                try:
                    url = f"{endpoint}{test_code}"
                    params = {
                        '___jsl': 'LST___t',
                        'date': test_date.strftime('%Y-%m-%d')
                    }
                    
                    async with session.get(url, params=params, timeout=10) as response:
                        self.logger.info(f"Status: {response.status}")
                        content = await response.text()
                        
                        if len(content) > 100:  # Has actual content
                            try:
                                data = json.loads(content)
                                if 'cells' in data and data.get('cells'):
                                    self.logger.info(f"✓ Found data: {len(data['cells'])} records")
                                    self.logger.info(f"Endpoint: {endpoint}")
                                    return endpoint
                            except:
                                pass
                                
                        self.logger.info(f"✗ No data or invalid format")
                        
                except Exception as e:
                    self.logger.error(f"Error: {e}")
        
        return None

async def main():
    """Run debug tests"""
    print("🔍 Starting LOF scraper debug session...")
    
    scraper = DebugScraper()
    
    # Test 1: Basic connectivity
    print("\n1. Testing connectivity...")
    connected = await scraper.test_connection()
    
    if connected:
        print("\n2. Testing endpoint structure...")
        correct_endpoint = await scraper.analyze_jisilu_structure()
        if correct_endpoint:
            print(f"🎯 Found correct endpoint: {correct_endpoint}")
        
        print("\n3. Testing LOF endpoints...")
        await scraper.test_multiple_codes()
        
        print("\n4. Testing date ranges...")
        await scraper.test_date_range()
    else:
        print("❌ Cannot connect to Jisilu")

if __name__ == "__main__":
    asyncio.run(main())