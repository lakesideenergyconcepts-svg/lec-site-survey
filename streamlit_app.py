import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- KONFIGURATION ---
st.set_page_config(page_title="LEC Manager", page_icon="⚡", layout="wide")

# --- SIMULIERTE DATENBANK ---
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
    ],
    "Installation": [
        {"name": "Steckdose Gira E2", "preis": 8.50},
        {"name": "Schalter Gira E2", "preis": 12.00},
        {"name": "NYM-J 3x1.5 (100m)", "preis": 65.00},
    ]
}

# --- FUNKTION: PLOT ---
def plot_floorplan(rooms, active_room_idx=None):
    if not rooms: return None
    
    # Figure etwas größer für Tablet
    fig, ax = plt.subplots(figsize=(10, 6))
    
    max_x = 0
    max_y = 0

    for idx, room in enumerate(rooms):
        # Farbe: Aktiver Raum wird hervorgehoben (Orange), andere Blau
        is_active = (idx == active_room_idx)
        face_col = '#ffcc80' if is_active else '#e3f2fd'
        edge_col = '#e65100' if is_active else '#1f77b4'
        lw = 3 if is_active else 2
        
        # Rechteck
        rect = patches.Rectangle((room['x'], room['y']), room['l'], room['b'], 
                                 linewidth=lw, edgecolor=edge_col, facecolor=face_col, alpha=0.9)
        ax.add_patch(rect)
        
        cx = room['x'] + room['l']/2
        cy = room['y'] + room['b']/2
        
        # Text
        label = f"{room['name']}\n{room['l']*room['b']:.1f}m²"
        ax.text(cx, cy, label, ha='center', va='center', fontsize=9, fontweight='bold')
        
        # Bemaßung nur wenn Platz ist
        if room['l'] > 1.0:
            ax.text(cx, room['y'] + 0.2, f"{room['l']}m", ha='center', va='bottom', fontsize=8)
        if room['b'] > 1.0:
            ax.text(room['x'] + 0.2, cy, f"{room['b']}m", ha='left', va='center', rotation=90, fontsize=8)

        max_x = max(max_x, room['x'] + room['l'])
        max_y = max(max_y, room['y'] + room['b'])

    ax.set_xlim(-1, max(10, max_x + 2)) 
    ax.set_ylim(-1, max(10, max_y + 2))
    ax.set_aspect('equal')
    ax.grid(True, linestyle=':', alpha=0.5)
    ax.set_title("Grundriss (Aktiver Raum orange markiert)")
    
    return fig

# --- SIDEBAR ---
st.sidebar.title("LEC Manager")
project_options = ["Neues Projekt"] + list(st.session_state.db_projects.keys())

def format_func(option):
    if option == "Neues Projekt": return option
    p = st.session_state.db_projects[option]
    return f"{p['kunde']} ({p['ort']})"

selection = st.sidebar.selectbox("Projekt wählen", project_options, format_func=format_func)

if selection == "Neues Projekt":
    st.sidebar.info("Bitte legen Sie ein neues Projekt an.")
    # (Abgekürzt für diesen Code-Block, Logik bleibt wie vorher)
else:
    st.session_state.current_project_id = selection

# --- MAIN ---
if st.session_state.current_project_id:
    curr_id = st.session_state.current_project_id
    proj_data = st.session_state.db_projects[curr_id]
    
    st.title(f"Projekt: {proj_data['kunde']}")
    
    tab1, tab2 = st.tabs(["🏗️ Editor & Grundriss", "📦 Material"])
    
    # --- TAB 1: INTERAKTIVER EDITOR ---
    with tab1:
        col_list, col_visual = st.columns([1, 2])
        
        # Sicherstellen, dass Raumliste existiert
        if curr_id not in st.session_state.db_rooms:
            st.session_state.db_rooms[curr_id] = []
        
        rooms = st.session_state.db_rooms[curr_id]
        
        with col_list:
            st.subheader("1. Raum wählen")
            
            # Button zum Erstellen eines NEUEN Raums
            with st.expander("➕ Neuen Raum anlegen", expanded=False):
                with st.form("new_room"):
                    n_name = st.text_input("Name", "Zimmer")
                    n_l = st.number_input("Länge", value=4.0)
                    n_b = st.number_input("Breite", value=3.0)
                    n_etage = st.selectbox("Etage", ["EG", "OG", "KG"])
                    if st.form_submit_button("Anlegen"):
                        st.session_state.db_rooms[curr_id].append(
                            {"name": n_name, "l": n_l, "b": n_b, "x": 0.0, "y": 0.0, "etage": n_etage}
                        )
                        st.rerun()

            st.divider()
            st.write("**Vorhandene Räume bearbeiten:**")
            
            # Radio Button Liste um den "Aktiven" Raum zu wählen
            if rooms:
                room_names = [f"{r['name']} ({r['etage']})" for r in rooms]
                selected_idx = st.radio("Raum zum Verschieben wählen:", range(len(rooms)), format_func=lambda x: room_names[x])
                
                # --- DER LIVE SCHIEBEREGLER ---
                st.markdown("### ✥ Positionieren")
                active_room = rooms[selected_idx]
                
                # Slider für X und Y (Live Update!)
                # Wir nutzen session_state key, damit es persistiert
                
                new_x = st.slider("X-Position (Links/Rechts)", -5.0, 20.0, float(active_room['x']), step=0.5, key=f"pos_x_{selected_idx}")
                new_y = st.slider("Y-Position (Oben/Unten)", -5.0, 20.0, float(active_room['y']), step=0.5, key=f"pos_y_{selected_idx}")
                
                # Update Database immediately
                st.session_state.db_rooms[curr_id][selected_idx]['x'] = new_x
                st.session_state.db_rooms[curr_id][selected_idx]['y'] = new_y
                
                st.info(f"Raum liegt bei: X={new_x} / Y={new_y}")
                
            else:
                st.warning("Keine Räume vorhanden.")
                selected_idx = None

        with col_visual:
            st.subheader("Grundriss Vorschau")
            # Wir übergeben den Index des aktiven Raums zum Highlighten
            fig = plot_floorplan(rooms, active_room_idx=selected_idx)
            if fig:
                st.pyplot(fig)

    # --- TAB 2: MATERIAL (Kurzfassung) ---
    with tab2:
        st.write("Material-Erfassung wie gehabt...")
        # (Hier würde der Material-Code stehen, den wir schon haben)

else:
    st.info("Bitte Projekt wählen.")
