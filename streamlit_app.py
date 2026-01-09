import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import graphviz
from PIL import Image
from streamlit_gsheets import GSheetsConnection

# ==========================================
# KONFIGURATION V5.0 (Performance & Room Edit)
# ==========================================
st.set_page_config(page_title="LEC Manager V5.0", page_icon="⚡", layout="wide")

# Globale Verbindung
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SESSION STATE INITIALISIERUNG ---
if 'nav' not in st.session_state: st.session_state.nav = "🏠 Dashboard"
if 'selected_pid' not in st.session_state: st.session_state.selected_pid = None
if 'blueprint' not in st.session_state: st.session_state.blueprint = None

# ==========================================
# DATENBANK ENGINE (ROBUST & CACHED)
# ==========================================

# Wir cachen das Lesen für 5 Sekunden, damit schnelle Klicks nicht die API blockieren
@st.cache_data(ttl=5)
def fetch_all_data():
    """Liest alle Sheets auf einmal ein und cached sie kurz."""
    def _read(ws, cols):
        try:
            df = conn.read(worksheet=ws, ttl=0) # ttl=0 hier wichtig für Aktualität
            if df.empty: return pd.DataFrame(columns=cols)
            df.columns = df.columns.str.lower().str.strip()
            for c in cols: 
                if c not in df.columns: df[c] = ""
            return df.fillna("")
        except: return pd.DataFrame(columns=cols)

    df_k = _read("kunden", ['id', 'firma', 'vorname', 'nachname', 'strasse', 'plz', 'ort', 'telefon', 'email'])
    df_p = _read("projekte", ['id', 'kunden_id', 'status', 'bemerkung', 'bp_width', 'bp_height', 'created_at'])
    df_r = _read("raeume", ['projekt_id', 'name', 'l', 'b', 'x', 'y'])
    df_s = _read("strings", ['projekt_id', 'id', 'name', 'fuse', 'factor', 'cable_name', 'cable_len', 'cable_price'])
    df_m = _read("installation", ['projekt_id', 'raum', 'string', 'artikel', 'menge', 'preis', 'watt', 'pos_x', 'pos_y'])

    # Join Display Name
    def build_name(row):
        f, v, n = str(row['firma']), str(row['vorname']), str(row['nachname'])
        full = f"{f} ({n}, {v})" if f and (v or n) else f or f"{n}, {v}"
        return full.strip(", ()")
    
    if not df_k.empty: df_k['display_name'] = df_k.apply(build_name, axis=1)
    else: df_k['display_name'] = ""

    # Join Projekte + Kunden
    if not df_p.empty and not df_k.empty:
        df_p['kunden_id'] = df_p['kunden_id'].astype(str)
        df_k['id'] = df_k['id'].astype(str)
        df_disp = pd.merge(df_p, df_k, left_on='kunden_id', right_on='id', how='left', suffixes=('', '_kd'))
    else:
        df_disp = df_p.copy()
        df_disp['display_name'] = "Unbekannt"
        df_disp['ort'] = "-"

    return df_k, df_p, df_disp, df_r, df_s, df_m

def clear_cache_and_reload():
    st.cache_data.clear()
    st.rerun()

def save_new_row(worksheet, data_dict):
    try:
        with st.spinner(f"Speichere in {worksheet}..."):
            df_curr = conn.read(worksheet=worksheet, ttl=0)
            if df_curr.empty: df_curr = pd.DataFrame(columns=data_dict.keys())
            df_comb = pd.concat([df_curr, pd.DataFrame([data_dict])], ignore_index=True)
            conn.update(worksheet=worksheet, data=df_comb)
        st.toast("Gespeichert!", icon="✅")
        clear_cache_and_reload()
        return True
    except Exception as e:
        st.error(f"Save Error: {e}"); return False

def update_record(worksheet, id_col, record_id, updates):
    try:
        with st.spinner("Aktualisiere Daten..."):
            df = conn.read(worksheet=worksheet, ttl=0)
            df[id_col] = df[id_col].astype(str)
            # WICHTIG: Wir suchen zeilenbasiert
            # Wir müssen sicherstellen, dass wir nicht strings mit ints vergleichen
            record_id = str(record_id)
            
            # Index finden
            mask = df[id_col] == record_id
            
            # Falls es sich um Räume handelt, ist der Name der Identifier (zusammen mit Projekt ID)
            # Das ist hier etwas vereinfacht. Für echte Robustheit bräuchten Räume auch IDs.
            # Workaround für Räume: Wir filtern vorher nicht hier, sondern nutzen delete/create logic
            
            idx = df[mask].index
            if not idx.empty:
                for k, v in updates.items(): df.at[idx[0], k] = v
                conn.update(worksheet=worksheet, data=df)
                st.toast("Update erfolgreich!", icon="✅")
                clear_cache_and_reload()
                return True
            else:
                st.warning(f"ID {record_id} nicht gefunden.")
                return False
    except Exception as e: st.error(f"Update Error: {e}"); return False

def delete_record(worksheet, col_name, value, project_id=None):
    """Löscht eine Zeile basierend auf einem Wert. 
    Bei Räumen müssen wir Projekt-ID mitprüfen, damit wir nicht Raum 'Wohnzimmer' aus ALLEN Projekten löschen."""
    try:
        with st.spinner("Lösche Eintrag..."):
            df = conn.read(worksheet=worksheet, ttl=0)
            
            if project_id:
                # Kombinierte Löschung (z.B. Raum in Projekt X)
                mask = (df[col_name] == value) & (df['projekt_id'] == project_id)
            else:
                # Einfache Löschung (z.B. Projekt ID)
                mask = (df[col_name] == str(value))
                
            df_new = df[~mask] # Behalte alles was NICHT matcht
            conn.update(worksheet=worksheet, data=df_new)
            
        st.success("Gelöscht!")
        clear_cache_and_reload()
    except Exception as e: st.error(f"Delete Error: {e}")

# ==========================================
# APP START & DATEN LADEN
# ==========================================

# Wir laden die Daten GANZ AM ANFANG einmal
try:
    df_kunden, df_projekte_raw, df_projekte_display, df_rooms, df_strings, df_mats = fetch_all_data()
except Exception as e:
    st.error("Verbindungsfehler zu Google Sheets. Bitte Seite neu laden.")
    st.stop()

# ==========================================
# GRAFIK ENGINE
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
# NAVIGATION
# ==========================================
st.sidebar.title("LEC V5.0")

# Navigations-Logik ohne Callbacks, um State-Verlust zu vermeiden
nav = st.sidebar.radio("Navigation", ["🏠 Dashboard", "➕ Neu", "📂 Projekte"])

# --- DASHBOARD ---
if nav == "🏠 Dashboard":
    st.header("Dashboard")
    k1, k2 = st.columns(2)
    k1.metric("Projekte", len(df_projekte_raw))
    k2.metric("Kunden", len(df_kunden))
    
    st.subheader("Projektliste")
    col_search, col_stat = st.columns([2,1])
    search = col_search.text_input("Suche", placeholder="Kunde, Ort...").lower()
    stat = col_stat.selectbox("Status", ["Alle", "Neu", "In Planung", "Fertig"])
    
    if not df_projekte_display.empty:
        df_show = df_projekte_display.copy()
        if stat != "Alle": df_show = df_show[df_show['status'] == stat]
        if search:
            df_show = df_show[df_show['display_name'].str.lower().str.contains(search) | df_show['ort'].str.lower().str.contains(search)]
        
        # Interaktive Auswahl
        event = st.dataframe(
            df_show[['id', 'display_name', 'ort', 'status', 'created_at']],
            use_container_width=True, hide_index=True,
            on_select="rerun", selection_mode="single-row"
        )
        
        if len(event.selection.rows) > 0:
            pid = df_show.iloc[event.selection.rows[0]]['id']
            st.session_state.selected_pid = pid
            st.info(f"Projekt {pid} ausgewählt! Wechseln Sie zu '📂 Projekte'.")

# --- NEU ANLEGEN ---
elif nav == "➕ Neu":
    st.header("Assistent")
    typ = st.radio("Was tun?", ["Kunde anlegen", "Projekt starten"])
    
    if typ == "Kunde anlegen":
        with st.form("new_k"):
            c1, c2 = st.columns(2)
            nf = c1.text_input("Firma"); nn = c2.text_input("Nachname *")
            no = st.text_input("Ort *")
            if st.form_submit_button("Speichern"):
                if nn or nf:
                    kid = f"K-{len(df_kunden)+1:03d}"
                    save_new_row("kunden", {"id": kid, "firma": nf, "nachname": nn, "ort": no})
                else: st.error("Name fehlt.")
                
    else:
        if df_kunden.empty: st.warning("Keine Kunden.")
        else:
            ksel = st.selectbox("Kunde", df_kunden['id'].tolist(), format_func=lambda x: df_kunden[df_kunden['id']==x]['display_name'].values[0])
            with st.form("new_p"):
                if st.form_submit_button("Projekt starten"):
                    pid = f"P-{len(df_projekte_raw)+1:03d}"
                    save_new_row("projekte", {"id": pid, "kunden_id": ksel, "status": "Neu", "bp_width": 20, "bp_height": 15, "created_at": "Heute"})
                    st.session_state.selected_pid = pid

# --- PROJEKT EDITOR ---
elif nav == "📂 Projekte":
    if not st.session_state.selected_pid:
        st.info("Bitte wählen Sie zuerst ein Projekt im Dashboard aus.")
    else:
        # Daten filtern
        p_sel = st.session_state.selected_pid
        # Sicherheitscheck: Existiert Projekt noch?
        if p_sel not in df_projekte_display['id'].values:
            st.error("Projekt nicht gefunden (vielleicht gelöscht?).")
            st.stop()
            
        p_row = df_projekte_display[df_projekte_display['id'] == p_sel].iloc[0]
        cur_kid = str(p_row['kunden_id'])
        
        my_rooms = df_rooms[df_rooms['projekt_id'] == p_sel]
        my_strings = df_strings[df_strings['projekt_id'] == p_sel]
        my_mats = df_mats[df_mats['projekt_id'] == p_sel]
        
        st.title(f"{p_row['display_name']}")
        
        t1, t2, t3, t4 = st.tabs(["Daten", "🏗️ Gebäude (Editor)", "⚡ Planung", "💰 Liste"])
        
        # TAB 1: Stammdaten
        with t1:
            with st.form("update_stat"):
                ns = st.selectbox("Status", ["Neu", "In Planung", "Fertig"], index=["Neu", "In Planung", "Fertig"].index(p_row['status']) if p_row['status'] in ["Neu", "In Planung", "Fertig"] else 0)
                if st.form_submit_button("Status Update"):
                    update_record("projekte", "id", p_sel, {"status": ns})

        # TAB 2: GEBÄUDE EDITOR (NEU!)
        with t2:
            c1, c2 = st.columns([1, 2])
            with c1:
                st.subheader("Plan & Wände")
                up = st.file_uploader("Grundriss", type=['jpg', 'png'], key="bp_up")
                if up: st.session_state.blueprint = Image.open(up)
                
                # Skalierung
                cw = float(p_row['bp_width']) if pd.notnull(p_row['bp_width']) else 20.0
                ch = float(p_row['bp_height']) if pd.notnull(p_row['bp_height']) else 15.0
                nw = st.number_input("Breite (m)", value=cw)
                nh = st.number_input("Höhe (m)", value=ch)
                if st.button("Maßstab speichern"):
                    update_record("projekte", "id", p_sel, {"bp_width": nw, "bp_height": nh})
                
                st.divider()
                
                # RAUM MANAGER
                mode = st.radio("Modus", ["➕ Neuer Raum", "✏️ Bearbeiten / Löschen"], horizontal=True)
                
                if mode == "➕ Neuer Raum":
                    with st.form("add_r"):
                        rn = st.text_input("Name", "Raum 1")
                        l = st.number_input("Länge", 4.0); b = st.number_input("Breite", 3.0)
                        if st.form_submit_button("Erstellen"):
                            save_new_row("raeume", {"projekt_id": p_sel, "name": rn, "l": l, "b": b, "x": nw/2, "y": nh/2})
                
                else: # Bearbeiten
                    if my_rooms.empty:
                        st.info("Keine Räume vorhanden.")
                    else:
                        r_edit = st.selectbox("Raum wählen", my_rooms['name'].unique())
                        # Daten des gewählten Raums holen
                        r_dat = my_rooms[my_rooms['name'] == r_edit].iloc[0]
                        
                        with st.form("edit_r"):
                            # Alte Werte laden
                            nl = st.number_input("Länge", value=float(r_dat['l']))
                            nb = st.number_input("Breite", value=float(r_dat['b']))
                            nx = st.number_input("Pos X", value=float(r_dat['x']))
                            ny = st.number_input("Pos Y", value=float(r_dat['y']))
                            
                            c_up, c_del = st.columns(2)
                            submitted_up = c_up.form_submit_button("💾 Speichern")
                            submitted_del = c_del.form_submit_button("🗑️ Löschen", type="primary")
                            
                            if submitted_up:
                                # Wir müssen hier tricksen: Da Räume keine echte ID im Sheet haben, 
                                # nutzen wir Namen+ProjektID als Identifier.
                                # Das ist nicht perfekt, aber funktioniert für V5.
                                # Wir löschen den alten und erstellen einen neuen (sauberster Weg in Sheets ohne ID)
                                delete_record("raeume", "name", r_edit, project_id=p_sel)
                                save_new_row("raeume", {"projekt_id": p_sel, "name": r_edit, "l": nl, "b": nb, "x": nx, "y": ny})
                                
                            if submitted_del:
                                delete_record("raeume", "name", r_edit, project_id=p_sel)

            with c2:
                st.pyplot(plot_map(my_rooms, pd.DataFrame(), pd.DataFrame(), bg_img=st.session_state.blueprint, dims=(nw, nh)))

        # TAB 3: PLANUNG
        with t3:
            c1, c2 = st.columns([1, 2])
            with c1:
                st.write("**Stromkreise**")
                # Lösch-Möglichkeit für Strings
                if not my_strings.empty:
                     del_s = st.selectbox("Löschen:", ["-"] + my_strings['name'].tolist())
                     if del_s != "-":
                         if st.button("Lösche Kreis"):
                             sid = my_strings[my_strings['name']==del_s].iloc[0]['id']
                             delete_record("strings", "id", sid) # Hier haben wir IDs!
                
                with st.form("add_s"):
                    sn = st.text_input("Name"); sf = st.selectbox("Ampere", [10,16,32])
                    if st.form_submit_button("Neuer Kreis"):
                        sid = f"S{len(my_strings)+1}"
                        save_new_row("strings", {"projekt_id": p_sel, "id": sid, "name": sn, "fuse": sf, "factor": 0.7, "cable_name": "NYM-J 3x1.5", "cable_len": 15, "cable_price": 0.65})

                st.divider()
                st.write("**Installation**")
                if not my_rooms.empty and not my_strings.empty:
                    rs = st.selectbox("Raum", my_rooms['name'].unique())
                    ss = st.selectbox("Kreis", my_strings['id'].unique())
                    ks = st.selectbox("Typ", ["Steuerung", "Verbraucher"])
                    il = st.selectbox("Art", [p['name'] for p in PRODUKT_KATALOG[ks]])
                    if st.button("Gerät setzen"):
                        pd_ = next(p for p in PRODUKT_KATALOG[ks] if p['name']==il)
                        tr = my_rooms[my_rooms['name']==rs].iloc[0]
                        save_new_row("installation", {"projekt_id": p_sel, "raum": rs, "string": ss, "artikel": il, "menge": 1, "preis": pd_['preis'], "watt": pd_['watt'], "pos_x": float(tr['l'])/2, "pos_y": float(tr['b'])/2})

            with c2:
                st.pyplot(plot_map(my_rooms, my_mats, my_strings, bg_img=st.session_state.blueprint, dims=(nw, nh)))

        # TAB 4: LISTE
        with t4:
            if not my_mats.empty:
                df_show = my_mats[['raum', 'artikel', 'menge', 'preis']].copy()
                df_show['Gesamt'] = df_show['menge'] * df_show['preis']
                st.dataframe(df_show, use_container_width=True)
                st.metric("Material Netto", f"{df_show['Gesamt'].sum():.2f} €")
