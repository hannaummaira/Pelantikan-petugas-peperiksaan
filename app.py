
import streamlit as st
import os
st.set_page_config(page_title="SPM 2026 Selangor", layout="wide", page_icon="🏫")

col_logo, col_title = st.columns([1,5])
with col_logo:
    for p in ["assets/jata_negara_hd.png","assets/jata_negara.png"]:
        if os.path.exists(p):
            st.image(p, width=80)
            break
with col_title:
    st.title("Sistem Pelantikan Petugas Peperiksaan SPM 2026")
    st.caption("Jabatan Pendidikan Negeri Selangor - 1 Projek | 1 Supabase | 1 GitHub")

st.divider()

c1,c2,c3,c4 = st.columns(4)
with c1:
    st.page_link("pages/1_SUP_Sekolah.py", label="Masuk SUP", icon="🏫")
with c2:
    st.page_link("pages/2_PPD_Daerah.py", label="Masuk PPD", icon="🏢")
with c3:
    st.page_link("pages/3_JPN_Negeri.py", label="Masuk JPN", icon="🏛️")
with c4:
    st.page_link("pages/4_Info_Panduan.py", label="Lihat Panduan", icon="ℹ️")

st.success("Deploy berjaya - Logo ada di assets/jata_negara_hd.png")
