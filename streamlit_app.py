import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import graphviz
import random

# --- KONFIGURATION ---
st.set_page_config(page_title="LEC Manager", page_icon="⚡", layout="wide")

# --- SIMULIERTE DATENBANK (Backend) ---
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

# NEU: Strings (Stromkreise) Datenbank
if 'db_strings' not in st.session_state:
    st.session_state.db_strings = {
        "P-001": [
            {"id": "S1", "name": "Steckdosen Küche", "fuse": 16, "factor": 0.7},
            {"id": "S2", "name": "Licht Allgemein", "fuse": 10, "factor": 1.0}
        ]
    }

if 'current_project_id' not in st.session_state:
    st.session_state.current_project_id = None

# --- KATALOG (Mit Leistung in WATT) ---
PRODUKT_KATALOG = {
    "Steuerung": [
        {"name": "Shelly Plus 2PM", "preis": 29.90, "watt": 1, "pdf": "https://kb.shelly.cloud/"},
        {"name": "Shelly Dimmer 2", "preis": 32.50, "watt": 1, "pdf": "https://kb.shelly.cloud/"},
    ],
    "Verbraucher (Last)": [
        {"name": "Steckdose (Standard)", "preis": 8.50, "watt": 200, "pdf": ""}, # Pauschale Annahme
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

# --- FUNKTION: VERTEILER-BAUM & LASTBERECHNUNG ---
def plot_electrical_tree(strings, materials):
    # Graphviz Initialisierung
    dot = graphviz.Digraph(comment='Verteilerplan')
    dot.attr(rankdir='TB') # Top to Bottom
    dot.attr('node', fontname='Arial')
    
    # Hauptverteiler (Wurzel)
    dot.node('UV', '⚡ Hauptverteiler (UV)', shape='doubleoctagon', style='filled', fillcolor='#ffeb3b')

    for s in strings:
        s_id = s['id']
        
        # 1. Last Berechnung für diesen String
        connected_mats = [m for m in materials if m.get('String') == s_id]
        
        # Summe der Anschlussleistung
        total_watt = sum([m.get('Watt', 0) * m['Menge'] for m in connected_mats])
        
        # Gleichzeitigkeitsfaktor anwenden
        real_load = total_watt * s['factor']
        
        # Überlast Prüfung (bei 230V)
        max_watt = s['fuse'] * 230
        load_percent = (real_load / max_watt) * 100 if max_watt > 0 else 0
        
        # Farb-Logik (Ampelsystem)
        color = '#c8e6c9' # Grün (Alles OK)
        warn_text = ""
        if load_percent > 80: 
            color = '#fff9c4' # Gelb (Grenzwertig)
        if load_percent > 100: 
            color = '#ffcdd2' # Rot (Überlast!)
            warn_text = "\n⚠️ ÜBERLAST"
        
        # Label für den String-Knoten
        label = f"{s['name']}\nSicherung: {s['fuse']}A\nLast (GLF {s['factor']}): {real_load:.0f}W{warn_text}"
        
        # String Knoten zeichnen
        dot.node(s_id, label, shape='folder', style='filled', fillcolor=color)
        dot.edge('UV', s_id)
        
        # 2. Geräte an den String hängen
        # Wir gruppieren gleiche Geräte, damit der Baum nicht explodiert
        grouped_items = {}
        for m in connected_mats:
            name = m['Artikel']
            if name not in grouped_items:
                grouped_items[name] = {"menge": 0, "watt": m.get('Watt', 0)}
            grouped_items[name]["menge"] += m['Menge']
            
        for item_name, data in grouped_items.items():
            # Kleine Boxen für Geräte
            node_id = f"{s_id}_{item_name}"
            total_item_watt = data['watt'] * data['menge']
            m_label = f"{data['menge']}x {item_name}\n({total_item_watt}W)"
            
            dot.node(node_id, m_label, shape='note', fontsize='9')
            dot.edge(s_id, node_id)
            
    return dot

# --- SIDEBAR ---
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
        st.session_state.db_strings[new_id] = [] # Leere String Liste
        st.success("Erstellt!")
        st.rerun()
else:
    st.session_state.current_project_id = selection

# --- MAIN ---
if st.session_state.current_project_id:
    curr_id = st.session_state.current_project_id
    proj_data = st.session_state.db_projects[curr_id]
    
    st.title(f"Projekt: {proj_data['kunde']}")
    
    # TABS
    tab1, tab2, tab3 = st.tabs(["🏗️ Editor", "⚡ Strings & Last", "📦 Material & Zuordnung"])
    
    # --- TAB 1: EDITOR (Räume) ---
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
                st.write("**Räume positionieren:**")
                r_labels = [r['name'] for r in rooms]
                idx = st.radio("Raum wählen", range(len(rooms)), format_func=lambda x: r_labels[x])
                
                cur = rooms[idx]
                nx = st.slider("X-Pos", -5.0, 25.0, float(cur['x']), 0.25, key=f"sx_{curr_id}")
                ny = st.slider("Y-Pos", -5.0, 25.0, float(cur['y']), 0.25, key=f"sy_{curr_id}")
                st.session_state.db_rooms[curr_id][idx]['x'] = nx
                st.session_state.db_rooms[curr_id][idx]['y'] = ny

        with col_view:
            # Einfacher Matplotlib Plot für Orientierung
            if rooms:
                fig, ax = plt.subplots(figsize=(8, 5))
                for idx, r in enumerate(rooms):
                    active = (idx == idx) # Dummy
                    rect = patches.Rectangle((r['x'], r['y']), r['l'], r['b'], linewidth=2, edgecolor='#1f77b4', facecolor='#e3f2fd', alpha=0.5)
                    ax.add_patch(rect)
                    ax.text(r['x']+r['l']/2, r['y']+r['b']/2, r['name'], ha='center')
                    ax.set_xlim(-2, 20); ax.set_ylim(-2, 20); ax.set_aspect('equal'); ax.grid(True, linestyle=':')
                st.pyplot(fig)

    # --- TAB 2: STRINGS & LAST (Das Herzstück) ---
    with tab2:
        col_def, col_tree = st.columns([1, 2])
        
        if curr_id not in st.session_state.db_strings: st.session_state.db_strings[curr_id] = []
        my_strings = st.session_state.db_strings[curr_id]
        
        with col_def:
            st.subheader("Stromkreise definieren")
            
            with st.form("new_string"):
                s_name = st.text_input("Bezeichnung (z.B. Küche)", "Küche Steckdosen")
                c1, c2 = st.columns(2)
                s_fuse = c1.selectbox("Absicherung (A)", [10, 13, 16, 20, 32], index=2)
                s_factor = c2.slider("Gleichzeitigkeitsfaktor", 0.1, 1.0, 0.7, 0.1, help="1.0 = Alle Geräte laufen gleichzeitig voll. 0.5 = Nur die Hälfte.")
                
                if st.form_submit_button("String anlegen"):
                    new_s_id = f"S{len(my_strings)+1:02d}"
                    st.session_state.db_strings[curr_id].append(
                        {"id": new_s_id, "name": s_name, "fuse": s_fuse, "factor": s_factor}
                    )
                    st.rerun()
            
            st.divider()
            st.write("**Konfigurierte Strings:**")
            if not my_strings: st.caption("Noch keine.")
            for s in my_strings:
                with st.expander(f"{s['id']}: {s['name']} ({s['fuse']}A)"):
                    st.write(f"Faktor: {s['factor']}")
                    if st.button(f"Löschen {s['id']}", key=f"del_{s['id']}"):
                        st.session_state.db_strings[curr_id].remove(s)
                        st.rerun()

        with col_tree:
            st.subheader("Verteiler & Lastfluss")
            # Wir holen das Material für die Berechnung
            proj_mats = [m for m in st.session_state.db_material if m['Projekt'] == curr_id]
            
            if my_strings:
                try:
                    chart = plot_electrical_tree(my_strings, proj_mats)
                    st.graphviz_chart(chart, use_container_width=True)
                except Exception as e:
                    st.error(f"Fehler beim Zeichnen: {e}")
                    st.info("Tipp: Haben Sie 'graphviz' in requirements.txt eingetragen?")
            else:
                st.warning("Bitte links Stromkreise anlegen.")

    # --- TAB 3: MATERIAL & ZUORDNUNG ---
    with tab3:
        st.subheader("Komponenten hinzufügen")
        
        my_rooms = [r['name'] for r in st.session_state.db_rooms.get(curr_id, [])]
        
        # String Liste bauen
        string_opts = {s['id']: f"{s['name']} ({s['fuse']}A)" for s in st.session_state.db_strings.get(curr_id, [])}
        
        if not my_rooms:
            st.warning("Bitte erst Räume anlegen!")
        elif not string_opts:
            st.warning("Bitte erst Strings (Tab 2) anlegen!")
        else:
            col_in1, col_in2 = st.columns(2)
            
            with col_in1:
                r_sel = st.selectbox("Ort / Raum", my_rooms)
                cat_sel = st.selectbox("Kategorie", list(PRODUKT_KATALOG.keys()))
                item_sel = st.selectbox("Artikel", [p['name'] for p in PRODUKT_KATALOG[cat_sel]])
            
            with col_in2:
                # Hier verbinden wir Material mit Stromkreis
                s_sel = st.selectbox("Anschluss an Stromkreis", list(string_opts.keys()), format_func=lambda x: string_opts[x])
                qty = st.number_input("Menge", 1, 50, 1)
                
                st.write("")
                if st.button("Hinzufügen & Verbinden", type="primary"):
                    p_data = next(p for p in PRODUKT_KATALOG[cat_sel] if p['name'] == item_sel)
                    st.session_state.db_material.append({
                        "Projekt": curr_id, 
                        "Raum": r_sel, 
                        "String": s_sel, # <--- WICHTIG
                        "Artikel": item_sel, 
                        "Menge": qty, 
                        "Preis": p_data['preis'], 
                        "Watt": p_data.get('watt', 0),
                        "PDF": p_data.get('pdf', '')
                    })
                    st.success("Gespeichert!")

            st.divider()
            
            # Auswertung
            proj_mats = [m for m in st.session_state.db_material if m['Projekt'] == curr_id]
            if proj_mats:
                df = pd.DataFrame(proj_mats)
                # Namen statt IDs anzeigen
                df['String'] = df['String'].map(string_opts)
                df['Gesamtlast'] = df['Menge'] * df['Watt']
                
                st.dataframe(
                    df[["Raum", "String", "Artikel", "Menge", "Gesamtlast"]], 
                    use_container_width=True,
                    column_config={
                        "Gesamtlast": st.column_config.NumberColumn(format="%d W")
                    }
                )
            else:
                st.info("Noch kein Material erfasst.")

else:
    st.info("Wählen Sie ein Projekt.")
