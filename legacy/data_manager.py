"""
Data management module for LOF historical data
Handles CSV storage, incremental updates, and data compatibility
"""
import pandas as pd
import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Any
from pathlib import Path
import hashlib
import json

from config import Config

class DataManager:
    """Manages LOF data storage and retrieval with incremental updates"""
    
    def __init__(self):
        self.data_dir = Path(Config.DATA_DIR)
        self.logger = logging.getLogger(__name__)
        Config.create_data_dir()
        
    def get_csv_path(self, lof_code: str) -> Path:
        """Get CSV file path for a LOF code"""
        return self.data_dir / f"lof_{lof_code}.csv"
    
    def get_metadata_path(self, lof_code: str) -> Path:
        """Get metadata file path for a LOF code"""
        return self.data_dir / f"lof_{lof_code}_meta.json"
    
    def load_existing_data(self, lof_code: str) -> pd.DataFrame:
        """Load existing data for a LOF code"""
        csv_path = self.get_csv_path(lof_code)
        
        if not csv_path.exists():
            return pd.DataFrame()
            
        try:
            df = pd.read_csv(csv_path, encoding=Config.CSV_ENCODING)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            return df
        except Exception as e:
            self.logger.error(f"Error loading data for {lof_code}: {e}")
            return pd.DataFrame()
    
    def save_data(self, lof_code: str, new_data: pd.DataFrame) -> bool:
        """Save new data with incremental updates"""
        if new_data.empty:
            return True
            
        try:
            # Ensure date column is datetime
            if 'date' in new_data.columns:
                new_data['date'] = pd.to_datetime(new_data['date'])
            
            # Load existing data
            existing_data = self.load_existing_data(lof_code)
            
            # Merge data (avoid duplicates)
            if not existing_data.empty:
                combined_data = pd.concat([existing_data, new_data])
                combined_data = combined_data.drop_duplicates(subset=['date'], keep='last')
                combined_data = combined_data.sort_values('date')
            else:
                combined_data = new_data.sort_values('date')
            
            # Save to CSV
            csv_path = self.get_csv_path(lof_code)
            combined_data.to_csv(csv_path, index=False, encoding=Config.CSV_ENCODING)
            
            # Update metadata
            self._update_metadata(lof_code, combined_data)
            
            self.logger.info(f"Saved {len(new_data)} new records for {lof_code}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving data for {lof_code}: {e}")
            return False
    
    def _update_metadata(self, lof_code: str, data: pd.DataFrame):
        """Update metadata file with data statistics"""
        if data.empty:
            return
            
        metadata = {
            "code": lof_code,
            "last_updated": datetime.now().isoformat(),
            "total_records": len(data),
            "date_range": {
                "start": data['date'].min().isoformat() if 'date' in data.columns else None,
                "end": data['date'].max().isoformat() if 'date' in data.columns else None
            },
            "data_hash": hashlib.md5(str(data.to_dict()).encode()).hexdigest()[:8]
        }
        
        with open(self.get_metadata_path(lof_code), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def get_missing_dates(self, lof_code: str, days_back: int = 15) -> List[date]:
        """Get missing dates that need to be fetched"""
        existing_data = self.load_existing_data(lof_code)
        
        if existing_data.empty or 'date' not in existing_data.columns:
            # Return last 15 days if no data
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days_back)
            return [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
        
        # Find gaps in data
        existing_dates = set(existing_data['date'].dt.date.unique())
        end_date = datetime.now().date()
        start_date = max(
            min(existing_dates) - timedelta(days=1),
            end_date - timedelta(days=days_back)
        )
        
        all_dates = [start_date + timedelta(days=i) 
                    for i in range((end_date - start_date).days + 1)]
        
        missing_dates = [date for date in all_dates if date not in existing_dates]
        return missing_dates
    
    def cleanup_old_backups(self, days_to_keep: int = 30):
        """Clean up old backup files"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for file_path in self.data_dir.glob("lof_*.csv"):
            if file_path.stat().st_mtime < cutoff_date.timestamp():
                backup_path = file_path.with_suffix('.csv.bak')
                file_path.rename(backup_path)
                self.logger.info(f"Backed up old file: {file_path.name}")
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Get summary of all stored data"""
        summary = {
            "total_lofs": 0,
            "total_records": 0,
            "lofs_with_data": [],
            "missing_lofs": []
        }
        
        lof_codes = Config.get_lof_codes()
        for code in lof_codes:
            csv_path = self.get_csv_path(code)
            if csv_path.exists():
                try:
                    df = pd.read_csv(csv_path)
                    summary["total_lofs"] += 1
                    summary["total_records"] += len(df)
                    summary["lofs_with_data"].append({
                        "code": code,
                        "records": len(df)
                    })
                except Exception as e:
                    self.logger.error(f"Error reading {code}: {e}")
            else:
                summary["missing_lofs"].append(code)
        
        return summary