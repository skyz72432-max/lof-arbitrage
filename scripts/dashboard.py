"""
LOF溢价率交易仪表板
基于Streamlit的交互式分析界面
"""
import sys
import os

# 添加路径以便导入模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils.data_manager import DataManager
from streamlit_autorefresh import st_autorefresh

def main():
    st_autorefresh(interval=5 * 60 * 1000, key="auto_refresh") # ✅ 5min自动刷新（最先执行）
    st.cache_data.clear()   # 👈 强制每次重算
    st.set_page_config(
        page_title="LOF溢价率交易仪表板",
        page_icon="📈",
        layout="wide"
    )
    
    st.title("📈 LOF溢价率交易仪表板")
    st.markdown("### 基于T+1确认数据的交易信号分析")
    
    manager = DataManager()
    
    # 侧边栏
    with st.sidebar:
        st.header("🔧 设置")
        
        # 获取所有LOF代码
        summary = manager.get_data_summary()
        all_codes = list(summary['latest_dates'].keys())
        
        selected_codes = st.multiselect(
            "选择LOF代码",
            options=all_codes,
            default=all_codes[:min(5, len(all_codes))] if all_codes else []
        )
    
    # 主要内容区域
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.header("🎯 交易信号")
        
        if selected_codes:
            signals = []
            
            for code in selected_codes:
                df = manager.load_lof_data(code)
                if not df.empty:
                    # 计算7日溢价率统计
                    recent_7d = df.tail(7)
                    if len(recent_7d) >= 7:
                        current = (recent_7d.iloc[-1]['price']/ recent_7d.iloc[-1]['est_val']-1)*100 if pd.isna(recent_7d.iloc[-1]['discount_rt']) else recent_7d.iloc[-1]['discount_rt'] #recent_7d.iloc[-1]['discount_rt']
                        mean_7d = recent_7d['discount_rt'].mean()
                        std_7d = recent_7d['discount_rt'].std()
                        
                        # 生成简单信号
                        if current < mean_7d - std_7d:
                            signal = "BUY"
                        elif current > mean_7d + std_7d:
                            signal = "SELL"
                        else:
                            signal = "HOLD"
                        
                        signals.append({
                            'code': code,
                            'current': current,
                            'mean_7d': mean_7d,
                            'signal': signal,
                            'latest_date': df['price_dt'].max().strftime('%Y-%m-%d')
                        })
            
            if signals:
                for signal in signals:
                    with st.expander(f"{signal['code']} - {signal['signal']}"):
                        col_a, col_b = st.columns(2)
                        
                        with col_a:
                            st.metric("当前溢价率", f"{signal['current']:.2f}%")
                            st.metric("7日平均", f"{signal['mean_7d']:.2f}%")
                        
                        with col_b:
                            st.metric("最新日期", signal['latest_date'])
    
    with col2:
        st.header("📊 排序列表")
        
        if selected_codes:
            data = []
            for code in selected_codes:
                df = manager.load_lof_data(code)
                if not df.empty:
                    latest = df.iloc[-1]
                    data.append({
                        '代码': code,
                        '当前溢价': f"{(latest['price']/ latest['est_val']-1)*100 if pd.isna(latest['discount_rt']) else latest['discount_rt']:.2f}%",
                        '收盘价': f"{latest['price']:.3f}",
                        '日期': latest['price_dt'].strftime('%m-%d')
                    })
            
            if data:
                df_display = pd.DataFrame(data)
                st.dataframe(df_display, use_container_width=True)
    
    with col3:
        st.header("📈 系统状态")
        
        summary = manager.get_data_summary()
        st.metric("总LOF数量", summary['total_lofs'])
        st.metric("总记录数", summary['total_records'])
        
        st.info("""
        **使用说明**
        1. 左侧选择LOF代码查看详情
        2. 基于7日溢价率生成交易信号
        3. 盘中溢价率根据实时估值计算，T日真实净值数据于T+1日盘前确认
        
        **风险提示**
        历史数据不代表未来表现
        投资有风险，决策需谨慎
        """)
    
    # 底部图表
    st.header("📈 溢价率趋势图")
    
    if selected_codes:
        selected_code = st.selectbox("选择代码", selected_codes)
        
        df = manager.load_lof_data(selected_code)
        if not df.empty:
            if pd.isna(df['discount_rt'].iloc[-1]):
                df['discount_rt'].iloc[-1] = (df['price'].iloc[-1]/df['est_val'].iloc[-1]-1)*100

            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=df['price_dt'],
                y=df['discount_rt'],
                mode='lines+markers',
                name='溢价率',
                line=dict(color='blue', width=2)
            ))
            
            # 添加7日均线
            df['ma7'] = df['discount_rt'].rolling(window=7).mean()
            fig.add_trace(go.Scatter(
                x=df['price_dt'],
                y=df['ma7'],
                mode='lines',
                name='7日均线',
                line=dict(color='red', width=1, dash='dash')
            ))
            
            fig.update_layout(
                title=f"{selected_code} 溢价率趋势",
                xaxis_title="日期",
                yaxis_title="溢价率 (%)",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()