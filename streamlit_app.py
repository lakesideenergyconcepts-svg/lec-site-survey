import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- KONFIGURATION ---
st.set_page_config(page_title="LEC Manager", page_icon="⚡", layout="wide")

# --- SIMULIERTE DATENBANK (Backend) ---
if 'db_projects' not in st.session_state:
    st.session_state.db_projects = {
        "P-001": {"kunde": "Müller", "ort": "Friedrichshafen", "status": "In Planung", "created": "2025-01-08"},
    }

if 'db_rooms' not in st.session_state:
    st.session_state.db_rooms = {
        "P-001": [
            {"name": "Wohnzimmer", "l": 5.0, "b": 4.0, "x": 0.0, "y": 0.0, "etage": "EG"},
            {"name": "Küche", "l": 3.0, "b": 4.0, "x": 5.0, "y": 0.0, "etage": "EG"}
        ]
    }

if 'db_material' not in st.session_state:
    st.session_state.db_material = []

if 'current_project_id' not in st.session_state:
    st.session_state.current_project_id = None

# --- KATALOG ---
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
        {"name": "Datendose 2-fach", "preis": 12.00},
    ],
    "Verteiler": [
        {"name": "FI-Schalter 40A", "preis": 35.00},
        {"name": "LS-Schalter B16", "preis": 2.80},
        {"name": "Reihenklemme Phoenix", "preis": 1.90},
    ]
}

# --- FUNKTION: GRUNDRISS PLOTTEN ---
def plot_floorplan(rooms, active_room_idx=None):
    if not rooms: return None
    
    # Figure Setup
    fig, ax = plt.subplots(figsize=(10, 6))
    
    max_x = 0
    max_y = 0

    for idx, room in enumerate(rooms):
        # Logic: Aktiver Raum (der gerade bearbeitet wird) ist ORANGE
        is_active = (idx == active_room_idx)
        face_col = '#ffcc80' if is_active else '#e3f2fd' # Orange vs Blau
        edge_col = '#e65100' if is_active else '#1f77b4'
        lw = 3 if is_active else 2
        z_order = 10 if is_active else 1
        
        # Rechteck zeichnen
        rect = patches.Rectangle((room['x'], room['y']), room['l'], room['b'], 
                                 linewidth=lw, edgecolor=edge_col, facecolor=face_col, alpha=0.9, zorder=z_order)
        ax.add_patch(rect)
        
        # Text Label (Mitte des Raums)
        cx = room['x'] + room['l']/2
        cy = room['y'] + room['b']/2
        
        label = f"{room['name']}\n{room['l']*room['b']:.1f}m²"
        font_weight = 'bold' if is_active else 'normal'
        ax.text(cx, cy, label, ha='center', va='center', fontsize=9, fontweight=font_weight, zorder=z_order+1)
        
        # Bemaßung (Länge unten, Breite links) - Nur wenn Raum groß genug
        if room['l'] > 1.0:
            ax.text(cx, room['y'] + 0.2, f"{room['l']}m", ha='center', va='bottom', fontsize=8, zorder=z_order+1)
        if room['b'] > 1.0:
            ax.text(room['x'] + 0.2, cy, f"{room['b']}m", ha='left', va='center', rotation=90, fontsize=8, zorder=z_order+1)

        # Plot Grenzen ermitteln
        max_x = max(max_x, room['x'] + room['l'])
        max_y = max(max_y, room['y'] + room['b'])

    # Achsen konfigurieren
    ax.set_xlim(-1, max(10, max_x + 2)) 
    ax.set_ylim(-1, max(10, max_y + 2))
    ax.set_aspect('equal')
    ax.grid(True, linestyle=':', alpha=0.5)
    ax.set_title("Grundriss Übersicht (Aktiver Raum hervorgehoben)", fontsize=14)
    ax.set_xlabel("Meter")
    ax.set_ylabel("Meter")
    
    return fig

# --- SIDEBAR: PROJEKTAUSWAHL ---
st.sidebar.title("LEC Manager")

project_options = ["Neues Projekt"] + list(st.session_state.db_projects.keys())

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
        if new_kunde:
            new_id = f"P-{len(st.session_state.db_projects)+1:03d}"
            st.session_state.db_projects[new_id] = {"kunde": new_kunde, "ort": new_ort, "status": "Neu", "created": "Heute"}
            st.session_state.db_rooms[new_id] = []
            st.success(f"Projekt {new_id} erstellt!")
            st.rerun()
else:
    st.session_state.current_project_id = selection

# --- HAUPTBEREICH ---
if st.session_state.current_project_id:
    curr_id = st.session_state.current_project_id
    proj_data = st.session_state.db_projects[curr_id]
    
    st.title(f"Projekt: {proj_data['kunde']}")
    st.caption(f"ID: {curr_id} | Ort: {proj_data['ort']}")
    
    # TABS
    tab1, tab2, tab3 = st.tabs(["🏗️ Editor & Grundriss", "📦 Material & Mengen", "📄 Doku"])
    
    # --- TAB 1: VISUELLER EDITOR ---
    with tab1:
        col_list, col_visual = st.columns([1, 2])
        
        # Daten laden
        if curr_id not in st.session_state.db_rooms:
            st.session_state.db_rooms[curr_id] = []
        rooms = st.session_state.db_rooms[curr_id]
        
        with col_list:
            # 1. NEUEN RAUM ERSTELLEN
            with st.expander("➕ Neuen Raum hinzufügen", expanded=False):
                with st.form("new_room_form"):
                    n_name = st.text_input("Bezeichnung", "Zimmer")
                    c1, c2 = st.columns(2)
                    n_l = c1.number_input("Länge", value=4.0, step=0.1)
                    n_b = c2.number_input("Breite", value=3.5, step=0.1)
                    n_etage = st.selectbox("Etage", ["KG", "EG", "OG1", "OG2", "DG"])
                    
                    if st.form_submit_button("Raum anlegen"):
                        st.session_state.db_rooms[curr_id].append(
                            {"name": n_name, "l": n_l, "b": n_b, "x": 0.0, "y": 0.0, "etage": n_etage}
                        )
                        st.rerun()

            st.divider()
            
            # 2. RÄUME BEARBEITEN (POSITIONIEREN)
            st.subheader("Raum Positionieren")
            
            if rooms:
                # Raumauswahl per Radio Button (dient als "Selektor")
                room_labels = [f"{r['name']} ({r['etage']})" for r in rooms]
                selected_idx = st.radio("Welchen Raum verschieben?", range(len(rooms)), format_func=lambda x: room_labels[x])
                
                active_room = rooms[selected_idx]
                
                # --- SCHIEBEREGLER MIT 0.25m SCHRITTEN ---
                st.markdown("##### Verschieben (X / Y)")
                
                # Slider X
                new_x = st.slider(
                    "X-Achse (Links/Rechts)", 
                    min_value=-5.0, max_value=25.0, 
                    value=float(active_room['x']), 
                    step=0.25,  # <--- HIER IST DIE ÄNDERUNG
                    key=f"slider_x_{curr_id}" # Key reset bei Projektwechsel
                )
                
                # Slider Y
                new_y = st.slider(
                    "Y-Achse (Oben/Unten)", 
                    min_value=-5.0, max_value=25.0, 
                    value=float(active_room['y']), 
                    step=0.25,  # <--- HIER IST DIE ÄNDERUNG
                    key=f"slider_y_{curr_id}"
                )
                
                # Update Database
                st.session_state.db_rooms[curr_id][selected_idx]['x'] = new_x
                st.session_state.db_rooms[curr_id][selected_idx]['y'] = new_y
                
                st.info(f"Position: X={new_x}m / Y={new_y}m")
                
            else:
                st.warning("Noch keine Räume angelegt.")
                selected_idx = None

        with col_visual:
            st.subheader("Grundriss Vorschau")
            # Wir übergeben den Index für das Highlighting
            fig = plot_floorplan(rooms, active_room_idx=selected_idx)
            if fig:
                st.pyplot(fig)

    # --- TAB 2: MATERIAL ---
    with tab2:
        st.subheader("Material Erfassung")
        
        my_rooms = [r['name'] for r in st.session_state.db_rooms.get(curr_id, [])]
        
        if not my_rooms:
            st.warning("⚠️ Bitte legen Sie zuerst Räume im Tab 'Editor' an.")
        else:
            # Eingabezeile
            c_room, c_cat, c_item = st.columns([1, 1, 1])
            with c_room: target_room = st.selectbox("Raum", my_rooms)
            with c_cat: cat = st.selectbox("Kategorie", list(PRODUKT_KATALOG.keys()))
            with c_item: item_name = st.selectbox("Artikel", [p['name'] for p in PRODUKT_KATALOG[cat]])
            
            c_qty, c_add = st.columns([1, 1])
            with c_qty: qty = st.number_input("Menge", 1, 100, 1)
            with c_add: 
                st.write("") # Spacer
                st.write("") # Spacer
                if st.button("Hinzufügen", type="primary", use_container_width=True):
                    price = next(p['preis'] for p in PRODUKT_KATALOG[cat] if p['name'] == item_name)
                    st.session_state.db_material.append({
                        "Projekt": curr_id, "Raum": target_room, 
                        "Artikel": item_name, "Menge": qty, "Preis": price
                    })
                    st.success("Gespeichert!")

            st.divider()
            
            # Tabelle & Auswertung
            proj_mat = [m for m in st.session_state.db_material if m['Projekt'] == curr_id]
            if proj_mat:
                df = pd.DataFrame(proj_mat)
                df['Gesamt'] = df['Menge'] * df['Preis']
                
                st.dataframe(
                    df[["Raum", "Artikel", "Menge", "Preis", "Gesamt"]],
                    use_container_width=True,
                    column_config={"Preis": st.column_config.NumberColumn(format="%.2f €"), "Gesamt": st.column_config.NumberColumn(format="%.2f €")}
                )
                
                st.metric("Projekt Summe (Netto)", f"{df['Gesamt'].sum():.2f} €")
            else:
                st.info("Noch kein Material für dieses Projekt erfasst.")

    # --- TAB 3: DOKU ---
    with tab3:
        st.info("Feature in Arbeit: PDF Export und Angebotserstellung.")

else:
    st.title("LEC Manager")
    st.info("Bitte wählen Sie links ein Projekt aus.")
