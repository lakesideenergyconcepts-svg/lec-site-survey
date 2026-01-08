import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("🔍 Datenbank-Diagnose")

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    st.info("Versuche Verbindung herzustellen...")
    
    # Wir lesen KEINE Daten, sondern fragen nur nach den Metadaten (Namen der Blätter)
    # Da die Library keine direkte "list_worksheets" Methode einfach exponiert,
    # probieren wir, das erste Blatt ohne Parameter zu lesen.
    df = conn.read() 
    
    st.success("✅ Verbindung erfolgreich!")
    st.write("Ich sehe folgende Daten (Erstes Blatt):")
    st.dataframe(df.head())
    
except Exception as e:
    st.error("❌ Es knallt immer noch.")
    st.code(str(e))
    
    st.warning("Checkliste:")
    st.markdown("""
    1. Ist der Link in `secrets.toml` korrekt? (Fängt an mit `https://docs.google.com/spreadsheets/d/...`)
    2. Hat der Bot ('streamlit-bot@...') **Editor**-Rechte im Sheet?
    3. Gibt es überhaupt Tabellenblätter?
    """)
