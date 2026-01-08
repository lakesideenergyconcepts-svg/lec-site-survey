import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import graphviz
from PIL import Image
from streamlit_gsheets import GSheetsConnection

# ==========================================
# KONFIGURATION & DATENBANK-VERBINDUNG
# ==========================================
st.set_page_config(page_title="LEC Manager V2.0", page_icon="⚡", layout="wide")

# Verbindung aufbauen
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """Lädt alle Tabellen aus dem Google Sheet"""
    # Cache leeren, damit wir immer frische Daten haben
    st.cache_data.clear()
    
    try:
        # Wir laden jedes Blatt einzeln
        df_proj = conn.read(worksheet="projekte", usecols=list(range(6)), ttl=0).dropna(how="all")
        df_rooms = conn.read(worksheet="raeume", usecols=list(range(6)), ttl=0).dropna(how="all")
        df_strings = conn.read(worksheet="strings", usecols=list(range(8)), ttl=0).dropna(how="all")
        df_mat = conn.read(worksheet="installation", usecols=list(range(9)), ttl=0).dropna(how="all")
        
        return df_proj, df_rooms, df_strings, df_mat
    except Exception as e:
        st.error(f"Datenbank-Fehler: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def save_row(worksheet, data_dict):
    """Fügt eine Zeile in ein Blatt ein (Append)"""
    try:
        df_current = conn.read(worksheet=worksheet, ttl=0)
        df_new = pd.DataFrame([data_dict])
        df_combined = pd.concat([df_current, df_new], ignore_index=True)
        conn.update(worksheet=worksheet, data=df_combined)
        st.toast(f"Gespeichert in '{worksheet}'!", icon="✅")
    except Exception as e:
        st.error(f"Speicher-Fehler: {e}")

# Initiales Laden
df_projects, df_rooms, df_strings, df_material = load_data()

# ==========================================
# HELPER & PLOTTING
# ==========================================
PRODUKT_KATALOG = {
    "Steuerung": [{"name": "Shelly Plus 2PM", "preis": 29.90, "watt": 1}, {"name": "Shelly Dimmer 2", "preis": 32.50, "watt": 1}],
    "Verbraucher": [{"name": "Steckdose", "preis": 8.50, "watt": 200}, {"name": "Lichtschalter", "preis": 12.00, "watt": 0}],
    "Kabel": [{"name": "NYM-J 3x1.5", "preis": 0.65, "watt": 0}, {"name": "NYM-J 5x1.5", "preis": 0.95, "watt": 0}]
}

def plot_installation_map(rooms, materials, strings, active_idx=None, blueprint_img=None, bp_dims=(20,15)):
    fig, ax = plt.subplots(figsize=(10, 7))
    if blueprint_img:
        ax.imshow(blueprint_img, extent=[0, bp_dims[0], 0, bp_dims[1]], origin='lower', alpha=0.5)

    for _, r in rooms.iterrows():
        rect = patches.Rectangle((r['x'], r['y']), r['l'], r['b'], linewidth=2, edgecolor='#0277bd', facecolor='#b3e5fc', alpha=0.3)
        ax.add_patch(rect)
        ax.text(r['x']+0.2, r['y']+r['b']-0.5, str(r['name']), fontweight='bold', color='#01579b')

    cmap = plt.get_cmap('tab10')
    # Strings Map: ID -> Farbe
    s_colors = {}
    if not strings.empty:
        unique_strings = strings['id'].unique()
        for i, sid in enumerate(unique_strings):
            s_colors[sid] = cmap(i%10)

    if not materials.empty:
        for idx, m in materials.iterrows():
            # Zugehörigen Raum finden
            room = rooms[rooms['name'] == m['raum']]
            if not room.empty:
                r = room.iloc[0]
                rel_x = m.get('pos_x', r['l']/2)
                rel_y = m.get('pos_y', r['b']/2)
                abs_x = r['x'] + rel_x
                abs_y = r['y'] + rel_y
                
                col = s_colors.get(m['string'], 'black')
                is_active = (idx == active_idx)
                size = 180 if is_active else 60
                edge = 'red' if is_active else 'white'
                
                ax.scatter(abs_x, abs_y, c=[col], s=size, edgecolors=edge, linewidth=2, zorder=10)
    
    ax.set_aspect('equal')
    ax.grid(True, linestyle=':', alpha=0.3)
    ax.set_xlim(-1, bp_dims[0]+1); ax.set_ylim(-1, bp_dims[1]+1)
    return fig

# ==========================================
# UI LOGIK
# ==========================================
st.sidebar.title("LEC Manager V2.0")

# Projekt Auswahl
project_options = ["Neues Projekt"] + df_projects['id'].tolist() if not df_projects.empty else ["Neues Projekt"]
def format_proj(pid):
    if pid == "Neues Projekt": return pid
    row = df_projects[df_projects['id'] == pid].iloc[0]
    return f"{row['kunde']} ({row['ort']})"

sel_p = st.sidebar.selectbox("Projekt", project_options, format_func=format_proj)

if sel_p == "Neues Projekt":
    st.sidebar.subheader("Neu anlegen")
    with st.sidebar.form("new_p"):
        k = st.text_input("Kunde")
        o = st.text_input("Ort")
        if st.form_submit_button("Erstellen"):
            new_id = f"P-{len(df_projects)+1:03d}"
            save_row("projekte", {"id": new_id, "kunde": k, "ort": o, "bp_width": 20.0, "bp_height": 15.0, "created_at": "Heute"})
            st.rerun()
    current_pid = None
else:
    current_pid = sel_p
    # Projekt Daten filtern
    proj_data = df_projects[df_projects['id'] == current_pid].iloc[0]
    my_rooms = df_rooms[df_rooms['projekt_id'] == current_pid]
    my_strings = df_strings[df_strings['projekt_id'] == current_pid]
    my_mats = df_material[df_material['projekt_id'] == current_pid]

if current_pid:
    st.title(f"Projekt: {proj_data['kunde']}")
    
    # Session State für Blueprint (Bilder können wir nicht im Sheet speichern, die bleiben im RAM oder müssen separat hochgeladen werden)
    if 'blueprint' not in st.session_state: st.session_state.blueprint = None
    
    tab1, tab2, tab3, tab4 = st.tabs(["🏗️ Gebäude", "⚡ Stromkreise", "📍 Installation", "💰 Liste"])

    # --- TAB 1: GEBÄUDE ---
    with tab1:
        c1, c2 = st.columns([1, 2])
        with c1:
            uploaded = st.file_uploader("Plan Upload", type=['jpg', 'png'])
            if uploaded: 
                st.session_state.blueprint = Image.open(uploaded)
            
            st.write("**Skalierung:**")
            nw = st.number_input("Breite", value=float(proj_data['bp_width']))
            nh = st.number_input("Höhe", value=float(proj_data['bp_height']))
            # Update Button für Skalierung wäre hier gut um API Calls zu sparen
            
            st.divider()
            with st.form("add_room"):
                rn = st.text_input("Raum Name")
                l = st.number_input("Länge", 4.0); b = st.number_input("Breite", 3.0)
                if st.form_submit_button("Raum speichern"):
                    save_row("raeume", {"projekt_id": current_pid, "name": rn, "l": l, "b": b, "x": nw/2, "y": nh/2})
                    st.rerun()
        
        with c2:
            fig = plot_installation_map(my_rooms, pd.DataFrame(), pd.DataFrame(), blueprint_img=st.session_state.blueprint, bp_dims=(nw, nh))
            st.pyplot(fig)

    # --- TAB 2: STRINGS ---
    with tab2:
        with st.form("add_string"):
            sn = st.text_input("Name"); sf = st.selectbox("Absicherung", [10, 16, 32])
            sc = st.selectbox("Kabel", [k['name'] for k in PRODUKT_KATALOG['Kabel']])
            sl = st.number_input("Länge", 15)
            if st.form_submit_button("Stromkreis speichern"):
                pr = next(k['preis'] for k in PRODUKT_KATALOG['Kabel'] if k['name']==sc)
                save_row("strings", {"projekt_id": current_pid, "id": f"S{len(my_strings)+1}", "name": sn, "fuse": sf, "factor": 0.7, "cable_name": sc, "cable_len": sl, "cable_price": pr})
                st.rerun()
        
        st.dataframe(my_strings)

    # --- TAB 3: INSTALLATION ---
    with tab3:
        if my_rooms.empty or my_strings.empty:
            st.warning("Erst Räume und Strings anlegen.")
        else:
            c_tools, c_map = st.columns([1, 2])
            with c_tools:
                r = st.selectbox("Raum", my_rooms['name'].tolist())
                s = st.selectbox("String", my_strings['id'].tolist())
                k = st.selectbox("Kat", ["Steuerung", "Verbraucher"])
                i = st.selectbox("Artikel", [p['name'] for p in PRODUKT_KATALOG[k]])
                
                if st.button("Platzieren"):
                    pd = next(p for p in PRODUKT_KATALOG[k] if p['name']==i)
                    # Raum Maße holen für Default Position
                    t_room = my_rooms[my_rooms['name'] == r].iloc[0]
                    save_row("installation", {
                        "projekt_id": current_pid, "raum": r, "string": s, "artikel": i, 
                        "menge": 1, "preis": pd['preis'], "watt": pd['watt'], 
                        "pos_x": t_room['l']/2, "pos_y": t_room['b']/2
                    })
                    st.rerun()
            
            with c_map:
                fig = plot_installation_map(my_rooms, my_mats, my_strings, blueprint_img=st.session_state.blueprint, bp_dims=(nw, nh))
                st.pyplot(fig)

    # --- TAB 4: LISTE ---
    with tab4:
        st.dataframe(my_mats)
        # Summenlogik hier ähnlich wie vorher einfügen
else:
    st.info("Bitte Projekt wählen oder neu erstellen.")
