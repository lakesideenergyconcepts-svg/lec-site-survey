import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Rescue Mode", page_icon="🚑")
st.title("🚑 Datenbank Reparatur-Kit")

# Verbindung herstellen
conn = st.connection("gsheets", type=GSheetsConnection)

st.write("""
Dieser Modus erzwingt das Schreiben der korrekten Spaltennamen in dein Google Sheet.
Klicke unten auf den Button, um die Struktur neu anzulegen.
""")

if st.button("⚠️ DATENBANK STRUKTUR NEU SCHREIBEN", type="primary"):
    try:
        # 1. PROJEKTE
        df_proj = pd.DataFrame(columns=['id', 'kunde', 'ort', 'bp_width', 'bp_height', 'created_at'])
        # Wir fügen eine Dummy-Zeile ein, damit Google Sheets die Spalten sicher erkennt
        df_proj.loc[0] = ["INIT", "Testkunde", "Testort", 20.0, 15.0, "System"]
        conn.update(worksheet="projekte", data=df_proj)
        st.success("✅ Tabelle 'projekte' repariert!")

        # 2. RAEUME
        df_room = pd.DataFrame(columns=['projekt_id', 'name', 'l', 'b', 'x', 'y'])
        conn.update(worksheet="raeume", data=df_room)
        st.success("✅ Tabelle 'raeume' repariert!")

        # 3. STRINGS
        df_str = pd.DataFrame(columns=['projekt_id', 'id', 'name', 'fuse', 'factor', 'cable_name', 'cable_len', 'cable_price'])
        conn.update(worksheet="strings", data=df_str)
        st.success("✅ Tabelle 'strings' repariert!")

        # 4. INSTALLATION
        df_inst = pd.DataFrame(columns=['projekt_id', 'raum', 'string', 'artikel', 'menge', 'preis', 'watt', 'pos_x', 'pos_y'])
        conn.update(worksheet="installation", data=df_inst)
        st.success("✅ Tabelle 'installation' repariert!")

        st.balloons()
        st.info("Jetzt kannst du den normalen Code (V2.2.1) wieder einfügen!")

    except Exception as e:
        st.error("Es ist immer noch ein Fehler aufgetreten:")
        st.code(str(e))
        st.warning("Checkliste:\n1. Ist der Link in Secrets korrekt?\n2. Hat der Bot 'Editor' Rechte?\n3. Hast du die NEUE json Datei in die Secrets kopiert?")
