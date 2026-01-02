import streamlit as st
import pandas as pd
from premium_dashboard import PremiumAnalyzer

# Debug version with more logging
st.set_page_config(page_title="DEBUG - LOF Dashboard", layout="wide")
st.title("🔍 DEBUG - LOF Premium Dashboard")

# Initialize analyzer with debug info
with st.spinner("Loading data..."):
    try:
        analyzer = PremiumAnalyzer()
        st.success(f"✅ Loaded {len(analyzer.lof_data)} LOF files")
        
        # Show what files were loaded
        with st.expander("📁 Loaded files"):
            st.write("Files found:", list(analyzer.lof_data.keys()))
            
        # Check if we have data
        if not analyzer.lof_data:
            st.error("❌ No data loaded!")
            st.stop()
            
        # Test get_all_trading_signals
        with st.spinner("Generating trading signals..."):
            all_signals = analyzer.get_all_trading_signals()
            st.success(f"✅ Generated {len(all_signals)} trading signals")
            
        # Show raw signals
        with st.expander("📊 Raw trading signals"):
            st.json(all_signals[:3] if all_signals else "No signals")
            
        # Test sidebar
        st.sidebar.header("🔧 Debug Settings")
        st.sidebar.write(f"Total LOFs: {len(analyzer.lof_data)}")
        st.sidebar.write(f"Total signals: {len(all_signals)}")
        
        selected_codes = st.sidebar.multiselect(
            "Select LOF codes",
            options=list(analyzer.lof_data.keys()),
            default=list(analyzer.lof_data.keys())[:3]
        )
        
        # Main content
        st.header("🎯 Trading Signals")
        
        if selected_codes:
            filtered_signals = [s for s in all_signals if s['code'] in selected_codes]
            st.write(f"Filtered signals: {len(filtered_signals)}")
            
            for signal in filtered_signals[:2]:  # Show first 2 for debug
                st.write(f"**{signal['code']}** - {signal['signal']}")
                st.write(f"Current premium: {signal['current_premium']}%")
        else:
            st.warning("No codes selected")
            
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())