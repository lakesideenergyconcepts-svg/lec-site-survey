import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- KONFIGURATION ---
st.set_page_config(page_title="LEC Manager", page_icon="⚡", layout="wide")

# --- SIMULIERTE DATENBANK (Backend) ---
if 'db_projects' not in st.session_state:
    st.session_state.db_projects = {
        "P-001": {"kunde": "Müller", "ort": "Friedrichshafen", "status": "In Planung", "created": "2025-01-08"},
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

if 'current_project_id' not in st.session_state:
    st.session_state.current_project_id = None

# --- KATALOG ---
PRODUKT_KATALOG = {
    "Steuerung": [
        {"name": "Shelly Plus 2PM", "preis": 29.90},
        {"name": "Shelly Dimmer 2", "preis": 32.50},
        {"name": "Shelly i4", "preis": 18.90},
    ],
    "Installation": [
        {"name": "Steckdose Gira E2", "preis": 8.50},
        {"name": "Schalter Gira E2", "preis": 12.00},
        {"name": "NYM-J 3x1.5 (100m)", "preis": 65.00},
        {"name": "Keystone Modul", "preis": 6.50},
        {"name": "Datendose 2-fach", "preis": 12.00},
    ],
    "Verteiler": [
        {"name": "FI-Schalter 40A", "preis": 35.00},
        {"name": "LS-Schalter B16", "preis": 2.80},
        {"name": "Reihenklemme Phoenix", "preis": 1.90},
    ]
}

# --- FUNKTION: GRUNDRISS PLOTTEN ---
def plot_floorplan(rooms, active_room_idx=None):
    if not rooms: return None
    
    # Figure Setup
    fig, ax = plt.subplots(figsize=(10, 6))
    
    max_x = 0
    max_y = 0

    for idx, room in enumerate(rooms):
        # Logic: Aktiver Raum (der gerade bearbeitet wird) ist ORANGE
        is_active = (idx == active_room_idx)
        face_col = '#ffcc80' if is_active else '#e3f2fd' # Orange vs Blau
        edge_col = '#e65100' if is_active else '#1f77b4'
        lw = 3 if is_active else 2
        z_order = 10 if is_active else 1
        
        # Rechteck zeichnen
        rect = patches.Rectangle((room['x'], room['y']), room['l'], room['b'], 
                                 linewidth=lw, edgecolor=edge_col, facecolor=face_col, alpha=0.9, zorder=z_order)
        ax.add_patch(rect)
        
        # Text Label (Mitte des Raums)
        cx = room['x'] + room['l']/2
        cy = room['y'] + room['b']/2
        
        label = f"{room['name']}\n{room['l']*room['b']:.1f}m²"
        font_weight = 'bold' if is_active else 'normal'
        ax.text(cx, cy, label, ha='center', va='center', fontsize=9, fontweight=font_weight, zorder=z_order+1)
        
        # Bemaßung (Länge unten, Breite links) - Nur wenn Raum groß genug
        if room['l'] > 1.0:
            ax.text(cx, room['y'] + 0.2, f"{room['l']}m", ha='center', va='bottom', fontsize=8, zorder=z_order+1)
        if room['b'] > 1.0:
            ax.text(room['x'] + 0.2, cy, f"{room['b']}m", ha='left', va='center', rotation=90, fontsize=8, zorder=z_order+1)

        # Plot Grenzen ermitteln
        max_x = max(max_x, room['x'] + room['l'])
        max_y = max(max_y, room['y'] + room['b'])

    # Achsen konfigurieren
    ax.set_xlim(-1, max(10, max_x + 2)) 
    ax.set_ylim(-1, max(10, max_y + 2))
    ax.set_aspect('equal')
