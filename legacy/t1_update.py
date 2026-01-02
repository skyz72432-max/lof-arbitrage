
"""
T+1 数据更新脚本
专门处理A股日内交易时段溢价率延迟问题
"""
import requests
import pandas as pd
import os
import json
import time
from datetime import datetime, timedelta

def load_existing_data(code):
    """Load existing data for a code"""
    filename = f"data/lof_{code}.csv"
    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename)
            df['price_dt'] = pd.to_datetime(df['price_dt'])
            return df
        except Exception as e:
            print(f"Error loading {code}: {e}")
    return pd.DataFrame()

def fetch_t1_data(code):
    """Fetch T+1 confirmed data (跳过T日未确认数据)"""
    url = f"https://www.jisilu.cn/data/lof/hist_list/{code}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    params = {
        '___jsl': 'LST___t',
        'rp': '50',
        'page': '1'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            rows = data.get('rows', [])
            
            if rows:
                records = []
                t_minus_records = []  # T-1日及以前的数据
                
                for row in rows:
                    cell = row['cell']
                    record = dict(cell)
                    record['code'] = code
                    
                    # 跳过T日未确认数据（discount_rt = "-"）
                    if record.get('discount_rt') == "-":
                        continue
                    
                    # 只保留有确定溢价率的数据
                    try:
                        discount_rt = float(record.get('discount_rt', 0))
                        records.append(record)
                    except (ValueError, TypeError):
                        continue
                
                if records:
                    new_df = pd.DataFrame(records)
                    new_df['price_dt'] = pd.to_datetime(new_df['price_dt'])
                    new_df['discount_rt'] = pd.to_numeric(new_df['discount_rt'], errors='coerce')
                    
                    return new_df
        
        return pd.DataFrame()
        
    except Exception as e:
        print(f"❌ Error fetching {code}: {e}")
        return pd.DataFrame()

def update_t1_confirmed_data():
    """更新T+1确认数据"""
    print("🔄 开始T+1数据更新（跳过未确认数据）...")
    
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
            lof_codes = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("❌ all_LOF.txt not found")
        return
    
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"📅 当前日期: {today}")
    print(f"📅 目标更新日期: {yesterday} 及以前（T+1确认数据）")
    
    total_new_records = 0
    updated_codes = 0
    skipped_codes = 0
    
    for i, code in enumerate(lof_codes, 1):
        print(f"[{i:2d}/{len(lof_codes)}] 处理 {code}...")
        
        # 加载现有数据
        existing_df = load_existing_data(code)
        
        # 获取T+1确认数据
        new_df = fetch_t1_data(code)
        
        if new_df.empty:
            print(f"  ⚠️ 无可用T+1确认数据")
            skipped_codes += 1
            continue
        
        # 合并数据，避免重复
        if not existing_df.empty:
            # 移除重复日期
            existing_dates = set(existing_df['price_dt'])
            new_df = new_df[~new_df['price_dt'].isin(existing_dates)]
            
            if not new_df.empty:
                combined_df = pd.concat([existing_df, new_df])
                combined_df = combined_df.sort_values('price_dt').reset_index(drop=True)
                
                # 保存更新后的数据
                combined_df.to_csv(f"data/lof_{code}.csv", index=False, encoding='utf-8-sig')
                
                latest_date = combined_df['price_dt'].max().strftime('%Y-%m-%d')
                print(f"  ✅ 新增 {len(new_df)} 条T+1确认数据，最新日期: {latest_date}")
                total_new_records += len(new_df)
                updated_codes += 1
            else:
                print(f"  ℹ️ 无新T+1确认数据")
        else:
            # 新建文件
            new_df = new_df.sort_values('price_dt').reset_index(drop=True)
            new_df.to_csv(f"data/lof_{code}.csv", index=False, encoding='utf-8-sig')
            
            latest_date = new_df['price_dt'].max().strftime('%Y-%m-%d')
            print(f"  🆕 创建文件，{len(new_df)} 条T+1确认数据，最新日期: {latest_date}")
            total_new_records += len(new_df)
            updated_codes += 1
        
        time.sleep(0.5)
    
    print("\n" + "="*50)
    print("📊 T+1数据更新完成")
    print(f"✅ 更新代码数: {updated_codes}")
    print(f"📈 新增确认记录: {total_new_records}")
    print(f"⏭️  跳过代码数: {skipped_codes}")
    
    # 显示最新数据状态
    latest_dates = []
    for code in lof_codes:
        if os.path.exists(f"data/lof_{code}.csv"):
            try:
                df = pd.read_csv(f"data/lof_{code}.csv")
                df['price_dt'] = pd.to_datetime(df['price_dt'])
                latest_dates.append(df['price_dt'].max().strftime('%Y-%m-%d'))
            except:
                pass
    
    if latest_dates:
        print(f"\n📅 最新数据日期分布:")
        date_counts = {}
        for date in latest_dates:
            date_counts[date] = date_counts.get(date, 0) + 1
        
        for date, count in sorted(date_counts.items(), reverse=True):
            print(f"  {date}: {count} 个LOF")

if __name__ == "__main__":
    update_t1_confirmed_data()