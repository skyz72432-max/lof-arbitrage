import streamlit as st
import pandas as pd

st.title("Simple Test Dashboard")
st.write("Testing if Streamlit is working...")

# Simple test data
df = pd.DataFrame({
    'A': [1, 2, 3, 4],
    'B': [10, 20, 30, 40]
})

st.write("DataFrame:")
st.dataframe(df)

st.write("Metrics:")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Test 1", "100")
with col2:
    st.metric("Test 2", "200")
with col3:
    st.metric("Test 3", "300")