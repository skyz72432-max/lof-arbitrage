#!/bin/bash
echo "🎯 LOF溢价率交易系统"
echo "===================="
echo ""
echo "1. 查看交易信号: python simple_trading_cli.py"
echo "2. 高级分析: python trading_framework.py"
echo "3. 启动Web仪表板: streamlit run premium_dashboard.py"
echo ""
echo "📊 当前数据状态:"
ls data/lof_*.csv | wc -l | xargs echo "   LOF数量:"
python -c "
import pandas as pd
import os
files = [f for f in os.listdir('data') if f.startswith('lof_')]
total = 0
for f in files:
    try:
        df = pd.read_csv('data/'+f)
        total += len(df)
    except:
        pass
print(f'   总记录数: {total}')
"
echo ""
echo "📈 使用说明:"
echo "   - 先运行simple_trading_cli.py查看基础信号"
echo "   - 再使用trading_framework.py获取详细分析"
echo "   - 最后用premium_dashboard.py启动交互式仪表板"
echo ""