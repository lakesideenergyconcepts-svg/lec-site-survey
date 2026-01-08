import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import graphviz
import random

# --- 1. KONFIGURATION ---
st.set_page_config(page_title="LEC Manager", page_icon="⚡", layout="wide")

# --- 2. SESSION STATE (DATENBANK) ---
if 'db_projects' not in st.session_state:
    st.session_state.db_projects = {
        "P-001": {"kunde": "Müller", "ort": "Friedrichshafen", "status": "In Planung"},
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

if 'db_strings' not in st.session_state:
    st.session_state.db_strings = {
        "P-001": [
            {"id": "S1", "name": "Steckdosen Küche", "fuse": 16, "factor": 0.7},
            {"id": "S2", "name": "Licht Allgemein", "fuse": 10, "factor": 1.0}
        ]
    }

if 'current_project_id' not in st.session_state:
    st.session_state.current_project_id = None

# --- 3. PRODUKT KATALOG ---
PRODUKT_KATALOG = {
    "Steuerung": [
        {"name": "Shelly Plus 2PM", "preis": 29.90, "watt": 1, "pdf": "https://kb.shelly.cloud/"},
        {"name": "Shelly Dimmer 2", "preis": 32.50, "watt": 1, "pdf": "https://kb.shelly.cloud/"},
    ],
    "Verbraucher (Last)": [
        {"name": "Steckdose (Standard)", "preis": 8.50, "watt": 200, "pdf": ""},
        {"name": "Steckdose (Waschmaschine)", "preis": 8.50, "watt": 2500, "pdf": ""},
        {"name": "Steckdose (Backofen)", "preis": 12.00, "watt": 3000, "pdf": ""},
        {"name": "Steckdose (Induktionsfeld)", "preis": 12.00, "watt": 7000, "pdf": ""},
        {"name": "LED Deckenspot", "preis": 25.00, "watt": 7, "pdf": ""},
    ],
    "Infrastruktur": [
        {"name": "NYM-J 3x1.5 (100m)", "preis": 65.00, "watt": 0, "pdf": ""},
        {"name": "NYM-J 5x1.5 (50m)", "preis": 85.00, "watt": 0, "pdf": ""},
    ]
}

# --- 4. FUNKTIONEN (PLOTTING) ---

def plot_electrical_tree(strings, materials):
    """Zeichnet den Verteiler-Stammbaum mit Graphviz"""
    dot = graphviz.Digraph(comment='Verteilerplan')
    dot.attr(rankdir='TB')
    dot.attr('node', fontname='Arial')
    
    # Hauptverteiler
    dot.node('UV', '⚡ Hauptverteiler (UV)', shape='doubleoctagon', style='filled', fillcolor='#ffeb3b')

    for s in strings:
        s_id = s['id']
        
        # Lastberechnung
        connected_mats = [m for m in materials if m.get('String') == s_id]
        total_watt = sum([m.get('Watt', 0) * m['Menge'] for m in connected_mats])
        real_load = total_watt * s['factor']
        
        # Überlast-Check
        max_watt = s['fuse'] * 230
        load_percent = (real_load / max_watt) * 100 if max_watt > 0 else 0
        
        # Farben
        color = '#c8e6c9' # Grün
        warn_text = ""
        if load_percent > 80: color = '#fff9c4' # Gelb
        if load_percent > 100: 
            color = '#ffcdd2' # Rot
            warn_text = "\n⚠️ ÜBERLAST"
        
        label = f"{s['name']}\n{s['fuse']}A | Faktor: {s['factor']}\nLast: {real_load:.0f}W{warn_text}"
        dot.node(s_id, label, shape='folder', style='filled', fillcolor=color)
        dot.edge('UV', s_id)
        
        # Geräte gruppieren
        grouped_items = {}
        for m in connected_mats:
            name = m['Artikel']
            if name not in grouped_items: grouped_items[name] = {"menge": 0, "watt": m.get('Watt', 0)}
            grouped_items[name]["menge"] += m['Menge']
            
        for item_name, data in grouped_items.items():
            node_id = f"{s_id}_{item_name}"
            m_label = f"{data['menge']}x {item_name}\n({data['watt']*data['menge']}W)"
            dot.node(node_id, m_label, shape='note', fontsize='9')
            dot.edge(s_id, node_id)
            
    return dot

def plot_room_map(rooms):
    """Zeichnet die einfache Raumkarte mit Matplotlib"""
    fig, ax = plt.subplots(figsize=(8, 5))
    for idx, r in enumerate(rooms):
        rect = patches.Rectangle((r['x'], r['y']), r['l'], r['b'], linewidth=2, edgecolor='#1f77b4', facecolor='#e3f2fd', alpha=0.5)
        ax.add_patch(rect)
        ax.text(r['x']+r['l']/2, r['y']+r['b']/2, r['name'], ha='center', fontweight='bold')
    
    ax.set_xlim(-2, 20)
    ax.set_ylim(-2, 20)
    ax.set_aspect('equal')
    ax.grid(True, linestyle=':')
    ax.set_title("Gebäudeübersicht")
    return fig

# --- 5. SIDEBAR ---
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
        st.session_state.db_strings[new_id] = []
        st.success("Erstellt!")
        st.rerun()
else:
    st.session_state.current_project_id = selection

# --- 6. MAIN CONTENT ---
if st.session_state.current_project_id:
    curr_id = st.session_state.current_project_id
    proj_data = st.session_state.db_projects[curr_id]
    
    st.title(f"Projekt: {proj_data['kunde']}")
    st.caption(f"Ort: {proj_data['ort']}")
    
    tab1, tab2, tab3 = st.tabs(["🏗️ Editor (Räume)", "⚡ Strings & Last", "📦 Material & Preise"])
    
    # --- TAB 1: RÄUME ---
    with tab1:
        col_edit, col_view = st.columns([1, 2])
        if curr_id not in st.session_state.db_rooms: st.session_state.db_rooms[curr_id] = []
        rooms = st.session_state.db_rooms[curr_id]
        
        with col_edit:
            with st.expander("➕ Raum hinzufügen"):
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
                st.write("**Verschieben:**")
                r_labels = [r['name'] for r in rooms]
                idx = st.radio("Raum wählen", range(len(rooms)), format_func=lambda x: r_labels[x])
                cur = rooms[idx]
                nx = st.slider("X-Position", -5.0, 25.0, float(cur['x']), 0.25, key=f"sx_{curr_id}")
                ny = st.slider("Y-Position", -5.0, 25.0, float(cur['y']), 0.25, key=f"sy_{curr_id}")
                st.session_state.db_rooms[curr_id][idx]['x'] = nx
                st.session_state.db_rooms[curr_id][idx]['y'] = ny

        with col_view:
            if rooms:
                st.pyplot(plot_room_map(rooms))

    # --- TAB 2: STRINGS ---
    with tab2:
        col_def, col_tree = st.columns([1, 2])
        if curr_id not in st.session_state.db_strings: st.session_state.db_strings[curr_id] = []
        my_strings = st.session_state.db_strings[curr_id]
        
        with col_def:
            st.subheader("Stromkreise")
            with st.form("new_string"):
                s_name = st.text_input("Bezeichnung", "Küche Steckdosen")
                c1, c2 = st.columns(2)
                s_fuse = c1.selectbox("Sicherung (A)", [10, 16, 20, 32], index=1)
                s_factor = c2.slider("GL-Faktor", 0.1, 1.0, 0.7)
                if st.form_submit_button("Anlegen"):
                    new_s_id = f"S{len(my_strings)+1:02d}"
                    st.session_state.db_strings[curr_id].append({"id": new_s_id, "name": s_name, "fuse": s_fuse, "factor": s_factor})
                    st.rerun()
            
            st.write("**Liste:**")
            for s in my_strings:
                with st.expander(f"{s['id']}: {s['name']}"):
                    if st.button("Löschen", key=f"del_{s['id']}"):
                        st.session_state.db_strings[curr_id].remove(s)
                        st.rerun()

        with col_tree:
            proj_mats = [m for m in st.session_state.db_material if m['Projekt'] == curr_id]
            if my_strings:
                try:
                    st.graphviz_chart(plot_electrical_tree(my_strings, proj_mats), use_container_width=True)
                except Exception:
                    st.error("Graphviz Fehler. Bitte requirements.txt prüfen.")

    # --- TAB 3: MATERIAL & PREISE ---
    with tab3:
        st.subheader("Material & Kosten")
        my_rooms = [r['name'] for r in st.session_state.db_rooms.get(curr_id, [])]
        string_opts = {s['id']: f"{s['name']} ({s['fuse']}A)" for s in st.session_state.db_strings.get(curr_id, [])}
        
        if my_rooms and string_opts:
            c1, c2, c3 = st.columns(3)
            r_sel = c1.selectbox("Ort", my_rooms)
            s_sel = c2.selectbox("Stromkreis", list(string_opts.keys()), format_func=lambda x: string_opts[x])
            k_sel = c3.selectbox("Kategorie", list(PRODUKT_KATALOG.keys()))
            
            c4, c5 = st.columns([2, 1])
            i_sel = c4.selectbox("Artikel", [p['name'] for p in PRODUKT_KATALOG[k_sel]])
            qty = c5.number_input("Menge", 1, 50, 1)
            
            if st.button("Hinzufügen", type="primary"):
                p_data = next(p for p in PRODUKT_KATALOG[k_sel] if p['name'] == i_sel)
                st.session_state.db_material.append({
                    "Projekt": curr_id, "Raum": r_sel, "String": s_sel, "Artikel": i_sel, 
                    "Menge": qty, "Preis": p_data['preis'], "Watt": p_data.get('watt', 0), "PDF": p_data.get('pdf', '')
                })
                st.success("Gespeichert!")

            st.divider()
            
            # Auswertung Tabelle
            proj_mats = [m for m in st.session_state.db_material if m['Projekt'] == curr_id]
            if proj_mats:
                df = pd.DataFrame(proj_mats)
                
                # Berechnungen
                df['String Name'] = df['String'].map(string_opts)
                df['Gesamtlast (W)'] = df['Menge'] * df['Watt']
                df['Gesamtpreis (€)'] = df['Menge'] * df['Preis']
                
                # Anzeige
                st.dataframe(
                    df[["Raum", "String Name", "Artikel", "Menge", "Preis", "Gesamtpreis (€)", "Gesamtlast (W)"]], 
                    use_container_width=True,
                    column_config={
                        "Preis": st.column_config.NumberColumn(format="%.2f €"),
                        "Gesamtpreis (€)": st.column_config.NumberColumn(format="%.2f €"),
                        "Gesamtlast (W)": st.column_config.NumberColumn(format="%d W"),
                    }
                )
                
                st.markdown("---")
                t_col1, t_col2 = st.columns(2)
                t_col1.metric("Projekt Summe (Netto)", f"{df['Gesamtpreis (€)'].sum():.2f} €")
                t_col2.metric("Gesamtanschlusswert", f"{df['Gesamtlast (W)'].sum()/1000:.1f} kW")
        else:
            st.warning("Bitte erst Räume (Tab 1) und Strings (Tab 2) anlegen.")

else:
    st.info("Bitte wählen Sie ein Projekt.")
