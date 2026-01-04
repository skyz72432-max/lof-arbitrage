import os
import subprocess
import sys

def run():
    # 确保在项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    # 运行你的同步脚本
    subprocess.check_call([
        sys.executable,
        "scripts/sync_daily.py"
    ])

    # Git 提交并推送
    subprocess.check_call(["git", "status"])
    subprocess.check_call(["git", "add", "data", "last_sync_time.txt"])
    subprocess.check_call([
        "git", "commit", "-m",
        "auto: daily lof data update"
    ])
    subprocess.check_call(["git", "push"])

def main_handler(event, context):
    run()
    return "OK"
