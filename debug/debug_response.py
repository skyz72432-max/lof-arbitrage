"""
Debug script to examine actual response content
"""
import asyncio
import aiohttp
import logging
from datetime import date

from config import Config

class ResponseDebugger:
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.DEBUG)
    
    async def analyze_response(self, lof_code: str = "161126", test_date: date = None):
        """Examine actual response content"""
        if test_date is None:
            test_date = date.today() - timedelta(days=1)
        
        # Try different possible URL structures
        test_urls = [
            f"https://www.jisilu.cn/data/lof/detail/{lof_code}",
            f"https://www.jisilu.cn/data/qdii/detail/{lof_code}",
            f"https://www.jisilu.cn/data/fund/detail/{lof_code}",
            f"https://www.jisilu.cn/data/lof/history/{lof_code}",
            f"https://www.jisilu.cn/data/qdii/history/{lof_code}",
            f"https://www.jisilu.cn/data/etf/history/{lof_code}",
            f"https://www.jisilu.cn/data/lof/detail_{lof_code}.json",
            f"https://www.jisilu.cn/data/qdii/detail_{lof_code}.json",
        ]
        
        # Also test with different parameter structures
        test_params = [
            {'date': test_date.strftime('%Y-%m-%d')},
            {'trade_date': test_date.strftime('%Y-%m-%d')},
            {'day': test_date.strftime('%Y-%m-%d')},
            {'___jsl': 'LST___t', 'date': test_date.strftime('%Y-%m-%d')},
            {},  # No parameters
        ]
        
        async with aiohttp.ClientSession(headers=self.config.get_headers()) as session:
            for url in test_urls:
                print(f"\n{'='*60}")
                print(f"Testing URL: {url}")
                print(f"Date: {test_date}")
                
                for params in test_params:
                    print(f"\nParameters: {params}")
                    
                    try:
                        async with session.get(url, params=params, timeout=10) as response:
                            print(f"Status: {response.status}")
                            print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
                            
                            content = await response.text()
                            content_length = len(content)
                            print(f"Content length: {content_length}")
                            
                            if content_length < 1000:
                                print(f"Full content: {content}")
                            else:
                                print(f"First 1000 chars: {content[:1000]}")
                                
                            # Check for redirects
                            if response.history:
                                print(f"Redirects: {[str(r.url) for r in response.history]}")
                            
                            # Check final URL
                            print(f"Final URL: {response.url}")
                            
                            # Look for common patterns
                            if 'json' in response.headers.get('content-type', ''):
                                print("✓ JSON response detected")
                            elif 'html' in response.headers.get('content-type', ''):
                                print("⚠ HTML response (may need different approach)")
                                # Look for specific patterns
                                if 'cells' in content:
                                    print("✓ Found 'cells' in content")
                                if 'fund' in content.lower():
                                    print("✓ Found fund-related content")
                                if 'nav' in content.lower():
                                    print("✓ Found NAV-related content")
                            
                            print("-" * 40)
                            
                    except Exception as e:
                        print(f"Error: {e}")
                        print("-" * 40)

if __name__ == "__main__":
    from datetime import timedelta
    
    debugger = ResponseDebugger()
    asyncio.run(debugger.analyze_response("161126", date.today() - timedelta(days=1)))