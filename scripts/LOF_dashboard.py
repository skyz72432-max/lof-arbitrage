"""
LOF 溢价套利胜率评分仪表板（完整版）
"""
import os
import warnings
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

warnings.filterwarnings("ignore")

APP_VERSION = "2026-01-14 01:36 UTC"

def get_project_root() -> str:
    """当前脚本所在目录的父目录"""
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)
    return os.path.dirname(current_dir)

def get_cache_path(project_root: str) -> str:
    for fname in os.listdir(project_root):
        if fname.startswith("fund_purchase_em_") and fname.endswith(".csv"):
            return os.path.join(project_root, fname)

# ======================================================
# 工具函数
# ======================================================

def is_monotonic_increasing(arr):
    return all(arr[i] < arr[i + 1] for i in range(len(arr) - 1))

def is_monotonic_decreasing(arr):
    return all(arr[i] > arr[i + 1] for i in range(len(arr) - 1))

def now_cn():
    return datetime.now(ZoneInfo("Asia/Shanghai"))

def is_pre_order_time():
    now = now_cn().time()
    return time(9, 30) <= now <= time(14, 00)

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

@st.cache_data(ttl=30, show_spinner=False) 
def get_last_sync_time():
    """
    读取最近一次 sync_daily.py 成功运行时间
    """
    project_root = get_project_root()
    path = os.path.join(project_root, "last_sync_time.txt")

    if not os.path.exists(path):
        return "暂无记录"

    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "读取失败"
        
# ======================================================
# 分析器
# ======================================================

class LOFArbitrageAnalyzer:

    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        # 不再在这里初始化 lof_data

    @staticmethod
    @st.cache_data(ttl=300, show_spinner=False)
    def load_all_data(data_dir):
        """加载所有LOF数据 (静态缓存方法)"""
        csv_files = [f for f in os.listdir(data_dir)
                    if f.startswith('lof_') and f.endswith('.csv')]
        lof_data = {}
        for file in csv_files:
            code = file.replace('lof_', '').replace('.csv', '')
            file_path = os.path.join(data_dir, file)
            try:
                df = pd.read_csv(file_path)
                df['price_dt'] = pd.to_datetime(df['price_dt'])
                df['discount_rt'] = pd.to_numeric(df['discount_rt'], errors='coerce')
                df["price_pct"] = df["price"].pct_change() * 100
                df['discount_rt'] = df['discount_rt'].fillna(((df['price'] / df['est_val'] - 1) * 100).round(2))
                lof_data[code] = df.sort_values('price_dt')
            except Exception as e:
                print(f"加载 {code} 数据失败: {e}")
        return lof_data

    def premium_stats(self, df, days):
        d = df.tail(days)
        return {
            "mean": d["discount_rt"].mean(),
            "std": d["discount_rt"].std()
        }

    def score_one_lof(self, lof_data, code):
        # 修改：将 lof_data 作为参数传入，而不是从 self 获取
        df = lof_data[code].copy()
        recent = df.tail(30)

        current = recent.iloc[-1]
        cur_premium = current["discount_rt"]
        cur_volume = current["volume"]
        cur_pct = current["price_pct"]

        stats7 = self.premium_stats(df, 5)
        stats14 = self.premium_stats(df, 10)
        stats21 = self.premium_stats(df, 15)

        # ================= 溢价率维度 =================
        premium_score = 0
        plus, minus = [], []
        
        if cur_premium < 0:
            minus.append("当前为折价，不适用溢价套利策略")
        elif pd.notna(cur_premium):
            premium_score += 60 if cur_premium >= 5 else int(cur_premium * 10)

            if cur_premium > stats7["mean"] + stats7["std"]:
                premium_score += 5
                plus.append(f"当前溢价率显著高于5日均值")

            if cur_premium - stats14["mean"] > stats14["std"] * 1.5:
                premium_score += 5
                plus.append("当前溢价率显著高于10日均值")

            if cur_premium - stats21["mean"] > stats21["std"] * 2:
                premium_score += 5
                plus.append("当前溢价率显著高于15日均值")

            if 10 <= cur_premium < 20:
                premium_score += 10
                plus.append("当前溢价率处于10–20%，套利空间充足")
            elif cur_premium >= 20:
                premium_score += 20
                plus.append("当前溢价率 ≥20%，属于极端溢价空间")

            last3 = recent["discount_rt"].tail(3).values

            if (last3 >= 5).all() and is_monotonic_increasing(last3):
                premium_score += 15
                plus.append(
                    "近3日溢价率均 ≥5%且逐日上升，套利空间稳步扩张"
                )
            elif (last3 >= 5).all():
                premium_score += 10
                plus.append(
                    "近3日溢价率均 ≥5%，套利空间稳定存在"
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
            plus.append("近3日成交额均 ≥1000万元，场内份额均 ≥1000万份，具备套利执行基础")

            # ---------- 加分条件：份额稳定性 ----------
            amount_incr_today = current["amount_incr"]
            last3_amount_incr = recent["amount_incr"].tail(3).values

            if abs(amount_incr_today) < 1:
                liquidity_score += 5
                plus.append(
                    "当日场内份额增速绝对值 <1%，套利盘未明显集中进出"
                )

            if (np.abs(last3_amount_incr) < 1).all():
                liquidity_score += 15
                plus.append(
                    "近3日份额增速绝对值均 <1%，份额结构高度稳定"
                )

            # ---------- 扣分条件：套利机会快速消失 ----------
            last3_premium = recent["discount_rt"].tail(3).values

            if amount_incr_today > 3 and is_monotonic_decreasing(last3_premium):
                liquidity_score -= 20
                minus.append(
                    "当日场内份额增速 >3% 且溢价率连续回落，套利盘加速撤离"
                )

        else:
            minus.append(
                "近3日成交额或场内份额不足，存在较大的流动性风险，套利需谨慎"
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
                "premium_5d": recent["discount_rt"].tail(5).mean()
            },
            "reasons": {
                "plus": plus,
                "minus": minus
            }
        }

    @st.cache_data(ttl=300, show_spinner=False)
    def get_all_signals(_self):
        """
        获取所有信号 (缓存方法)
        关键：使用 _self 别名来避免 self 被哈希，并在内部调用静态缓存方法
        """
        # 1. 通过静态缓存方法加载数据
        lof_data = _self.load_all_data(_self.data_dir)

        # 2. 读取基金申购信息 (这部分代码你原来就有，可能需要微调路径)
        project_root = get_project_root()
        cache_path = get_cache_path(project_root)
        fund_purchase_df = pd.read_csv(cache_path, dtype={"基金代码": str})
        fund_purchase_df.rename(columns={
            "基金代码": "code",
            "基金简称": "fund_name",
            "申购状态": "purchase_status",
            "赎回状态": "redeem_status",
            "日累计限定金额": "purchase_limit",
            "手续费": "fee_pct"
        }, inplace=True)
        fund_purchase_df["code"] = fund_purchase_df["code"].astype(str)
        purchase_info_map = (
            fund_purchase_df
            .set_index("code")[[
                "fund_name",
                "purchase_status",
                "redeem_status",
                "purchase_limit",
                "fee_pct"
            ]]
            .to_dict(orient="index")
        )

        # 3. 为每个LOF计算分数
        signals = []
        for code in lof_data:
            # 调用 score_one_lof，并传入当前循环的 lof_data
            s = _self.score_one_lof(lof_data, code)
            purchase_info = purchase_info_map.get(code, {})
            s["purchase_info"] = {
                "fund_name": purchase_info.get("fund_name"),
                "purchase_status": purchase_info.get("purchase_status"),
                "redeem_status": purchase_info.get("redeem_status"),
                "purchase_limit": purchase_info.get("purchase_limit"),
                "fee_pct": purchase_info.get("fee_pct")
            }
            signals.append(s)
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
    st.set_page_config(
        page_title="LOF溢价套利【每日机会】",
        page_icon="📈",
        layout="wide"
    )
    st.cache_data.clear()
    st.title("📈 LOF 溢价套利【每日机会】")
    st.markdown("### 基于行情数据，寻找套利机会，盘中定时更新")
    st.caption(f"👉 交易日更新时点：09:30，10:30，11:30，13:30，14:00，14:15，14:30，14:45，15:00，21:00")
    st.caption(f"🚀 场内申购建议：**14:00-14:30 观察筛选，14:30-15:00 完成交易**，尽量使盘中估值≈当日净值")
    st.caption(f"🕒 最后更新时间：{get_last_sync_time()}")
    
    analyzer = LOFArbitrageAnalyzer()
    lof_data = analyzer.load_all_data(analyzer.data_dir)
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
        all_codes = list(lof_data.keys())

        selected_codes = st.multiselect(
            "选择LOF代码",
            options=all_codes,
            default=[c for c in default_codes if c in all_codes]
        )

    # ================= 今日推荐 =================
    st.header("🔥 今日推荐")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        top_df = pd.DataFrame([{
            "基金代码": s["code"],
            "基金简称": s["purchase_info"]["fund_name"],
            "当前溢价": f"{s['current_premium']:.2f}%",
            "当前成交": f"{int(s['current_volume'])}万",
            "申购状态": s["purchase_info"]["purchase_status"],
            "赎回状态": s["purchase_info"]["redeem_status"],
            "手续费": f"{s['purchase_info']['fee_pct']:.2f}%",      
            "套利机会": s["signal"],
            "综合得分": f"{s['score']:.0f}"
        } for s in default_signals])

        styled_top_df = (
            top_df
            .style
            .set_properties(**{"text-align": "center"})
            .applymap(signal_font_color, subset=["套利机会"])
        )

        st.dataframe(styled_top_df, use_container_width=True)
        st.caption("注：当日基金净值公布前，**当前溢价**根据**实时估值**计算。")

    with col_right:
        st.info(
            """
            **📊 评分说明**

            - **≥  80 分**：极高胜率  
            - **65 – 79 分**：高胜率  
            - **50 – 64 分**：中等胜率  
            - **35 – 49 分**：低胜率  
            - **<  35 分**：放弃  

            基于当前溢价、溢价稳定性、流动性综合评估
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
                st.metric("近3日平均溢价", f"{s['key_metrics']['premium_3d']:.2f}%")
                st.metric("近5日平均溢价", f"{s['key_metrics']['premium_5d']:.2f}%")

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

    # ================= 原底部趋势图 =================
    st.header("📊 溢价趋势")

    if filtered_signals:
        signal_codes = [s["code"] for s in filtered_signals]
        selected_code = st.selectbox("选择代码查看趋势", signal_codes)

        # Chart settings
        col_settings1, col_settings2 = st.columns([2, 1])
        
        with col_settings1:
            chart_type = st.radio(
                "图表显示模式",
                ["价格 vs 净值", "溢价率", "价格", "净值"],
                horizontal=True
            )
        
        with col_settings2:
            st.write("均线设置")
            cols = st.columns([1, 1, 1])
            show_7d  = cols[0].checkbox("5日均线", True, key="chart_7d")
            show_14d = cols[1].checkbox("10日均线", True, key="chart_14d")
            show_21d = cols[2].checkbox("15日均线", False, key="chart_21d")
        
        if selected_code in lof_data:
            df = lof_data[selected_code]
            df['discount_rt'] = df['discount_rt'].fillna(((df['price'] / df['est_val'] - 1) * 100).round(2))
            df['price_dt_str'] = df['price_dt'].dt.strftime('%Y-%m-%d')
            
            fig = go.Figure()
            
            # ==========================
            # 价格 vs 净值
            # ==========================
            if chart_type == "价格 vs 净值":
                # 左轴：价格
                fig.add_trace(go.Scatter(
                    x=df['price_dt_str'],
                    y=df['price'],
                    mode='lines+markers',
                    name='价格',
                    line=dict(color='#E3B341', width=2),
                    yaxis='y'
                ))
            
                # 左轴：基金净值
                fig.add_trace(go.Scatter(
                    x=df['price_dt_str'],
                    y=df['net_value'].fillna(df['est_val']),
                    mode='lines+markers',
                    name='净值',
                    line=dict(color='#8b5a2b', width=2),
                    yaxis='y'
                ))
            
                # 右轴：溢价率（柱状）
                colors = ['red' if v >= 0 else 'green' for v in df['discount_rt']]
                fig.add_trace(go.Bar(
                    x=df['price_dt_str'],
                    y=df['discount_rt'],
                    name='溢价率(右轴)',
                    marker_color=colors,
                    opacity=0.6,
                    yaxis='y2',
                    text=df['discount_rt'].round(2),
                    textposition='outside'
                ))
            
                fig.update_layout(
                    title=f"{selected_code} 价格 vs 净值",
                    # 左轴：价格 & 净值（不画网格）
                    yaxis=dict(
                        title="价格(元)",
                        showgrid=False,
                        zeroline=False
                    ),
                
                    # 右轴：溢价率（唯一的辅助线来源）
                    yaxis2=dict(
                        title="溢价率(%)",
                        overlaying='y',
                        side='right',
                        showgrid=True,    # 只画右轴网格
                        gridcolor='rgba(200,200,200,0.45)',
                        zeroline=True,
                        zerolinecolor='rgba(120,120,120,0.6)'
                    ),
                    
                    height=400
                )
                
            # ==========================
            # 溢价率
            # ==========================            
            elif chart_type == "溢价率": 
                fig.add_trace(go.Scatter(
                    x=df['price_dt_str'],
                    y=df['discount_rt'],
                    mode='lines+markers',
                    name='溢价率',
                    line=dict(color='blue', width=2)
                ))
            
                if show_7d:
                    fig.add_trace(go.Scatter(
                        x=df['price_dt_str'],
                        y=df['discount_rt'].rolling(5).mean(),
                        mode='lines',
                        name='5日均线',
                        line=dict(color='red', dash='dash')
                    ))
            
                if show_14d:
                    fig.add_trace(go.Scatter(
                        x=df['price_dt_str'],
                        y=df['discount_rt'].rolling(10).mean(),
                        mode='lines',
                        name='10日均线',
                        line=dict(color='green', dash='dash')
                    ))
            
                if show_21d:
                    fig.add_trace(go.Scatter(
                        x=df['price_dt_str'],
                        y=df['discount_rt'].rolling(15).mean(),
                        mode='lines',
                        name='15日均线',
                        line=dict(color='orange', dash='dash')
                    ))
            
                fig.update_layout(
                    title=f"{selected_code} 溢价趋势",
                    yaxis_title="溢价率(%)",
                    height=400
                )
            
            # ==========================
            # 价格
            # ==========================
            elif chart_type == "价格":
                fig.add_trace(go.Scatter(
                    x=df['price_dt_str'],
                    y=df['price'],
                    mode='lines+markers',
                    name='价格',
                    line=dict(color='#E3B341', width=2)
                ))
            
                if show_7d:
                    fig.add_trace(go.Scatter(
                        x=df['price_dt_str'],
                        y=df['price'].rolling(5).mean(),
                        mode='lines',
                        name='5日均线',
                        line=dict(color='red', dash='dash')
                    ))
            
                if show_14d:
                    fig.add_trace(go.Scatter(
                        x=df['price_dt_str'],
                        y=df['price'].rolling(10).mean(),
                        mode='lines',
                        name='10日均线',
                        line=dict(color='green', dash='dash')
                    ))
            
                if show_21d:
                    fig.add_trace(go.Scatter(
                        x=df['price_dt_str'],
                        y=df['price'].rolling(15).mean(),
                        mode='lines',
                        name='15日均线',
                        line=dict(color='orange', dash='dash')
                    ))
            
                fig.update_layout(
                    title=f"{selected_code} 价格趋势",
                    yaxis_title="价格(元)",
                    height=400
                )
            
            # ==========================
            # 净值
            # ==========================
            else:
                fig.add_trace(go.Scatter(
                    x=df['price_dt_str'],
                    y=df['net_value'].fillna(df['est_val']),
                    mode='lines+markers',
                    name='净值',
                    line=dict(color='#8b5a2b', width=2)
                ))
            
                if show_7d:
                    fig.add_trace(go.Scatter(
                        x=df['price_dt_str'],
                        y=df['net_value'].fillna(df['est_val']).rolling(5).mean(),
                        mode='lines',
                        name='5日均线',
                        line=dict(color='red', dash='dash')
                    ))
            
                if show_14d:
                    fig.add_trace(go.Scatter(
                        x=df['price_dt_str'],
                        y=df['net_value'].fillna(df['est_val']).rolling(10).mean(),
                        mode='lines',
                        name='10日均线',
                        line=dict(color='green', dash='dash')
                    ))
            
                if show_21d:
                    fig.add_trace(go.Scatter(
                        x=df['price_dt_str'],
                        y=df['net_value'].fillna(df['est_val']).rolling(15).mean(),
                        mode='lines',
                        name='15日均线',
                        line=dict(color='orange', dash='dash')
                    ))
            
                fig.update_layout(
                    title=f"{selected_code} 净值趋势",
                    yaxis_title="净值(元)",
                    height=400
                )
            
            # ==========================
            # 公共布局（x轴重点修正）
            # ==========================
            fig.update_layout(
                xaxis=dict(
                    type='category',
                    tickmode='auto',
                    nticks=8,
                    tickangle=0,
                    tickfont=dict(size=12)
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.08,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=14)
                ),
                margin=dict(t=80)
            )
            
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("🧮 详细数据", expanded=True):
            display_df = df[['fund_id','price_dt','price','net_value','est_val','discount_rt','volume','amount','amount_incr']].copy()
            display_df["price_dt"] = display_df["price_dt"].dt.strftime("%Y-%m-%d")
            display_df['price_pct'] = (display_df["price"].pct_change()*100).apply(lambda x: format(x,'.2f'))
            display_df = display_df[['fund_id','price_dt','price','net_value','est_val','discount_rt','price_pct','volume','amount','amount_incr']]
            display_df.columns = ['基金代码', '交易日期', '现价', '基金净值', '实时估值', '溢价率(%)', '涨跌幅(%)','成交(万元)','场内份额(万份)','场内新增(万份)']

            st.dataframe(display_df.tail(10), use_container_width=True)

    # ================= 套利操作 =================
    current_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(current_dir, "arbitrage_flow.png")
    st.header("🧩 新手教程")
    st.image(
        img_path,
        caption="LOF 溢价套利操作流程",
        use_container_width=True
    )

    with st.expander("一、LOF 基础概念"):
        st.markdown("### 🔹 LOF 基金定义")
        st.markdown("""
        - LOF 基金是集合投资工具，由基金管理人统一管理投资者资金，进行专业化投资，实现风险分散和收益共享
        """)

        st.markdown("### 🔹 LOF 基金特点")
        st.markdown("""
        - **唯一同时支持场内和场外交易的基金**
        - **场内**：证券交易所买卖，像股票一样交易  
        - **场外**：支付宝、天天基金等平台申购赎回
        - 同一基金代码，后缀不同（场内.SZ/.SH，场外.OF）
        """)

    with st.expander("二、交易场所详解"):
        st.markdown("### 🔹 场内交易（二级市场）")
        st.markdown("""
        - **平台**：通过股票账户在证券交易所交易  
        - **交易品种**：ETF 基金、LOF 基金等
        - **操作方式**：实时买卖，价格随时变动            
        """)

        st.markdown("### 🔹 场外交易")
        st.markdown("""
        - **平台**：天天基金、支付宝、券商APP场外通道  
        - **操作方式**：申购赎回，按当日净值成交
        - **示例**：美元债LOF(501300)支持场外申购转场内  
        """)

    with st.expander("三、净值、估值、价格"):
        st.markdown("### 🔹 净值")
        st.markdown("""
        - 基金公司每晚公布的实际价值，申购赎回基准  
        """)

        st.markdown("### 🔹 估值")
        st.markdown("""
        - 盘中估算值，各平台算法不同结果可能不同
        """)

        st.markdown("### 🔹 价格")
        st.markdown("""
        - 场内实时交易价格，受市场情绪影响
        """)

        st.info("""
        **三者关系**
        - 价格 > 净值 → 溢价 → 套利机会
        - 价格 < 净值 → 折价 → 套利机会  
        - 净值是实际价值，价格是交易价格，估值是参考值
        """)

    with st.expander("四、净值更新时间"):
        st.markdown("### 🔹 A 股基金")
        st.markdown("""
        - T 日晚更新，一般 19:00-24:00  
        """)

        st.markdown("### 🔹 QDII 基金")
        st.markdown("""
        - 有时差市场(美股)：T 日晚更新 T-1 日净值
        - 无时差市场(港股)：T 日晚更新 T 日净值
        """)

    # ===== 套利原理说明 =====
    with st.expander("五、套利基本原理"):
        st.markdown("### 🔹 溢价套利（价格 > 净值）")
        st.markdown("""
        - **条件**：场内价格 大于 基金净值  
        - **操作**：场内申购 → 到账后卖出  
        - **收益来源**：价格与净值的差价  
        - **关键**：套利机会转瞬即逝，建议优先通过**场内申购**
        """)

        st.markdown("### 🔹 折价套利（价格 < 净值）")
        st.markdown("""
        - **条件**：场内价格 小于 基金净值  
        - **操作**：场内买入 → 赎回  
        - **收益来源**：净值与价格的差价
        """)

        st.info("""
        **核心要点**
        - 溢价套利：场内申购 → 场内卖出  
        - 折价套利：场内买入 → 场内赎回  
        - 场外申购转场内只适合长期持有，不适合套利
        """)

    # ===== 溢价套利操作流程 =====
    with st.expander("六、溢价套利流程 🔥"):
        st.markdown("### 🔹 第一步：场内申购")
        st.markdown("""
        - **时间**：交易日 15:00 前  
        - **平台**：券商 APP 的场内基金申购通道  
        - **成交价**：按当日净值成交  
        - **关键**：必须是**场内申购**，不是场外申购
        """)

        st.markdown("### 🔹 第二步：等待到账")
        st.markdown("""
        - **A股 LOF**：T+2 日到账  
        - **QDII-LOF**：T+3 日到账  
        - **注意**：申购后份额冻结，期间无法交易
        """)

        st.markdown("### 🔹 第三步：场内卖出")
        st.markdown("""
        - **时间**：份额到账当日  
        - **操作**：与卖股票相同，输入价格和数量  
        - **策略**：到账后尽快卖出，锁定溢价收益
        """)

        st.info("""
        **重要区别：场内申购 vs 场外申购**
        - 场内申购：直接进入股票账户，无需转托管  
        - 场外申购：需转托管到场内，多一步操作  
        - 溢价套利必须用场内申购，否则无法及时卖出
        """)

    # ===== 关键时间节点 =====
    with st.expander("七、关键时点把控"):
        st.markdown("### 🔹 A股 LOF 基金")
        st.markdown("""
        - T 日 15:00 前申购 → 按 T 日净值成交  
        - T+1 日：份额确认  
        - T+2 日：可转托管至场内，到账后即可卖出
        """)

        st.markdown("### 🔹 QDII-LOF 基金（投资海外）")
        st.markdown("""
        - 申购到账：T+3 日  
        - 赎回到账：T+7 日  
        - 净值更新：通常晚一天（如 T+1 日晚更新 T 日净值）
        """)

    # ===== 费用成本 =====
    with st.expander("八、费用成本计算"):
        st.markdown("### 🔹 申购费")
        st.markdown("""
        - 1.2% – 1.5%  
        - 通常一折后约 **0.12% – 0.15%**
        """)

        st.markdown("### 🔹 赎回费")
        st.markdown("""
        - 持有 < 7 天：1.5%（惩罚性费率）  
        - 持有 ≥ 7 天：约 0.5%（以基金合同为准）
        """)

        st.markdown("### 🔹 交易成本")
        st.markdown("""
        - 场内买卖佣金：万分之一起（0.01%）  
        - 最低收费：0.2 元起
        """)

        st.info("""
        **套利盈亏平衡点**  
        = 申购费 + 赎回费 + 交易佣金 + 时间成本
        """)

    with st.expander("九、卖出时机建议"):
        st.markdown("### 🔹 基本原则")
        st.markdown("""
        - 到账后开盘即卖，降低不确定性风险
        """)

        st.markdown("### 🔹 具体建议")
        st.markdown("""
        - **高溢价(> 3%)**：集合竞价挂单  
        - **中等溢价**：早盘观察后决策
        - **低溢价(< 1%)**：14:30 后决定
        """)

        st.markdown("### 🔹 执行纪律")
        st.markdown("""
        - 设定溢价阈值，严格执行策略  
        """)

    with st.expander("十、风险控制要点"):
        st.markdown("### 🔹 溢价消失风险")
        st.markdown("""
        - 在申购后、份额到账前  
        - **溢价可能快速收窄甚至消失**
        """)

        st.markdown("### 🔹 净值下跌风险")
        st.markdown("""
        - 套利期间基金净值可能下跌  
        - **直接侵蚀溢价套利收益**
        """)

        st.markdown("### 🔹 流动性风险")
        st.markdown("""
        - 小众 LOF 基金成交清淡  
        - 可能出现 **卖不出 / 大幅滑点**
        """)

        st.markdown("### 🔹 操作风险")
        st.markdown("""
        - 误操作（如选错申购渠道、时间错误）  
        - 可能导致 **成本上升或套利失败**
        """)

        st.info("""
        **风控建议**
        - 优先选择：高成交额、成熟 LOF  
        - 控制单笔规模，避免流动性冲击  
        - 严格区分「场内申购」与「场外申购」
        """)
        
    # ================= 风险提示 =================
    st.header("⚠️ 风险提示")
    st.info("""
    - **免责声明**：本网页仅供投资者学习交流，所选产品仅供参考，不构成任何投资建议！市场有风险，投资需谨慎。
    - **数据来源**：集思录，东方财富（网页更新略有延迟，实时数据请见官网）
    """)

main()
