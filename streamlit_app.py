import streamlit as st
st.header("🔋 Lakeside Energy Concepts")
st.write("Tablet-Mode: AKTIV")
kunde = st.text_input("Kundenname:")
if st.button("Projekt anlegen"):
st.success(f"Hallo {kunde}, willkommen bei LEC!")
