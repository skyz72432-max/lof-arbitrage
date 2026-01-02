#!/bin/bash

# LOF每日数据同步脚本
# 每天自动运行，智能追加新数据，永不丢失历史记录

# 设置工作目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 配置
LOG_FILE="$SCRIPT_DIR/logs/daily_sync_$(date +%Y%m%d).log"
PID_FILE="$SCRIPT_DIR/logs/daily_sync.pid"

# 创建日志目录
mkdir -p logs

# 检查是否已在运行
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] 同步已在运行 (PID: $PID)" | tee -a "$LOG_FILE"
        exit 0
    else
        rm -f "$PID_FILE"
    fi
fi

# 记录PID
echo $$ > "$PID_FILE"

# 函数：记录日志
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"
}

# 函数：清理PID
cleanup() {
    rm -f "$PID_FILE"
}

# 注册清理函数
trap cleanup EXIT

log "[START] 开始每日LOF数据同步"

# 检查虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
    log "[OK] 虚拟环境已激活"
else
    log "[WARN] 未找到虚拟环境，使用系统Python"
fi

# 检查必要文件
if [ ! -f "all_LOF.txt" ]; then
    log "[ERROR] all_LOF.txt 不存在"
    exit 1
fi

# 运行数据同步
log "[RUN] 执行数据同步..."
python3 scripts/sync_daily.py 2>> "$LOG_FILE"
EXIT_CODE=$?

# 检查同步结果
if [ $EXIT_CODE -eq 0 ]; then
    log "[SUCCESS] 数据同步完成"
    
    # 显示同步结果
    if [ -f "data/lof_160140.csv" ]; then
        LATEST_DATE=$(tail -1 data/lof_160140.csv | cut -d',' -f2)
        RECORD_COUNT=$(wc -l < data/lof_160140.csv)
        log "[RESULT] 示例LOF(160140) 最新数据: $LATEST_DATE, 总记录: $RECORD_COUNT"
    fi
else
    log "[ERROR] 数据同步失败，退出码: $EXIT_CODE"
    exit $EXIT_CODE
fi

# 可选：数据验证
log "[VERIFY] 验证数据完整性..."
python3 -c "
import sys
sys.path.append('.')
from utils.data_manager import DataManager
manager = DataManager()
summary = manager.get_data_summary()
print(f'总LOF: {summary[\"total_lofs\"]}, 总记录: {summary[\"total_records\"]}')
" 2>> "$LOG_FILE"

log "[COMPLETE] 每日同步完成"

# 清理旧日志（保留最近7天）
find logs/ -name "daily_sync_*.log" -mtime +7 -delete 2>/dev/null || true

echo "✅ 同步完成！详情查看: $LOG_FILE"