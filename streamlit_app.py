import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import graphviz
from PIL import Image
from streamlit_gsheets import GSheetsConnection

# ==========================================
# KONFIGURATION & DATENBANK
# ==========================================
st.set_page_config(page_title="LEC Manager V2.1", page_icon="⚡", layout="wide")

# Verbindung (Cache TTL=0 damit wir Änderungen sofort sehen)
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_read(worksheet_name, required_columns):
    """Liest ein Blatt sicher ein, auch wenn es leer ist."""
    try:
        # Wir lesen ohne 'usecols', um 400-Fehler bei leeren Blättern zu vermeiden
        df = conn.read(worksheet=worksheet_name, ttl=0)
        
        # Wenn das Blatt leer ist oder Spalten fehlen, leeres DF zurückgeben
        if df.empty or len(df.columns) == 0:
            return pd.DataFrame(columns=required_columns)
        
        # Spaltennamen normalisieren (Lower case und Strip) für Robustheit
        df.columns = df.columns.str.lower().str.strip()
        
        # Sicherstellen, dass alle benötigten Spalten da sind (sonst füllen wir mit None)
        for col in required_columns:
            if col not in df.columns:
                df[col] = None
                
        return df
    except Exception:
        # Fallback, falls das Blatt gar nicht existiert oder komplett leer ist
        return pd.DataFrame(columns=required_columns)

def load_data():
    st.cache_data.clear()
    
    # Definition der erwarteten Spalten
    cols_proj = ['id', 'kunde', 'ort', 'bp_width', 'bp_height', 'created_at']
    cols_room = ['projekt_id', 'name', 'l', 'b', 'x', 'y']
    cols_str  = ['projekt_id', 'id', 'name', 'fuse', 'factor', 'cable_name', 'cable_len', 'cable_price']
    cols_mat  = ['projekt_id', 'raum', 'string', 'artikel', 'menge', 'preis', 'watt', 'pos_x', 'pos_y']

    # Sicheres Laden
    df_proj = safe_read("projekte", cols_proj)
    df_rooms = safe_read("raeume", cols_room)
    df_strings = safe_read("strings", cols_str)
    df_mat = safe_read("installation", cols_mat)

    # Bereinigen (Leere Zeilen raus)
    df_proj = df_proj.dropna(subset=['id'])
    
    return df_proj, df_rooms, df_strings, df_mat

def save_row(worksheet, data_dict):
    """Speichert eine Zeile."""
    try:
        # Aktuellen Stand holen
        df_curr = conn.read(worksheet=worksheet, ttl=0)
        # Neue Zeile anhängen
        df_new = pd.DataFrame([data_dict])
        df_comb = pd.concat([df_curr, df_new], ignore_index=True)
        # Update
        conn.update(worksheet=worksheet, data=df_comb)
        st.toast(f"Gespeichert in {worksheet}!", icon="💾")
        st.cache_data.clear() # Cache invalidieren
    except Exception as e:
        st.error(f"Speicherfehler: {e}")

# Initiales Laden
df_projects, df_rooms, df_strings, df_material = load_data()

# ==========================================
# HELPER
# ==========================================
PRODUKT_KATALOG = {
    "Steuerung": [{"name": "Shelly Plus 2PM", "preis": 29.90, "watt": 1}, {"name": "Shelly Dimmer 2", "preis": 32.50, "watt": 1}],
    "Verbraucher": [{"name": "Steckdose", "preis": 8.50, "watt": 200}, {"name": "Lichtschalter", "preis": 12.00, "watt": 0}],
    "Kabel": [{"name": "NYM-J 3x1.5", "preis": 0.65, "watt": 0}, {"name": "NYM-J 5x1.5", "preis": 0.95, "watt": 0}]
}

def plot_installation_map(rooms_df, mats_df, strings_df, active_idx=None, blueprint_img=None, bp_dims=(20,15)):
    fig, ax = plt.subplots(figsize=(10, 7))
    
    # Blueprint
    if blueprint_img:
        ax.imshow(blueprint_img, extent=[0, bp_dims[0], 0, bp_dims[1]], origin='lower', alpha=0.5)

    # Räume
    if not rooms_df.empty:
        for _, r in rooms_df.iterrows():
            # Fallback falls Werte fehlen
            rx, ry = float(r.get('x', 0) or 0), float(r.get('y', 0) or 0)
            rl, rb = float(r.get('l', 4) or 4), float(r.get('b', 3) or 3)
            
            rect = patches.Rectangle((rx, ry), rl, rb, linewidth=2, edgecolor='#0277bd', facecolor='#b3e5fc', alpha=0.3)
            ax.add_patch(rect)
            ax.text(rx+0.2, ry+rb-0.5, str(r['name']), fontweight='bold', color='#01579b')

    # Geräte
    if not mats_df.empty and not rooms_df.empty:
        # Farben generieren
        cmap = plt.get_cmap('tab10')
        s_colors = {}
        if not strings_df.empty:
            for i, sid in enumerate(strings_df['id'].unique()):
                s_colors[sid] = cmap(i%10)

        for idx, m in mats_df.iterrows():
            # Raum finden
            room = rooms_df[rooms_df['name'] == m['raum']]
            if not room.empty:
                r = room.iloc[0]
                rx, ry = float(r.get('x', 0) or 0), float(r.get('y', 0) or 0)
                rl, rb = float(r.get('l', 4) or 4), float(r.get('b', 3) or 3)
                
                # Position
                px = float(m.get('pos_x') if pd.notnull(m.get('pos_x')) else rl/2)
                py = float(m.get('pos_y') if pd.notnull(m.get('pos_y')) else rb/2)
                
                abs_x, abs_y = rx + px, ry + py
                
                col = s_colors.get(m['string'], 'black')
                is_active = (idx == active_idx)
                size = 180 if is_active else 60
                edge = 'red' if is_active else 'white'
                
                ax.scatter(abs_x, abs_y, c=[col], s=size, edgecolors=edge, linewidth=2, zorder=10)

    ax.set_aspect('equal')
    ax.grid(True, linestyle=':', alpha=0.3)
    ax.set_xlim(-1, bp_dims[0]+1); ax.set_ylim(-1, bp_dims[1]+1)
    return fig

def plot_wiring_tree(strings_df, mats_df):
    dot = graphviz.Digraph(comment='Verteiler')
    dot.attr(rankdir='TB', bgcolor='transparent')
    dot.attr('node', fontname='Arial', fontsize='10', shape='box', style='filled')
    dot.node('UV', '⚡ Hauptverteiler', fillcolor='#ffeb3b', shape='doubleoctagon')

    if not strings_df.empty:
        for _, s in strings_df.iterrows():
            s_id = s['id']
            # Last berechnen
            s_load = 0
            if not mats_df.empty:
                s_mats = mats_df[mats_df['string'] == s_id]
                s_load = (s_mats['menge'] * s_mats['watt']).sum()
            
            s_load_calc = s_load * float(s['factor'])
            label = f"{s['name']}\n{s_load_calc:.0f}W"
            dot.node(s_id, label, fillcolor='#c8e6c9', shape='folder')
            dot.edge('UV', s_id)
            
    return dot

# ==========================================
# APP UI
# ==========================================
st.sidebar.title("LEC Manager V2.1")

# PROJEKT WAHL
proj_list = df_projects['id'].tolist() if not df_projects.empty else []
sel_p = st.sidebar.selectbox("Projekt", ["Neues Projekt"] + proj_list)

if sel_p == "Neues Projekt":
    st.sidebar.subheader("Neues Projekt")
    with st.sidebar.form("np"):
        k = st.text_input("Kunde"); o = st.text_input("Ort")
        if st.form_submit_button("Starten"):
            # ID generieren
            nid = f"P-{len(proj_list)+1:03d}"
            save_row("projekte", {"id": nid, "kunde": k, "ort": o, "bp_width": 20.0, "bp_height": 15.0, "created_at": "Neu"})
            st.rerun()
    cur_pid = None
else:
    cur_pid = sel_p
    # Daten filtern
    p_data = df_projects[df_projects['id'] == cur_pid].iloc[0]
    my_rooms = df_rooms[df_rooms['projekt_id'] == cur_pid] if not df_rooms.empty else pd.DataFrame()
    my_strings = df_strings[df_strings['projekt_id'] == cur_pid] if not df_strings.empty else pd.DataFrame()
    my_mats = df_material[df_material['projekt_id'] == cur_pid] if not df_material.empty else pd.DataFrame()

if cur_pid:
    st.title(f"Projekt: {p_data['kunde']}")
    
    # Blueprint Session State
    if 'blueprint' not in st.session_state: st.session_state.blueprint = None
    
    t1, t2, t3, t4 = st.tabs(["🏗️ Gebäude", "⚡ Stromkreise", "📍 Installation", "💰 Liste"])

    # --- TAB 1: GEBÄUDE ---
    with t1:
        c1, c2 = st.columns([1, 2])
        with c1:
            up = st.file_uploader("Plan Upload", type=['jpg', 'png'])
            if up: st.session_state.blueprint = Image.open(up)
            
            st.write("**Skalierung:**")
            # Wir nutzen float() um sicherzustellen, dass es Zahlen sind
            cur_w = float(p_data['bp_width']) if pd.notnull(p_data['bp_width']) else 20.0
            cur_h = float(p_data['bp_height']) if pd.notnull(p_data['bp_height']) else 15.0
            
            nw = st.number_input("Breite", value=cur_w)
            nh = st.number_input("Höhe", value=cur_h)
            # Update Button sparen wir uns hier für Performance, ist in DB erst beim nächsten Reload fix
            
            st.divider()
            with st.form("nr"):
                rn = st.text_input("Raum Name", "Raum 1")
                l = st.number_input("Länge", 4.0); b = st.number_input("Breite", 3.0)
                if st.form_submit_button("Raum speichern"):
                    save_row("raeume", {"projekt_id": cur_pid, "name": rn, "l": l, "b": b, "x": nw/2, "y": nh/2})
                    st.rerun()
        with c2:
            fig = plot_installation_map(my_rooms, pd.DataFrame(), pd.DataFrame(), blueprint_img=st.session_state.blueprint, bp_dims=(nw, nh))
            st.pyplot(fig)

    # --- TAB 2: STRINGS ---
    with t2:
        c1, c2 = st.columns(2)
        with c1:
            with st.form("ns"):
                sn = st.text_input("Bezeichnung"); sf = st.selectbox("Sicherung", [10, 16, 32])
                sc = st.selectbox("Kabel", [k['name'] for k in PRODUKT_KATALOG['Kabel']])
                sl = st.number_input("Länge", 15)
                if st.form_submit_button("Anlegen"):
                    pr = next(k['preis'] for k in PRODUKT_KATALOG['Kabel'] if k['name']==sc)
                    # ID generieren
                    sid = f"S{len(my_strings)+1}"
                    save_row("strings", {"projekt_id": cur_pid, "id": sid, "name": sn, "fuse": sf, "factor": 0.7, "cable_name": sc, "cable_len": sl, "cable_price": pr})
                    st.rerun()
        with c2:
            if not my_strings.empty: st.dataframe(my_strings[['name', 'fuse', 'cable_name']])

    # --- TAB 3: INSTALLATION ---
    with t3:
        if my_rooms.empty or my_strings.empty:
            st.warning("Bitte erst Räume und Stromkreise anlegen.")
        else:
            c1, c2 = st.columns([1, 2])
            with c1:
                r_sel = st.selectbox("Raum", my_rooms['name'].unique())
                s_sel = st.selectbox("Stromkreis", my_strings['id'].unique())
                k_sel = st.selectbox("Kategorie", ["Steuerung", "Verbraucher"])
                i_sel = st.selectbox("Artikel", [p['name'] for p in PRODUKT_KATALOG[k_sel]])
                
                if st.button("Hinzufügen"):
                    p_info = next(p for p in PRODUKT_KATALOG[k_sel] if p['name']==i_sel)
                    # Raum Maße für Default Pos
                    t_room = my_rooms[my_rooms['name'] == r_sel].iloc[0]
                    rx, ry = float(t_room.get('l', 4)), float(t_room.get('b', 3))
                    
                    save_row("installation", {
                        "projekt_id": cur_pid, "raum": r_sel, "string": s_sel, "artikel": i_sel, 
                        "menge": 1, "preis": p_info['preis'], "watt": p_info['watt'], 
                        "pos_x": rx/2, "pos_y": ry/2
                    })
                    st.rerun()
            with c2:
                fig = plot_installation_map(my_rooms, my_mats, my_strings, blueprint_img=st.session_state.blueprint, bp_dims=(nw, nh))
                st.pyplot(fig)

    # --- TAB 4: LISTE ---
    with t4:
        c1, c2 = st.columns(2)
        with c1:
            if not my_mats.empty:
                st.dataframe(my_mats[['raum', 'artikel', 'preis']])
                summe = (my_mats['menge'] * my_mats['preis']).sum()
                st.metric("Material Summe", f"{summe:.2f} €")
        with c2:
            st.graphviz_chart(plot_wiring_tree(my_strings, my_mats))

else:
    st.info("Bitte Projekt wählen.")
