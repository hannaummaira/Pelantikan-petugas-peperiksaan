
import streamlit as st
st.set_page_config(page_title="SPM Selangor - Sistem Lantikan", layout="wide", page_icon="📚", initial_sidebar_state="collapsed")

from common.config import TAHUN_PILIHAN, tahun_aktif, default_tahun, PPD_MAP, reset_sesi_kekal_tahun
from common.supabase_client import get_supa
from modules.sup_module import render_sup
from modules.ppd_module import render_ppd
from modules.jpn_module import render_jpn

# Hide fork button
st.markdown("""<style>
header[data-testid="stHeader"], [data-testid="stToolbar"], .stAppDeployButton, #MainMenu, footer {display:none!important;}
.stApp { background: linear-gradient(180deg, #eef3fb 0%, #f8fafd 40%, #ffffff 100%); }
.block-container { padding-top:1rem; max-width:1400px; }
</style>""", unsafe_allow_html=True)

# Tahun bar
def render_bar_tahun():
    t = tahun_aktif()
    key = "tahun_sel_main"
    def on_change():
        try:
            st.session_state["_tahun"] = int(st.session_state[key])
        except: pass
    c1, c2 = st.columns([2.5, 3.5])
    with c1:
        st.radio("📅 Tahun Peperiksaan", TAHUN_PILIHAN, index=TAHUN_PILIHAN.index(t), horizontal=True, key=key, on_change=on_change)
    with c2:
        st.caption(f"Data aktif tahun **{t}** - Semua cadangan, guru, pusat, surat ikut tahun ini. Tukar tahun di sini untuk lihat tahun lain.")

render_bar_tahun()

st.title(f"Sistem Pelantikan Petugas SPM Selangor {tahun_aktif()}")

role = st.sidebar.radio("Pilih Peranan", ["SUP (Sekolah)", "PPD (Daerah)", "JPN (Negeri)"], index=0)
st.sidebar.markdown("---")
if st.sidebar.button("Log Keluar (kekal tahun)"):
    reset_sesi_kekal_tahun()
    st.rerun()

if "SUP" in role:
    render_sup()
elif "PPD" in role:
    render_ppd()
else:
    render_jpn()

st.markdown(f"<div style='text-align:center;color:#888;font-size:10pt;margin-top:40px;'>Sistem Pelantikan SPM Selangor {tahun_aktif()} · JPN Selangor · Mantap & Modular</div>", unsafe_allow_html=True)
