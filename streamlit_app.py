import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import graphviz
from PIL import Image
from streamlit_gsheets import GSheetsConnection

# ==========================================
# KONFIGURATION V4.0 (Relationale DB)
# ==========================================
st.set_page_config(page_title="LEC Manager V4.0", page_icon="⚡", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- DATENBANK CORE ---
def safe_read(worksheet, cols):
    try:
        df = conn.read(worksheet=worksheet, ttl=0)
        if df.empty: return pd.DataFrame(columns=cols)
        df.columns = df.columns.str.lower().str.strip()
        for c in cols: 
            if c not in df.columns: df[c] = None
        return df
    except: return pd.DataFrame(columns=cols)

def load_data():
    st.cache_data.clear()
    
    # 1. KUNDEN (Stammdaten)
    df_k = safe_read("kunden", ['id', 'name', 'strasse', 'plz', 'ort', 'telefon', 'email'])
    
    # 2. PROJEKTE (Verknüpft über kunden_id)
    df_p = safe_read("projekte", ['id', 'kunden_id', 'status', 'bemerkung', 'bp_width', 'bp_height', 'created_at'])
    
    # Rest bleibt gleich
    df_r = safe_read("raeume", ['projekt_id', 'name', 'l', 'b', 'x', 'y'])
    df_s = safe_read("strings", ['projekt_id', 'id', 'name', 'fuse', 'factor', 'cable_name', 'cable_len', 'cable_price'])
    df_m = safe_read("installation", ['projekt_id', 'raum', 'string', 'artikel', 'menge', 'preis', 'watt', 'pos_x', 'pos_y'])
    
    # --- JOIN LOGIK ---
    # Wir kleben die Kundendaten an die Projekte dran für die Anzeige
    if not df_p.empty and not df_k.empty:
        # Sicherstellen dass IDs Strings sind
        df_p['kunden_id'] = df_p['kunden_id'].astype(str)
        df_k['id'] = df_k['id'].astype(str)
        
        # Merge: Projekte + Kunden-Infos
        df_display = pd.merge(df_p, df_k, left_on='kunden_id', right_on='id', how='left', suffixes=('', '_kd'))
    else:
        df_display = df_p.copy()
        if 'name' not in df_display.columns: df_display['name'] = "Unbekannt"
        if 'ort' not in df_display.columns: df_display['ort'] = "-"

    return df_k, df_p, df_display, df_r, df_s, df_m

def save_new_row(worksheet, data_dict):
    try:
        st.info(f"Speichere in {worksheet}...", icon="⏳")
        df_curr = conn.read(worksheet=worksheet, ttl=0)
        df_comb = pd.concat([df_curr, pd.DataFrame([data_dict])], ignore_index=True)
        conn.update(worksheet=worksheet, data=df_comb)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Save Error: {e}"); return False

def update_record(worksheet, id_col, record_id, updates):
    """Universeller Updater für Kunden oder Projekte"""
    try:
        df = conn.read(worksheet=worksheet, ttl=0)
        df[id_col] = df[id_col].astype(str) # Sicherheits-Cast
        idx = df[df[id_col] == str(record_id)].index
        if not idx.empty:
            for k, v in updates.items(): df.at[idx[0], k] = v
            conn.update(worksheet=worksheet, data=df)
            st.toast("Gespeichert!", icon="✅"); st.cache_data.clear()
            return True
    except Exception as e: st.error(f"Update Error: {e}"); return False

# LOAD
df_kunden, df_projekte_raw, df_projekte_display, df_rooms, df_strings, df_mats = load_data()

# ==========================================
# PLOTTING
# ==========================================
PRODUKT_KATALOG = {
    "Steuerung": [{"name": "Shelly Plus 2PM", "preis": 29.90, "watt": 1}, {"name": "Shelly Dimmer 2", "preis": 32.50, "watt": 1}],
    "Verbraucher": [{"name": "Steckdose", "preis": 8.50, "watt": 200}, {"name": "Lichtschalter", "preis": 12.00, "watt": 0}],
    "Kabel": [{"name": "NYM-J 3x1.5", "preis": 0.65, "watt": 0}, {"name": "NYM-J 5x1.5", "preis": 0.95, "watt": 0}]
}

def plot_map(rooms, mats, strings, active_idx=None, bg_img=None, dims=(20,15)):
    fig, ax = plt.subplots(figsize=(10, 7))
    if bg_img: ax.imshow(bg_img, extent=[0, dims[0], 0, dims[1]], origin='lower', alpha=0.5)
    
    for _, r in rooms.iterrows():
        rx, ry = float(r.get('x',0)), float(r.get('y',0))
        rl, rb = float(r.get('l',4)), float(r.get('b',3))
        ax.add_patch(patches.Rectangle((rx, ry), rl, rb, lw=2, ec='#0277bd', fc='#b3e5fc', alpha=0.3))
        ax.text(rx+0.2, ry+rb-0.5, str(r['name']), fw='bold', color='#01579b')

    if not mats.empty:
        cmap = plt.get_cmap('tab10')
        sc = {sid: cmap(i%10) for i, sid in enumerate(strings['id'].unique())} if not strings.empty else {}
        for idx, m in mats.iterrows():
            rm = rooms[rooms['name']==m['raum']]
            if not rm.empty:
                r=rm.iloc[0]
                rx,ry,rl,rb = float(r.get('x',0)), float(r.get('y',0)), float(r.get('l',4)), float(r.get('b',3))
                px, py = float(m.get('pos_x', rl/2)), float(m.get('pos_y', rb/2))
                col = sc.get(m['string'], 'black')
                sz = 180 if idx==active_idx else 60
                ax.scatter(rx+px, ry+py, c=[col], s=sz, ec='red' if idx==active_idx else 'white', lw=2, zorder=10)
    
    ax.set_aspect('equal'); ax.grid(True, ls=':', alpha=0.3)
    ax.set_xlim(-1, dims[0]+1); ax.set_ylim(-1, dims[1]+1)
    return fig

# ==========================================
# UI NAVIGATION
# ==========================================
st.sidebar.title("LEC V4.0")

nav = st.sidebar.radio("Menü", ["🏠 Dashboard", "➕ Neues Projekt", "📂 Projekte öffnen"])

# --- DASHBOARD ---
if nav == "🏠 Dashboard":
    st.header("Übersicht")
    kpi1, kpi2 = st.columns(2)
    kpi1.metric("Projekte", len(df_projekte_raw))
    kpi2.metric("Kunden", len(df_kunden))
    
    st.subheader("Alle Projekte")
    if not df_projekte_display.empty:
        st.dataframe(df_projekte_display[['id', 'name', 'ort', 'status', 'created_at']], use_container_width=True, hide_index=True)
    else:
        st.info("Keine Projekte gefunden.")

# --- NEUES PROJEKT (DER NEUE WIZARD) ---
elif nav == "➕ Neues Projekt":
    st.header("Projekt anlegen")
    
    # Entscheidung: Neu oder Bestand?
    mode = st.radio("Kunde:", ["Bestandskunde wählen", "Neuen Kunden anlegen"], horizontal=True)
    
    kunden_id_to_use = None
    
    if mode == "Bestandskunde wählen":
        if df_kunden.empty:
            st.warning("Noch keine Kunden angelegt.")
        else:
            # Dropdown mit Namen
            k_sel = st.selectbox("Kunde auswählen", df_kunden['id'].tolist(), format_func=lambda x: df_kunden[df_kunden['id']==x]['name'].values[0])
            kunden_id_to_use = k_sel
            
            # Vorschau
            k_dat = df_kunden[df_kunden['id']==k_sel].iloc[0]
            st.info(f"Gewählt: {k_dat['name']} aus {k_dat['ort']}")

    else: # Neuer Kunde
        with st.form("new_cust"):
            st.subheader("1. Neue Stammdaten")
            c1, c2 = st.columns(2)
            nn = c1.text_input("Firmenname / Name *")
            no = c2.text_input("Ort *")
            ns = c1.text_input("Straße")
            np = c2.text_input("PLZ")
            nt = c1.text_input("Telefon"); ne = c2.text_input("Email")
            
            if st.form_submit_button("Kunde anlegen"):
                if nn and no:
                    kid = f"K-{len(df_kunden)+1:03d}"
                    ok = save_new_row("kunden", {"id": kid, "name": nn, "strasse": ns, "plz": np, "ort": no, "telefon": nt, "email": ne})
                    if ok:
                        st.success(f"Kunde {nn} angelegt! Bitte jetzt unten Projekt starten.")
                        st.rerun() # Reload damit er in der Liste ist
                else:
                    st.error("Name und Ort sind Pflicht.")

    # Projekt Starten Button (nur sichtbar wenn Kunde da)
    if not df_kunden.empty:
        st.divider()
        st.subheader("2. Projekt initialisieren")
        # Wenn wir oben einen neuen angelegt haben, nehmen wir den neuesten, sonst den ausgewählten
        if mode == "Neuen Kunden anlegen":
            # Wir nehmen den letzten Eintrag aus der DB (der gerade angelegt wurde)
            # Das ist ein einfacher Hack, sauberer wäre Session State, aber reicht hier
            last_k = df_kunden.iloc[-1]
            kunden_id_to_use = last_k['id']
            st.write(f"Projekt wird erstellt für: **{last_k['name']}**")
        
        if kunden_id_to_use:
            with st.form("start_proj"):
                pbem = st.text_area("Projekt-Notiz (Optional)")
                if st.form_submit_button("🚀 Projekt starten"):
                    pid = f"P-{len(df_projekte_raw)+1:03d}"
                    save_new_row("projekte", {
                        "id": pid, "kunden_id": kunden_id_to_use, 
                        "status": "Neu", "bemerkung": pbem,
                        "bp_width": 20.0, "bp_height": 15.0, "created_at": "Heute"
                    })
                    st.success(f"Projekt {pid} erstellt!")
                    # Wir könnten hier direkt zur Projektansicht springen, aber User muss manuell wählen
                    st.info("Wechseln Sie nun links zu 'Projekte öffnen'.")

# --- PROJEKT ARBEITSBEREICH ---
elif nav == "📂 Projekte öffnen":
    # Sidebar Liste
    if df_projekte_display.empty:
        st.warning("Keine Projekte.")
    else:
        # Selectbox mit schönem Namen (Müller - P-001)
        p_sel = st.sidebar.selectbox("Projekt wählen", df_projekte_display['id'].tolist(), 
                                     format_func=lambda x: f"{df_projekte_display[df_projekte_display['id']==x]['name'].values[0]} ({x})")
        
        # Daten holen
        p_row = df_projekte_display[df_projekte_display['id'] == p_sel].iloc[0]
        cur_kid = p_row['kunden_id']
        k_row = df_kunden[df_kunden['id'] == str(cur_kid)].iloc[0] # Kunden Stammdaten
        
        # Detail Daten filtern
        my_rooms = df_rooms[df_rooms['projekt_id'] == p_sel]
        my_strings = df_strings[df_strings['projekt_id'] == p_sel]
        my_mats = df_mats[df_mats['projekt_id'] == p_sel]
        
        if 'blueprint' not in st.session_state: st.session_state.blueprint = None

        st.title(f"{k_row['name']} | {p_row['status']}")
        st.caption(f"Projekt: {p_sel} | Kunde: {cur_kid} | Ort: {k_row['ort']}")

        t1, t2, t3, t4 = st.tabs(["👤 Kunde & Infos", "🏗️ Gebäude", "⚡ Planung", "💰 Liste"])

        # TAB 1: STAMMDATEN (Bearbeitet Tabelle 'kunden')
        with t1:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Kunden-Stammdaten")
                with st.form("edit_k"):
                    en = st.text_input("Name", k_row['name'])
                    eo = st.text_input("Ort", k_row['ort'])
                    et = st.text_input("Tel", k_row['telefon'])
                    if st.form_submit_button("Kunde speichern"):
                        update_record("kunden", "id", cur_kid, {"name": en, "ort": eo, "telefon": et})
                        st.rerun()
            with c2:
                st.subheader("Projekt-Infos")
                with st.form("edit_p"):
                    estat = st.selectbox("Status", ["Neu", "In Planung", "Fertig"], index=["Neu", "In Planung", "Fertig"].index(p_row['status']) if p_row['status'] in ["Neu", "In Planung", "Fertig"] else 0)
                    ebem = st.text_area("Notiz", p_row['bemerkung'])
                    if st.form_submit_button("Projektstatus speichern"):
                        update_record("projekte", "id", p_sel, {"status": estat, "bemerkung": ebem})
                        st.rerun()

        # TAB 2: GEBÄUDE
        with t2:
            c1, c2 = st.columns([1,2])
            with c1:
                up = st.file_uploader("Plan", type=['jpg','png'])
                if up: st.session_state.blueprint = Image.open(up)
                
                cur_w = float(p_row['bp_width']) if pd.notnull(p_row['bp_width']) else 20.0
                cur_h = float(p_row['bp_height']) if pd.notnull(p_row['bp_height']) else 15.0
                nw = st.number_input("Breite", value=cur_w)
                nh = st.number_input("Höhe", value=cur_h)
                if st.button("Skalierung speichern"):
                    update_record("projekte", "id", p_sel, {"bp_width": nw, "bp_height": nh})
                
                st.divider()
                rn = st.text_input("Raum Name", "Raum 1")
                l = st.number_input("Länge", 4.0); b = st.number_input("Breite", 3.0)
                if st.button("Raum adden"):
                    save_new_row("raeume", {"projekt_id": p_sel, "name": rn, "l": l, "b": b, "x": nw/2, "y": nh/2})
                    st.rerun()
            with c2:
                st.pyplot(plot_map(my_rooms, pd.DataFrame(), pd.DataFrame(), bg_img=st.session_state.blueprint, dims=(nw,nh)))

        # TAB 3: PLANUNG (Kombiniert Strings & Mats)
        with t3:
            c1, c2 = st.columns([1,2])
            with c1:
                st.markdown("##### 1. Stromkreis")
                sn = st.text_input("Name"); sf = st.selectbox("A", [10,16,32], key="sf")
                if st.button("Kreis +"):
                    sid=f"S{len(my_strings)+1}"
                    save_new_row("strings", {"projekt_id": p_sel, "id": sid, "name": sn, "fuse": sf, "factor": 0.7, "cable_name": "NYM-J 3x1.5", "cable_len": 15, "cable_price": 0.65})
                    st.rerun()
                
                st.divider()
                st.markdown("##### 2. Gerät setzen")
                if not my_rooms.empty and not my_strings.empty:
                    rs = st.selectbox("Raum", my_rooms['name'].unique())
                    ss = st.selectbox("Kreis", my_strings['id'].unique())
                    ks = st.selectbox("Kat", ["Steuerung", "Verbraucher"])
                    ils = st.selectbox("Art", [p['name'] for p in PRODUKT_KATALOG[ks]])
                    if st.button("Platzieren"):
                        pd_ = next(p for p in PRODUKT_KATALOG[ks] if p['name']==ils)
                        tr = my_rooms[my_rooms['name']==rs].iloc[0]
                        save_new_row("installation", {"projekt_id": p_sel, "raum": rs, "string": ss, "artikel": ils, "menge": 1, "preis": pd_['preis'], "watt": pd_['watt'], "pos_x": float(tr['l'])/2, "pos_y": float(tr['b'])/2})
                        st.rerun()
            with c2:
                st.pyplot(plot_map(my_rooms, my_mats, my_strings, bg_img=st.session_state.blueprint, dims=(nw,nh)))

        # TAB 4: LISTE
        with t4:
             if not my_mats.empty:
                 st.dataframe(my_mats[['raum','artikel','menge','preis']])
                 st.metric("Total", f"{(my_mats['menge']*my_mats['preis']).sum():.2f} €")
