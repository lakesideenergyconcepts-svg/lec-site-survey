import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import graphviz
import random

# --- KONFIGURATION ---
st.set_page_config(page_title="LEC Manager", page_icon="⚡", layout="wide")

# --- DATENBANK & STATE ---
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

# NEU: Datenbank für Stromkreise
if 'db_circuits' not in st.session_state:
    # Struktur: { "ProjektID": [ { "id": "F1", "name": "Licht WZ", "kabel": "NYM 3x1.5", "faktor": 1.0 } ] }
    st.session_state.db_circuits = {}

if 'current_project_id' not in st.session_state:
    st.session_state.current_project_id = None

# --- KATALOG (Erweitert um WATT) ---
PRODUKT_KATALOG = {
    "Steuerung": [
        {"name": "Shelly Plus 2PM", "preis": 29.90, "watt": 2, "pdf": "https://kb.shelly.cloud/"},
        {"name": "Shelly Dimmer 2", "preis": 32.50, "watt": 1, "pdf": "https://kb.shelly.cloud/"},
    ],
    "Verbraucher": [
        {"name": "LED Spot 5W", "preis": 15.00, "watt": 5, "pdf": ""},
        {"name": "Steckdose (Pauschallast)", "preis": 8.50, "watt": 200, "pdf": ""}, # Annahme für Steckdose
        {"name": "Rolladen Motor (Standard)", "preis": 45.00, "watt": 150, "pdf": ""},
        {"name": "Waschmaschine", "preis": 0.00, "watt": 2300, "pdf": ""},
    ],
    "Kabel": [
        {"name": "NYM-J 3x1.5", "preis": 0.65},
        {"name": "NYM-J 5x1.5", "preis": 0.95},
        {"name": "NYM-J 3x2.5", "preis": 1.10},
        {"name": "KNX Busleitung", "preis": 0.50},
    ]
}

# --- HELFER: WIRING DIAGRAM (Graphviz) ---
def plot_circuit_graph(circuit, devices):
    dot = graphviz.Digraph()
    dot.attr(rankdir='LR')
    
    # Verteiler & Sicherung
    dot.node('UV', 'Verteiler (UV)', shape='box3d', style='filled', fillcolor='#cfd8dc')
    dot.node('F', f"{circuit['id']}\n{circuit['name']}", shape='component', style='filled', fillcolor='#ffccbc')
    
    # Kabel
    kabel_label = circuit.get('kabel', 'Kabel?')
    dot.edge('UV', 'F')
    
    # Geräte
    prev_node = 'F'
    for idx, dev in enumerate(devices):
        node_id = f"D{idx}"
        label = f"{dev['Artikel']}\n({dev['Raum']})"
        dot.node(node_id, label, shape='box', style='rounded')
        
        # Kette bilden (Reihenschaltung im Diagramm, logisch parallel)
        dot.edge(prev_node, node_id, label=kabel_label if prev_node == 'F' else "")
        prev_node = node_id
        
    return dot

# --- FUNKTION: GRUNDRISS PLOT (Vereinfacht für Übersicht) ---
def plot_simple_map(rooms, materials):
    if not rooms: return None
    fig, ax = plt.subplots(figsize=(8, 5))
    for r in rooms:
        rect = patches.Rectangle((r['x'], r['y']), r['l'], r['b'], fill=False, edgecolor='gray')
        ax.add_patch(rect)
        ax.text(r['x']+r['l']/2, r['y']+r['b']/2, r['name'], ha='center', color='gray')
    
    # Geräte als Punkte
    for m in materials:
        # Finde Raum-Koordinaten
        rm = next((r for r in rooms if r['name'] == m['Raum']), None)
        if rm:
            # Zufallsposition im Raum
            rx = rm['x'] + rm['l']/2 + random.uniform(-0.5, 0.5)
            ry = rm['y'] + rm['b']/2 + random.uniform(-0.5, 0.5)
            
            # Farbe je nach Status (Zugewiesen zu Kreis oder nicht)
            col = 'green' if m.get('circuit_id') else 'red'
            ax.scatter(rx, ry, c=col, s=30)
            
    ax.autoscale()
    ax.set_aspect('equal')
    ax.axis('off')
    return fig

# --- MAIN APP ---
st.sidebar.title("LEC Manager")
project_options = ["Neues Projekt"] + list(st.session_state.db_projects.keys())

def format_func(option):
    if option == "Neues Projekt": return option
    p = st.session_state.db_projects[option]
    return f"{p['kunde']} ({p['ort']})"

selection = st.sidebar.selectbox("Projekt wählen", project_options, format_func=format_func)

if selection == "Neues Projekt":
    st.sidebar.subheader("Neuanlage")
    new_kunde = st.sidebar.text_input("Kunde")
    new_ort = st.sidebar.text_input("Ort")
    if st.sidebar.button("Projekt erstellen", type="primary"):
        new_id = f"P-{len(st.session_state.db_projects)+1:03d}"
        st.session_state.db_projects[new_id] = {"kunde": new_kunde, "ort": new_ort, "status": "Neu"}
        st.session_state.db_rooms[new_id] = []
        st.session_state.db_circuits[new_id] = []
        st.rerun()
else:
    st.session_state.current_project_id = selection

if st.session_state.current_project_id:
    curr_id = st.session_state.current_project_id
    proj_data = st.session_state.db_projects[curr_id]
    
    st.title(f"Projekt: {proj_data['kunde']}")
    
    # TABS
    tab1, tab2, tab3, tab4 = st.tabs(["🏗️ Editor", "📦 Material", "📍 Map", "⚡ Verteiler & Last"])
    
    # --- TAB 1, 2, 3 (Zusammengefasst/Bekannt) ---
    with tab1:
        st.caption("Raum Editor (Siehe vorherige Versionen)")
        if curr_id not in st.session_state.db_rooms: st.session_state.db_rooms[curr_id] = []
        rooms = st.session_state.db_rooms[curr_id]
        with st.expander("Schnell-Raum"):
            n = st.text_input("Name", "Raum X")
            if st.button("Add Room"):
                st.session_state.db_rooms[curr_id].append({"name": n, "l": 4, "b": 4, "x": 0, "y": 0, "etage": "EG"})
                st.rerun()
        st.dataframe(pd.DataFrame(rooms))

    with tab2:
        st.caption("Material Erfassung")
        my_rooms = [r['name'] for r in st.session_state.db_rooms.get(curr_id, [])]
        c1, c2, c3 = st.columns(3)
        if my_rooms:
            r = c1.selectbox("Raum", my_rooms)
            k = c2.selectbox("Kat", list(PRODUKT_KATALOG.keys()))
            i = c3.selectbox("Item", [p['name'] for p in PRODUKT_KATALOG[k]])
            if st.button("Add Item"):
                p_data = next(p for p in PRODUKT_KATALOG[k] if p['name'] == i)
                st.session_state.db_material.append({
                    "Projekt": curr_id, "Raum": r, "Artikel": i, 
                    "Menge": 1, "Watt": p_data.get('watt', 0), # Watt speichern
                    "circuit_id": None # WICHTIG: Noch keinem Kreis zugewiesen
                })
                st.success("OK")
        
        # Liste anzeigen
        proj_mat = [m for m in st.session_state.db_material if m['Projekt'] == curr_id]
        if proj_mat:
            df = pd.DataFrame(proj_mat)
            st.dataframe(df[["Raum", "Artikel", "Watt", "circuit_id"]])

    with tab3:
        st.caption("Grüne Punkte = Zugewiesen, Rote Punkte = Offen")
        proj_mat = [m for m in st.session_state.db_material if m['Projekt'] == curr_id]
        rooms = st.session_state.db_rooms.get(curr_id, [])
        if rooms:
            st.pyplot(plot_simple_map(rooms, proj_mat))

    # --- TAB 4: VERTEILER & LASTBERECHNUNG (NEU) ---
    with tab4:
        st.subheader("Stromkreise & Dimensionierung")
        
        # Sicherstellen dass DB Eintrag existiert
        if curr_id not in st.session_state.db_circuits:
            st.session_state.db_circuits[curr_id] = []
        
        circuits = st.session_state.db_circuits[curr_id]
        
        # SPALTE 1: KREIS VERWALTUNG
        col_mgmt, col_assign = st.columns([1, 2])
        
        with col_mgmt:
            st.markdown("### 1. Sicherung anlegen")
            with st.form("new_circuit"):
                c_id = st.text_input("Kennung (z.B. F1)", "F1")
                c_name = st.text_input("Bezeichnung", "Licht Wohnzimmer")
                c_cable = st.selectbox("Kabel-Typ", [c['name'] for c in PRODUKT_KATALOG['Kabel']])
                if st.form_submit_button("Kreis erstellen"):
                    st.session_state.db_circuits[curr_id].append({
                        "id": c_id, "name": c_name, "kabel": c_cable, "faktor": 1.0
                    })
                    st.rerun()
            
            st.divider()
            st.markdown("### Vorhandene Kreise")
            # Auswahl des aktiven Kreises
            if circuits:
                c_labels = [f"{c['id']} - {c['name']}" for c in circuits]
                sel_c_idx = st.radio("Bearbeiten:", range(len(circuits)), format_func=lambda x: c_labels[x])
                active_circuit = circuits[sel_c_idx]
            else:
                st.warning("Keine Kreise definiert.")
                active_circuit = None

        # SPALTE 2: ZUORDNUNG & LAST
        with col_assign:
            if active_circuit:
                st.markdown(f"### Bearbeite: {active_circuit['id']} ({active_circuit['name']})")
                
                # --- A. GERÄTE ZUORDNEN ---
                st.markdown("#### Geräte zuweisen")
                # Filtere Geräte, die NOCH KEINEN Kreis haben ODER zu DIESEM gehören
                proj_mat = [m for m in st.session_state.db_material if m['Projekt'] == curr_id]
                
                # Multiselect Box bauen
                # Wir brauchen eine Liste von Tupeln (Index, Label) für den State
                available_devices = []
                for idx, m in enumerate(st.session_state.db_material):
                    if m['Projekt'] == curr_id:
                        # Zeige an wenn schon zugewiesen
                        assigned_str = f"[{m['circuit_id']}] " if m['circuit_id'] else "[NEU] "
                        label = f"{assigned_str}{m['Artikel']} ({m['Raum']}) - {m['Watt']}W"
                        
                        # In die Auswahl aufnehmen, wenn frei oder aktueller Kreis
                        if m['circuit_id'] is None or m['circuit_id'] == active_circuit['id']:
                            available_devices.append((idx, label))
                
                # Pre-Selection: Welche sind schon in diesem Kreis?
                current_selection_indices = [idx for idx, m in enumerate(st.session_state.db_material) 
                                             if m['Projekt'] == curr_id and m['circuit_id'] == active_circuit['id']]
                
                # Widget
                options = [x[0] for x in available_devices]
                labels = [x[1] for x in available_devices]
                
                selected_indices = st.multiselect(
                    "
