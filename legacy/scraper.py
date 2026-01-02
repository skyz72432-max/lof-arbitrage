"""
High-concurrency web scraper for Jisilu LOF data
Provides async data fetching with retry mechanisms and rate limiting
"""
import asyncio
import aiohttp
import logging
import time
from datetime import datetime, date, timedelta
from typing import Dict, List, Any
import json
import pandas as pd
from dataclasses import dataclass
import random

from config import Config
from data_manager import DataManager

@dataclass
class ScrapingTask:
    """Represents a scraping task for a specific LOF and date"""
    lof_code: str
    date: datetime
    priority: int = 1
    retry_count: int = 0

class RateLimiter:
    """Rate limiter for controlling request frequency"""
    
    def __init__(self, rate: float):
        self.rate = rate
        self.min_interval = 1.0 / rate
        self.last_request_time = 0
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make a request"""
        async with self._lock:
            now = time.time()
            time_since_last = now - self.last_request_time
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                await asyncio.sleep(sleep_time)
            self.last_request_time = time.time()

class RetryHandler:
    """Handles retry logic with exponential backoff"""
    
    @staticmethod
    async def execute_with_retry(
        coro, 
        max_retries: int = 3, 
        base_delay: float = 1.0,
        max_delay: float = 30.0
    ):
        """Execute coroutine with exponential backoff retry"""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return await coro()
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                    logging.getLogger(__name__).warning(
                        f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logging.getLogger(__name__).error(f"All {max_retries + 1} attempts failed")
                    raise last_exception

class LOFScraper:
    """Main scraper class for fetching LOF data"""
    
    def __init__(self):
        self.config = Config()
        self.data_manager = DataManager()
        self.rate_limiter = RateLimiter(self.config.REQUESTS_PER_SECOND)
        self.logger = logging.getLogger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(
            limit=self.config.MAX_CONCURRENT_REQUESTS,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        timeout = aiohttp.ClientTimeout(total=self.config.REQUEST_TIMEOUT)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.config.get_headers()
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def fetch_lof_data(self, lof_code: str, target_date: date) -> List[Dict[str, Any]]:
        """Fetch data for a specific LOF on a specific date"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        await self.rate_limiter.acquire()
        
        url = f"{self.config.LOF_DETAIL_URL}{lof_code}"
        params = {
            '___jsl': 'LST___t',
            'rp': '50',
            'page': '1'
        }
        
        response = await RetryHandler.execute_with_retry(
            lambda: self._make_request(url, params),
            max_retries=self.config.MAX_RETRIES,
            base_delay=self.config.RETRY_DELAY
        )
        if response:
            return await self._parse_response(response, lof_code, target_date)
        return None
    
    async def _make_request(self, url: str, params: Dict[str, str]) -> aiohttp.ClientResponse:
        """Make HTTP request with error handling"""
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return response
                elif response.status == 429:  # Rate limited
                    raise aiohttp.ClientError(f"Rate limited: {response.status}")
                else:
                    raise aiohttp.ClientError(f"HTTP {response.status}")
        except asyncio.TimeoutError:
            raise aiohttp.ClientError("Request timeout")
        except Exception as e:
            raise aiohttp.ClientError(str(e))
    
    async def _parse_response(self, response: aiohttp.ClientResponse, lof_code: str, target_date: date) -> List[Dict[str, Any]]:
        """Parse response data"""
        try:
            text = await response.text()
            
            # Handle JSON response
            if 'application/json' in response.headers.get('content-type', ''):
                data = await response.json()
            else:
                # Try to parse as JSON anyway
                data = json.loads(text)
            
            # Extract relevant data based on Jisilu structure
            return self._extract_lof_data(data, lof_code, target_date)
            
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Error parsing response for {lof_code}: {e}")
            return None
    
    def _extract_lof_data(self, raw_data: Dict[str, Any], lof_code: str, target_date: date) -> List[Dict[str, Any]]:
        """Extract LOF data from Jisilu response"""
        if not isinstance(raw_data, dict):
            return []
        
        extracted_data = []
        
        # Jisilu response has 'rows' with 'cell' objects
        rows = raw_data.get('rows', [])
        
        for row in rows:
            if isinstance(row, dict) and 'cell' in row:
                cell = row['cell']
                
                # Extract data from Jisilu format
                record = {
                    'code': lof_code,
                    'date': cell.get('price_dt') or cell.get('net_value_dt'),
                    'timestamp': datetime.now().isoformat(),
                    'nav': cell.get('net_value'),
                    'price': cell.get('price'),
                    'premium': cell.get('discount_rt'),
                    'volume': cell.get('amount'),
                    'turnover': cell.get('amount'),  # Note: Jisilu uses 'amount' for turnover
                    'est_val': cell.get('est_val'),
                    'est_error_rt': cell.get('est_error_rt'),
                    'ref_increase_rt': cell.get('ref_increase_rt')
                }
                
                # Convert date format if needed
                if record['date']:
                    record['date'] = str(record['date'])
                
                extracted_data.append(record)
        
        return extracted_data
    
    async def fetch_lof_batch(self, tasks: List[ScrapingTask]) -> List[Dict[str, Any]]:
        """Fetch multiple LOF data points concurrently"""
        semaphore = asyncio.Semaphore(self.config.MAX_CONCURRENT_REQUESTS)
        
        async def fetch_single(task: ScrapingTask) -> List[Dict[str, Any]]:
            async with semaphore:
                try:
                    return await self.fetch_lof_data(task.lof_code, task.date)
                except Exception as e:
                    self.logger.error(f"Failed to fetch {task.lof_code} for {task.date}: {e}")
                    return None
        
        results = await asyncio.gather(*[fetch_single(task) for task in tasks], return_exceptions=True)
        
        # Filter out exceptions and None values
        valid_results = [r for r in results if isinstance(r, dict)]
        return valid_results
    
    async def sync_lof_data(self, lof_code: str, days_back: int = 15) -> int:
        """Sync data for a single LOF code"""
        self.logger.info(f"Fetching historical data for {lof_code}")
        
        # Fetch all available data for this LOF
        data = await self.fetch_lof_data(lof_code, date.today())
        
        if data:
            # Filter for recent data
            cutoff_date = date.today() - timedelta(days=days_back)
            filtered_data = [
                record for record in data 
                if record.get('date') and 
                pd.to_datetime(record['date']).date() >= cutoff_date
            ]
            
            if filtered_data:
                df = pd.DataFrame(filtered_data)
                self.data_manager.save_data(lof_code, df)
                logger.info(f"Saved {len(filtered_data)} records for {lof_code}")
                return len(filtered_data)
        
        return 0
    
    async def sync_all_lofs(self, days_back: int = 15) -> Dict[str, int]:
        """Sync data for all LOF codes"""
        lof_codes = Config.get_lof_codes()
        results = {}
        
        self.logger.info(f"Starting sync for {len(lof_codes)} LOF codes")
        
        for i, code in enumerate(lof_codes, 1):
            try:
                count = await self.sync_lof_data(code, days_back)
                results[code] = count
                self.logger.info(f"Progress: {i}/{len(lof_codes)} - {code}: {count} records")
            except Exception as e:
                self.logger.error(f"Failed to sync {code}: {e}")
                results[code] = 0
        
        return results

async def main():
    """Main execution function"""
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Config.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    
    async with LOFScraper() as scraper:
        results = await scraper.sync_all_lofs()
        
        total_records = sum(results.values())
        print(f"\nSync completed!")
        print(f"Total LOFs processed: {len(results)}")
        print(f"Total new records: {total_records}")
        
        # Print summary
        successful = {k: v for k, v in results.items() if v > 0}
        failed = {k: v for k, v in results.items() if v == 0}
        
        if successful:
            print(f"\nSuccessful ({len(successful)}):")
            for code, count in list(successful.items())[:10]:  # Show first 10
                print(f"  {code}: {count} records")
        
        if failed:
            print(f"\nFailed ({len(failed)}):")
            for code in list(failed.keys())[:10]:  # Show first 10
                print(f"  {code}")

if __name__ == "__main__":
    asyncio.run(main())