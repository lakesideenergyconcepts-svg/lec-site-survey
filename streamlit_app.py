import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import graphviz
import random

# ==========================================
# MODUL 1: KONFIGURATION & DATENSTRUKTUREN
# ==========================================
st.set_page_config(page_title="LEC Manager V1.0", page_icon="⚡", layout="wide")

# --- Initialisierung Session State (Datenbank) ---
def init_db():
    defaults = {
        'db_projects': {"P-001": {"kunde": "Müller", "ort": "Friedrichshafen", "status": "In Planung"}},
        'db_rooms': {"P-001": [
            {"name": "Wohnzimmer", "l": 5.0, "b": 4.0, "x": 0.0, "y": 0.0},
            {"name": "Küche", "l": 3.0, "b": 4.0, "x": 5.0, "y": 0.0}
        ]},
        'db_strings': {"P-001": [
            {"id": "S1", "name": "Steckdosen Küche", "fuse": 16, "factor": 0.7, "cable_name": "NYM-J 3x1.5", "cable_len": 15, "cable_price": 0.65},
            {"id": "S2", "name": "Licht", "fuse": 10, "factor": 1.0, "cable_name": "NYM-J 3x1.5", "cable_len": 20, "cable_price": 0.65},
        ]},
        'db_material': [], # Liste aller verbauten Teile
        'current_project_id': None
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_db()

# --- Produkt Katalog ---
PRODUKT_KATALOG = {
    "Steuerung": [
        {"name": "Shelly Plus 2PM", "preis": 29.90, "watt": 1},
        {"name": "Shelly Dimmer 2", "preis": 32.50, "watt": 1},
    ],
    "Verbraucher": [
        {"name": "Steckdose (Standard)", "preis": 8.50, "watt": 200},
        {"name": "Steckdose (Backofen)", "preis": 12.00, "watt": 3000},
        {"name": "Lichtschalter", "preis": 12.00, "watt": 0},
        {"name": "LED Spot", "preis": 25.00, "watt": 7},
    ],
    "Kabel": [
        {"name": "NYM-J 3x1.5", "preis": 0.65, "watt": 0}, 
        {"name": "NYM-J 5x1.5", "preis": 0.95, "watt": 0},
        {"name": "KNX Busleitung", "preis": 0.55, "watt": 0},
    ]
}

# ==========================================
# MODUL 2: VISUALISIERUNG (PLOTS)
# ==========================================

def plot_wiring_tree(strings, materials):
    """Zeichnet den logischen Verteilerplan"""
    dot = graphviz.Digraph(comment='Verteiler')
    dot.attr(rankdir='TB')
    dot.attr('node', fontname='Arial', fontsize='10', shape='box', style='filled')
    
    # Hauptverteiler
    dot.node('UV', '⚡ Hauptverteiler', fillcolor='#ffeb3b', shape='doubleoctagon')

    for s in strings:
        s_id = s['id']
        # Last berechnen
        mats = [m for m in materials if m.get('String') == s_id]
        watts = sum([m.get('Watt', 0) * m['Menge'] for m in mats])
        load = watts * s['factor']
        
        # Auslastung prüfen
        max_load = s['fuse'] * 230
        ratio = load / max_load if max_load > 0 else 0
        
        col = '#c8e6c9' # Grün
        if ratio > 0.8: col = '#fff9c4' # Gelb
        if ratio > 1.0: col = '#ffcdd2' # Rot
        
        label = f"{s['name']}\n({s['fuse']}A)\nLast: {load:.0f}W"
        dot.node(s_id, label, fillcolor=col, shape='folder')
        dot.edge('UV', s_id)
        
        # Geräte (zusammengefasst)
        counts = {}
        for m in mats:
            counts[m['Artikel']] = counts.get(m['Artikel'], 0) + m['Menge']
            
        for art, count in counts.items():
            nid = f"{s_id}_{art}"
            dot.node(nid, f"{count}x {art}", fontsize='8', fillcolor='white')
            dot.edge(s_id, nid)
            
    return dot

def plot_installation_map(rooms, materials, strings, active_idx=None):
    """Zeichnet den Gebäudeplan mit Geräten"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Farben für Strings
    cmap = plt.get_cmap('tab10')
    s_colors = {s['id']: cmap(i%10) for i, s in enumerate(strings)}

    # Räume
    for r in rooms:
        rect = patches.Rectangle((r['x'], r['y']), r['l'], r['b'], linewidth=2, edgecolor='#546e7a', facecolor='#eceff1', alpha=0.5, zorder=1)
        ax.add_patch(rect)
        ax.text(r['x']+0.2, r['y']+r['b']-0.4, r['name'], fontweight='bold', color='#37474f', zorder=2)

    # Geräte
    for idx, m in enumerate(materials):
        # Position ermitteln (Default: Raummitte)
        room = next((r for r in rooms if r['name'] == m['Raum']), None)
        if room:
            # Absolute Koordinaten
            rel_x = m.get('pos_x', room['l']/2)
            rel_y = m.get('pos_y', room['b']/2)
            abs_x = room['x'] + rel_x
            abs_y = room['y'] + rel_y
            
            # Style
            col = s_colors.get(m['String'], 'black')
            is_active = (idx == active_idx)
            size = 150 if is_active else 50
            edge = 'red' if is_active else 'white'
            
            ax.scatter(abs_x, abs_y, c=[col], s=size, edgecolors=edge, linewidth=2, zorder=10)
            if is_active:
                ax.text(abs_x, abs_y+0.5, m['Artikel'], ha='center', fontweight='bold', color='red', zorder=11)

    ax.set_aspect('equal')
    ax.grid(True, linestyle=':', alpha=0.3)
    ax.set_title("Installationsplan")
    
    # Skalierung
    if rooms:
        mx = max([r['x']+r['l'] for r in rooms]) + 1
        my = max([r['y']+r['b'] for r in rooms]) + 1
        ax.set_xlim(-1, mx)
        ax.set_ylim(-1, my)
        
    return fig

# ==========================================
# MODUL 3: HAUPTPROGRAMM (UI)
# ==========================================

# Sidebar: Projektwahl
st.sidebar.title("LEC Manager v1.0")
projs = st.session_state.db_projects
sel_p = st.sidebar.selectbox("Projekt", ["Neues Projekt"] + list(projs.keys()), 
                             format_func=lambda x: "Neues Projekt" if x=="Neues Projekt" else f"{projs[x]['kunde']}")

if sel_p == "Neues Projekt":
    if st.sidebar.button("Erstellen"):
        pid = f"P-{len(projs)+1:03d}"
        st.session_state.db_projects[pid] = {"kunde": "Neu", "ort": "-", "status": "Neu"}
        st.session_state.db_rooms[pid] = []
        st.session_state.db_strings[pid] = []
        st.rerun()
else:
    st.session_state.current_project_id = sel_p

# Hauptfenster
if st.session_state.current_project_id:
    pid = st.session_state.current_project_id
    pdata = st.session_state.db_projects[pid]
    
    st.title(f"Projekt: {pdata['kunde']}")
    
    # DIE VIER SÄULEN DER MACHT
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏗️ Räume (Editor)", 
        "⚡ Stromkreise", 
        "📍 Installation (Map)", 
        "💰 Kalkulation (Liste)"
    ])
    
    # Daten laden
    rooms = st.session_state.db_rooms.get(pid, [])
    strings = st.session_state.db_strings.get(pid, [])
    mats = [m for m in st.session_state.db_material if m['Projekt'] == pid]

    # --- TAB 1: RAUM EDITOR ---
    with tab1:
        c1, c2 = st.columns([1, 2])
        with c1:
            with st.form("add_room"):
                rn = st.text_input("Raum Name")
                l = st.number_input("Länge", 4.0)
                b = st.number_input("Breite", 3.0)
                if st.form_submit_button("Raum anlegen"):
                    rooms.append({"name": rn, "l": l, "b": b, "x": 0.0, "y": 0.0})
                    st.rerun()
            
            if rooms:
                st.divider()
                st.write("**Raum schieben:**")
                ridx = st.radio("Raum:", range(len(rooms)), format_func=lambda i: rooms[i]['name'])
                rooms[ridx]['x'] = st.slider("X", -5.0, 20.0, rooms[ridx]['x'], 0.5)
                rooms[ridx]['y'] = st.slider("Y", -5.0, 20.0, rooms[ridx]['y'], 0.5)
        
        with c2:
            if rooms: st.pyplot(plot_installation_map(rooms, [], [], None))

    # --- TAB 2: STROMKREISE ---
    with tab2:
        c1, c2 = st.columns([1, 2])
        with c1:
            with st.form("add_string"):
                sn = st.text_input("Bezeichnung", "Steckdosen X")
                sf = st.selectbox("Sicherung (A)", [10, 16, 32], index=1)
                sc = st.selectbox("Kabeltyp", [k['name'] for k in PRODUKT_KATALOG['Kabel']])
                sl = st.number_input("Länge (m)", 15)
                if st.form_submit_button("Kreis anlegen"):
                    pr = next(k['preis'] for k in PRODUKT_KATALOG['Kabel'] if k['name']==sc)
                    strings.append({"id": f"S{len(strings)+1}", "name": sn, "fuse": sf, "factor": 0.7, 
                                    "cable_name": sc, "cable_len": sl, "cable_price": pr})
                    st.rerun()
            
            # Liste löschen
            for s in strings:
                if st.button(f"Lösche {s['name']}", key=f"d_{s['id']}"):
                    strings.remove(s); st.rerun()

        with c2:
            st.info("Kabel-Kosten werden automatisch in der Kalkulation (Tab 4) erfasst.")

    # --- TAB 3: INSTALLATION (KARTE) ---
    with tab3:
        if not rooms or not strings:
            st.warning("Erst Räume und Stromkreise anlegen!")
        else:
            c_map, c_tool = st.columns([2, 1])
            
            with c_tool:
                st.subheader("Gerät hinzufügen")
                # Quick Add
                r_sel = st.selectbox("Raum", [r['name'] for r in rooms])
                s_sel = st.selectbox("Stromkreis", [s['id'] for s in strings], format_func=lambda x: next(s['name'] for s in strings if s['id']==x))
                k_sel = st.selectbox("Kategorie", ["Steuerung", "Verbraucher"])
                i_sel = st.selectbox("Artikel", [p['name'] for p in PRODUKT_KATALOG[k_sel]])
                
                if st.button("Platzieren"):
                    p_dat = next(p for p in PRODUKT_KATALOG[k_sel] if p['name']==i_sel)
                    t_room = next(r for r in rooms if r['name']==r_sel)
                    st.session_state.db_material.append({
                        "Projekt": pid, "Raum": r_sel, "String": s_sel, "Artikel": i_sel, "Menge": 1,
                        "Preis": p_dat['preis'], "Watt": p_dat['watt'],
                        "pos_x": t_room['l']/2, "pos_y": t_room['b']/2 # Mitte
                    })
                    st.rerun()

                st.divider()
                st.write("**Fein-Justierung:**")
                if mats:
                    midx = st.radio("Gerät wählen:", range(len(mats)), format_func=lambda i: f"{mats[i]['Artikel']} ({mats[i]['Raum']})")
                    curr_mat = mats[midx]
                    # Original-Objekt im State finden (Achtung: mats ist Kopie/Filter)
                    # Wir nutzen hier vereinfacht den Index, in Produktion bräuchten wir IDs
                    real_idx = st.session_state.db_material.index(curr_mat)
                    
                    # Raum Grenzen für Slider
                    r_lim = next(r for r in rooms if r['name'] == curr_mat['Raum'])
                    
                    nx = st.slider("Pos X", 0.0, float(r_lim['l']), float(curr_mat.get('pos_x', 0)), 0.25, key="m_x")
                    ny = st.slider("Pos Y", 0.0, float(r_lim['b']), float(curr_mat.get('pos_y', 0)), 0.25, key="m_y")
                    
                    st.session_state.db_material[real_idx]['pos_x'] = nx
                    st.session_state.db_material[real_idx]['pos_y'] = ny
                
            with c_map:
                midx = locals().get('midx', None) # Index aus der Spalte nebenan
                st.pyplot(plot_installation_map(rooms, mats, strings, active_idx=midx))
                st.caption("Farben entsprechen den Stromkreisen.")

    # --- TAB 4: KALKULATION (LISTE & BAUM) ---
    with tab4:
        c_list, c_tree = st.columns([1, 1])
        
        with c_list:
            st.subheader("Material & Kosten")
            
            # 1. Materialtabelle
            rows = []
            # A) Echte Geräte
            for m in mats:
                s_name = next((s['name'] for s in strings if s['id'] == m['String']), "?")
                rows.append({
                    "Typ": "Gerät", "Artikel": m['Artikel'], "Raum": m['Raum'], 
                    "Menge": m['Menge'], "Einzel": m['Preis'], "Gesamt": m['Menge']*m['Preis']
                })
            # B) Kabel (Automatisch aus Strings)
            for s in strings:
                rows.append({
                    "Typ": "Kabel", "Artikel": f"Kabel {s['name']}", "Raum": "Infra",
                    "Menge": s['cable_len'], "Einzel": s['cable_price'], "Gesamt": s['cable_len']*s['cable_price']
                })
                
            if rows:
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True, height=300)
                
                total = df['Gesamt'].sum()
                st.success(f"Gesamtsumme (Netto): {total:.2f} €")
            else:
                st.info("Keine Positionen.")

        with c_tree:
            st.subheader("Lastverteilung")
            if strings:
                st.graphviz_chart(plot_wiring_tree(strings, mats))
            else:
                st.write("Keine Stromkreise.")

else:
    st.info("Bitte Projekt wählen.")
