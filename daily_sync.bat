@echo off
chcp 65001
echo 开始执行集思录数据同步...
cd /d "D:\Desktop\华泰工作\策略设计\中心策略\LOF套利\get_jisilu-main\scripts"
python sync_daily.py
echo 数据同步完成
pause