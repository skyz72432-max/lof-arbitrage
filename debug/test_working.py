"""
Test the working scraper with actual Jisilu data
"""
import asyncio
import logging
from datetime import date

from scraper import LOFScraper
from config import Config

async def test_single_lof():
    """Test a single LOF code"""
    logging.basicConfig(level=logging.INFO)
    
    print("🧪 Testing corrected scraper...")
    
    # Get test codes
    codes = Config.get_lof_codes()
    if not codes:
        print("❌ No LOF codes found")
        return
    
    test_code = codes[0]  # Test first code
    print(f"📊 Testing code: {test_code}")
    
    async with LOFScraper() as scraper:
        try:
            # Test single LOF
            count = await scraper.sync_lof_data(test_code, days_back=15)
            print(f"✅ Successfully saved {count} records for {test_code}")
            
            # Test all LOFs (first 3 only for testing)
            print(f"\n📈 Testing first 3 LOFs...")
            results = {}
            for code in codes[:3]:
                count = await scraper.sync_lof_data(code, days_back=7)
                results[code] = count
                print(f"  {code}: {count} records")
            
            total = sum(results.values())
            print(f"\n🎯 Total: {total} records across {len(results)} LOFs")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_single_lof())