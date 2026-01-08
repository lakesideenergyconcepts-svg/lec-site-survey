import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import graphviz
from PIL import Image

# ==========================================
# CONFIG & DB
# ==========================================
st.set_page_config(page_title="LEC Manager V1.2", page_icon="⚡", layout="wide")

def init_db():
    defaults = {
        'db_projects': {
            "P-001": {"kunde": "Müller", "ort": "FN", "bp_width": 20.0, "bp_height": 15.0}
        },
        'db_rooms': {
            "P-001": [{"name": "Wohnzimmer", "l": 5.0, "b": 4.0, "x": 2.0, "y": 2.0}]
        },
        'db_strings': {
            "P-001": [{"id": "S1", "name": "Steckdosen", "fuse": 16, "factor": 0.7, "cable_name": "NYM-J 3x1.5", "cable_len": 15, "cable_price": 0.65}]
        },
        'db_material': [],
        'db_blueprints_data': {}, 
        'current_project_id': None
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_db()

PRODUKT_KATALOG = {
    "Steuerung": [{"name": "Shelly Plus 2PM", "preis": 29.90, "watt": 1}, {"name": "Shelly Dimmer 2", "preis": 32.50, "watt": 1}],
    "Verbraucher": [{"name": "Steckdose", "preis": 8.50, "watt": 200}, {"name": "Lichtschalter", "preis": 12.00, "watt": 0}],
    "Kabel": [{"name": "NYM-J 3x1.5", "preis": 0.65, "watt": 0}, {"name": "NYM-J 5x1.5", "preis": 0.95, "watt": 0}]
}

# ==========================================
# PLOTTING
# ==========================================

def plot_wiring_tree(strings, materials):
    dot = graphviz.Digraph(comment='Verteiler')
    dot.attr(rankdir='TB', bgcolor='transparent')
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
        dot.node(s_id, f"{s['name']}\n{load:.0f}W", fillcolor=col, shape='folder')
        dot.edge('UV', s_id)
    return dot

def plot_installation_map(rooms, materials, strings, active_idx=None, blueprint_img=None, bp_dims=(20,15)):
    # Figure Size anpassen
    fig, ax = plt.subplots(figsize=(10, 7))
    
    # 1. BLUEPRINT (Hintergrund)
    if blueprint_img is not None:
        # Extent definiert die Grenzen: [Links, Rechts, Unten, Oben]
        ax.imshow(blueprint_img, extent=[0, bp_dims[0], 0, bp_dims[1]], origin='lower', alpha=0.5)

    # 2. RÄUME
    for r in rooms:
        rect = patches.Rectangle((r['x'], r['y']), r['l'], r['b'], linewidth=2, edgecolor='#0277bd', facecolor='#b3e5fc', alpha=0.3, zorder=5)
        ax.add_patch(rect)
        ax.text(r['x']+0.2, r['y']+r['b']-0.5, r['name'], fontweight='bold', color='#01579b', zorder=6)

    # 3. GERÄTE
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
            
            ax.scatter(abs_x, abs_y, c=[col], s=size, edgecolors=edge, linewidth=2, zorder=10)
            if is_active:
                ax.text(abs_x, abs_y+0.6, m['Artikel'], ha='center', fontweight='bold', color='red', zorder=11, bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

    ax.set_aspect('equal')
    ax.grid(True, linestyle=':', alpha=0.3)
    ax.set_title("Installationsplan")
    
    # Grenzen setzen
    max_x = bp_dims[0] if blueprint_img else 20
    max_y = bp_dims[1] if blueprint_img else 15
    if rooms:
        max_x = max(max_x, max([r['x']+r['l'] for r in rooms]) + 1)
        max_y = max(max_y, max([r['y']+r['b'] for r in rooms]) + 1)
    
    ax.set_xlim(-1, max_x)
    ax.set_ylim(-1, max_y)
    return fig

# ==========================================
# UI
# ==========================================
st.sidebar.title("LEC Manager v1.2")
projs = st.session_state.db_projects
sel_p = st.sidebar.selectbox("Projekt", ["Neues Projekt"] + list(projs.keys()), 
                             format_func=lambda x: "Neues Projekt" if x=="Neues Projekt" else f"{projs[x]['kunde']}")

if sel_p == "Neues Projekt":
    if st.sidebar.button("Erstellen"):
        pid = f"P-{len(projs)+1:03d}"
        st.session_state.db_projects[pid] = {"kunde": "Neu", "ort": "-", "bp_width": 20.0, "bp_height": 15.0}
        st.session_state.db_rooms[pid] = []
        st.session_state.db_strings[pid] = []
        st.rerun()
else:
    st.session_state.current_project_id = sel_p

if st.session_state.current_project_id:
    pid = st.session_state.current_project_id
    pdata = st.session_state.db_projects[pid]
    
    st.title(f"Projekt: {pdata['kunde']}")
    
    tab1, tab2, tab3, tab4 = st.tabs(["🏗️ Plan & Räume", "⚡ Stromkreise", "📍 Installation", "💰 Liste"])
    
    # DATEN LADEN
    rooms = st.session_state.db_rooms.get(pid, [])
    strings = st.session_state.db_strings.get(pid, [])
    mats = [m for m in st.session_state.db_material if m['Projekt'] == pid]
    
    blueprint_data = st.session_state.db_blueprints_data.get(pid)
    bp_w = pdata.get('bp_width', 20.0)
    bp_h = pdata.get('bp_height', 15.0)

    # --- TAB 1: BLUEPRINT & RÄUME ---
    with tab1:
        c_conf, c_view = st.columns([1, 2])
        with c_conf:
            st.subheader("1. Gebäudeplan")
            
            # FILE UPLOADER
            uploaded_file = st.file_uploader("Grundriss laden (Bild)", type=['png', 'jpg', 'jpeg'], key="bp_upload")
            
            if uploaded_file is not None:
                try:
                    # Bild laden und im State speichern
                    image = Image.open(uploaded_file)
                    st.session_state.db_blueprints_data[pid] = image
                    blueprint_data = image
                    st.success("Bild erfolgreich geladen!")
                    # VORSCHAU ANZEIGEN (Damit man sieht, dass es geklappt hat)
                    st.image(image, caption="Vorschau", use_container_width=True)
                except Exception as e:
                    st.error(f"Fehler beim Laden: {e}")
            
            elif blueprint_data:
                st.info("Plan ist aktiv.")
                with st.expander("Aktuellen Plan anzeigen"):
                    st.image(blueprint_data, caption="Aktiver Plan", use_container_width=True)

            st.divider()
            st.write("**Skalierung:**")
            c_w, c_h = st.columns(2)
            nw = c_w.number_input("Breite (m)", value=bp_w)
            nh = c_h.number_input("Höhe (m)", value=bp_h)
            if nw != bp_w or nh != bp_h:
                st.session_state.db_projects[pid]['bp_width'] = nw
                st.session_state.db_projects[pid]['bp_height'] = nh
                st.rerun()

            st.divider()
            st.subheader("2. Raum Editor")
            with st.form("new_room"):
                rn = st.text_input("Name", "Raum 01")
                cl, cb = st.columns(2)
                l = cl.number_input("Länge", 4.0)
                b = cb.number_input("Breite", 3.0)
                if st.form_submit_button("Raum erstellen"):
                    rooms.append({"name": rn, "l": l, "b": b, "x": nw/2, "y": nh/2})
                    st.rerun()
            
            if rooms:
                st.write("Raum schieben:")
                ri = st.radio("Wahl:", range(len(rooms)), format_func=lambda i: rooms[i]['name'])
                rooms[ri]['x'] = st.slider("X", -5.0, nw+5, rooms[ri]['x'], 0.5)
                rooms[ri]['y'] = st.slider("Y", -5.0, nh+5, rooms[ri]['y'], 0.5)

        with c_view:
            # PLOT AUFRUFEN
            fig = plot_installation_map(rooms, [], strings, blueprint_img=blueprint_data, bp_dims=(nw, nh))
            st.pyplot(fig)

    # --- TAB 2: STROMKREISE ---
    with tab2:
        c1, c2 = st.columns([1, 2])
        with c1:
            with st.form("ns"):
                sn = st.text_input("Name", "Kreis")
                sf = st.selectbox("Sicherung", [10, 16, 32], index=1)
                sc = st.selectbox("Kabel", [k['name'] for k in PRODUKT_KATALOG['Kabel']])
                sl = st.number_input("Länge", 15)
                if st.form_submit_button("Add"):
                    pr = next(k['preis'] for k in PRODUKT_KATALOG['Kabel'] if k['name']==sc)
                    strings.append({"id": f"S{len(strings)+1}", "name": sn, "fuse": sf, "factor": 0.7, "cable_name": sc, "cable_len": sl, "cable_price": pr})
                    st.rerun()
            for s in strings:
                if st.button(f"Del {s['name']}", key=f"d{s['id']}"): strings.remove(s); st.rerun()
        with c2: st.info("Details in Tab 4.")

    # --- TAB 3: INSTALLATION ---
    with tab3:
        if not rooms or not strings: st.warning("Fehlende Daten (Räume/Kreise)")
        else:
            cm, ct = st.columns([2, 1])
            with ct:
                st.subheader("Platzierung")
                r = st.selectbox("Raum", [r['name'] for r in rooms], key="qr")
                s = st.selectbox("Kreis", [s['id'] for s in strings], format_func=lambda x: next(si['name'] for si in strings if si['id']==x), key="qs")
                k = st.selectbox("Kat", ["Steuerung", "Verbraucher"], key="qk")
                i = st.selectbox("Art", [p['name'] for p in PRODUKT_KATALOG[k]], key="qi")
                if st.button("Setzen"):
                    pd = next(p for p in PRODUKT_KATALOG[k] if p['name']==i)
                    tr = next(rx for rx in rooms if rx['name']==r)
                    st.session_state.db_material.append({
                        "Projekt": pid, "Raum": r, "String": s, "Artikel": i, "Menge": 1, 
                        "Preis": pd['preis'], "Watt": pd['watt'], "pos_x": tr['l']/2, "pos_y": tr['b']/2
                    })
                    st.rerun()
                
                st.divider()
                if mats:
                    mi = st.radio("Edit:", range(len(mats)), format_func=lambda x: f"{mats[x]['Artikel']}")
                    cm_ = mats[mi]
                    rix = st.session_state.db_material.index(cm_)
                    rl = next(rx for rx in rooms if rx['name']==cm_['Raum'])
                    st.session_state.db_material[rix]['pos_x'] = st.slider("X", 0.0, rl['l'], cm_['pos_x'], 0.25, key="mx")
                    st.session_state.db_material[rix]['pos_y'] = st.slider("Y", 0.0, rl['b'], cm_['pos_y'], 0.25, key="my")
                else: mi = None
            
            with cm:
                st.pyplot(plot_installation_map(rooms, mats, strings, active_idx=mi, blueprint_img=blueprint_data, bp_dims=(bp_w, bp_h)))

    # --- TAB 4: LISTE ---
    with tab4:
        cl, ct = st.columns(2)
        with cl:
            d = []
            for m in mats: d.append({"Typ": "Item", "Name": m['Artikel'], "€": m['Preis']})
            for s in strings: d.append({"Typ": "Kabel", "Name": s['cable_name'], "€": s['cable_len']*s['cable_price']})
            if d:
                df = pd.DataFrame(d)
                st.dataframe(df, use_container_width=True)
                st.metric("Total", f"{df['€'].sum():.2f} €")
        with ct:
            if strings: st.graphviz_chart(plot_wiring_tree(strings, mats))
