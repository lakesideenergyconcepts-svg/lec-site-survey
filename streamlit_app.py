import streamlit as st
import pandas as pd

# --- KONFIGURATION ---
st.set_page_config(page_title="LEC Field App", page_icon="⚡")

# --- DUMMY DATENBANK (Simuliert späteres Google Sheet) ---
# Das ist Ihr "Katalog", der später aus der Cloud kommt.
PRODUKT_KATALOG = {
    "Steuerung": [
        {"name": "Shelly Plus 2PM (Rolladen)", "art_nr": "SH-2PM", "preis": 29.90},
        {"name": "Shelly Dimmer 2", "art_nr": "SH-DIM2", "preis": 32.50},
        {"name": "Shelly i4 (Taster-Interface)", "art_nr": "SH-I4", "preis": 18.90},
    ],
    "Netzwerk": [
        {"name": "Keystone Modul CAT6a", "art_nr": "KEY-C6A", "preis": 6.50},
        {"name": "Datendose 2-fach (Leer)", "art_nr": "DD-2F", "preis": 12.00},
        {"name": "Patchpanel 24-Port", "art_nr": "PP-24", "preis": 45.00},
    ],
    "Verteilerbau": [
        {"name": "FI-Schalter 40A/30mA", "art_nr": "RCD-40", "preis": 35.00},
        {"name": "LS-Schalter B16", "art_nr": "LS-B16", "preis": 2.80},
        {"name": "Reihenklemme Phoenix 3-stock", "art_nr": "PH-3S", "preis": 1.90},
    ]
}

# --- SESSION STATE (Das Gedächtnis der App) ---
# Wir müssen die Liste speichern, auch wenn wir klicken.
if 'projekt_liste' not in st.session_state:
    st.session_state.projekt_liste = []

# --- SIDEBAR: PROJEKT DATEN ---
with st.sidebar:
    # Platzhalter Logo (kann später durch Ihr eigenes ersetzt werden)
    st.header("Lakeside Energy Concepts")
    st.subheader("Projekt Metadaten")
    kunde = st.text_input("Kunden Name", "Familie Muster")
    projekt = st.text_input("Projekt / Ort", "Neubau Seestraße")
    
    st.divider()
    # Aktion: Liste löschen
    if st.button("🗑️ Liste leeren"):
        st.session_state.projekt_liste = []
        st.rerun()

# --- HAUPTBEREICH ---
st.title("⚡ LEC Aufmaß-Tool")
st.caption(f"Aktuelles Projekt: {projekt} | Kunde: {kunde}")

# 1. EINGABEBEREICH
with st.container():
    st.markdown("### ➕ Material erfassen")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        # Kategorie wählen
        kategorie = st.selectbox("Kategorie", list(PRODUKT_KATALOG.keys()))
    
    with col2:
        # Produkte basierend auf Kategorie filtern
        produkte_in_kat = [p["name"] for p in PRODUKT_KATALOG[kategorie]]
        produkt_name = st.selectbox("Produkt", produkte_in_kat)
    
    with col3:
        menge = st.number_input("Menge", min_value=1, value=1, step=1)

    # Raum Zuweisung
    raum = st.selectbox("Raum / Ort", ["Wohnzimmer", "Küche", "Technikraum", "Schlafzimmer", "UV Verteiler", "Außenbereich"])

    # Hinzufügen Button
    if st.button("In Liste übernehmen", type="primary"):
        # Preis und Details suchen
        selected_item = next(item for item in PRODUKT_KATALOG[kategorie] if item["name"] == produkt_name)
        
        # Eintrag erstellen
        neuer_eintrag = {
            "Raum": raum,
            "Kategorie": kategorie,
            "Artikel": produkt_name,
            "Art-Nr": selected_item["art_nr"],
            "Menge": menge,
            "Einzelpreis": selected_item["preis"],
            "Gesamtpreis": menge * selected_item["preis"]
        }
        
        # In Session State speichern
        st.session_state.projekt_liste.append(neuer_eintrag)
        st.success(f"{menge}x {produkt_name} für {raum} hinzugefügt!")

# 2. AUSGABEBEREICH (TABELLE)
st.divider()
st.markdown("### 📋 Aktuelle Materialliste")

if st.session_state.projekt_liste:
    # Liste in DataFrame wandeln für schöne Darstellung
    df = pd.DataFrame(st.session_state.projekt_liste)
    
    # Spaltenreihenfolge ordnen
    df = df[["Raum", "Kategorie", "Artikel", "Art-Nr", "Menge", "Einzelpreis", "Gesamtpreis"]]

    # Tabelle anzeigen
    st.dataframe(df, use_container_width=True)
    
    # Summen berechnen
    total_netto = df["Gesamtpreis"].sum()
    total_brutto = total_netto * 1.19
    
    # Kosten Dashboard
    st.markdown("---")
    col_sum1, col_sum2 = st.columns(2)
    col_sum1.metric("Netto Summe", f"{total_netto:.2f} €")
    col_sum2.metric("Brutto (inkl. MwSt)", f"{total_brutto:.2f} €")
    
else:
    st.info("Noch keine Positionen erfasst. Starten Sie oben.")
