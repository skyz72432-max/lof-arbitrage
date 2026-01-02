# 每日自动运行配置

## 🕐 方法一：使用crontab (推荐)

### 1. 编辑crontab
```bash
crontab -e
```

### 2. 添加定时任务
```bash
# 每天上午9:30运行数据同步
30 9 * * * /Users/moonshot/cursor/get_jisilu/daily_sync.sh

# 或者每天下午3:30运行 (避开交易时段)
30 15 * * * /Users/moonshot/cursor/get_jisilu/daily_sync.sh

# 每6小时运行一次 (更频繁)
0 6,12,18,0 * * * /Users/moonshot/cursor/get_jisilu/daily_sync.sh
```

### 3. 验证crontab
```bash
crontab -l
```

## 🐳 方法二：使用launchd (macOS)

### 创建plist文件
```bash
# 创建LaunchAgent目录
mkdir -p ~/Library/LaunchAgents

# 创建plist文件
cat > ~/Library/LaunchAgents/com.lof.daily-sync.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.lof.daily-sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/moonshot/cursor/get_jisilu/daily_sync.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/moonshot/cursor/get_jisilu/logs/daily_sync.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/moonshot/cursor/get_jisilu/logs/daily_sync_error.log</string>
</dict>
</plist>
EOF

# 加载并启动
launchctl load ~/Library/LaunchAgents/com.lof.daily-sync.plist
launchctl start com.lof.daily-sync
```

## 📊 监控日志

### 查看今日日志
```bash
tail -f logs/daily_sync_$(date +%Y%m%d).log
```

### 查看所有日志
```bash
ls -la logs/
tail -n 50 logs/daily_sync_$(date +%Y%m%d).log
```

## 🔍 故障排除

### 测试手动运行
```bash
./daily_sync.sh
```

### 检查Python环境
```bash
source venv/bin/activate
python -c "from core.data_sync import DataSyncCore; print('OK')"
```

### 检查文件权限
```bash
ls -la daily_sync.sh
chmod +x daily_sync.sh
```