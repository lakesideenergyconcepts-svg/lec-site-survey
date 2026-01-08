import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import graphviz
import random

# ==========================================
# V1.1 - INIT & KONFIGURATION
# ==========================================
st.set_page_config(page_title="LEC Manager V1.1", page_icon="⚡", layout="wide")

def init_db():
    """Initialisiert die simulierte Datenbank im Session State"""
    defaults = {
        # Projekt-Metadaten + NEU: Blueprint-Infos
        'db_projects': {
            "P-001": {"kunde": "Müller", "ort": "FN", "bp_width": 20.0, "bp_height": 15.0}
        },
        'db_rooms': {
            "P-001": [{"name": "Wohnzimmer", "l": 5.0, "b": 4.0, "x": 1.0, "y": 1.0}]
        },
        'db_strings': {
            "P-001": [{"id": "S1", "name": "Std. Küche", "fuse": 16, "factor": 0.7, "cable_name": "NYM-J 3x1.5", "cable_len": 15, "cable_price": 0.65}]
        },
        'db_material': [],
        # NEU: Speicher für die Bilddaten der Grundrisse
        'db_blueprints_data': {}, 
        'current_project_id': None
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_db()

# --- Katalog (Unverändert) ---
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
# V1.1 - VISUALISIERUNG (PLOTS)
# ==========================================

def plot_wiring_tree(strings, materials):
    """Zeichnet den logischen Verteilerplan (Graphviz)"""
    dot = graphviz.Digraph(comment='Verteiler')
    dot.attr(rankdir='TB')
    dot.attr('node', fontname='Arial', fontsize='10', shape='box', style='filled')
    dot.node('UV', '⚡ Hauptverteiler', fillcolor='#ffeb3b', shape='doubleoctagon')

    for s in strings:
        s_id = s['id']
        mats = [m for m in materials if m.get('String') == s_id]
        watts = sum([m.get('Watt', 0) * m['Menge'] for m in mats])
        load = watts * s['factor']
        max_load = s['fuse'] * 230
        ratio = load / max_load if max_load > 0 else 0
        
        col = '#c8e6c9'
        if ratio > 0.8: col = '#fff9c4'
        if ratio > 1.0: col = '#ffcdd2'
        
        label = f"{s['name']}\n({s['fuse']}A)\nLast: {load:.0f}W"
        dot.node(s_id, label, fillcolor=col, shape='folder')
        dot.edge('UV', s_id)
        
        counts = {}
        for m in mats: counts[m['Artikel']] = counts.get(m['Artikel'], 0) + m['Menge']
        for art, count in counts.items():
            nid = f"{s_id}_{art}"
            dot.node(nid, f"{count}x {art}", fontsize='8', fillcolor='white')
            dot.edge(s_id, nid)
    return dot

def plot_installation_map(rooms, materials, strings, active_idx=None, blueprint_img=None, bp_dims=(20,15)):
    """
    Zeichnet den Gebäudeplan.
    NEU: Unterstützt jetzt ein Hintergrundbild (blueprint_img) und dessen Dimensionen (bp_dims).
    """
    fig, ax = plt.subplots(figsize=(10, 7))
    
    # --- LAYER 0: BLUEPRINT (Hintergrundplan) ---
    if blueprint_img is not None:
        # Das Bild wird von (0,0) bis (Breite, Höhe) gestreckt
        # origin='lower' ist wichtig, damit Y=0 unten ist, wie bei unserem Koordinatensystem
        ax.imshow(blueprint_img, extent=[0, bp_dims[0], 0, bp_dims[1]], origin='lower', alpha=0.4)

    # --- LAYER 1: RÄUME (Gezeichnete Wände) ---
    for r in rooms:
        # Etwas transparenter, damit man den Plan darunter sieht
        rect = patches.Rectangle((r['x'], r['y']), r['l'], r['b'], linewidth=2, edgecolor='#0277bd', facecolor='#b3e5fc', alpha=0.3, zorder=5)
        ax.add_patch(rect)
        ax.text(r['x']+0.2, r['y']+r['b']-0.4, r['name'], fontweight='bold', color='#01579b', zorder=6)

    # --- LAYER 2: GERÄTE (Punkte) ---
    cmap = plt.get_cmap('tab10')
    s_colors = {s['id']: cmap(i%10) for i, s in enumerate(strings)}

    for idx, m in enumerate(materials):
        room = next((r for r in rooms if r['name'] == m['Raum']), None)
        if room:
            rel_x = m.get('pos_x', room['l']/2)
            rel_y = m.get('pos_y', room['b']/2)
            abs_x = room['x'] + rel_x
            abs_y = room['y'] + rel_y
            
            col = s_colors.get(m['String'], 'black')
            is_active = (idx == active_idx)
            size = 180 if is_active else 60
            edge = 'red' if is_active else 'white'
            
            # Z-Order hoch, damit sie über dem Plan liegen
            ax.scatter(abs_x, abs_y, c=[col], s=size, edgecolors=edge, linewidth=2, zorder=10)
            if is_active:
                ax.text(abs_x, abs_y+0.6, m['Artikel'], ha='center', fontweight='bold', color='red', zorder=11, bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

    ax.set_aspect('equal')
    ax.grid(True, linestyle=':', alpha=0.2)
    ax.set_title("Installationsplan (Mit Blueprint Overlay)")
    
    # Skalierung: Entweder Blueprint-Größe oder Raum-Größe, je nachdem was größer ist
    max_x = bp_dims[0] if blueprint_img is not None else 20
    max_y = bp_dims[1] if blueprint_img is not None else 15

    if rooms:
        max_x = max(max_x, max([r['x']+r['l'] for r in rooms]) + 1)
        max_y = max(max_y, max([r['y']+r['b'] for r in rooms]) + 1)

    ax.set_xlim(-1, max_x)
    ax.set_ylim(-1, max_y)
        
    return fig

# ==========================================
# V1.1 - HAUPTPROGRAMM (UI)
# ==========================================

# Sidebar
st.sidebar.title("LEC Manager v1.1")
projs = st.session_state.db_projects
sel_p = st.sidebar.selectbox("Projekt", ["Neues Projekt"] + list(projs.keys()), 
                             format_func=lambda x: "Neues Projekt" if x=="Neues Projekt" else f"{projs[x]['kunde']}")

if sel_p == "Neues Projekt":
    if st.sidebar.button("Erstellen"):
        pid = f"P-{len(projs)+1:03d}"
        # Default Blueprint Größe: 20x15m
        st.session_state.db_projects[pid] = {"kunde": "Neu", "ort": "-", "bp_width": 20.0, "bp_height": 15.0}
        st.session_state.db_rooms[pid] = []
        st.session_state.db_strings[pid] = []
        st.rerun()
else:
    st.session_state.current_project_id = sel_p

# Main App
if st.session_state.current_project_id:
    pid = st.session_state.current_project_id
    pdata = st.session_state.db_projects[pid]
    
    st.title(f"Projekt: {pdata['kunde']}")
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🏗️ Gebäude & Plan", "⚡ Stromkreise", "📍 Installation", "💰 Liste"])
    
    # Daten laden
    rooms = st.session_state.db_rooms.get(pid, [])
    strings = st.session_state.db_strings.get(pid, [])
    mats = [m for m in st.session_state.db_material if m['Projekt'] == pid]
    
    # Blueprint Daten laden (falls vorhanden)
    blueprint_data = st.session_state.db_blueprints_data.get(pid)
    bp_w = pdata.get('bp_width', 20.0)
    bp_h = pdata.get('bp_height', 15.0)

    # --- TAB 1: GEBÄUDE & BLUEPRINT ---
    with tab1:
        c_conf, c_view = st.columns([1, 2])
        
        with c_conf:
            # 1. BLUEPRINT UPLOAD
            st.subheader("1. Gebäudeplan (Optional)")
            with st.expander("🖨️ Plan hochladen & skalieren", expanded=True):
                uploaded_file = st.file_uploader("Bilddatei (JPG/PNG)", type=['png', 'jpg', 'jpeg'])
                if uploaded_file is not None:
                    # Bild im Session State speichern (temporär)
                    st.session_state.db_blueprints_data[pid] = uploaded_file
                    blueprint_data = uploaded_file # Sofort verfügbar machen
                    st.success("Plan geladen!")
                
                st.write("**Plan-Skalierung (in Metern):**")
                st.caption("Wie groß ist der Bereich, den der Plan zeigt?")
                c_w, c_h = st.columns(2)
                new_w = c_w.number_input("Breite (X)", value=bp_w, key="bpw")
                new_h = c_h.number_input("Höhe (Y)", value=bp_h, key="bph")
                
                # Speichern der Dimensionen bei Änderung
                if new_w != bp_w or new_h != bp_h:
                    st.session_state.db_projects[pid]['bp_width'] = new_w
                    st.session_state.db_projects[pid]['bp_height'] = new_h
                    st.rerun()

            st.divider()

            # 2. RÄUME DEFINIEREN
            st.subheader("2. Räume einzeichnen")
            with st.form("add_room"):
                rn = st.text_input("Name", "Raum 1")
                c_l, c_b = st.columns(2)
                l = c_l.number_input("Länge", value=4.0)
                b = c_b.number_input("Breite", value=3.0)
                if st.form_submit_button("Raum anlegen"):
                    # Default Position mittig im Plan
                    rooms.append({"name": rn, "l": l, "b": b, "x": bp_w/2-l/2, "y": bp_h/2-b/2})
                    st.rerun()
            
            if rooms:
                st.write("**Raum verschieben:**")
                ridx = st.radio("Raum:", range(len(rooms)), format_func=lambda i: rooms[i]['name'])
                rooms[ridx]['x'] = st.slider("X-Pos", -5.0, bp_w+5, rooms[ridx]['x'], 0.5)
                rooms[ridx]['y'] = st.slider("Y-Pos", -5.0, bp_h+5, rooms[ridx]['y'], 0.5)
        
        with c_view:
            # Plot mit Blueprint!
            fig = plot_installation_map(rooms, [], strings, blueprint_img=blueprint_data, bp_dims=(new_w, new_h))
            st.pyplot(fig)
            st.caption("Tipp: Passen Sie die 'Plan-Skalierung' links an, damit das Raster stimmt.")

    # --- TAB 2: STROMKREISE (Unverändert) ---
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
            for s in strings:
                if st.button(f"Lösche {s['name']}", key=f"d_{s['id']}"): strings.remove(s); st.rerun()
        with c2: st.info("Kabelkosten erscheinen in Tab 4.")

    # --- TAB 3: INSTALLATION (KARTE MIT BLUEPRINT) ---
    with tab3:
        if not rooms or not strings:
            st.warning("Erst Räume und Stromkreise anlegen!")
        else:
            c_map, c_tool = st.columns([2, 1])
            with c_tool:
                # Quick Add
                st.subheader("Geräte")
                r_sel = st.selectbox("Raum", [r['name'] for r in rooms], key="qa_r")
                s_sel = st.selectbox("String", [s['id'] for s in strings], format_func=lambda x: next(s['name'] for s in strings if s['id']==x), key="qa_s")
                k_sel = st.selectbox("Kat", ["Steuerung", "Verbraucher"], key="qa_k")
                i_sel = st.selectbox("Art", [p['name'] for p in PRODUKT_KATALOG[k_sel]], key="qa_i")
                if st.button("Platzieren"):
                    p_dat = next(p for p in PRODUKT_KATALOG[k_sel] if p['name']==i_sel)
                    t_room = next(r for r in rooms if r['name']==r_sel)
                    st.session_state.db_material.append({
                        "Projekt": pid, "Raum": r_sel, "String": s_sel, "Artikel": i_sel, "Menge": 1,
                        "Preis": p_dat['preis'], "Watt": p_dat['watt'], "pos_x": t_room['l']/2, "pos_y": t_room['b']/2
                    })
                    st.rerun()

                # Positionierung
                st.divider()
                if mats:
                    st.write("**Fein-Positionierung:**")
                    midx = st.radio("Gerät:", range(len(mats)), format_func=lambda i: f"{mats[i]['Artikel']} ({mats[i]['Raum']})")
                    curr_mat = mats[midx]
                    real_idx = st.session_state.db_material.index(curr_mat)
                    r_lim = next(r for r in rooms if r['name'] == curr_mat['Raum'])
                    nx = st.slider("X (im Raum)", 0.0, float(r_lim['l']), float(curr_mat.get('pos_x', 0)), 0.25, key="m_x")
                    ny = st.slider("Y (im Raum)", 0.0, float(r_lim['b']), float(curr_mat.get('pos_y', 0)), 0.25, key="m_y")
                    st.session_state.db_material[real_idx]['pos_x'] = nx
                    st.session_state.db_material[real_idx]['pos_y'] = ny
                else:
                    midx = None

            with c_map:
                # Plotten MIT Blueprint Daten
                fig = plot_installation_map(rooms, mats, strings, active_idx=midx, blueprint_img=blueprint_data, bp_dims=(bp_w, bp_h))
                st.pyplot(fig)

    # --- TAB 4: KALKULATION (Unverändert) ---
    with tab4:
        c_list, c_tree = st.columns([1, 1])
        with c_list:
            rows = []
            for m in mats:
                rows.append({"Typ": "Gerät", "Artikel": m['Artikel'], "Menge": m['Menge'], "Gesamt": m['Menge']*m['Preis']})
            for s in strings:
                rows.append({"Typ": "Kabel", "Artikel": f"Kabel {s['name']}", "Menge": s['cable_len'], "Gesamt": s['cable_len']*s['cable_price']})
            if rows:
                df = pd.DataFrame(rows)
                st.dataframe(df[["Typ", "Artikel", "Menge", "Gesamt"]], use_container_width=True)
                st.success(f"Summe Netto: {df['Gesamt'].sum():.2f} €")
        with c_tree:
            if strings: st.graphviz_chart(plot_wiring_tree(strings, mats))

else:
    st.info("Bitte Projekt wählen.")
