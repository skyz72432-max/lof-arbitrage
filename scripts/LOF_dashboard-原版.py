"""
LOF 溢价套利胜率评分仪表板（完整版）
在保留原交易导向仪表板功能的基础上，加入胜率评分模型
"""
import os
import warnings
from datetime import datetime, timedelta, time

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

warnings.filterwarnings("ignore")

# ======================================================
# 工具函数
# ======================================================

def is_monotonic_increasing(arr):
    return all(arr[i] < arr[i + 1] for i in range(len(arr) - 1))

def is_monotonic_decreasing(arr):
    return all(arr[i] > arr[i + 1] for i in range(len(arr) - 1))

def is_pre_order_time():
    now = datetime.now().time()
    return time(9, 30) <= now <= time(14, 30)

def score_to_signal(score):
    if score >= 80:
        return "极高胜率"
    elif score >= 65:
        return "高胜率"
    elif score >= 50:
        return "中等胜率"
    elif score >= 35:
        return "低胜率"
    else:
        return "放弃"

# ======================================================
# 分析器
# ======================================================

class LOFArbitrageAnalyzer:

    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.lof_data = {}
        self.load_all_data()

    def load_all_data(self):
        """加载所有LOF数据"""
        csv_files = [f for f in os.listdir(self.data_dir) 
                    if f.startswith('lof_') and f.endswith('.csv')]
        
        for file in csv_files:
            code = file.replace('lof_', '').replace('.csv', '')
            file_path = os.path.join(self.data_dir, file)
            try:
                df = pd.read_csv(file_path)
                df['price_dt'] = pd.to_datetime(df['price_dt'])
                df['discount_rt'] = pd.to_numeric(df['discount_rt'], errors='coerce')
                df["price_pct"] = df["price"].pct_change() * 100
                if pd.isna(df['discount_rt'].iloc[-1]):
                    df['discount_rt'].iloc[-1] = round((df['price'].iloc[-1]/df['est_val'].iloc[-1]-1)*100,2)
                self.lof_data[code] = df.sort_values('price_dt')
            except Exception as e:
                print(f"加载 {code} 数据失败: {e}")

    def premium_stats(self, df, days):
        cutoff = datetime.now() - timedelta(days=days)
        d = df[df["price_dt"] >= cutoff]
        return {
            "mean": d["discount_rt"].mean(),
            "std": d["discount_rt"].std()
        }

    def score_one_lof(self, code):
        df = self.lof_data[code].copy()
        recent = df.tail(30)

        current = recent.iloc[-1]
        cur_premium = current["discount_rt"]
        cur_volume = current["volume"]
        cur_pct = current["price_pct"]

        stats7 = self.premium_stats(df, 7)
        stats14 = self.premium_stats(df, 14)
        stats21 = self.premium_stats(df, 21)

        # ================= 溢价率维度 =================
        premium_score = 0
        plus, minus = [], []
        
        if cur_premium < 0:
            minus.append("当前为折价，不适用溢价套利策略")
        elif pd.notna(cur_premium):
            premium_score += 60 if cur_premium >= 5 else int(cur_premium * 10)

            if cur_premium > stats7["mean"] + stats7["std"]:
                premium_score += 5
                plus.append(f"当前溢价率显著高于7日均值")

            if cur_premium - stats14["mean"] > stats14["std"] * 1.5:
                premium_score += 5
                plus.append("当前溢价率显著高于14日均值")

            if cur_premium - stats21["mean"] > stats21["std"] * 2:
                premium_score += 5
                plus.append("当前溢价率显著高于21日均值")

            if 10 <= cur_premium < 20:
                premium_score += 10
                plus.append("当前溢价率处于10–20%，套利空间充足")
            elif cur_premium >= 20:
                premium_score += 20
                plus.append("当前溢价率≥20%，属极端溢价空间")

            last3 = recent["discount_rt"].tail(3).values

            if (last3 >= 5).all() and is_monotonic_increasing(last3):
                premium_score += 15
                plus.append(
                    "近3日溢价率均≥5%且逐日上升，套利空间稳步扩张"
                )
            elif (last3 >= 5).all():
                premium_score += 10
                plus.append(
                    "近3日溢价率均≥5%，套利空间稳定存在"
                )
            elif (last3 >= 3).all():
                premium_score += 5
                plus.append(
                    "近3日溢价率维持在3%–5%，具备溢价套利基础"
                )

            if is_monotonic_decreasing(last3):
                premium_score -= 10
                minus.append(
                    "溢价率近3日逐日下降，短期套利窗口收敛"
                )
            elif recent["discount_rt"].iloc[-1] < recent["discount_rt"].iloc[-2]:
                premium_score -= 5
                minus.append(
                    "溢价率较昨日有所下滑，但尚未连续回落，短期套利动能减弱"
                )

            if cur_pct <= -9.5:
                premium_score -= 20
                minus.append(
                    "场内价格接近跌停，情绪化抛压显著，套利风险极高"
                )
            elif cur_pct <= -8:
                premium_score -= 15
                minus.append(
                    "场内价格跌超8%，恐慌性下跌阶段，溢价稳定性存疑"
                )
            elif cur_pct <= -5:
                premium_score -= 10
                minus.append(
                    "场内价格跌超5%，短期情绪偏弱，需防止溢价快速回落"
                )
        else:
            minus.append("当日溢价率缺失，无法进一步分析")

        premium_score = max(0, 0.6*min(100, premium_score))

        # ================= 流动性维度 =================
        liquidity_score = 0

        # ---------- 基础流动性门槛 ----------
        if is_pre_order_time():
            liquidity_window = recent.iloc[-4:-1]   # 不含今日
        else:
            liquidity_window = recent.iloc[-3:]     # 含今日

        if len(liquidity_window) == 3 and \
        (liquidity_window["volume"] >= 1000).all() and \
        (liquidity_window["amount"] >= 1000).all():

            liquidity_score += 60
            plus.append("近3日成交额均≥1000万元，场内份额均≥1000万份，具备套利执行基础")

            # ---------- 加分条件：份额稳定性 ----------
            amount_incr_today = current["amount_incr"]
            last3_amount_incr = recent["amount_incr"].tail(3).values

            if abs(amount_incr_today) < 1:
                liquidity_score += 5
                plus.append(
                    "当日场内份额增速绝对值<1%，套利盘未明显集中进出"
                )

            if (np.abs(last3_amount_incr) < 1).all():
                liquidity_score += 15
                plus.append(
                    "近3日份额增速绝对值均<1%，份额结构高度稳定"
                )

            # ---------- 扣分条件：套利机会快速消失 ----------
            last3_premium = recent["discount_rt"].tail(3).values

            if amount_incr_today > 3 and is_monotonic_decreasing(last3_premium):
                liquidity_score -= 20
                minus.append(
                    "当日场内份额增速>3% 且溢价率连续回落，套利盘加速撤离"
                )

        else:
            minus.append(
                "近3日成交额或场内份额不足，套利执行存在流动性风险"
            )

        liquidity_score = max(0, 0.5*min(80, liquidity_score))

        total_score = int(premium_score + liquidity_score)

        return {
            "code": code,
            "score": total_score,
            "signal": score_to_signal(total_score),
            "current_premium": cur_premium,
            "current_volume": cur_volume,
            "price_pct": cur_pct,
            "key_metrics": {
                "premium_3d": recent["discount_rt"].tail(3).mean(),
                "premium_7d": recent["discount_rt"].tail(7).mean()
            },
            "reasons": {
                "plus": plus,
                "minus": minus
            }
        }

    def get_all_signals(self):
        signals = []
        for code in self.lof_data:
            signals.append(self.score_one_lof(code))
        return sorted(signals, key=lambda x: x["score"], reverse=True)

def signal_font_color(val):
    """
    仅修改字体颜色，不修改背景
    胜率越高，红色越深；放弃为深灰
    """
    color_map = {
        "极高胜率": "color: #8B0000;",   # 深红
        "高胜率":   "color: #CD2626;",   # 红
        "中等胜率": "color: #FF4500;",   # 橙红
        "低胜率":   "color: #A0522D;",   # 棕色
        "放弃":     "color: #4F4F4F;"    # 深灰
    }
    return color_map.get(val, "")

# ======================================================
# Streamlit 页面
# ======================================================

def main():
    st_autorefresh(interval= 5 * 60 * 1000, key="auto_refresh")
    st.cache_data.clear()
    st.set_page_config(
        page_title="LOF溢价套利-每日机会",
        page_icon="📈",
        layout="wide"
    )

    st.title("📈 LOF溢价套利-每日机会")
    st.markdown("### 基于历史数据的溢价套利信号")

    analyzer = LOFArbitrageAnalyzer()
    all_signals = analyzer.get_all_signals()

    # ========= 新：默认展示逻辑 =========
    mid_and_up = [s for s in all_signals if s["score"] >= 50]

    if len(mid_and_up) > 5:
        default_signals = sorted(mid_and_up, key=lambda x: x["score"], reverse=True)
    else:
        default_signals = all_signals[:5]

    default_codes = [s["code"] for s in default_signals]

    # ================= 侧边栏 =================
    with st.sidebar:
        st.header("🔧 设置")
        all_codes = list(analyzer.lof_data.keys())

        selected_codes = st.multiselect(
            "选择LOF代码",
            options=all_codes,
            default=[c for c in default_codes if c in all_codes]
        )

    # ================= 今日推荐 =================
    st.header("🔥 今日推荐（综合评分 TOP）")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        top_df = pd.DataFrame([{
            "代码": s["code"],
            "当前溢价(%)": f"{s['current_premium']:.2f}",
            "成交额(万元)": int(s["current_volume"]),
            "交易信号": s["signal"],
            "综合得分": s["score"]
        } for s in default_signals])

        styled_top_df = (
            top_df
            .style
            .set_properties(**{"text-align": "center"})
            .applymap(signal_font_color, subset=["交易信号"])
        )

        st.dataframe(styled_top_df, use_container_width=True)

    with col_right:
        st.info(
            """
            **📊 评分说明**

            - **≥  80 分**：极高胜率  
            - **65 – 79 分**：高胜率  
            - **50 – 64 分**：中等胜率  
            - **35 – 49 分**：低胜率  
            - **<  35 分**：放弃  

            基于当前溢价率、溢价稳定性、流动性综合评估
            """
        )

    # ================= 筛选逻辑 =================
    if not selected_codes:
        filtered_signals = all_signals
        st.info(f"显示所有 {len(filtered_signals)} 个LOF的套利机会评分")
    else:
        filtered_signals = [s for s in all_signals if s["code"] in selected_codes]
        st.info(f"显示选中的 {len(filtered_signals)} 个LOF的套利机会评分")

    # ================= 信号详情 =================
    st.header("🎯 机会评分")

    for s in filtered_signals:
        with st.expander(f"{s['code']} ｜ {s['signal']} ｜ 得分 {s['score']}"):
            c1, c2, c3 = st.columns(3)

            with c1:
                st.metric("当前溢价率", f"{s['current_premium']:.2f}%")
                st.metric("近3日均溢价", f"{s['key_metrics']['premium_3d']:.2f}%")
                st.metric("近7日均溢价", f"{s['key_metrics']['premium_7d']:.2f}%")

            with c2:
                st.metric("最新涨跌幅", f"{s['price_pct']:.2f}%")
                st.metric("最新成交额", f"{int(s['current_volume'])} 万元")

            with c3:
                st.write("**加分项**")
                for r in s["reasons"]["plus"]:
                    st.write(f"➕ {r}")
                if s["reasons"]["minus"]:
                    st.write("**扣分项**")
                    for r in s["reasons"]["minus"]:
                        st.write(f"➖ {r}")

    # ================= 原底部趋势图（完全保留） =================
    st.header("📈 溢价率与价格趋势图")

    if filtered_signals:
        signal_codes = [s["code"] for s in filtered_signals]
        selected_code = st.selectbox("选择代码查看趋势", signal_codes)

        col1, col2 = st.columns([2, 1])
        with col1:
            chart_type = st.radio("图表显示模式", ["溢价率", "价格", "双轴对比"], horizontal=True)
        with col2:
            show_7d = st.checkbox("7日均线", True)
            show_14d = st.checkbox("14日均线", True)
            show_21d = st.checkbox("21日均线", False)

        df = analyzer.lof_data[selected_code]

        fig = go.Figure()

        if chart_type == "溢价率":
            fig.add_trace(go.Scatter(x=df["price_dt"], y=df["discount_rt"], name="溢价率"))
            if show_7d:
                fig.add_trace(go.Scatter(x=df["price_dt"], y=df["discount_rt"].rolling(7).mean(), name="7日均线"))
            if show_14d:
                fig.add_trace(go.Scatter(x=df["price_dt"], y=df["discount_rt"].rolling(14).mean(), name="14日均线"))
            if show_21d:
                fig.add_trace(go.Scatter(x=df["price_dt"], y=df["discount_rt"].rolling(21).mean(), name="21日均线"))

        elif chart_type == "价格":
            fig.add_trace(go.Scatter(x=df["price_dt"], y=df["price"], name="价格"))

        else:
            fig.add_trace(go.Scatter(x=df["price_dt"], y=df["price"], name="价格"))
            fig.add_trace(go.Scatter(x=df["price_dt"], y=df["discount_rt"], name="溢价率", yaxis="y2"))
            fig.update_layout(yaxis2=dict(overlaying="y", side="right"))

        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📊 详细数据", expanded=True):
            display_df = df[['fund_id','price_dt','price','net_value','est_val','discount_rt','volume','amount','amount_incr']].copy()
            display_df["price_dt"] = display_df["price_dt"].dt.strftime("%Y-%m-%d")
            display_df['price_pct'] = (display_df["price"].pct_change()*100).apply(lambda x: format(x,'.2f'))
            display_df = display_df[['fund_id','price_dt','price','net_value','est_val','discount_rt','price_pct','volume','amount','amount_incr']]
            display_df.columns = ['代码', '交易日期', '现价', '基金净值', '实时估值', '溢价率(%)', '涨跌幅(%)','成交(万元)','场内份额(万份)','场内新增(万份)']

            st.dataframe(display_df.tail(10), use_container_width=True)

    # ================= 套利操作 =================
    current_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(current_dir, "arbitrage_flow.png")
    st.header("🧩 套利操作")
    st.image(
        img_path,
        caption="LOF 溢价套利操作流程",
        use_container_width=True
    )

    # ================= 风险提示 =================
    st.header("⚠️ 风险提示")
    st.info("""
    本模型用于筛选当日更具溢价套利性价比的 LOF 标的，
    不构成任何投资建议。请结合人工判断与仓位控制使用。
    """)

main()