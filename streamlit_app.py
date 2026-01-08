import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import graphviz
import random

# --- 1. KONFIGURATION ---
st.set_page_config(page_title="LEC Manager", page_icon="⚡", layout="wide")

# --- 2. SESSION STATE ---
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
            {"id": "S1", "name": "Steckdosen Küche", "fuse": 16, "factor": 0.7, "cable_name": "NYM-J 3x1.5", "cable_len": 15, "cable_price": 0.65},
            {"id": "S2", "name": "Licht", "fuse": 10, "factor": 1.0, "cable_name": "NYM-J 3x1.5", "cable_len": 20, "cable_price": 0.65},
        ]
    }

if 'current_project_id' not in st.session_state:
    st.session_state.current_project_id = None

# --- 3. KATALOG ---
PRODUKT_KATALOG = {
    "Steuerung": [
        {"name": "Shelly Plus 2PM", "preis": 29.90, "watt": 1},
        {"name": "Shelly Dimmer 2", "preis": 32.50, "watt": 1},
    ],
    "Verbraucher (Last)": [
        {"name": "Steckdose (Standard)", "preis": 8.50, "watt": 200},
        {"name": "Steckdose (Backofen)", "preis": 12.00, "watt": 3000},
        {"name": "LED Deckenspot", "preis": 25.00, "watt": 7},
        {"name": "Lichtschalter", "preis": 12.00, "watt": 0},
    ],
    "Kabel (Meterware)": [
        {"name": "NYM-J 3x1.5", "preis": 0.65, "watt": 0}, 
        {"name": "NYM-J 5x1.5", "preis": 0.95, "watt": 0},
        {"name": "KNX Busleitung", "preis": 0.55, "watt": 0},
    ]
}

# --- 4. FUNKTIONEN ---

def plot_electrical_tree(strings, materials):
    """Zeichnet Verteilerbaum"""
    dot = graphviz.Digraph(comment='Verteiler')
    dot.attr(rankdir='TB')
    dot.attr('node', fontname='Arial')
    dot.node('UV', '⚡ UV', shape='doubleoctagon', style='filled', fillcolor='#ffeb3b')

    for s in strings:
        s_id = s['id']
        mats = [m for m in materials if m.get('String') == s_id]
        watts = sum([m.get('Watt', 0) * m['Menge'] for m in mats])
        load = watts * s['factor']
        
        col = '#c8e6c9'
        if (load / (s['fuse']*230)) > 0.8: col = '#fff9c4'
        if (load / (s['fuse']*230)) > 1.0: col = '#ffcdd2'
        
        dot.node(s_id, f"{s['name']}\n{load:.0f}W", shape='folder', style='filled', fillcolor=col)
        dot.edge('UV', s_id)
    return dot

def plot_full_map(rooms, materials, strings, active_mat_idx=None):
    """Zeichnet Räume UND Geräte"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Farben für Strings generieren (damit man sieht was zusammengehört)
    cmap = plt.get_cmap('tab10')
    string_colors = {s['id']: cmap(i % 10) for i, s in enumerate(strings)}

    # 1. Räume zeichnen
    for r in rooms:
        rect = patches.Rectangle((r['x'], r['y']), r['l'], r['b'], linewidth=2, edgecolor='#546e7a', facecolor='#eceff1', alpha=0.5, zorder=1)
        ax.add_patch(rect)
        ax.text(r['x']+0.2, r['y']+r['b']-0.3, r['name'], fontsize=9, color='#455a64', fontweight='bold', zorder=2)

    # 2. Geräte zeichnen
    for idx, mat in enumerate(materials):
        # Raum Koordinaten finden
        room = next((r for r in rooms if r['name'] == mat['Raum']), None)
        if room:
            # Absolute Position berechnen (Raum-Pos + Relative Geräte-Pos)
            # Default auf Raum-Mitte, falls noch keine Pos gespeichert
            rel_x = mat.get('pos_x', room['l']/2)
            rel_y = mat.get('pos_y', room['b']/2)
            
            abs_x = room['x'] + rel_x
            abs_y = room['y'] + rel_y
            
            # Style
            s_id = mat.get('String')
            color = string_colors.get(s_id, 'black')
            
            # Highlight aktives Gerät
            is_active = (idx == active_mat_idx)
            size = 150 if is_active else 50
            edge = 'red' if is_active else 'white'
            z = 10 if is_active else 5
            
            ax.scatter(abs_x, abs_y, c=[color], s=size, edgecolors=edge, linewidth=2, zorder=z, label=mat['Artikel'] if idx==0 else "")
            
            # Wenn aktiv, Label zeigen
            if is_active:
                ax.text(abs_x, abs_y+0.4, mat['Artikel'], ha='center', fontsize=10, fontweight='bold', color='red', zorder=11, bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

    ax.set_aspect('equal')
    ax.grid(True, linestyle=':', alpha=0.3)
    ax.set_title("Installationsplan (Farbe = Stromkreis)")
    
    # Dynamische Grenzen
    if rooms:
        mx = max([r['x']+r['l'] for r in rooms]) + 1
        my = max([r['y']+r['b'] for r in rooms]) + 1
        ax.set_xlim(-1, mx)
        ax.set_ylim(-1, my)
        
    return fig

# --- 5. SIDEBAR ---
st.sidebar.title("LEC Manager")
project_options = ["Neues Projekt"] + list(st.session_state.db_projects.keys())

def fmt(opt):
    if opt == "Neues Projekt": return opt
    return st.session_state.db_projects[opt]['kunde']

sel = st.sidebar.selectbox("Projekt", project_options, format_func=fmt)

if sel == "Neues Projekt":
    if st.sidebar.button("Erstellen"):
        nid = f"P-{len(st.session_state.db_projects)+1:03d}"
        st.session_state.db_projects[nid] = {"kunde": "Neu", "ort": "-", "status": "Neu"}
        st.session_state.db_rooms[nid] = []
        st.session_state.db_strings[nid] = []
        st.rerun()
else:
    st.session_state.current_project_id = sel

# --- 6. MAIN ---
if st.session_state.current_project_id:
    pid = st.session_state.current_project_id
    
    st.title(f"Projekt: {st.session_state.db_projects[pid]['kunde']}")
    
    tab1, tab2, tab3 = st.tabs(["🏗️ Raum-Editor", "⚡ Stromkreise", "📍 Plan & Material"])
    
    # --- TAB 1: RÄUME ---
    with tab1:
        c1, c2 = st.columns([1, 2])
        rooms = st.session_state.db_rooms.get(pid, [])
        
        with c1:
            with st.form("nr"):
                rn = st.text_input("Name")
                l = st.number_input("Länge", 4.0)
                b = st.number_input("Breite", 3.0)
                if st.form_submit_button("Add"):
                    rooms.append({"name": rn, "l": l, "b": b, "x": 0.0, "y": 0.0, "etage": "EG"})
                    st.rerun()
            
            if rooms:
                st.divider()
                ridx = st.radio("Verschieben:", range(len(rooms)), format_func=lambda i: rooms[i]['name'])
                rooms[ridx]['x'] = st.slider("X", -5.0, 20.0, rooms[ridx]['x'], 0.5)
                rooms[ridx]['y'] = st.slider("Y", -5.0, 20.0, rooms[ridx]['y'], 0.5)
                
        with c2:
            # Zeigt hier nur Räume (ohne Material) zur Übersicht
            fig = plot_full_map(rooms, [], [], None)
            st.pyplot(fig)

    # --- TAB 2: STRINGS ---
    with tab2:
        c1, c2 = st.columns([1, 2])
        strings = st.session_state.db_strings.get(pid, [])
        mats = [m for m in st.session_state.db_material if m['Projekt'] == pid]
        
        with c1:
            with st.form("ns"):
                sn = st.text_input("Name", "Kreis 1")
                sf = st.selectbox("Ampere", [10, 16, 32], index=1)
                sc = st.selectbox("Kabel", [k['name'] for k in PRODUKT_KATALOG['Kabel (Meterware)']])
                if st.form_submit_button("Add"):
                    pr = next(x['preis'] for x in PRODUKT_KATALOG['Kabel (Meterware)'] if x['name']==sc)
                    strings.append({"id": f"S{len(strings)+1}", "name": sn, "fuse": sf, "factor": 0.7, "cable_name": sc, "cable_len": 15, "cable_price": pr})
                    st.rerun()
        
        with c2:
            if strings: st.graphviz_chart(plot_electrical_tree(strings, mats))

    # --- TAB 3: PLANUNG (Das Herzstück) ---
    with tab3:
        rooms = st.session_state.db_rooms.get(pid, [])
        strings = st.session_state.db_strings.get(pid, [])
        mats = [m for m in st.session_state.db_material if m['Projekt'] == pid]
        
        col_map, col_data = st.columns([2, 1])
        
        # --- RECHTE SEITE: EINGABE & LISTE ---
        with col_data:
            st.subheader("Material")
            
            # A) NEUES MATERIAL
            with st.expander("➕ Gerät hinzufügen", expanded=False):
                if rooms and strings:
                    r_sel = st.selectbox("Raum", [r['name'] for r in rooms])
                    s_sel = st.selectbox("String", [s['id'] for s in strings], format_func=lambda x: next(s['name'] for s in strings if s['id']==x))
                    k_sel = st.selectbox("Art", ["Steuerung", "Verbraucher (Last)"])
                    i_sel = st.selectbox("Item", [p['name'] for p in PRODUKT_KATALOG[k_sel]])
                    
                    if st.button("Speichern"):
                        p_dat = next(p for p in PRODUKT_KATALOG[k_sel] if p['name']==i_sel)
                        # Default Position: Mitte des Raumes
                        tr = next(r for r in rooms if r['name']==r_sel)
                        
                        st.session_state.db_material.append({
                            "Projekt": pid, "Raum": r_sel, "String": s_sel, "Artikel": i_sel, "Menge": 1,
                            "Preis": p_dat['preis'], "Watt": p_dat.get('watt', 0),
                            "pos_x": tr['l']/2, "pos_y": tr['b']/2 # DEFAULT POS
                        })
                        st.rerun()
                else:
                    st.warning("Erst Räume & Strings anlegen!")

            # B) LISTE & POSITIONIERUNG
            st.divider()
            st.write("**Geräte Positionieren:**")
            
            if mats:
                # Liste zum Auswählen
                labels = [f"{m['Artikel']} ({m['Raum']})" for m in mats]
                sel_idx = st.radio("Gerät wählen:", range(len(mats)), format_func=lambda i: labels[i])
                
                target_mat = st.session_state.db_material[len(st.session_state.db_material) - len(mats) + sel_idx] # Hack für Index Mapping
                
                # SLIDER FÜR POSITION
                st.info(f"Verschiebe: {target_mat['Artikel']}")
                
                # Sliders relativ zur Raumgröße
                room_obj = next(r for r in rooms if r['name'] == target_mat['Raum'])
                
                # Wir ändern direkt im Session State
                px = st.slider("Pos X (im Raum)", 0.0, float(room_obj['l']), float(target_mat.get('pos_x', 0)), 0.25, key=f"px_{sel_idx}")
                py = st.slider("Pos Y (im Raum)", 0.0, float(room_obj['b']), float(target_mat.get('pos_y', 0)), 0.25, key=f"py_{sel_idx}")
                
                target_mat['pos_x'] = px
                target_mat['pos_y'] = py
                
                # Preis Info
                st.caption(f"Preis: {target_mat['Preis']}€ | Last: {target_mat['Watt']}W")
                
            else:
                sel_idx = None
                st.info("Keine Geräte.")

        # --- LINKE SEITE: GROSSE KARTE ---
        with col_map:
            if rooms:
                fig = plot_full_map(rooms, mats, strings, active_mat_idx=sel_idx)
                st.pyplot(fig)
                
                # Legende
                st.caption("Farb-Legende (Stromkreise):")
                cols = st.columns(len(strings)+1) if strings else []
                for i, s in enumerate(strings):
                    cols[i].color_picker(s['name'], value='#000000', disabled=True, key=f"c_{i}") # Dummy visualization
            else:
                st.info("Bitte Räume anlegen.")

else:
    st.info("Projekt wählen.")
