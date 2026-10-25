
import streamlit as st
import os

# Supabase - ambil dari secrets dulu, fallback env
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    SUPABASE_URL = os.getenv("SUPABASE_URL", "https://gnmaijhugkkvxejvsotk.supabase.co")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# PPD Map Selangor
PPD_MAP = {
    "BA": "Petaling Utama", "BP": "Petaling Perdana", "SA": "Shah Alam",
    "KL": "Klang", "KD": "Kuala Selangor", "KS": "Kuala Langat",
    "SB": "Sabak Bernam", "HS": "Hulu Selangor", "HL": "Hulu Langat", "GP": "Gombak",
    "BH": "Bahagian"
}

TAHUN_PILIHAN = [2026, 2027, 2028, 2029, 2030]
TAHUN_TABLES = {"cadangan_sup", "guru_master", "pusat_master", "bilik_kebal_master", "surat_hantar_sekolah_asal"}

import datetime
def default_tahun():
    y = datetime.date.today().year
    return y if y in TAHUN_PILIHAN else TAHUN_PILIHAN[0] if y < TAHUN_PILIHAN[0] else TAHUN_PILIHAN[-1]

def tahun_aktif():
    try:
        t = int(st.session_state.get("_tahun", default_tahun()))
        return t if t in TAHUN_PILIHAN else default_tahun()
    except:
        return default_tahun()

def reset_sesi_kekal_tahun():
    t = st.session_state.get("_tahun")
    st.session_state.clear()
    if t:
        st.session_state["_tahun"] = t
