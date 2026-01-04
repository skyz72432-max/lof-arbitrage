"""
每日数据同步脚本
核心功能的简洁调用接口
"""
import sys
import os
import argparse

# 添加路径以便导入模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime
from utils.trading_calendar import is_trading_day
from core.data_sync import DataSyncCore
from utils.data_manager import DataManager
from fetch_fund_purchase import fetch_or_load_fund_purchase
from zoneinfo import ZoneInfo

def write_last_update_time():
    """
    在项目根目录写入最近一次成功同步时间（北京时间）
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(project_root, "last_sync_time.txt")

    now_cn = datetime.now(ZoneInfo("Asia/Shanghai"))
    now_str = now_cn.strftime("%Y-%m-%d %H:%M")

    with open(path, "w", encoding="utf-8") as f:
        f.write(now_str)
        
def main():

    # ===== 交易日判断=====
    if not is_trading_day(datetime.now(ZoneInfo("Asia/Shanghai")).date()):
        print("📅 非交易日，跳过同步")
        return

    print("📈 交易日，开始同步数据...")

    fetch_or_load_fund_purchase() # 同步申购赎回信息

    parser = argparse.ArgumentParser(description="LOF每日数据同步")
    parser.add_argument("--init", action="store_true", help="首次初始化数据")
    parser.add_argument("--code", type=str, help="指定单个LOF代码")
    parser.add_argument("--verify", action="store_true", help="验证数据完整性")
    
    args = parser.parse_args()
    
    syncer = DataSyncCore()
    manager = DataManager()
    
    if args.init:
        print("🚀 首次数据初始化...")
        results = syncer.sync_all()
        
        updated = len(results['updated'])
        total = len(results['updated']) + len(results['no_change']) + len(results['failed'])
        
        print(f"✅ 初始化完成: {updated}/{total} 个LOF已更新")
        return
    
    if args.code:
        print(f"🔄 同步单个LOF: {args.code}")
        result = syncer.sync_single_lof(args.code)
        print(f"{result['code']}: {result['status']} - {result['existing']}→{result['total']}条")
        return
    
    if args.verify:
        print("🔍 验证数据完整性...")
        summary = manager.get_data_summary()
        print(f"📊 总LOF: {summary['total_lofs']}, 总记录: {summary['total_records']}")
        
        # 显示最近5个LOF的数据状态
        latest = list(summary['latest_dates'].items())[-5:]
        for code, date in latest:
            print(f"  {code}: {date}")
        return
    
    # 默认：执行增量同步
    print("🔄 执行增量数据同步...")
    results = syncer.sync_all()
    
    updated = len(results['updated'])
    total = len(results['updated']) + len(results['no_change']) + len(results['failed'])
    new_records = sum(r['new'] for r in results['updated'])
    
    print(f"✅ 同步完成: {updated}/{total} 个LOF更新, 新增{new_records}条记录")

    write_last_update_time()
    print("🕒 已记录最后同步时间")

def main_handler(event, context):
    """
    腾讯云 SCF 入口
    """
    try:
        print("🚀腾讯云 SCF 触发执行 sync_daily")
        main()
        return {
            "status": "success",
            "time": datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        print("❌ SCF 执行异常:", e)
        raise
        
if __name__ == "__main__":
    main()
