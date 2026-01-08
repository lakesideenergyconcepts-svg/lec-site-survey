import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import graphviz
from PIL import Image
from streamlit_gsheets import GSheetsConnection

# ==========================================
# KONFIGURATION V2.2.1 (Fix Icon Error)
# ==========================================
st.set_page_config(page_title="LEC Manager V2.2.1", page_icon="⚡", layout="wide")

# Verbindung
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_read(worksheet_name, required_columns):
    """Liest Blatt ein, fängt Fehler ab."""
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if df.empty:
            return pd.DataFrame(columns=required_columns)
        
        # Spaltenbereinigung
        df.columns = df.columns.str.lower().str.strip()
        return df
    except Exception as e:
        return pd.DataFrame(columns=required_columns)

def load_data():
    st.cache_data.clear()
    
    # Spalten-Definitionen
    cols_proj = ['id', 'kunde', 'ort', 'bp_width', 'bp_height', 'created_at']
    cols_room = ['projekt_id', 'name', 'l', 'b', 'x', 'y']
    cols_str  = ['projekt_id', 'id', 'name', 'fuse', 'factor', 'cable_name', 'cable_len', 'cable_price']
    cols_mat  = ['projekt_id', 'raum', 'string', 'artikel', 'menge', 'preis', 'watt', 'pos_x', 'pos_y']

    df_proj = safe_read("projekte", cols_proj)
    df_rooms = safe_read("raeume", cols_room)
    df_strings = safe_read("strings", cols_str)
    df_mat = safe_read("installation", cols_mat)
    
    if not df_proj.empty and 'id' in df_proj.columns:
        df_proj = df_proj.dropna(subset=['id'])
    
    return df_proj, df_rooms, df_strings, df_mat

def save_row(worksheet, data_dict):
    """Speichert Daten in Google Sheets."""
    try:
        # HIER WAR DER FEHLER: Icon korrigiert zu '⏳'
        st.info(f"Speichere in '{worksheet}'...", icon="⏳")
        
        # 1. Aktuelle Daten lesen
        df_curr = conn.read(worksheet=worksheet, ttl=0)
        
        # 2. Neue Zeile vorbereiten
        df_new = pd.DataFrame([data_dict])
        
        # 3. Zusammenfügen
        if df_curr.empty:
            df_comb = df_new
        else:
            df_comb = pd.concat([df_curr, df_new], ignore_index=True)
            
        # 4. Schreiben
        conn.update(worksheet=worksheet, data=df_comb)
        
        st.success("Erfolgreich gespeichert!", icon="✅")
        st.cache_data.clear()
        return True 
        
    except Exception as e:
        st.error(f"❌ FEHLER BEIM SPEICHERN in {worksheet}:")
        st.code(str(e)) 
        return False 

# Initial Laden
df_projects, df_rooms, df_strings, df_material = load_data()

# ==========================================
# PLOTTING
# ==========================================
PRODUKT_KATALOG = {
    "Steuerung": [{"name": "Shelly Plus 2PM", "preis": 29.90, "watt": 1}, {"name": "Shelly Dimmer 2", "preis": 32.50, "watt": 1}],
    "Verbraucher": [{"name": "Steckdose", "preis": 8.50, "watt": 200}, {"name": "Lichtschalter", "preis": 12.00, "watt": 0}],
    "Kabel": [{"name": "NYM-J 3x1.5", "preis": 0.65, "watt": 0}, {"name": "NYM-J 5x1.5", "preis": 0.95, "watt": 0}]
}

def plot_installation_map(rooms_df, mats_df, strings_df, active_idx=None, blueprint_img=None, bp_dims=(20,15)):
    fig, ax = plt.subplots(figsize=(10, 7))
    if blueprint_img: ax.imshow(blueprint_img, extent=[0, bp_dims[0], 0, bp_dims[1]], origin='lower', alpha=0.5)

    if not rooms_df.empty:
        for _, r in rooms_df.iterrows():
            rx, ry = float(r.get('x', 0) or 0), float(r.get('y', 0) or 0)
            rl, rb = float(r.get('l', 4) or 4), float(r.get('b', 3) or 3)
            rect = patches.Rectangle((rx, ry), rl, rb, linewidth=2, edgecolor='#0277bd', facecolor='#b3e5fc', alpha=0.3)
            ax.add_patch(rect)
            ax.text(rx+0.2, ry+rb-0.5, str(r['name']), fontweight='bold', color='#01579b')

    if not mats_df.empty and not rooms_df.empty:
        cmap = plt.get_cmap('tab10')
        s_colors = {}
        if not strings_df.empty:
            for i, sid in enumerate(strings_df['id'].unique()): s_colors[sid] = cmap(i%10)

        for idx, m in mats_df.iterrows():
            room = rooms_df[rooms_df['name'] == m['raum']]
            if not room.empty:
                r = room.iloc[0]
                rx, ry = float(r.get('x', 0) or 0), float(r.get('y', 0) or 0)
                rl, rb = float(r.get('l', 4) or 4), float(r.get('b', 3) or 3)
                px = float(m.get('pos_x') if pd.notnull(m.get('pos_x')) else rl/2)
                py = float(m.get('pos_y') if pd.notnull(m.get('pos_y')) else rb/2)
                
                col = s_colors.get(m['string'], 'black')
                size = 180 if (idx == active_idx) else 60
                edge = 'red' if (idx == active_idx) else 'white'
                ax.scatter(rx+px, ry+py, c=[col], s=size, edgecolors=edge, linewidth=2, zorder=10)
    
    ax.set_aspect('equal'); ax.grid(True, linestyle=':', alpha=0.3)
    ax.set_xlim(-1, bp_dims[0]+1); ax.set_ylim(-1, bp_dims[1]+1)
    return fig

def plot_wiring_tree(strings_df, mats_df):
    dot = graphviz.Digraph(comment='Verteiler', node_attr={'shape': 'box', 'style': 'filled'})
    dot.node('UV', '⚡ Hauptverteiler', fillcolor='#ffeb3b', shape='doubleoctagon')
    if not strings_df.empty:
        for _, s in strings_df.iterrows():
            s_id = s['id']
            s_load = 0
            if not mats_df.empty:
                s_mats = mats_df[mats_df['string'] == s_id]
                s_load = (s_mats['menge'] * s_mats['watt']).sum()
            label = f"{s['name']}\n{s_load*float(s['factor']):.0f}W"
            dot.node(s_id, label, fillcolor='#c8e6c9', shape='folder')
            dot.edge('UV', s_id)
    return dot

# ==========================================
# UI HAUPTBEREICH
# ==========================================
st.sidebar.title("LEC Manager V2.2.1")

# Projektliste
proj_list = df_projects['id'].tolist() if not df_projects.empty else []
sel_p = st.sidebar.selectbox("Projekt", ["Neues Projekt"] + proj_list)

if sel_p == "Neues Projekt":
    st.sidebar.subheader("Neues Projekt")
    k = st.sidebar.text_input("Kunde")
    o = st.sidebar.text_input("Ort")
    
    if st.sidebar.button("Projekt erstellen", type="primary"):
        if not k:
            st.sidebar.error("Kunde fehlt!")
        else:
            nid = f"P-{len(proj_list)+1:03d}"
            # Versuch zu speichern
            success = save_row("projekte", {
                "id": nid, "kunde": k, "ort": o, 
                "bp_width": 20.0, "bp_height": 15.0, 
                "created_at": "Neu"
            })
            if success:
                st.rerun()

    cur_pid = None
else:
    cur_pid = sel_p
    p_data = df_projects[df_projects['id'] == cur_pid].iloc[0]
    my_rooms = df_rooms[df_rooms['projekt_id'] == cur_pid] if not df_rooms.empty else pd.DataFrame()
    my_strings = df_strings[df_strings['projekt_id'] == cur_pid] if not df_strings.empty else pd.DataFrame()
    my_mats = df_material[df_material['projekt_id'] == cur_pid] if not df_material.empty else pd.DataFrame()

if cur_pid:
    st.title(f"Projekt: {p_data['kunde']}")
    if 'blueprint' not in st.session_state: st.session_state.blueprint = None
    
    t1, t2, t3, t4 = st.tabs(["🏗️ Gebäude", "⚡ Stromkreise", "📍 Installation", "💰 Liste"])

    # TAB 1
    with t1:
        c1, c2 = st.columns([1, 2])
        with c1:
            up = st.file_uploader("Plan", type=['jpg', 'png'])
            if up: st.session_state.blueprint = Image.open(up)
            
            nw = st.number_input("Breite", value=float(p_data['bp_width']) if pd.notnull(p_data['bp_width']) else 20.0)
            nh = st.number_input("Höhe", value=float(p_data['bp_height']) if pd.notnull(p_data['bp_height']) else 15.0)
            
            st.divider()
            rn = st.text_input("Raum Name", "Raum 1")
            l = st.number_input("Länge", 4.0); b = st.number_input("Breite", 3.0)
            if st.button("Raum speichern"):
                save_row("raeume", {"projekt_id": cur_pid, "name": rn, "l": l, "b": b, "x": nw/2, "y": nh/2})
                st.rerun()

        with c2:
            st.pyplot(plot_installation_map(my_rooms, pd.DataFrame(), pd.DataFrame(), blueprint_img=st.session_state.blueprint, bp_dims=(nw, nh)))

    # TAB 2
    with t2:
        c1, c2 = st.columns(2)
        with c1:
            sn = st.text_input("Kreis Name"); sf = st.selectbox("Sicherung", [10, 16, 32])
            sc = st.selectbox("Kabel", [k['name'] for k in PRODUKT_KATALOG['Kabel']]); sl = st.number_input("Länge", 15)
            if st.button("Stromkreis speichern"):
                pr = next(k['preis'] for k in PRODUKT_KATALOG['Kabel'] if k['name']==sc)
                sid = f"S{len(my_strings)+1}"
                save_row("strings", {"projekt_id": cur_pid, "id": sid, "name": sn, "fuse": sf, "factor": 0.7, "cable_name": sc, "cable_len": sl, "cable_price": pr})
                st.rerun()
        with c2:
            if not my_strings.empty: st.dataframe(my_strings)

    # TAB 3
    with t3:
        if my_rooms.empty or my_strings.empty: st.warning("Fehlende Daten")
        else:
            c1, c2 = st.columns([1, 2])
            with c1:
                r_sel = st.selectbox("Raum", my_rooms['name'].unique())
                s_sel = st.selectbox("Stromkreis", my_strings['id'].unique())
                k_sel = st.selectbox("Kat", ["Steuerung", "Verbraucher"])
                i_sel = st.selectbox("Art", [p['name'] for p in PRODUKT_KATALOG[k_sel]])
                if st.button("Platzieren"):
                    pd = next(p for p in PRODUKT_KATALOG[k_sel] if p['name']==i_sel)
                    t_room = my_rooms[my_rooms['name'] == r_sel].iloc[0]
                    save_row("installation", {
                        "projekt_id": cur_pid, "raum": r_sel, "string": s_sel, "artikel": i_sel, 
                        "menge": 1, "preis": pd['preis'], "watt": pd['watt'], 
                        "pos_x": float(t_room['l'])/2, "pos_y": float(t_room['b'])/2
                    })
                    st.rerun()
            with c2:
                st.pyplot(plot_installation_map(my_rooms, my_mats, my_strings, blueprint_img=st.session_state.blueprint, bp_dims=(nw, nh)))

    # TAB 4
    with t4:
        c1, c2 = st.columns(2)
        with c1:
            if not my_mats.empty:
                st.dataframe(my_mats)
                st.metric("Total", f"{(my_mats['menge'] * my_mats['preis']).sum():.2f} €")
        with c2:
            st.graphviz_chart(plot_wiring_tree(my_strings, my_mats))
else:
    st.info("Bitte Projekt wählen.")
