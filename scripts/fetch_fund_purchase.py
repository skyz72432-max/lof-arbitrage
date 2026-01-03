"""
每日只运行一次 AkShare fund_purchase_em()
并缓存到父目录为 CSV 文件

文件名示例：
fund_purchase_em_20251231.csv
"""

import os
import pandas as pd
import akshare as ak
from datetime import datetime
from zoneinfo import ZoneInfo

def today_str() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d")

def get_project_root() -> str:
    """当前脚本所在目录的父目录"""
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)
    return os.path.dirname(current_dir)


def get_today_cache_path(project_root: str) -> str:
    return os.path.join(
        project_root,
        f"fund_purchase_em_{today_str()}.csv"
    )


def cleanup_old_cache(project_root: str):
    """删除历史 fund_purchase_em 缓存"""
    for fname in os.listdir(project_root):
        if fname.startswith("fund_purchase_em_") and fname.endswith(".csv"):
            os.remove(os.path.join(project_root, fname))


def normalize_purchase_status(df: pd.DataFrame) -> pd.DataFrame:
    """
    规范化“申购状态”字段：
    - 仅处理 '限大额'
    - 根据“日累计限定金额”改写为：
        < 10000  → 限购500
        >=10000  → 限购10万
    """
    df = df.copy()

    # 确保金额为数值
    df["日累计限定金额"] = pd.to_numeric(
        df["日累计限定金额"], errors="coerce"
    )

    def _rewrite(row):
        if row["申购状态"] != "限大额":
            return row["申购状态"]

        limit = row["日累计限定金额"]
        if pd.isna(limit):
            return row["申购状态"]

        if limit < 10000:
            return f"限购{int(limit)}"
        else:
            return f"限购{int(limit // 10000)}万"

    df["申购状态"] = df.apply(_rewrite, axis=1)
    return df


def fetch_or_load_fund_purchase() -> pd.DataFrame:
    """
    对外唯一接口：
    - 当天已存在 → 直接读取
    - 否则 → 调用 AkShare 并缓存
    """
    project_root = get_project_root()
    cache_path = get_today_cache_path(project_root)

    if os.path.exists(cache_path):
        print(f"📄 使用当日缓存：{os.path.basename(cache_path)}")
        return pd.read_csv(cache_path, dtype={"基金代码": str})

    print("🌐 今日首次运行，调用 ak.fund_purchase_em()")

    cleanup_old_cache(project_root)

    df = ak.fund_purchase_em().drop(columns=["序号"], errors="ignore")

    # 🔧 关键：规范化申购状态
    df = normalize_purchase_status(df)

    df["fetch_date"] = today_str()

    df.to_csv(cache_path, index=False, encoding="utf-8-sig")
    print(f"✅ 已生成缓存文件：{cache_path}")

    return df


if __name__ == "__main__":
    fetch_or_load_fund_purchase()
