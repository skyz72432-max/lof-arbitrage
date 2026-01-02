"""
Semi-automatic data synchronization system
Provides cron-like scheduling and incremental updates
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any
import json
from pathlib import Path

from scraper import LOFScraper
from data_manager import DataManager
from date_handler import DateHandler, DataCompatibilityManager
from config import Config

class SyncManager:
    """Manages semi-automatic data synchronization"""
    
    def __init__(self):
        self.config = Config()
        self.data_manager = DataManager()
        self.date_handler = DateHandler()
        self.compatibility_manager = DataCompatibilityManager()
        self.logger = logging.getLogger(__name__)
        
        # Sync state tracking
        self.sync_state_file = Path(self.config.DATA_DIR) / "sync_state.json"
        self.last_sync = self._load_sync_state()
        
    def _load_sync_state(self) -> Dict[str, Any]:
        """Load last synchronization state"""
        if self.sync_state_file.exists():
            try:
                with open(self.sync_state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading sync state: {e}")
        
        return {
            "last_full_sync": None,
            "last_incremental_sync": None,
            "failed_codes": [],
            "success_count": 0,
            "total_records": 0
        }
    
    def _save_sync_state(self):
        """Save synchronization state"""
        try:
            with open(self.sync_state_file, 'w', encoding='utf-8') as f:
                json.dump(self.last_sync, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving sync state: {e}")
    
    async def incremental_sync(self, days_back: int = 1) -> Dict[str, Any]:
        """Perform incremental sync for recent missing data"""
        self.logger.info("Starting incremental sync...")
        
        start_time = datetime.now()
        lof_codes = Config.get_lof_codes()
        
        results = {
            "sync_type": "incremental",
            "start_time": start_time.isoformat(),
            "total_codes": len(lof_codes),
            "successful_codes": 0,
            "failed_codes": [],
            "total_records": 0,
            "errors": []
        }
        
        async with LOFScraper() as scraper:
            for code in lof_codes:
                try:
                    count = await scraper.sync_lof_data(code, days_back)
                    if count > 0:
                        results["successful_codes"] += 1
                        results["total_records"] += count
                    else:
                        results["failed_codes"].append(code)
                        
                except Exception as e:
                    self.logger.error(f"Failed to sync {code}: {e}")
                    results["failed_codes"].append(code)
                    results["errors"].append({"code": code, "error": str(e)})
        
        # Update sync state
        self.last_sync["last_incremental_sync"] = start_time.isoformat()
        self.last_sync["success_count"] = results["successful_codes"]
        self.last_sync["total_records"] += results["total_records"]
        self.last_sync["failed_codes"] = results["failed_codes"]
        self._save_sync_state()
        
        results["end_time"] = datetime.now().isoformat()
        results["duration_seconds"] = (datetime.now() - start_time).total_seconds()
        
        self.logger.info(f"Incremental sync completed: {results['total_records']} records for {results['successful_codes']} codes")
        return results
    
    async def full_sync(self, days_back: int = 30) -> Dict[str, Any]:
        """Perform full sync for all historical data"""
        self.logger.info("Starting full sync...")
        
        start_time = datetime.now()
        lof_codes = Config.get_lof_codes()
        
        results = {
            "sync_type": "full",
            "start_time": start_time.isoformat(),
            "total_codes": len(lof_codes),
            "successful_codes": 0,
            "failed_codes": [],
            "total_records": 0,
            "errors": []
        }
        
        async with LOFScraper() as scraper:
            for code in lof_codes:
                try:
                    count = await scraper.sync_lof_data(code, days_back)
                    if count > 0:
                        results["successful_codes"] += 1
                        results["total_records"] += count
                    else:
                        results["failed_codes"].append(code)
                        
                except Exception as e:
                    self.logger.error(f"Failed to sync {code}: {e}")
                    results["failed_codes"].append(code)
                    results["errors"].append({"code": code, "error": str(e)})
        
        # Update sync state
        self.last_sync["last_full_sync"] = start_time.isoformat()
        self.last_sync["success_count"] = results["successful_codes"]
        self.last_sync["total_records"] = results["total_records"]
        self.last_sync["failed_codes"] = results["failed_codes"]
        self._save_sync_state()
        
        results["end_time"] = datetime.now().isoformat()
        results["duration_seconds"] = (datetime.now() - start_time).total_seconds()
        
        self.logger.info(f"Full sync completed: {results['total_records']} records for {results['successful_codes']} codes")
        return results
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status"""
        summary = self.data_manager.get_data_summary()
        
        return {
            "last_sync": self.last_sync,
            "data_summary": summary,
            "next_incremental_sync": self._get_next_sync_time("incremental"),
            "next_full_sync": self._get_next_sync_time("full"),
            "recommendation": self._get_sync_recommendation()
        }
    
    def _get_next_sync_time(self, sync_type: str) -> Any:
        """Calculate next sync time based on last sync"""
        if sync_type == "incremental":
            last_sync_str = self.last_sync.get("last_incremental_sync")
            if last_sync_str:
                last_sync = datetime.fromisoformat(last_sync_str)
                next_sync = last_sync + timedelta(hours=6)  # Every 6 hours
                return next_sync.isoformat()
        
        elif sync_type == "full":
            last_sync_str = self.last_sync.get("last_full_sync")
            if last_sync_str:
                last_sync = datetime.fromisoformat(last_sync_str)
                next_sync = last_sync + timedelta(days=7)  # Weekly
                return next_sync.isoformat()
        
        return None
    
    def _get_sync_recommendation(self) -> str:
        """Get sync recommendation based on current state"""
        now = datetime.now()
        
        # Check if incremental sync is needed
        last_incremental = self.last_sync.get("last_incremental_sync")
        if last_incremental:
            last_time = datetime.fromisoformat(last_incremental)
            if (now - last_time).total_seconds() > 6 * 3600:  # 6 hours
                return "Incremental sync recommended - data may be stale"
        
        # Check if full sync is needed
        last_full = self.last_sync.get("last_full_sync")
        if last_full:
            last_time = datetime.fromisoformat(last_full)
            if (now - last_time).days > 7:  # 7 days
                return "Full sync recommended - weekly refresh needed"
        
        return "Data appears up to date"
    
    def schedule_daily_sync(self, hour: int = 9, minute: int = 0):
        """Schedule daily sync at specified time (manual implementation)"""
        self.logger.info(f"Daily sync scheduled at {hour:02d}:{minute:02d}")
        self.logger.info("Use cron or systemd for actual scheduling")
    
    def schedule_weekly_sync(self, day: str = "sunday", hour: int = 2, minute: int = 0):
        """Schedule weekly full sync (manual implementation)"""
        self.logger.info(f"Weekly sync scheduled on {day.capitalize()} at {hour:02d}:{minute:02d}")
        self.logger.info("Use cron or systemd for actual scheduling")
    
    def run_scheduler(self):
        """Run the scheduler in a loop (simplified version)"""
        self.logger.info("Starting manual sync scheduler...")
        self.logger.info("For production use, set up cron jobs:")
        self.logger.info("0 9 * * * cd /path/to/get_jisilu && python sync_manager.py --incremental")
        self.logger.info("0 2 * * 0 cd /path/to/get_jisilu && python sync_manager.py --full")
    
    async def retry_failed_codes(self) -> Dict[str, Any]:
        """Retry syncing failed codes"""
        failed_codes = self.last_sync.get("failed_codes", [])
        
        if not failed_codes:
            return {"message": "No failed codes to retry", "retried_codes": []}
        
        self.logger.info(f"Retrying {len(failed_codes)} failed codes...")
        
        results = {
            "retry_type": "failed_codes",
            "retried_codes": [],
            "successful_codes": 0,
            "failed_codes": [],
            "total_records": 0
        }
        
        async with LOFScraper() as scraper:
            for code in failed_codes:
                try:
                    count = await scraper.sync_lof_data(code, days_back=7)
                    if count > 0:
                        results["successful_codes"] += 1
                        results["total_records"] += count
                        results["retried_codes"].append(code)
                    else:
                        results["failed_codes"].append(code)
                        
                except Exception as e:
                    self.logger.error(f"Retry failed for {code}: {e}")
                    results["failed_codes"].append(code)
        
        # Update sync state
        self.last_sync["failed_codes"] = results["failed_codes"]
        self._save_sync_state()
        
        return results

class SyncCLI:
    """Command line interface for sync operations"""
    
    def __init__(self):
        self.sync_manager = SyncManager()
    
    def run(self):
        """Run CLI interface"""
        import argparse
        
        parser = argparse.ArgumentParser(description="Jisilu LOF Data Sync Tool")
        parser.add_argument("--incremental", action="store_true", help="Run incremental sync")
        parser.add_argument("--full", action="store_true", help="Run full sync")
        parser.add_argument("--status", action="store_true", help="Show sync status")
        parser.add_argument("--schedule", action="store_true", help="Run scheduler")
        parser.add_argument("--retry", action="store_true", help="Retry failed codes")
        parser.add_argument("--days", type=int, default=1, help="Days back for incremental sync")
        
        args = parser.parse_args()
        
        if not any([args.incremental, args.full, args.status, args.schedule, args.retry]):
            args.status = True  # Default to status
        
        if args.status:
            status = self.sync_manager.get_sync_status()
            print("\n=== Sync Status ===")
            print(f"Last incremental sync: {status['last_sync'].get('last_incremental_sync', 'Never')}")
            print(f"Last full sync: {status['last_sync'].get('last_full_sync', 'Never')}")
            print(f"Total LOFs with data: {status['data_summary']['total_lofs']}")
            print(f"Total records: {status['data_summary']['total_records']}")
            print(f"Missing LOFs: {len(status['data_summary']['missing_lofs'])}")
            print(f"Recommendation: {status['recommendation']}")
            print(f"Next incremental sync: {status['next_incremental_sync']}")
            print(f"Next full sync: {status['next_full_sync']}")
        
        elif args.incremental:
            asyncio.run(self.sync_manager.incremental_sync(args.days))
        
        elif args.full:
            asyncio.run(self.sync_manager.full_sync(30))
        
        elif args.schedule:
            self.sync_manager.run_scheduler()
        
        elif args.retry:
            asyncio.run(self.sync_manager.retry_failed_codes())

if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Config.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    
    cli = SyncCLI()
    cli.run()