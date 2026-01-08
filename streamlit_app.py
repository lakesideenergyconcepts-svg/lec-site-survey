import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import graphviz

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

# --- KATALOG & SCHEMATA DATENBANK ---
PRODUKT_KATALOG = {
    "Steuerung": [
        {"name": "Shelly Plus 2PM", "preis": 29.90, "typ": "Rolladen"},
        {"name": "Shelly Dimmer 2", "preis": 32.50, "typ": "Licht"},
        {"name": "Shelly i4", "preis": 18.90, "typ": "Taster"},
    ],
    "Installation": [
        {"name": "Steckdose Gira E2", "preis": 8.50, "typ": "Power"},
        {"name": "Schalter Gira E2", "preis": 12.00, "typ": "Switch"},
    ]
}

# --- FUNKTION: GRUNDRISS PLOTTEN ---
def plot_floorplan(rooms, active_room_idx=None):
    if not rooms: return None
    fig, ax = plt.subplots(figsize=(10, 6))
    max_x, max_y = 0, 0

    for idx, room in enumerate(rooms):
        is_active = (idx == active_room_idx)
        face_col = '#ffcc80' if is_active else '#e3f2fd'
        edge_col = '#e65100' if is_active else '#1f77b4'
        lw = 3 if is_active else 2
        z_order = 10 if is_active else 1
        
        rect = patches.Rectangle((room['x'], room['y']), room['l'], room['b'], 
                                 linewidth=lw, edgecolor=edge_col, facecolor=face_col, alpha=0.9, zorder=z_order)
        ax.add_patch(rect)
        
        cx, cy = room['x'] + room['l']/2, room['y'] + room['b']/2
        label = f"{room['name']}\n{room['l']*room['b']:.1f}m²"
        font_weight = 'bold' if is_active else 'normal'
        ax.text(cx, cy, label, ha='center', va='center', fontsize=9, fontweight=font_weight, zorder=z_order+1)
        
        if room['l'] > 1.0: ax.text(cx, room['y'] + 0.2, f"{room['l']}m", ha='center', va='bottom', fontsize=8, zorder=z_order+1)
        if room['b'] > 1.0: ax.text(room['x'] + 0.2, cy, f"{room['b']}m", ha='left', va='center', rotation=90, fontsize=8, zorder=z_order+1)

        max_x = max(max_x, room['x'] + room['l'])
        max_y = max(max_y, room['y'] + room['b'])

    ax.set_xlim(-1, max(10, max_x + 2)) 
    ax.set_ylim(-1, max(10, max_y + 2))
    ax.set_aspect('equal')
    ax.grid(True, linestyle=':', alpha=0.5)
    return fig

# --- FUNKTION: LOGIK-SCHEMA GENERIEREN ---
def get_wiring_diagram(component_name):
    graph = graphviz.Digraph()
    graph.attr(rankdir='LR', bgcolor='transparent')
    
    # Standard Styles
    graph.attr('node', shape='box', style='rounded,filled', fillcolor='white', fontname='Arial')
    
    if "Shelly Plus 2PM" in component_name:
        graph.node('L', 'L (Phase)', fillcolor='#ffcdd2')
        graph.node('N', 'N (Neutral)', fillcolor='#bbdefb')
        graph.node('S1', 'Schalter Auf')
        graph.node('S2', 'Schalter Ab')
        graph.node('SH', 'Shelly 2PM', fillcolor='#fff9c4', shape='component')
        graph.node('M', 'Rolladen Motor', fillcolor='#e0e0e0')
        
        graph.edge('L', 'SH', label='L')
        graph.edge('N', 'SH', label='N')
        graph.edge('L', 'S1')
        graph.edge('L', 'S2')
        graph.edge('S1', 'SH', label='SW1')
        graph.edge('S2', 'SH', label='SW2')
        graph.edge('SH', 'M', label='O1 (Auf)')
        graph.edge('SH', 'M', label='O2 (Ab)')
        graph.edge('N', 'M')
        
    elif "Shelly Dimmer" in component_name:
        graph.node('L', 'L (Phase)', fillcolor='#ffcdd2')
        graph.node('N', 'N (Neutral)', fillcolor='#bbdefb')
        graph.node('T', 'Taster', shape='circle')
        graph.node('SH', 'Shelly Dimmer 2', fillcolor='#fff9c4', shape='component')
        graph.node('La', 'Lampe (Dimmbar)', shape='circle', fillcolor='#fff176')
        
        graph.edge('L', 'SH', label='L')
        graph.edge('N', 'SH', label='N')
        graph.edge('L', 'T')
        graph.edge('T', 'SH', label='SW1')
        graph.edge('SH', 'La', label='O')
        graph.edge('N', 'La')
        
    else:
        graph.node('Info', f'Kein Schema für {component_name} hinterlegt.')
        
    return graph

# --- MAIN APP ---
st.sidebar.title("LEC Manager")

# Projekt Auswahl
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
        st.session_state.db_projects[new_id] = {"kunde": new_kunde, "ort": new_ort, "status": "Neu", "created": "Heute"}
        st.session_state.db_rooms[new_id] = []
        st.rerun()
else:
    st.session_state.current_project_id = selection

if st.session_state.current_project_id:
    curr_id = st.session_state.current_project_id
    proj_data = st.session_state.db_projects[curr_id]
    
    st.title(f"Projekt: {proj_data['kunde']}")
    
    # TABS
    tab1, tab2, tab3 = st.tabs(["🏗️ Editor", "📦 Material", "🔌 Schemata & Wiki"])
    
    # --- TAB 1: EDITOR ---
    with tab1:
        col_list, col_visual = st.columns([1, 2])
        if curr_id not in st.session_state.db_rooms: st.session_state.db_rooms[curr_id] = []
        rooms = st.session_state.db_rooms[curr_id]
        
        with col_list:
            with st.expander("➕ Neuer Raum"):
                with st.form("new_room_form"):
                    n_name = st.text_input("Name", "Zimmer")
                    c1, c2 = st.columns(2)
                    n_l = c1.number_input("Länge", 4.0)
                    n_b = c2.number_input("Breite", 3.5)
                    n_etage = st.selectbox("Etage", ["KG", "EG", "OG1", "OG2"])
                    if st.form_submit_button("Anlegen"):
                        st.session_state.db_rooms[curr_id].append({"name": n_name, "l": n_l, "b": n_b, "x": 0.0, "y": 0.0, "etage": n_etage})
                        st.rerun()

            if rooms:
                st.divider()
                st.markdown("**Positionieren:**")
                room_labels = [f"{r['name']}" for r in rooms]
                selected_idx = st.radio("Raum wählen", range(len(rooms)), format_func=lambda x: room_labels[x])
                active_room = rooms[selected_idx]
                
                new_x = st.slider("X", -5.0, 25.0, float(active_room['x']), 0.25, key=f"sx_{curr_id}")
                new_y = st.slider("Y", -5.0, 25.0, float(active_room['y']), 0.25, key=f"sy_{curr_id}")
                st.session_state.db_rooms[curr_id][selected_idx]['x'] = new_x
                st.session_state.db_rooms[curr_id][selected_idx]['y'] = new_y
            else:
                selected_idx = None

        with col_visual:
            st.pyplot(plot_floorplan(rooms, active_room_idx=selected_idx))

    # --- TAB 2: MATERIAL ---
    with tab2:
        my_rooms = [r['name'] for r in st.session_state.db_rooms.get(curr_id, [])]
        if my_rooms:
            c1, c2, c3 = st.columns(3)
            r = c1.selectbox("Raum", my_rooms)
            k = c2.selectbox("Kat", list(PRODUKT_KATALOG.keys()))
            i = c3.selectbox("Item", [p['name'] for p in PRODUKT_KATALOG[k]])
            qty = st.number_input("Menge", 1, 100, 1)
            if st.button("Add", type="primary", use_container_width=True):
                p = next(p['preis'] for p in PRODUKT_KATALOG[k] if p['name'] == i)
                st.session_state.db_material.append({"Projekt": curr_id, "Raum": r, "Artikel": i, "Menge": qty, "Preis": p})
            
            proj_mat = [m for m in st.session_state.db_material if m['Projekt'] == curr_id]
            if proj_mat:
                df = pd.DataFrame(proj_mat)
                df['Gesamt'] = df['Menge'] * df['Preis']
                st.dataframe(df[["Raum", "Artikel", "Menge", "Gesamt"]], use_container_width=True)
                st.metric("Total", f"{df['Gesamt'].sum():.2f} €")
        else:
            st.warning("Erst Räume anlegen.")

    # --- TAB 3: SCHEMATA ---
    with tab3:
        st.subheader("Technisches Handbuch & Wiring")
        st.caption("Wählen Sie eine Komponente, um das Anschlussschema zu sehen.")
        
        # 1. Auswahl
        col_select, col_view = st.columns([1, 2])
        
        with col_select:
            # Wir nehmen alle Komponenten aus der Steuerung
            comps = [p['name'] for p in PRODUKT_KATALOG["Steuerung"]]
            selected_comp = st.radio("Komponente wählen", comps)
            
            st.info("💡 Tipp: Diese Schemata werden automatisch generiert.")
        
        with col_view:
            st.markdown(f"### Anschlussplan: {selected_comp}")
            
            # Diagramm holen
            diag = get_wiring_diagram(selected_comp)
            st.graphviz_chart(diag)
            
            # Hier könnten wir später echte Bilder einblenden
            # st.image("https://hersteller-website.com/schema.jpg")
            
            with st.expander("Technische Notizen anzeigen"):
                if "Shelly Plus 2PM" in selected_comp:
                    st.write("""
                    * **Kalibrierung:** Nach Einbau zwingend Rolladen-Kalibrierung via App durchführen.
                    * **Last:** Max 10A pro Kanal, aber bei induktiver Last (Motoren) RC-Snubber empfohlen.
                    """)
                elif "Dimmer" in selected_comp:
                    st.write("""
                    * **Bypass:** Bei < 10W Last (LED) wird ein Bypass benötigt, falls ohne N-Leiter gearbeitet wird.
                    * **Taster:** Funktioniert mit Schalter und Taster (in App konfigurieren).
                    """)

else:
    st.info("Bitte Projekt wählen.")
