import os
import subprocess
import sys

# ===== 请填你自己的信息 =====
GITHUB_TOKEN = "ghp_"
GITHUB_USER = "skyz72432-max"
GITHUB_EMAIL = "skyz72432@gmail.com"
REPO_URL = "https://github.com/skyz72432-max/lof-arbitrage.git"

def run():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    print("🚀 Start lof-arbitrage daily sync")

    # 1️⃣ 配置 git 身份
    subprocess.check_call(["git", "config", "--global", "user.name", GITHUB_USER])
    subprocess.check_call(["git", "config", "--global", "user.email", GITHUB_EMAIL])

    # 2️⃣ 设置带 token 的 origin
    authed_repo = f"https://{GITHUB_TOKEN}@github.com/skyz72432-max/lof-arbitrage.git"
    subprocess.check_call(["git", "remote", "set-url", "origin", authed_repo])

    # 3️⃣ 拉取最新代码（避免冲突）
    subprocess.check_call(["git", "pull", "origin", "main"])

    # 4️⃣ 运行你的同步脚本
    subprocess.check_call([sys.executable, "scripts/sync_daily.py"])

    # 5️⃣ 提交并推送
    subprocess.check_call(["git", "add", "data", "last_sync_time.txt"])

    try:
        subprocess.check_call(
            ["git", "commit", "-m", "auto: daily lof data update"]
        )
    except subprocess.CalledProcessError:
        print("ℹ️ No changes to commit")

    subprocess.check_call(["git", "push", "origin", "main"])
    print("✅ Done")

def main_handler(event, context):
    run()
    return "OK"
