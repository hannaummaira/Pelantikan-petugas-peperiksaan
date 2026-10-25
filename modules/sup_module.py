
import streamlit as st
import pandas as pd
from common.supabase_client import get_supa
from common.config import tahun_aktif, PPD_MAP

def render_sup():
    supa = get_supa()
    st.subheader(f"Modul SUP - Tahun {tahun_aktif()}")
    kod_sekolah = st.session_state.get("kod_sekolah", "BEA1234")
    
    tab1, tab2 = st.tabs(["📋 Cadangan Saya", "📄 Surat Sampai Sekolah Asal"])
    with tab1:
        try:
            res = supa.table("cadangan_sup").select("*").limit(2000).execute()
            df = pd.DataFrame(res.data or [])
            if not df.empty:
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Belum ada cadangan untuk tahun ini.")
        except Exception as e:
            st.error(f"Ralat: {e}")

    with tab2:
        try:
            res = supa.table("surat_hantar_sekolah_asal").select("*").limit(1000).execute()
            df = pd.DataFrame(res.data or [])
            st.dataframe(df, use_container_width=True)
        except:
            st.info("Jadual surat_hantar_sekolah_asal belum wujud - jalankan migrasi SQL tahun.")
