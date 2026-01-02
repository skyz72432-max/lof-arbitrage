import streamlit as st

st.title("Minimal Test")
st.write("This is a minimal test")

# Simple counter to test interactivity
if 'count' not in st.session_state:
    st.session_state.count = 0

if st.button("Click me"):
    st.session_state.count += 1

st.write(f"Count: {st.session_state.count}")