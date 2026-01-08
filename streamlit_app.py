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

# Strings jetzt mit Kabel-Info
if 'db_strings' not in st.session_state:
    st.session_state.db_strings = {
        "P-001": [
            # Beispiel: S1 hat Kabel NYM-J 3x1.5 mit 15m Länge
            {"id": "S1", "name": "Steckdosen Küche", "fuse": 16, "factor": 0.7, "cable_name": "NYM-J 3x1.5", "cable_len": 15, "cable_price": 0.65},
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
    "Kabel (Meterware)": [
        {"name": "NYM-J 3x1.5", "preis": 0.65, "watt": 0, "pdf": ""}, # Preis pro Meter
        {"name": "NYM-J 5x1.5", "preis": 0.95, "watt": 0, "pdf": ""},
        {"name": "NYM-J 5x2.5 (Herd)", "preis": 1.40, "watt": 0, "pdf": ""},
        {"name": "KNX Busleitung", "preis": 0.55, "watt": 0, "pdf": ""},
    ]
}

# --- 4. FUNKTIONEN (PLOTTING) ---

def plot_electrical_tree(strings, materials):
    """Zeichnet den Verteiler-Stammbaum"""
    dot = graphviz.Digraph(comment='Verteilerplan')
    dot.attr(rankdir='TB')
    dot.attr('node', fontname='Arial')
    
    dot.node('UV', '⚡ Hauptverteiler (UV)', shape='doubleoctagon', style='filled', fillcolor='#ffeb3b')

    for s in strings:
        s_id = s['id']
        
        # Lastberechnung
        connected_mats = [m for m in materials if m.get('String') == s_id]
        total_watt = sum([m.get('Watt', 0) * m['Menge'] for m in connected_mats])
        real_load = total_watt * s['factor']
        
        max_watt = s['fuse'] * 230
        load_percent = (real_load / max_watt) * 100 if max_watt > 0 else 0
        
        # Ampel-Farben
        color = '#c8e6c9' # Grün
        warn_text = ""
        if load_percent > 80: color = '#fff9c4' # Gelb
        if load_percent > 100: 
            color = '#ffcdd2' # Rot
            warn_text = "\n⚠️ ÜBERLAST"
        
        # Kabel Info im Label
        cable_info = f"\nKabel: {s.get('cable_name', '?')} ({s.get('cable_len', 0)}m)"
        
        label = f"{s['name']}\n{s['fuse']}A | Faktor: {s['factor']}{cable_info}\nLast: {real_load:.0f}W{warn_text}"
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
    """Zeichnet die einfache Raumkarte"""
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
    
    tab1, tab2, tab3 = st.tabs(["🏗️ Editor", "⚡ Strings (Kabel)", "📦 Material & Kosten"])
    
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
                r_labels = [r['name'] for r in rooms]
                idx = st.radio("Raum wählen", range(len(rooms)), format_func=lambda x: r_labels[x])
                cur = rooms[idx]
                nx = st.slider("X", -5.0, 25.0, float(cur['x']), 0.25, key=f"sx_{curr_id}")
                ny = st.slider("Y", -5.0, 25.0, float(cur['y']), 0.25, key=f"sy_{curr_id}")
                st.session_state.db_rooms[curr_id][idx]['x'] = nx
                st.session_state.db_rooms[curr_id][idx]['y'] = ny

        with col_view:
            if rooms:
                st.pyplot(plot_room_map(rooms))

    # --- TAB 2: STRINGS & KABEL ---
    with tab2:
        col_def, col_tree = st.columns([1, 2])
        if curr_id not in st.session_state.db_strings: st.session_state.db_strings[curr_id] = []
        my_strings = st.session_state.db_strings[curr_id]
        
        with col_def:
            st.subheader("Stromkreis Konfiguration")
            with st.form("new_string"):
                s_name = st.text_input("Name (z.B. Küche)", "Küche Steckdosen")
                
                c1, c2 = st.columns(2)
                s_fuse = c1.selectbox("Sicherung (A)", [10, 16, 20, 32], index=1)
                s_factor = c2.slider("GL-Faktor", 0.1, 1.0, 0.7)
                
                st.markdown("**Kabel Auswahl**")
                # Kabel aus Katalog laden
                cable_opts = [p['name'] for p in PRODUKT_KATALOG["Kabel (Meterware)"]]
                s_cable = st.selectbox("Kabeltyp", cable_opts)
                
                # Standard 15m
                s_len = st.number_input("Länge (Meter)", value=15, step=5, help="Standardannahme pro Raum: 15m")
                
                if st.form_submit_button("String anlegen"):
                    # Preis ermitteln
                    cable_price = next(p['preis'] for p in PRODUKT_KATALOG["Kabel (Meterware)"] if p['name'] == s_cable)
                    
                    new_s_id = f"S{len(my_strings)+1:02d}"
                    st.session_state.db_strings[curr_id].append({
                        "id": new_s_id, 
                        "name": s_name, 
                        "fuse": s_fuse, 
                        "factor": s_factor,
                        "cable_name": s_cable,
                        "cable_len": s_len,
                        "cable_price": cable_price
                    })
                    st.rerun()
            
            st.write("**Vorhandene Kreise:**")
            for s in my_strings:
                with st.expander(f"{s['id']}: {s['name']}"):
                    st.write(f"Kabel: {s.get('cable_name')} ({s.get('cable_len')}m)")
                    if st.button("Löschen", key=f"del_{s['id']}"):
                        st.session_state.db_strings[curr_id].remove(s)
                        st.rerun()

        with col_tree:
            proj_mats = [m for m in st.session_state.db_material if m['Projekt'] == curr_id]
            if my_strings:
                try:
                    st.graphviz_chart(plot_electrical_tree(my_strings, proj_mats), use_container_width=True)
                except:
                    st.error("Graphviz Fehler.")

    # --- TAB 3: MATERIAL & PREISE ---
    with tab3:
        st.subheader("Material & Kosten")
        my_rooms = [r['name'] for r in st.session_state.db_rooms.get(curr_id, [])]
        string_opts = {s['id']: f"{s['name']}" for s in st.session_state.db_strings.get(curr_id, [])}
        
        if my_rooms and string_opts:
            # EINGABE
            c1, c2, c3 = st.columns(3)
            r_sel = c1.selectbox("Ort", my_rooms)
            s_sel = c2.selectbox("Stromkreis", list(string_opts.keys()), format_func=lambda x: string_opts[x])
            k_sel = c3.selectbox("Kat", list(PRODUKT_KATALOG.keys()))
            
            c4, c5 = st.columns([2, 1])
            cat_items = [p['name'] for p in PRODUKT_KATALOG[k_sel]]
            i_sel = c4.selectbox("Artikel", cat_items)
            qty = c5.number_input("Menge", 1, 50, 1)
            
            if st.button("Hinzufügen", type="primary"):
                p_data = next(p for p in PRODUKT_KATALOG[k_sel] if p['name'] == i_sel)
                st.session_state.db_material.append({
                    "Projekt": curr_id, "Raum": r_sel, "String": s_sel, "Artikel": i_sel, 
                    "Menge": qty, "Preis": p_data['preis'], "Watt": p_data.get('watt', 0), "PDF": p_data.get('pdf', '')
                })
                st.success("Gespeichert!")

            st.divider()
            
            # --- DATEN AUFBEREITUNG FÜR DIE LISTE ---
            
            # 1. Die normalen Artikel
            raw_mats = [m for m in st.session_state.db_material if m['Projekt'] == curr_id]
            df_items = pd.DataFrame(raw_mats)
            
            if not df_items.empty:
                df_items['Typ'] = 'Material'
                df_items['String Name'] = df_items['String'].map(string_opts)
                df_items['Gesamtpreis (€)'] = df_items['Menge'] * df_items['Preis']
                df_items['Gesamtlast (W)'] = df_items['Menge'] * df_items['Watt']
            else:
                df_items = pd.DataFrame(columns=["Raum", "String Name", "Artikel", "Menge", "Preis", "Gesamtpreis (€)", "Gesamtlast (W)", "Typ"])

            # 2. Die Kabel (aus den Strings generieren)
            cable_rows = []
            strings_curr = st.session_state.db_strings.get(curr_id, [])
            for s in strings_curr:
                cable_rows.append({
                    "Projekt": curr_id,
                    "Raum": "Infrastruktur", # Sammelposten
                    "String": s['id'],
                    "String Name": s['name'],
                    "Artikel": f"Kabel: {s.get('cable_name')}",
                    "Menge": s.get('cable_len', 0),
                    "Preis": s.get('cable_price', 0),
                    "Watt": 0,
                    "PDF": "",
                    "Typ": "Kabel",
                    "Gesamtpreis (€)": s.get('cable_len', 0) * s.get('cable_price', 0),
                    "Gesamtlast (W)": 0
                })
            
            df_cables = pd.DataFrame(cable_rows)
            
            # 3. Zusammenfügen
            df_final = pd.concat([df_items, df_cables], ignore_index=True)
            
            if not df_final.empty:
                # Sortieren: Erst Material, dann Kabel
                df_final = df_final.sort_values(by=["Typ", "Raum"], ascending=[False, True])
                
                # Tabelle anzeigen
                st.dataframe(
                    df_final[["Typ", "Raum", "String Name", "Artikel", "Menge", "Preis", "Gesamtpreis (€)"]], 
                    use_container_width=True,
                    column_config={
                        "Preis": st.column_config.NumberColumn(format="%.2f €"),
                        "Gesamtpreis (€)": st.column_config.NumberColumn(format="%.2f €"),
                    }
                )
                
                # SUMMEN
                st.markdown("---")
                t_col1, t_col2 = st.columns(2)
                total_euro = df_final['Gesamtpreis (€)'].sum()
                total_watt = df_final['Gesamtlast (W)'].sum()
                
                t_col1.metric("Projekt Summe (Netto)", f"{total_euro:.2f} €")
                t_col2.metric("Gesamtanschlusswert", f"{total_watt/1000:.1f} kW")
            else:
                st.info("Keine Daten.")
        else:
            st.warning("Bitte erst Räume und Strings anlegen.")

else:
    st.info("Bitte wählen Sie ein Projekt.")
