# LOF溢价率交易系统 - 项目结构

## 📁 目录结构

```
get_jisilu/
├── 📂 core/                    # 核心模块
│   ├── __init__.py
│   ├── data_sync.py           # 智能数据同步
│   ├── premium_analyzer.py    # 溢价率分析器
│   └── trading_signals.py     # 交易信号生成
├── 📂 utils/                   # 工具模块
│   ├── __init__.py
│   ├── data_manager.py        # 数据管理工具
│   ├── api_client.py          # API客户端
│   └── file_handler.py        # 文件处理工具
├── 📂 tests/                   # 测试模块
│   ├── __init__.py
│   ├── test_data_sync.py      # 数据同步测试
│   ├── test_trading.py        # 交易逻辑测试
│   └── test_utils.py          # 工具函数测试
├── 📂 data/                    # 数据目录
│   ├── lof_*.csv             # LOF历史数据
│   └── sync_state.json       # 同步状态
├── 📂 configs/                 # 配置文件
│   └── config.py              # 全局配置
├── 📂 scripts/                 # 脚本工具
│   ├── quick_start.sh         # 快速启动
│   ├── sync_daily.py          # 每日同步
│   └── dashboard.py           # Web仪表板
└── 📂 docs/                    # 文档
    ├── README.md
    └── API.md
```

## 🎯 核心文件说明

### 核心模块 (core/)
- **data_sync.py**: 智能增量数据同步，处理API滚动窗口
- **premium_analyzer.py**: 溢价率统计分析和信号生成
- **trading_signals.py**: 基于历史数据的交易信号逻辑

### 工具模块 (utils/)
- **data_manager.py**: 数据加载、保存、验证
- **api_client.py**: 集思录API交互封装
- **file_handler.py**: 文件IO和路径管理

### 用户接口
- **scripts/sync_daily.py**: 每日数据同步脚本
- **scripts/dashboard.py**: Streamlit Web仪表板
- **scripts/quick_start.sh**: 快速启动和检查

### 测试文件
- **tests/test_data_sync.py**: 数据同步逻辑测试
- **tests/test_trading.py**: 交易信号准确性测试

## 🚀 使用流程

1. **首次运行**:
   ```bash
   python scripts/sync_daily.py --init
   python scripts/dashboard.py
   ```

2. **日常更新**:
   ```bash
   python scripts/sync_daily.py
   ```

3. **测试验证**:
   ```bash
   python -m pytest tests/
   ```

## 📊 数据结构

### LOF数据文件格式
```csv
fund_id,price_dt,price,net_value_dt,net_value,discount_rt,amount,...
160140,2025-07-23,1.284,2025-07-22,1.2963,-0.89,11077,...
```

### 同步状态
```json
{
  "last_full_sync": "2025-07-23T10:00:00",
  "last_incremental_sync": "2025-07-23T10:00:00",
  "total_records": 1872,
  "codes_updated": 36
}
```