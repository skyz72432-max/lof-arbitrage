"""
数据管理工具
处理数据的保存、加载、验证和清理
"""
import pandas as pd
import os
import json
from datetime import datetime
from typing import Dict, List, Any

class DataManager:
    """数据管理器"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def save_lof_data(self, code: str, df: pd.DataFrame) -> bool:
        """保存LOF数据"""
        try:
            filename = f"{self.data_dir}/lof_{code}.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            return True
        except Exception as e:
            print(f"❌ 保存 {code} 失败: {e}")
            return False
    
    def load_lof_data(self, code: str) -> pd.DataFrame:
        """加载LOF数据"""
        filename = f"{self.data_dir}/lof_{code}.csv"
        if os.path.exists(filename):
            try:
                df = pd.read_csv(filename)
                df['price_dt'] = pd.to_datetime(df['price_dt'])
                return df
            except Exception as e:
                print(f"❌ 加载 {code} 失败: {e}")
        return pd.DataFrame()
    
    def get_data_summary(self) -> Dict[str, Any]:
        """获取数据汇总"""
        files = [f for f in os.listdir(self.data_dir) if f.startswith('lof_') and f.endswith('.csv')]
        
        total_records = 0
        latest_dates = {}
        missing_lofs = []
        
        for file in files:
            code = file.replace('lof_', '').replace('.csv', '')
            try:
                df = pd.read_csv(f"{self.data_dir}/{file}")
                total_records += len(df)
                if 'price_dt' in df.columns:
                    df['price_dt'] = pd.to_datetime(df['price_dt'])
                    latest_dates[code] = df['price_dt'].max().strftime('%Y-%m-%d')
            except Exception:
                missing_lofs.append(code)
        
        return {
            'total_lofs': len(files),
            'total_records': total_records,
            'latest_dates': latest_dates,
            'missing_lofs': missing_lofs
        }
    
    def validate_data(self, code: str) -> Dict[str, Any]:
        """验证数据完整性"""
        df = self.load_lof_data(code)
        if df.empty:
            return {'valid': False, 'error': '无数据'}
        
        issues = []
        
        # 检查缺失值
        missing_discount = df['discount_rt'].isna().sum()
        if missing_discount > 0:
            issues.append(f"缺失溢价率: {missing_discount}条")
        
        # 检查T日未确认数据
        t_minus = (df['discount_rt'] == "-").sum()
        if t_minus > 0:
            issues.append(f"T日未确认: {t_minus}条")
        
        # 检查日期排序
        if not df['price_dt'].is_monotonic_increasing:
            issues.append("日期未排序")
        
        return {
            'valid': len(issues) == 0,
            'records': len(df),
            'latest_date': df['price_dt'].max().strftime('%Y-%m-%d') if not df.empty else None,
            'issues': issues
        }