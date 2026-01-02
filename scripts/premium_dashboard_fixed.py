"""
交易导向的溢价率分析仪表板
提供7/14/21日平均值和交易信号，支持价格对比
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Tuple
from streamlit_autorefresh import st_autorefresh
import warnings
warnings.filterwarnings('ignore')

class PremiumAnalyzer:
    """溢价率分析器"""
    
    def __init__(self, data_dir: str = "data"):
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
                if pd.isna(df['discount_rt'].iloc[-1]):
                    df['discount_rt'].iloc[-1] = round((df['price'].iloc[-1]/df['est_val'].iloc[-1]-1)*100,2)
                self.lof_data[code] = df.sort_values('price_dt')
            except Exception as e:
                print(f"加载 {code} 数据失败: {e}")
    
    def calculate_premium_stats(self, code: str, days: int) -> Dict:
        """计算指定天数的溢价率统计"""
        if code not in self.lof_data:
            return {}
        
        df = self.lof_data[code]
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 获取最近days天的数据
        recent_data = df[df['price_dt'] >= cutoff_date].copy()
        
        if recent_data.empty:
            return {}
        
        return {
            'mean': float(recent_data['discount_rt'].mean()),
            'median': float(recent_data['discount_rt'].median()),
            'std': float(recent_data['discount_rt'].std()),
            'min': float(recent_data['discount_rt'].min()),
            'max': float(recent_data['discount_rt'].max()),
            'current': (recent_data['price'].iloc[-1]/recent_data['est_val'].iloc[-1]-1)*100 if pd.isna(recent_data['discount_rt'].iloc[-1]) else recent_data['discount_rt'].iloc[-1],
            #float(recent_data['discount_rt'].iloc[-1]) if not recent_data.empty else 0,
            'count': len(recent_data),
            'z_score': float(((recent_data['price'].iloc[-1]/recent_data['est_val'].iloc[-1]-1)*100 - recent_data['discount_rt'].mean()) / recent_data['discount_rt'].std()) if pd.isna(recent_data['discount_rt'].iloc[-1]) else float((recent_data['discount_rt'].iloc[-1] - recent_data['discount_rt'].mean()) / recent_data['discount_rt'].std())
            # float((recent_data['discount_rt'].iloc[-1] - recent_data['discount_rt'].mean()) / recent_data['discount_rt'].std()) if len(recent_data) > 1 else 0
        }
    
    def get_trading_signal(self, code: str) -> Dict:
        """生成交易信号"""
        if code not in self.lof_data:
            return {}
        
        stats_7d = self.calculate_premium_stats(code, 7)
        stats_14d = self.calculate_premium_stats(code, 14)
        stats_21d = self.calculate_premium_stats(code, 21)
        
        if not all([stats_7d, stats_14d, stats_21d]):
            return {}
        
        current = stats_7d['current']
        
        # 交易信号逻辑
        signal = "HOLD"
        confidence = 0.5
        reasons = []
        
        # 相对于7日均值
        if current > stats_7d['mean'] + stats_7d['std']:
            signal = "SELL"
            confidence = min(0.9, abs(current - stats_7d['mean']) / stats_7d['std'] * 0.3)
            reasons.append(f"当前溢价率({current:.2f}%)高于7日均值({stats_7d['mean']:.2f}%) + 1σ")
        elif current < stats_7d['mean'] - stats_7d['std']:
            signal = "BUY"
            confidence = min(0.9, abs(current - stats_7d['mean']) / stats_7d['std'] * 0.3)
            reasons.append(f"当前折价率({current:.2f}%)低于7日均值({stats_7d['mean']:.2f}%) - 1σ")
        
        # 相对于14日均值
        if abs(current - stats_14d['mean']) > stats_14d['std'] * 1.5:
            reasons.append(f"偏离14日均值显著")
        
        # 相对于21日均值
        if abs(current - stats_21d['mean']) > stats_21d['std'] * 2:
            reasons.append(f"偏离21日均值显著")
        
        return {
            'code': code,
            'signal': signal,
            'confidence': round(confidence, 2),
            'current_premium': current,
            'stats': {
                '7d': stats_7d,
                '14d': stats_14d,
                '21d': stats_21d
            },
            'reasons': reasons,
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def get_all_trading_signals(self) -> List[Dict]:
        """获取所有LOF的交易信号"""
        signals = []
        for code in self.lof_data.keys():
            signal = self.get_trading_signal(code)
            if signal:
                signals.append(signal)
        return sorted(signals, key=lambda x: abs(x['current_premium']), reverse=True)

# Streamlit Dashboard
def main():
    st_autorefresh(interval=5 * 60 * 1000, key="auto_refresh") # ✅ 5min自动刷新（最先执行）
    st.cache_data.clear()   # 👈 强制每次重算
    st.set_page_config(
        page_title="LOF溢价率交易仪表板",
        page_icon="📈",
        layout="wide"
    )
    
    st.title("📈 LOF溢价率交易仪表板")
    st.markdown("### 基于历史数据的交易信号分析")
    
    analyzer = PremiumAnalyzer()
    
    # 侧边栏
    with st.sidebar:
        st.header("🔧 设置")
        all_codes = list(analyzer.lof_data.keys())
        selected_codes = st.multiselect(
            "选择LOF代码",
            options=all_codes,
            default=all_codes[:min(5, len(all_codes))] if all_codes else []
        )
    
    # 主要内容区域
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.header("🎯 交易信号")
        
        # 获取所有交易信号
        all_signals = analyzer.get_all_trading_signals()
        
        # 筛选选中的代码
        if not selected_codes:
            filtered_signals = all_signals
            st.info(f"显示所有 {len(filtered_signals)} 个LOF的交易信号")
        else:
            filtered_signals = [s for s in all_signals if s['code'] in selected_codes]
            st.info(f"显示选中的 {len(filtered_signals)} 个LOF的交易信号")
        
        if filtered_signals:
            for signal in filtered_signals:
                with st.expander(f"{signal['code']} - {signal['signal']} ({signal['confidence']})"):
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        st.metric("当前溢价率", f"{signal['current_premium']:.2f}%")
                        st.metric("7日平均", f"{signal['stats']['7d']['mean']:.2f}%")
                        st.metric("14日平均", f"{signal['stats']['14d']['mean']:.2f}%")
                        st.metric("21日平均", f"{signal['stats']['21d']['mean']:.2f}%")
                    
                    with col_b:
                        st.metric("7日标准差", f"{signal['stats']['7d']['std']:.2f}%")
                        st.metric("Z-Score", f"{signal['stats']['7d']['z_score']:.2f}")
                        st.metric("数据天数", signal['stats']['7d']['count'])
                    
                    if signal['reasons']:
                        st.write("**交易理由:**")
                        for reason in signal['reasons']:
                            st.write(f"- {reason}")
        else:
            st.error("❌ 没有生成任何交易信号")
    
    with col2:
        st.header("📊 排序列表")
        
        if filtered_signals:
            df_display = pd.DataFrame([
                {
                    '代码': s['code'],
                    '当前溢价': f"{s['current_premium']:.2f}%",
                    '信号': s['signal'],
                    '置信度': s['confidence']
                } for s in filtered_signals
            ])
            st.dataframe(df_display, use_container_width=True)
        else:
            st.info("没有选择任何代码或没有生成信号")
    
    with col3:
        st.header("⚠️ 风险提示")
        
        st.info("""
        **使用说明:**
        1. 绿色=买入信号（折价较大）
        2. 红色=卖出信号（溢价较大）
        3. 灰色=持有观望
        
        **风险提示:**
        - 历史数据不代表未来表现
        - 请结合其他指标综合判断
        - 投资有风险，决策需谨慎
        """)
    
    # 底部图表
    st.header("📈 溢价率与价格趋势图")
    
    if filtered_signals:
        # Use the codes that actually have signals
        signal_codes = [s['code'] for s in filtered_signals]
        selected_code = st.selectbox("选择代码查看趋势", signal_codes)
        
        # Chart settings
        col_settings1, col_settings2 = st.columns([2, 1])
        
        with col_settings1:
            chart_type = st.radio(
                "图表显示模式",
                ["溢价率", "价格", "双轴对比"],
                horizontal=True
            )
        
        with col_settings2:
            st.write("📊 均线设置")
            show_7d = st.checkbox("7日均线", value=True, key="chart_7d")
            show_14d = st.checkbox("14日均线", value=True, key="chart_14d")
            show_21d = st.checkbox("21日均线", value=False, key="chart_21d")
        
        if selected_code in analyzer.lof_data:
            df = analyzer.lof_data[selected_code]
            if pd.isna(df['discount_rt'].iloc[-1]):
                df['discount_rt'].iloc[-1] = round((df['price'].iloc[-1]/df['est_val'].iloc[-1]-1)*100,2)
            
            fig = go.Figure()
            
            if chart_type == "溢价率":
                # 溢价率曲线
                fig.add_trace(go.Scatter(
                    x=df['price_dt'],
                    y=df['discount_rt'],
                    mode='lines+markers',
                    name='溢价率',
                    line=dict(color='blue', width=2)
                ))
                
                # 根据checkbox显示均线
                if show_7d:
                    df['ma7'] = df['discount_rt'].rolling(window=7).mean()
                    fig.add_trace(go.Scatter(
                        x=df['price_dt'],
                        y=df['ma7'],
                        mode='lines',
                        name='7日均线',
                        line=dict(color='red', width=1, dash='dash')
                    ))
                
                if show_14d:
                    df['ma14'] = df['discount_rt'].rolling(window=14).mean()
                    fig.add_trace(go.Scatter(
                        x=df['price_dt'],
                        y=df['ma14'],
                        mode='lines',
                        name='14日均线',
                        line=dict(color='green', width=1, dash='dash')
                    ))
                
                if show_21d:
                    df['ma21'] = df['discount_rt'].rolling(window=21).mean()
                    fig.add_trace(go.Scatter(
                        x=df['price_dt'],
                        y=df['ma21'],
                        mode='lines',
                        name='21日均线',
                        line=dict(color='orange', width=1, dash='dash')
                    ))
                
                fig.update_layout(
                    title=f"{selected_code} 溢价率趋势",
                    xaxis_title="日期",
                    yaxis_title="溢价率 (%)",
                    height=400
                )
                
            elif chart_type == "价格":
                # 价格曲线
                fig.add_trace(go.Scatter(
                    x=df['price_dt'],
                    y=df['price'],
                    mode='lines+markers',
                    name='收盘价',
                    line=dict(color='orange', width=2)
                ))
                
                # 根据checkbox显示价格均线
                if show_7d:
                    df['price_ma7'] = df['price'].rolling(window=7).mean()
                    fig.add_trace(go.Scatter(
                        x=df['price_dt'],
                        y=df['price_ma7'],
                        mode='lines',
                        name='价格7日均线',
                        line=dict(color='purple', width=1, dash='dash')
                    ))
                
                if show_14d:
                    df['price_ma14'] = df['price'].rolling(window=14).mean()
                    fig.add_trace(go.Scatter(
                        x=df['price_dt'],
                        y=df['price_ma14'],
                        mode='lines',
                        name='价格14日均线',
                        line=dict(color='brown', width=1, dash='dash')
                    ))
                
                if show_21d:
                    df['price_ma21'] = df['price'].rolling(window=21).mean()
                    fig.add_trace(go.Scatter(
                        x=df['price_dt'],
                        y=df['price_ma21'],
                        mode='lines',
                        name='价格21日均线',
                        line=dict(color='pink', width=1, dash='dash')
                    ))
                
                fig.update_layout(
                    title=f"{selected_code} 价格趋势",
                    xaxis_title="日期",
                    yaxis_title="价格 (元)",
                    height=400
                )
                
            else:  # 双轴对比
                fig = go.Figure()
                
                # 价格轴 (左)
                fig.add_trace(go.Scatter(
                    x=df['price_dt'],
                    y=df['price'],
                    mode='lines+markers',
                    name='收盘价',
                    line=dict(color='orange', width=2),
                    yaxis='y'
                ))
                
                # 溢价率轴 (右)
                fig.add_trace(go.Scatter(
                    x=df['price_dt'],
                    y=df['discount_rt'],
                    mode='lines+markers',
                    name='溢价率',
                    line=dict(color='blue', width=2),
                    yaxis='y2'
                ))
                
                fig.update_layout(
                    title=f"{selected_code} 价格与溢价率对比",
                    xaxis_title="日期",
                    yaxis=dict(
                        title="价格 (元)",
                        side="left"
                    ),
                    yaxis2=dict(
                        title="溢价率 (%)",
                        side="right",
                        overlaying="y"
                    ),
                    height=400
                )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 数据表格显示
            with st.expander("📊 详细数据"):
                display_df = df[['fund_id','price_dt','price','net_value','est_val','discount_rt','volume','amount','amount_incr']].copy()
                display_df["price_dt"] = display_df["price_dt"].dt.strftime("%Y-%m-%d")
                display_df['涨跌幅(%)'] = (display_df["price"].pct_change()*100).apply(lambda x: format(x,'.2f'))
                display_df = display_df[['fund_id','price_dt','price','net_value','est_val','discount_rt','涨跌幅(%)','volume','amount','amount_incr']]
                display_df.columns = ['代码', '交易日期', '现价', '基金净值', '实时估值', '溢价率(%)', '涨跌幅(%)','成交(万元)','场内份额(万份)','场内新增(万份)']
                
                st.dataframe(display_df.tail(10), use_container_width=True)

# Ensure Streamlit runs the main function
main()