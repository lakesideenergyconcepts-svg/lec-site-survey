import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- KONFIGURATION ---
st.set_page_config(page_title="LEC Manager", page_icon="⚡", layout="wide")

# --- SIMULIERTE DATENBANK (Backend) ---
# Hier werden später die Daten aus Google Sheets geladen.
# Aktuell halten wir sie im Speicher, damit die App sofort funktioniert.

if 'db_projects' not in st.session_state:
    st.session_state.db_projects = {
        "P-001": {"kunde": "Müller", "ort": "Friedrichshafen", "status": "In Planung", "created": "2025-01-08"},
        "P-002": {"kunde": "Bäckerei Weck", "ort": "Tettnang", "status": "Ausführung", "created": "2025-01-10"}
    }

if 'db_rooms' not in st.session_state:
    # Struktur: ProjektID -> Liste der Räume
    # Beispiel: P-001 hat Wohnzimmer und Küche
    st.session_state.db_rooms = {
        "P-001": [
            {"name": "Wohnzimmer", "l": 5.0, "b": 4.0, "x": 0, "y": 0, "etage": "EG"},
            {"name": "Küche", "l": 3.0, "b": 4.0, "x": 5, "y": 0, "etage": "EG"}
        ]
    }

if 'db_material' not in st.session_state:
    st.session_state.db_material = []

if 'current_project_id' not in st.session_state:
    st.session_state.current_project_id = None

# --- KATALOG (Simuliert) ---
PRODUKT_KATALOG = {
    "Steuerung": [
        {"name": "Shelly Plus 2PM", "preis": 29.90},
        {"name": "Shelly Dimmer 2", "preis": 32.50},
        {"name": "Shelly i4", "preis": 18.90},
    ],
    "Installation": [
        {"name": "Steckdose Gira E2", "preis": 8.50},
        {"name": "Schalter Gira E2", "preis": 12.00},
        {"name": "NYM-J 3x1.5 (100m)", "preis": 65.00},
        {"name": "Keystone Modul", "preis": 6.50},
    ],
    "Verteiler": [
        {"name": "FI-Schalter 40A", "preis": 35.00},
        {"name": "LS-Schalter B16", "preis": 2.80},
    ]
}

# --- FUNKTION: GRUNDRISS ZEICHNEN ---
def plot_floorplan(rooms):
    if not rooms:
        return None
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Automatische Skalierung der Achsen berechnen
    max_x = 0
    max_y = 0

    for room in rooms:
        # Rechteck zeichnen
        rect = patches.Rectangle((room['x'], room['y']), room['l'], room['b'], 
                                 linewidth=2, edgecolor='#1f77b4', facecolor='#e3f2fd', alpha=0.9)
        ax.add_patch(rect)
        
        # Text Label (Raumname + m²)
        cx = room['x'] + room['l']/2
        cy = room['y'] + room['b']/2
        
        # Schriftgröße an Raumgröße anpassen (einfache Logik)
        fontsize = 8 if room['l'] < 2 or room['b'] < 2 else 10
        
        ax.text(cx, cy, f"{room['name']}\n{room['l']*room['b']:.1f}m²", 
                ha='center', va='center', fontsize=fontsize, color='#0d47a1', fontweight='bold')

        # Maxima für Plot-Grenzen aktualisieren
        max_x = max(max_x, room['x'] + room['l'])
        max_y = max(max_y, room['y'] + room['b'])

    # Plot Grenzen setzen (mit etwas Rand)
    ax.set_xlim(-1, max_x + 2) 
    ax.set_ylim(-1, max_y + 2)
    ax.set_aspect('equal')
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.set_title("Schematischer Grundriss", fontsize=14)
    ax.set_xlabel("Meter")
    ax.set_ylabel("Meter")
    
    return fig

# --- SIDEBAR: NAVIGATION ---
st.sidebar.title("LEC Manager")

# Projekt Auswahl Logik
project_options = ["Neues Projekt"] + list(st.session_state.db_projects.keys())

# Formatierung für Dropdown (zeigt Kunde statt ID)
def format_func(option):
    if option == "Neues Projekt": return option
    p = st.session_state.db_projects[option]
    return f"{p['kunde']} ({p['ort']})"

selection = st.sidebar.selectbox("Projekt wählen", project_options, format_func=format_func)

if selection == "Neues Projekt":
    st.sidebar.divider()
    st.sidebar.subheader("Neuanlage")
    new_kunde = st.sidebar.text_input("Kunde")
    new_ort = st.sidebar.text_input("Ort")
    
    if st.sidebar.button("Projekt erstellen", type="primary"):
        if new_kunde and new_ort:
            new_id = f"P-{len(st.session_state.db_projects)+1:03d}"
            st.session_state.db_projects[new_id] = {"kunde": new_kunde, "ort": new_ort, "status": "Neu", "created": "Heute"}
            st.session_state.db_rooms[new_id] = [] # Leere Raumliste für neues Projekt
            st.success(f"Projekt {new_id} erstellt!")
            st.rerun()
        else:
            st.sidebar.error("Bitte Kunde und Ort angeben.")
else:
    st.session_state.current_project_id = selection

# --- HAUPTBEREICH (MAIN) ---
if st.session_state.current_project_id:
    curr_id = st.session_state.current_project_id
    proj_data = st.session_state.db_projects[curr_id]
    
    st.title(f"Projekt: {proj_data['kunde']}")
    st.caption(f"ID: {curr_id} | Ort: {proj_data['ort']} | Status: {proj_data['status']}")
    
    # TABS FÜR WORKFLOW
    tab1, tab2, tab3 = st.tabs(["🏗️ Gebäude & Räume", "📦 Material & Mengen", "📄 Dokumentation"])
    
    # --- TAB 1: GEBÄUDE STRUKTUR ---
    with tab1:
        col_input, col_grafik = st.columns([1, 2])
        
        with col_input:
            st.subheader("Raum definieren")
            with st.form("room_form"):
                r_name = st.text_input("Raumbezeichnung", "Büro")
                r_etage = st.selectbox("Etage", ["KG", "EG", "OG1", "OG2", "DG"])
                
                c1, c2 = st.columns(2)
                r_l = c1.number_input("Länge (m)", 0.0, 50.0, 4.0)
                r_b = c2.number_input("Breite (m)", 0.0, 50.0, 3.5)
                
                st.markdown("**Position im Plan (X/Y)**")
                c3, c4 = st.columns(2)
                r_x = c3.number_input("X-Pos", 0.0, 100.0, 0.0, step=1.0)
                r_y = c4.number_input("Y-Pos", 0.0, 100.0, 0.0, step=1.0)
                
                submitted = st.form_submit_button("Raum hinzufügen")
                
                if submitted:
                    new_room = {"name": r_name, "l": r_l, "b": r_b, "x": r_x, "y": r_y, "etage": r_etage}
                    # Sicherstellen, dass die Liste existiert
                    if curr_id not in st.session_state.db_rooms:
                        st.session_state.db_rooms[curr_id] = []
                    
                    st.session_state.db_rooms[curr_id].append(new_room)
                    st.success("Gespeichert")
                    st.rerun()
                
            st.divider()
            st.markdown("##### Raumliste")
            if curr_id in st.session_state.db_rooms:
                for idx, r in enumerate(st.session_state.db_rooms[curr_id]):
                    st.text(f"{idx+1}. {r['name']} ({r['etage']}): {r['l']}x{r['b']}m")

        with col_grafik:
            st.subheader("Grundriss Visualisierung")
            rooms = st.session_state.db_rooms.get(curr_id, [])
            
            if rooms:
                # Filteroptionen
                all_etagen = list(set([r['etage'] for r in rooms]))
                filter_etage = st.radio("Etage anzeigen", ["Alle"] + sorted(all_etagen), horizontal=True)
                
                rooms_to_plot = rooms if filter_etage == "Alle" else [r for r in rooms if r['etage'] == filter_etage]
                
                fig = plot_floorplan(rooms_to_plot)
                if fig:
                    st.pyplot(fig)
            else:
                st.info("Noch keine Räume definiert. Starten Sie links.")

    # --- TAB 2: MATERIAL ---
    with tab2:
        st.subheader("Massenermittlung")
        
        # Prüfen ob Räume da sind
        my_rooms = [r['name'] for r in st.session_state.db_rooms.get(curr_id, [])]
        
        if not my_rooms:
            st.warning("⚠️ Bitte erst Räume in Tab 1 anlegen!")
        else:
            col_mat1, col_mat2, col_mat3 = st.columns([1, 1, 1])
            
            with col_mat1:
                target_room = st.selectbox("Raum wählen", my_rooms)
            with col_mat2:
                cat = st.selectbox("Gewerk", list(PRODUKT_KATALOG.keys()))
            with col_mat3:
                # Dynamische Artikelliste
                item_name = st.selectbox("Artikel", [p['name'] for p in PRODUKT_KATALOG[cat]])
            
            col_qty, col_btn = st.columns([1, 1])
            with col_qty:
                amount = st.number_input("Menge", 1, 500, 1)
            with col_btn:
                st.write("") # Spacer
                st.write("") # Spacer
                if st.button("Hinzufügen", type="primary", use_container_width=True):
                    # Preis suchen
                    price = next(p['preis'] for p in PRODUKT_KATALOG[cat] if p['name'] == item_name)
                    st.session_state.db_material.append({
                        "Projekt": curr_id,
                        "Raum": target_room,
                        "Artikel": item_name,
                        "Menge": amount,
                        "Preis": price
                    })
                    st.success("Gebucht!")
            
            st.divider()
            
            # Tabelle zeigen (nur für dieses Projekt)
            proj_mat = [m for m in st.session_state.db_material if m['Projekt'] == curr_id]
            
            if proj_mat:
                df = pd.DataFrame(proj_mat)
                df['Gesamt'] = df['Menge'] * df['Preis']
                
                # Schöne Tabelle
                st.dataframe(
                    df[["Raum", "Artikel", "Menge", "Preis", "Gesamt"]], 
                    use_container_width=True,
                    column_config={
                        "Preis": st.column_config.NumberColumn(format="%.2f €"),
                        "Gesamt": st.column_config.NumberColumn(format="%.2f €")
                    }
                )
                
                # Summen
                total = df['Gesamt'].sum()
                st.metric("Projekt Summe (Netto)", f"{total:.2f} €")
            else:
                st.info("Noch kein Material erfasst.")

    # --- TAB 3: DOKUMENTATION ---
    with tab3:
        st.write("Hier entsteht der PDF Export und Rechnungsdruck.")
        st.info("Feature in Entwicklung: PDF Generierung mit ReportLab")

else:
    # Begrüßungsbildschirm wenn kein Projekt gewählt
    st.title("Willkommen bei LEC Manager ⚡")
    st.info("Bitte wählen Sie links ein Projekt aus oder erstellen Sie ein neues.")