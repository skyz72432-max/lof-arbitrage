"""
Date handling and data compatibility utilities
Ensures seamless data integration across different time periods
"""
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Optional, Union
import logging

class DateHandler:
    """Handles date-related operations for LOF data"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def standardize_date(date_input: Union[str, datetime, date]) -> date:
        """Convert various date formats to standard date object"""
        if isinstance(date_input, str):
            return pd.to_datetime(date_input).date()
        elif isinstance(date_input, datetime):
            return date_input.date()
        elif isinstance(date_input, date):
            return date_input
        else:
            raise ValueError(f"Invalid date format: {type(date_input)}")
    
    @staticmethod
    def get_trading_days(start_date: date, end_date: date) -> List[date]:
        """Get all trading days between start and end dates"""
        # This is a simplified version - in practice, you'd want to use a trading calendar
        days = []
        current = start_date
        while current <= end_date:
            # Skip weekends
            if current.weekday() < 5:  # Monday = 0, Sunday = 6
                days.append(current)
            current += timedelta(days=1)
        return days
    
    @staticmethod
    def get_last_n_trading_days(n: int, end_date: Optional[date] = None) -> List[date]:
        """Get last n trading days"""
        if end_date is None:
            end_date = date.today()
        
        days = []
        current = end_date
        while len(days) < n:
            if current.weekday() < 5:  # Skip weekends
                days.append(current)
            current -= timedelta(days=1)
        
        return sorted(days)
    
    @staticmethod
    def find_gaps_in_dates(existing_dates: List[date], 
                          start_date: date, 
                          end_date: date) -> List[date]:
        """Find missing trading days in date range"""
        all_trading_days = DateHandler.get_trading_days(start_date, end_date)
        existing_set = set(existing_dates)
        return [d for d in all_trading_days if d not in existing_set]
    
    @staticmethod
    def validate_date_range(start_date: date, end_date: date) -> bool:
        """Validate date range"""
        if start_date > end_date:
            return False
        
        # Check if dates are reasonable (not too far in future/past)
        today = date.today()
        if end_date > today + timedelta(days=1):
            return False
        if start_date < today - timedelta(days=365*5):  # 5 years back
            return False
        
        return True
    
    @staticmethod
    def get_date_range_description(start_date: date, end_date: date) -> str:
        """Get human-readable date range description"""
        days_diff = (end_date - start_date).days
        return f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({days_diff} days)"

class DataCompatibilityManager:
    """Manages data compatibility across different versions and formats"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize dataframe to standard format"""
        if df.empty:
            return df
        
        # Standard column names
        column_mapping = {
            'date': 'date',
            'trade_date': 'date',
            'trading_date': 'date',
            '时间': 'date',
            '代码': 'code',
            '基金代码': 'code',
            'fund_code': 'code',
            '净值': 'nav',
            '单位净值': 'nav',
            'fund_nav': 'nav',
            '价格': 'price',
            '市场价格': 'price',
            'market_price': 'price',
            '溢价率': 'premium',
            'discount_rt': 'premium',
            '成交量': 'volume',
            'trade_volume': 'volume',
            '成交额': 'turnover',
            'trade_amount': 'turnover',
        }
        
        # Rename columns
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        # Ensure required columns exist
        required_columns = ['date', 'code']
        for col in required_columns:
            if col not in df.columns:
                self.logger.warning(f"Missing required column: {col}")
        
        # Standardize date format
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.date
        
        # Ensure numeric columns are properly typed
        numeric_columns = ['nav', 'price', 'premium', 'volume', 'turnover']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    def merge_dataframes(self, old_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
        """Merge old and new dataframes with conflict resolution"""
        if old_df.empty:
            return new_df
        
        if new_df.empty:
            return old_df
        
        # Normalize both dataframes
        old_df = self.normalize_dataframe(old_df)
        new_df = self.normalize_dataframe(new_df)
        
        # Combine and remove duplicates
        combined = pd.concat([old_df, new_df])
        
        # Remove duplicates based on date and code, keeping latest
        combined = combined.drop_duplicates(
            subset=['date', 'code'], 
            keep='last'
        ).sort_values('date')
        
        return combined
    
    def detect_data_issues(self, df: pd.DataFrame) -> List[str]:
        """Detect potential data quality issues"""
        issues = []
        
        if df.empty:
            return ["Empty dataframe"]
        
        # Check for missing values
        missing_cols = df.columns[df.isnull().any()].tolist()
        if missing_cols:
            issues.append(f"Missing values in: {missing_cols}")
        
        # Check date range
        if 'date' in df.columns:
            dates = pd.to_datetime(df['date'])
            min_date = dates.min()
            max_date = dates.max()
            
            if (max_date - min_date).days > 365 * 2:
                issues.append(f"Unusually large date range: {(max_date - min_date).days} days")
        
        # Check for outliers in numerical columns
        numeric_cols = ['nav', 'price', 'premium']
        for col in numeric_cols:
            if col in df.columns:
                col_series = pd.to_numeric(df[col], errors='coerce')
                col_data = col_series.dropna()
                if len(col_data) > 0:
                    q1 = col_data.quantile(0.25)
                    q3 = col_data.quantile(0.75)
                    iqr = q3 - q1
                    mask = (col_data < q1 - 3*iqr) | (col_data > q3 + 3*iqr)
                    outliers = col_data[mask]
                    if len(outliers) > 0:
                        issues.append(f"Potential outliers in {col}: {len(outliers)} values")
        
        return issues
    
    def create_backup_name(self, lof_code: str, timestamp: Optional[datetime] = None) -> str:
        """Create standardized backup filename"""
        if timestamp is None:
            timestamp = datetime.now()
        
        return f"lof_{lof_code}_{timestamp.strftime('%Y%m%d_%H%M%S')}.csv"
    
    def validate_data_integrity(self, old_df: pd.DataFrame, new_df: pd.DataFrame) -> bool:
        """Validate data integrity after merge"""
        merged = self.merge_dataframes(old_df, new_df)
        
        # Check for duplicate dates
        if 'date' in merged.columns and 'code' in merged.columns:
            duplicates = merged.duplicated(subset=['date', 'code'])
            if duplicates.any():
                self.logger.error("Duplicate dates found after merge")
                return False
        
        # Check for data consistency
        issues = self.detect_data_issues(merged)
        if issues:
            self.logger.warning(f"Data integrity issues: {issues}")
        
        return True