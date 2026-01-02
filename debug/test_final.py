"""
Final test of the corrected scraper
"""
import asyncio
import logging
from datetime import date

from scraper import LOFScraper
from config import Config

async def final_test():
    """Final comprehensive test"""
    logging.basicConfig(level=logging.INFO)
    
    print("🚀 Final Test: Corrected Jisilu LOF Scraper")
    print("=" * 50)
    
    # Get available LOF codes
    codes = Config.get_lof_codes()
    print(f"📋 Found {len(codes)} LOF codes")
    
    if not codes:
        print("❌ No codes found")
        return
    
    print("First 5 codes:", codes[:5])
    
    async with LOFScraper() as scraper:
        print("\n🔍 Testing individual LOF...")
        
        # Test first code
        test_code = codes[0]
        print(f"Testing: {test_code}")
        
        try:
            count = await scraper.sync_lof_data(test_code, days_back=7)
            print(f"✅ Fetched {count} records for {test_code}")
            
            # Test sync all (first 3 only)
            print(f"\n📊 Testing sync for first 3 LOFs...")
            results = {}
            
            for code in codes[:3]:
                count = await scraper.sync_lof_data(code, days_back=5)
                results[code] = count
                print(f"  {code}: {count} records")
            
            total = sum(results.values())
            print(f"\n🎯 SUMMARY:")
            print(f"  Total records: {total}")
            print(f"  Successful codes: {len([c for c, v in results.items() if v > 0])}")
            print(f"  Data saved to: ./data/ directory")
            
            # Show file contents
            import pandas as pd
            import os
            
            for code in codes[:1]:  # Show first file
                filename = f"data/lof_{code}.csv"
                if os.path.exists(filename):
                    df = pd.read_csv(filename)
                    print(f"\n📈 Sample data for {code}:")
                    print(df.head(3))
                    print(f"Columns: {list(df.columns)}")
                break
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(final_test())