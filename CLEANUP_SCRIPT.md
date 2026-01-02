# 项目清理脚本

## 🧹 需要清理的旧文件

### 保留的核心文件
- ✅ `core/` - 核心模块
- ✅ `utils/` - 工具模块  
- ✅ `scripts/` - 用户脚本
- ✅ `data/` - 数据目录
- ✅ `all_LOF.txt` - LOF代码列表
- ✅ `PROJECT_STRUCTURE.md` - 项目文档
- ✅ `quick_start.py` - 快速启动

### 清理旧文件
以下文件将被移动到 `legacy/` 目录作为备份：

1. **数据同步相关**:
   - sync_all_data.py → 功能已合并到core/data_sync.py
   - sync_manager.py → 功能已合并
   - incremental_update.py → 功能已合并
   - t1_update.py → 功能已合并
   - fix_t1_data.py → 功能已合并
   - smart_append.py → 功能已合并

2. **仪表板相关**:
   - premium_dashboard.py → 功能已合并到scripts/dashboard.py
   - premium_dashboard_fixed.py → 功能已合并
   - debug_dashboard.py → 调试版本

3. **测试文件**:
   - check_latest.py → 功能已合并
   - minimal_test.py → 测试功能
   - test_simple.py → 测试功能

4. **其他**:
   - batch_sync.py → 功能已合并
   - date_handler.py → 功能已合并
   - get_jisilu_LOF_data.py → 空文件
   - scraper.py → 功能已合并
   - simple_trading_cli.py → CLI功能已合并
   - config.py → 配置已简化

## 🎯 清理后结构

```
get_jisilu/
├── core/
│   ├── data_sync.py          # 智能数据同步
│   └── __init__.py
├── utils/
│   ├── data_manager.py       # 数据管理
│   └── __init__.py
├── scripts/
│   ├── sync_daily.py         # 每日同步
│   ├── dashboard.py          # Web仪表板
│   └── __init__.py
├── data/                     # 数据存储
├── legacy/                   # 旧文件备份
├── all_LOF.txt              # LOF代码列表
├── quick_start.py           # 快速启动
└── PROJECT_STRUCTURE.md     # 项目文档
```

## 🚀 清理命令

```bash
# 创建legacy目录
mkdir -p legacy

# 移动旧文件到legacy
mv *.py legacy/ 2>/dev/null || true

# 恢复核心文件
cp core/*.py core/
cp utils/*.py utils/
cp scripts/*.py scripts/
cp quick_start.py .
cp all_LOF.txt .
cp PROJECT_STRUCTURE.md .
```