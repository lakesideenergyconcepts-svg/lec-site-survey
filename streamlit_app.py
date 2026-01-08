import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import random

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

# --- KATALOG MIT PDF LINKS ---
# Hier hinterlegen wir die Links zu den Datenblättern (Google Drive oder Hersteller)
PRODUKT_KATALOG = {
    "Steuerung": [
        {"name": "Shelly Plus 2PM", "preis": 29.90, "pdf": "https://kb.shelly.cloud/knowledge-base/shelly-plus-2pm"},
        {"name": "Shelly Dimmer 2", "preis": 32.50, "pdf": "https://kb.shelly.cloud/knowledge-base/shelly-dimmer-2"},
        {"name": "Shelly i4", "preis": 18.90, "pdf": "https://kb.shelly.cloud/knowledge-base/shelly-plus-i4"},
    ],
    "Installation": [
        {"name": "Steckdose Gira E2", "preis": 8.50, "pdf": "https://partner.gira.de/data3/01881710.pdf"},
        {"name": "Schalter Gira E2", "preis": 12.00, "pdf": "https://partner.gira.de/data3/01061710.pdf"},
        {"name": "NYM-J 3x1.5 (100m)", "preis": 65.00, "pdf": "https://www.lappkabel.de/"},
    ]
}

# --- FUNKTION: GRUNDRISS MIT GERÄTEN PLOTTEN ---
def plot_installation_map(rooms, materials, active_material_idx=None):
    if not rooms: return None
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 1. Räume zeichnen (Basis-Layer)
    room_centers = {}
    max_x, max_y = 0, 0
    
    for room in rooms:
        # Raum-Rechteck
        rect = patches.Rectangle((room['x'], room['y']), room['l'], room['b'], 
                                 linewidth=2, edgecolor='#90a4ae', facecolor='#eceff1', alpha=0.5, zorder=1)
        ax.add_patch(rect)
        
        # Mittelpunkt speichern für Geräte-Verteilung
        cx, cy = room['x'] + room['l']/2, room['y'] + room['b']/2
        room_centers[room['name']] = (cx, cy)
        
        # Raumname
        ax.text(room['x']+0.2, room['y']+0.2, room['name'], fontsize=8, color='#546e7a', zorder=2, fontweight='bold')
        
        # Grenzen für Plot berechnen
        max_x = max(max_x, room['x'] + room['l'])
        max_y = max(max_y, room['y'] + room['b'])

    # 2. Geräte zeichnen (Device-Layer)
    # Wir verteilen die Geräte leicht zufällig um die Raummitte (Jitter), damit sie nicht übereinander liegen.
    random.seed(42) # Fixer Seed, damit die Punkte beim Neuladen nicht springen

    for idx, mat in enumerate(materials):
        r_name = mat['Raum']
        if r_name in room_centers:
            cx, cy = room_centers[r_name]
            
            # Zufälliger Offset (Simulation der Position im Raum)
            ox = random.uniform(-1.0, 1.0)
            oy = random.uniform(-1.0, 1.0)
            px, py = cx + ox, cy + oy
            
            # Highlight Logik: Wenn ausgewählt -> ROT und GROSS, sonst BLAU und klein
            is_active = (idx == active_material_idx)
            
            color = '#d50000' if is_active else '#2962ff' 
            size = 180 if is_active else 60
            marker = 'P' if "Shelly" in mat['Artikel'] else 'o' # P = Plus (für Smart Home), o = Kreis (Standard)
            alpha = 1.0 if is_active else 0.7
            
            # Punkt zeichnen
            ax.scatter(px, py, c=color, s=size, marker=marker, zorder=5, edgecolors='white', alpha=alpha)
            
            # Label nur zeichnen, wenn aktiv
            if is_active:
                ax.text(px, py+0.4, mat['Artikel'], ha='center', fontsize=9, fontweight='bold', color='#d50000', zorder=6,
                        bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1))

    # Achsen-Setup
    ax.set_xlim(-1, max(10, max_x + 2)) 
    ax.set_ylim(-1, max(10, max_y + 2))
    ax.set_aspect('equal')
    ax.grid(True, linestyle=':', alpha=0.3)
    ax.set_title("Installations-Plan (Interaktiv)", fontsize=14)
    ax.set_xlabel("Meter")
    ax.set_ylabel("Meter")
    
    return fig

# --- SIDEBAR: PROJEKTWAHL ---
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
        new_id = f"P-{len(st.session_state.db_projects)+1:03d}"
        st.session_state.db_projects[new_id] = {"kunde": new_kunde, "ort": new_ort, "status": "Neu", "created": "Heute"}
        st.session_state.db_rooms[new_id] = []
        st.success("Erstellt!")
        st.rerun()
else:
    st.session_state.current_project_id = selection

# --- HAUPTBEREICH ---
if st.session_state.current_project_id:
    curr_id = st.session_state.current_project_id
    proj_data = st.session_state.db_projects[curr_id]
    
    st.title(f"Projekt: {proj_data['kunde']}")
    st.caption(f"ID: {curr_id} | Ort: {proj_data['ort']}")
    
    # TABS DEFINITION
    tab1, tab2, tab3 = st.tabs(["🏗️ Editor", "📦 Material", "📍 Installation (Live)"])
    
    # --- TAB 1: EDITOR (Räume anlegen & schieben) ---
    with tab1:
        col_edit, col_view = st.columns([1, 2])
        if curr_id not in st.session_state.db_rooms: st.session_state.db_rooms[curr_id] = []
        rooms = st.session_state.db_rooms[curr_id]
        
        with col_edit:
            with st.expander("➕ Raum hinzufügen", expanded=False):
                with st.form("new_room"):
                    n_name = st.text_input("Name", "Zimmer")
                    c1, c2 = st.columns(2)
                    n_l = c1.number_input("Länge", 4.0)
                    n_b = c2.number_input("Breite", 3.0)
                    if st.form_submit_button("Speichern"):
                        st.session_state.db_rooms[curr_id].append({"name": n_name, "l": n_l, "b": n_b, "x": 0.0, "y": 0.0, "etage": "EG"})
                        st.rerun()
            
            if rooms:
                st.divider()
                st.write("**Räume verschieben:**")
                r_labels = [r['name'] for r in rooms]
                idx = st.radio("Raum wählen", range(len(rooms)), format_func=lambda x: r_labels[x])
                
                cur = rooms[idx]
                nx = st.slider("X-Pos", -5.0, 25.0, float(cur['x']), 0.25, key=f"sx_{curr_id}")
                ny = st.slider("Y-Pos", -5.0, 25.0, float(cur['y']), 0.25, key=f"sy_{curr_id}")
                st.session_state.db_rooms[curr_id][idx]['x'] = nx
                st.session_state.db_rooms[curr_id][idx]['y'] = ny
            else:
                idx = None

        with col_view:
            # Einfacher Plot ohne Geräte für den Editor
            # Wir nutzen die gleiche Funktion, übergeben aber leere Materialliste
            fig = plot_installation_map(rooms, [], active_material_idx=None)
            if fig: st.pyplot(fig)

    # --- TAB 2: MATERIAL (Erfassung) ---
    with tab2:
        my_rooms = [r['name'] for r in st.session_state.db_rooms.get(curr_id, [])]
        if my_rooms:
            c1, c2, c3 = st.columns(3)
            r = c1.selectbox("Raum", my_rooms)
            k = c2.selectbox("Kategorie", list(PRODUKT_KATALOG.keys()))
            i = c3.selectbox("Artikel", [p['name'] for p in PRODUKT_KATALOG[k]])
            
            if st.button("Hinzufügen", type="primary"):
                p_data = next(p for p in PRODUKT_KATALOG[k] if p['name'] == i)
                st.session_state.db_material.append({
                    "Projekt": curr_id, "Raum": r, "Artikel": i, 
                    "Menge": 1, "Preis": p_data['preis'], "PDF": p_data['pdf']
                })
                st.success("Gespeichert")
            
            # Liste anzeigen
            proj_mat = [m for m in st.session_state.db_material if m['Projekt'] == curr_id]
            if proj_mat:
                st.dataframe(pd.DataFrame(proj_mat)[["Raum", "Artikel", "Preis"]], use_container_width=True)
        else:
            st.warning("Bitte erst Räume im Editor anlegen.")

    # --- TAB 3: INSTALLATION & DOKU (Das neue Feature) ---
    with tab3:
        st.subheader("Geräte-Locator & Dokumentation")
        
        col_map, col_list = st.columns([2, 1])
        
        proj_mat = [m for m in st.session_state.db_material if m['Projekt'] == curr_id]
        rooms = st.session_state.db_rooms.get(curr_id, [])
        
        active_idx = None
        
        with col_list:
            st.markdown("### Komponenten Liste")
            if proj_mat:
                # Interaktive Liste via Radio Buttons
                mat_labels = [f"{m['Artikel']} ({m['Raum']})" for m in proj_mat]
                sel_label = st.radio("Wählen zum Anzeigen:", mat_labels)
                
                # Index finden
                active_idx = mat_labels.index(sel_label)
                active_item = proj_mat[active_idx]
                
                st.divider()
                st.markdown(f"**Gewählt:** {active_item['Artikel']}")
                
                # PDF BUTTON
                if active_item.get('PDF'):
                    st.link_button(f"📄 Datenblatt öffnen", active_item['PDF'], type="primary")
                else:
                    st.info("Kein PDF hinterlegt.")
            else:
                st.info("Keine Komponenten verbaut.")

        with col_map:
            if rooms:
                # Plot mit Highlight des aktiven Geräts
                fig = plot_installation_map(rooms, proj_mat, active_material_idx=active_idx)
                st.pyplot(fig)
            else:
                st.warning("Keine Räume.")

else:
    st.info("Bitte wählen Sie links ein Projekt.")
