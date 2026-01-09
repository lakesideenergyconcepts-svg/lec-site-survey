import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import graphviz
from PIL import Image
from streamlit_gsheets import GSheetsConnection

# ==========================================
# KONFIGURATION V4.1.1 (Bugfix Grafik)
# ==========================================
st.set_page_config(page_title="LEC Manager V4.1", page_icon="⚡", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

def safe_read(worksheet, cols):
    try:
        df = conn.read(worksheet=worksheet, ttl=0)
        if df.empty: return pd.DataFrame(columns=cols)
        df.columns = df.columns.str.lower().str.strip()
        for c in cols: 
            if c not in df.columns: df[c] = "" 
        return df.fillna("")
    except: return pd.DataFrame(columns=cols)

def load_data():
    st.cache_data.clear()
    
    # 1. KUNDEN
    df_k = safe_read("kunden", ['id', 'firma', 'vorname', 'nachname', 'strasse', 'plz', 'ort', 'telefon', 'email'])
    
    def build_name(row):
        f, v, n = str(row['firma']), str(row['vorname']), str(row['nachname'])
        full = ""
        if f: full += f
        if v or n: 
            if f: full += f" ({n}, {v})"
            else: full += f"{n}, {v}"
        return full.strip(", ")

    if not df_k.empty:
        df_k['display_name'] = df_k.apply(build_name, axis=1)
    else:
        df_k['display_name'] = ""

    # 2. PROJEKTE
    df_p = safe_read("projekte", ['id', 'kunden_id', 'status', 'bemerkung', 'bp_width', 'bp_height', 'created_at'])
    
    # Rest
    df_r = safe_read("raeume", ['projekt_id', 'name', 'l', 'b', 'x', 'y'])
    df_s = safe_read("strings", ['projekt_id', 'id', 'name', 'fuse', 'factor', 'cable_name', 'cable_len', 'cable_price'])
    df_m = safe_read("installation", ['projekt_id', 'raum', 'string', 'artikel', 'menge', 'preis', 'watt', 'pos_x', 'pos_y'])
    
    # JOIN
    if not df_p.empty and not df_k.empty:
        df_p['kunden_id'] = df_p['kunden_id'].astype(str)
        df_k['id'] = df_k['id'].astype(str)
        df_display = pd.merge(df_p, df_k, left_on='kunden_id', right_on='id', how='left', suffixes=('', '_kd'))
    else:
        df_display = df_p.copy()
        df_display['display_name'] = "Unbekannt"
        df_display['ort'] = "-"

    return df_k, df_p, df_display, df_r, df_s, df_m

def save_new_row(worksheet, data_dict):
    try:
        st.info(f"Speichere...", icon="⏳")
        df_curr = conn.read(worksheet=worksheet, ttl=0)
        if df_curr.empty: df_curr = pd.DataFrame(columns=data_dict.keys())
        df_comb = pd.concat([df_curr, pd.DataFrame([data_dict])], ignore_index=True)
        conn.update(worksheet=worksheet, data=df_comb)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Save Error: {e}"); return False

def update_record(worksheet, id_col, record_id, updates):
    try:
        df = conn.read(worksheet=worksheet, ttl=0)
        df[id_col] = df[id_col].astype(str)
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
# GRAFIK LOGIK (BUGFIX HIER)
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
        rx, ry = float(r.get('x',0) or 0), float(r.get('y',0) or 0)
        rl, rb = float(r.get('l',4) or 4), float(r.get('b',3) or 3)
        ax.add_patch(patches.Rectangle((rx, ry), rl, rb, lw=2, ec='#0277bd', fc='#b3e5fc', alpha=0.3))
        # HIER WAR DER FEHLER: fw='bold' -> fontweight='bold'
        ax.text(rx+0.2, ry+rb-0.5, str(r['name']), fontweight='bold', color='#01579b')

    if not mats.empty and not rooms.empty:
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
# HAUPTNAVIGATION
# ==========================================
st.sidebar.title("LEC V4.1")

nav = st.sidebar.radio("Menü", ["🏠 Dashboard", "➕ Neuer Kunde / Projekt", "📂 Projekte öffnen"])

# --- VIEW 1: DASHBOARD ---
if nav == "🏠 Dashboard":
    st.header("Dashboard")
    k1, k2, k3 = st.columns(3)
    k1.metric("Projekte", len(df_projekte_raw))
    k2.metric("Kunden", len(df_kunden))
    k3.metric("Offene Aufträge", len(df_projekte_raw[df_projekte_raw['status']!='Fertig']))
    
    st.divider()
    st.subheader("Projekt Suche")
    
    col_search, col_stat = st.columns([2,1])
    search_term = col_search.text_input("🔍 Suche", placeholder="Name, Firma...")
    stat_filter = col_stat.selectbox("Status", ["Alle", "Neu", "In Planung", "Fertig"])
    
    if not df_projekte_display.empty:
        df_show = df_projekte_display.copy()
        if stat_filter != "Alle": df_show = df_show[df_show['status'] == stat_filter]
        if search_term:
            term = search_term.lower()
            df_show = df_show[df_show['display_name'].str.lower().str.contains(term) | df_show['ort'].str.lower().str.contains(term) | df_show['id'].str.lower().str.contains(term)]
        
        st.dataframe(df_show[['id', 'display_name', 'ort', 'status', 'created_at']], use_container_width=True, hide_index=True)
    else: st.info("Keine Daten.")

# --- VIEW 2: NEU ANLEGEN ---
elif nav == "➕ Neuer Kunde / Projekt":
    st.header("Neu anlegen")
    typ = st.radio("Aktion:", ["Neuen Kunden anlegen", "Projekt für Bestandskunde"], horizontal=True)
    
    if typ == "Neuen Kunden anlegen":
        with st.form("new_k"):
            c1, c2, c3 = st.columns(3)
            nf = c1.text_input("Firma"); nv = c2.text_input("Vorname"); nn = c3.text_input("Nachname *")
            c4, c5 = st.columns(2)
            ns = c4.text_input("Straße"); np = c5.text_input("PLZ / Ort")
            nt = c4.text_input("Telefon"); ne = c5.text_input("Email")
            
            if st.form_submit_button("Kunde speichern"):
                if nn or nf:
                    kid = f"K-{len(df_kunden)+1:03d}"
                    ok = save_new_row("kunden", {"id": kid, "firma": nf, "vorname": nv, "nachname": nn, "strasse": ns, "plz": np, "ort": np, "telefon": nt, "email": ne})
                    if ok: st.success(f"Kunde {kid} angelegt!"); st.rerun()
                else: st.error("Firma oder Nachname fehlt.")

    else: 
        if df_kunden.empty: st.warning("Keine Kunden.")
        else:
            ksel = st.selectbox("Kunde", df_kunden['id'].tolist(), format_func=lambda x: df_kunden[df_kunden['id']==x]['display_name'].values[0])
            with st.form("new_p"):
                bem = st.text_area("Notiz")
                if st.form_submit_button("Starten"):
                    pid = f"P-{len(df_projekte_raw)+1:03d}"
                    save_new_row("projekte", {"id": pid, "kunden_id": ksel, "status": "Neu", "bemerkung": bem, "bp_width": 20.0, "bp_height": 15.0, "created_at": "Heute"})
                    st.success("Erstellt!"); st.info("Bitte zu 'Projekte öffnen' wechseln.")

# --- VIEW 3: PROJEKT ---
elif nav == "📂 Projekte öffnen":
    if df_projekte_display.empty: st.warning("Leer.")
    else:
        p_sel = st.sidebar.selectbox("Projekt", df_projekte_display['id'].tolist(), format_func=lambda x: f"{df_projekte_display[df_projekte_display['id']==x]['display_name'].values[0]} ({x})")
        
        p_row = df_projekte_display[df_projekte_display['id'] == p_sel].iloc[0]
        cur_kid = str(p_row['kunden_id'])
        k_row = df_kunden[df_kunden['id'] == cur_kid].iloc[0]
        
        my_rooms = df_rooms[df_rooms['projekt_id'] == p_sel]
        my_strings = df_strings[df_strings['projekt_id'] == p_sel]
        my_mats = df_mats[df_mats['projekt_id'] == p_sel]
        
        if 'blueprint' not in st.session_state: st.session_state.blueprint = None

        st.title(f"{p_row['display_name']}")
        st.caption(f"Status: {p_row['status']} | Ort: {k_row['ort']}")

        t1, t2, t3, t4 = st.tabs(["Stammdaten", "Gebäude", "Planung", "Kalkulation"])

        with t1:
            c1, c2 = st.columns(2)
            with c1:
                with st.form("ed_k"):
                    ef = st.text_input("Firma", k_row['firma']); en = st.text_input("Name", k_row['nachname'])
                    if st.form_submit_button("Kunde speichern"):
                        update_record("kunden", "id", cur_kid, {"firma": ef, "nachname": en})
                        st.rerun()
            with c2:
                with st.form("ed_p"):
                    es = st.selectbox("Status", ["Neu", "In Planung", "Fertig"], index=["Neu", "In Planung", "Fertig"].index(p_row['status']) if p_row['status'] in ["Neu", "In Planung", "Fertig"] else 0)
                    if st.form_submit_button("Status speichern"):
                        update_record("projekte", "id", p_sel, {"status": es})
                        st.rerun()

        with t2:
            c1, c2 = st.columns([1,2])
            with c1:
                up = st.file_uploader("Plan", type=['jpg','png'])
                if up: st.session_state.blueprint = Image.open(up)
                nw = st.number_input("Breite", value=float(p_row['bp_width']) if pd.notnull(p_row['bp_width']) else 20.0)
                nh = st.number_input("Höhe", value=float(p_row['bp_height']) if pd.notnull(p_row['bp_height']) else 15.0)
                if st.button("Maße speichern"): update_record("projekte", "id", p_sel, {"bp_width": nw, "bp_height": nh})
                st.divider()
                rn = st.text_input("Raum Name", "Raum 1"); l = st.number_input("Länge", 4.0); b = st.number_input("Breite", 3.0)
                if st.button("Raum +"):
                    save_new_row("raeume", {"projekt_id": p_sel, "name": rn, "l": l, "b": b, "x": nw/2, "y": nh/2})
                    st.rerun()
            with c2: st.pyplot(plot_map(my_rooms, pd.DataFrame(), pd.DataFrame(), bg_img=st.session_state.blueprint, dims=(nw,nh)))

        with t3:
            c1, c2 = st.columns([1,2])
            with c1:
                st.write("**Strom**"); sn = st.text_input("Kreis Name"); sf = st.selectbox("Ampere", [10,16,32])
                if st.button("Kreis +"):
                    save_new_row("strings", {"projekt_id": p_sel, "id": f"S{len(my_strings)+1}", "name": sn, "fuse": sf, "factor": 0.7, "cable_name": "NYM-J 3x1.5", "cable_len": 15, "cable_price": 0.65})
                    st.rerun()
                st.divider(); st.write("**Gerät**")
                if not my_rooms.empty and not my_strings.empty:
                    rs = st.selectbox("Raum", my_rooms['name'].unique()); ss = st.selectbox("Kreis", my_strings['id'].unique())
                    ks = st.selectbox("Kat", ["Steuerung", "Verbraucher"]); il = st.selectbox("Art", [p['name'] for p in PRODUKT_KATALOG[ks]])
                    if st.button("Setzen"):
                        pd_ = next(p for p in PRODUKT_KATALOG[ks] if p['name']==il)
                        tr = my_rooms[my_rooms['name']==rs].iloc[0]
                        save_new_row("installation", {"projekt_id": p_sel, "raum": rs, "string": ss, "artikel": il, "menge": 1, "preis": pd_['preis'], "watt": pd_['watt'], "pos_x": float(tr['l'])/2, "pos_y": float(tr['b'])/2})
                        st.rerun()
            with c2: st.pyplot(plot_map(my_rooms, my_mats, my_strings, bg_img=st.session_state.blueprint, dims=(nw,nh)))

        with t4:
             if not my_mats.empty:
                 df_s = my_mats[['raum','artikel','menge','preis']].copy(); df_s['Gesamt'] = df_s['menge']*df_s['preis']
                 st.dataframe(df_s, use_container_width=True); st.metric("Summe", f"{df_s['Gesamt'].sum():.2f} €")
