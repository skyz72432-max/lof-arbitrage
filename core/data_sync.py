"""
智能增量数据同步核心模块
处理集思录API滚动窗口50条限制的数据同步
"""
import requests
import pandas as pd
import os
import json
import time
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Any

class DataSyncCore:
    """核心数据同步器"""
    
    def __init__(self):
        current_file = os.path.abspath(__file__)
        core_dir = os.path.dirname(current_file)
        project_root = os.path.dirname(core_dir)   # get_jisilu-main

        self.data_dir = os.path.join(project_root, "data")
        #if os.path.exists(self.data_dir):
        #    shutil.rmtree(self.data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
        }
        self.params = {
            '___jsl': 'LST___t',
            'rp': '50',
            'page': '1'
        }
    
    def load_lof_codes(self) -> List[str]:
        """读取LOF代码列表"""
        try:
            # 获取当前脚本的绝对路径
            current_script_path = os.path.abspath(__file__)
            # 获取当前脚本所在目录
            current_script_dir = os.path.dirname(current_script_path)
            # 获取父目录
            parent_dir = os.path.dirname(current_script_dir)
            # 构建all_LOF.txt在父目录中的路径
            lof_file_path = os.path.join(parent_dir, 'all_LOF.txt')

            with open(lof_file_path, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            raise FileNotFoundError("all_LOF.txt not found")
    
    def load_existing_data(self, code: str) -> pd.DataFrame:
        """加载现有数据"""
        filename = f"{self.data_dir}/lof_{code}.csv"
        if os.path.exists(filename):
            try:
                df = pd.read_csv(filename, dtype=str)
                df['price_dt'] = pd.to_datetime(df['price_dt'])
                numeric_cols = ['price', 'discount_rt', 'net_value']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                return df
            except Exception as e:
                print(f"❌ 加载 {code} 失败: {e}")
        return pd.DataFrame()
    
    def fetch_api_data(self, code: str) -> pd.DataFrame:
        """获取API数据"""
        url = f"https://www.jisilu.cn/data/lof/hist_list/{code}"
        
        try:
            response = requests.get(url, params=self.params, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                rows = data.get('rows', [])
                
                if rows:
                    records = []
                    for row in rows:
                        cell = row['cell']
                        record = dict(cell)
                        record['code'] = code
                        
                        records.append(record)
                    
                    df = pd.DataFrame(records)
                    df['price_dt'] = pd.to_datetime(df['price_dt'])
                    
                    # 数据类型转换
                    numeric_cols = ['price', 'discount_rt', 'net_value']
                    for col in numeric_cols:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    # 保留所有数据（包括T日未确认的），用于增量更新
                    return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ API获取失败 {code}: {e}")
            return pd.DataFrame()
    
    def sync_single_lof(self, code: str) -> Dict[str, Any]:
        """同步单个LOF，包括更新之前为"-"的溢价率数据"""
        existing_df = self.load_existing_data(code)
        api_df = self.fetch_api_data(code)
        
        if api_df.empty:
            return {
                'code': code,
                'status': 'failed',
                'existing': len(existing_df),
                'new': 0,
                'updated': 0,
                'total': len(existing_df)
            }
        
        if existing_df.empty:
            # 全新数据
            combined_df = api_df
            new_records = len(api_df)
            updated_records = 0
        else:
            # 智能合并：新增记录 + 更新已有记录
            api_df['price_dt_str'] = api_df['price_dt'].dt.strftime('%Y-%m-%d')
            existing_df['price_dt_str'] = existing_df['price_dt'].dt.strftime('%Y-%m-%d')
            
            # 找出需要更新的记录（日期已存在但discount_rt为NaN或-）
            merged_df = existing_df.copy()
            updated_records = 0
            
            for _, api_row in api_df.iterrows():
                api_date = api_row['price_dt_str']
                mask = merged_df['price_dt_str'] == api_date
                
                if mask.any():
                    # 已存在记录，检查是否需要更新
                    existing_discount = merged_df.loc[mask, 'discount_rt'].iloc[0]
                    if pd.isna(existing_discount) or str(existing_discount) == "-" or abs(existing_discount) < 0.01:
                        # 更新这条记录
                        for col in api_row.index:
                            if col != 'price_dt_str':
                                merged_df.loc[mask, col] = api_row[col]
                        updated_records += 1
                else:
                    # 新增记录
                    new_row = api_row.to_dict()
                    new_row.pop('price_dt_str', None)
                    merged_df = pd.concat([merged_df, pd.DataFrame([new_row])], ignore_index=True)
            
            combined_df = merged_df.drop(columns=['price_dt_str'], errors='ignore')
            new_records = len(combined_df) - len(existing_df)
        
        if new_records > 0 or updated_records > 0:
            combined_df = combined_df.sort_values('price_dt').reset_index(drop=True)
            
            filename = f"{self.data_dir}/lof_{code}.csv"
            combined_df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            return {
                'code': code,
                'status': 'updated',
                'existing': len(existing_df),
                'new': new_records,
                'updated': updated_records,
                'total': len(combined_df),
                'latest': combined_df['price_dt'].max().strftime('%Y-%m-%d')
            }
        
        return {
            'code': code,
            'status': 'no_change',
            'existing': len(existing_df),
            'new': 0,
            'updated': 0,
            'total': len(existing_df)
        }
    
    def sync_all(self) -> Dict[str, List[Dict]]:
        """同步所有LOF"""
        codes = self.load_lof_codes()
        results = {'updated': [], 'no_change': [], 'failed': []}
        
        for code in codes:
            try:
                result = self.sync_single_lof(code)
                if result['status'] == 'updated':
                    results['updated'].append(result)
                elif result['status'] == 'no_change':
                    results['no_change'].append(result)
                else:
                    results['failed'].append(result)
            except Exception as e:
                results['failed'].append({'code': code, 'error': str(e)})
        
        return results