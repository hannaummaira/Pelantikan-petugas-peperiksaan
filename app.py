
import streamlit as st
import os

# ONE set_page_config only - here
st.set_page_config(page_title="SPM 2026 Selangor", layout="wide", page_icon="🏫")

st.markdown("""
<style>
.card {
  background:white;
  border-radius:20px;
  padding:24px;
  box-shadow:0 4px 12px rgba(0,0,0,0.06);
  border:1px solid #eef2f7;
  text-align:center;
  height:260px;
}
.header {
  background:linear-gradient(135deg,#1e3a8a,#3b82f6);
  border-radius:16px;
  padding:18px 24px;
  color:white;
}
</style>
""", unsafe_allow_html=True)

logo = None
for p in ["assets/jata_negara_hd.png","assets/jata_negara.png","assets/jata_cropped.png"]:
    if os.path.exists(p):
        logo = p
        break

colL, colT = st.columns([1,5])
with colL:
    if logo: st.image(logo, width=80)
with colT:
    st.markdown('<div class="header"><h2 style="margin:0;color:white">Sistem Pelantikan Petugas SPM 2026 - Selangor</h2><p style="margin:0;opacity:0.9">Main: fix4_surat.py dikekalkan | Assets: jata + tandatangan | 4 Muka Depan</p></div>', unsafe_allow_html=True)

st.write("")

c1,c2,c3,c4 = st.columns(4)
with c1:
    st.markdown('<div class="card"><h1>🏫</h1><h3>SUP</h3><p>Sekolah & Pusat<br>Penolong Kanan</p></div>', unsafe_allow_html=True)
    st.page_link("pages/1_SUP_Sekolah.py", label="Masuk SUP", icon="🏫")
with c2:
    st.markdown('<div class="card"><h1>🏢</h1><h3>PPD</h3><p>Pejabat Pendidikan Daerah<br>Template + ZIP</p></div>', unsafe_allow_html=True)
    st.page_link("pages/2_PPD_Daerah.py", label="Masuk PPD", icon="🏢")
with c3:
    st.markdown('<div class="card"><h1>🏛️</h1><h3>JPN</h3><p>Jabatan Pendidikan Negeri<br>Dashboard</p></div>', unsafe_allow_html=True)
    st.page_link("pages/3_JPN_Negeri.py", label="Masuk JPN", icon="🏛️")
with c4:
    st.markdown('<div class="card"><h1>ℹ️</h1><h3>INFO</h3><p>Panduan & Status<br>Bantuan</p></div>', unsafe_allow_html=True)
    st.page_link("pages/4_Info_Panduan.py", label="Info", icon="ℹ️")

st.divider()
st.info("Jika nampak 4 kad ini, 'Oh no' dah fix. Sekarang klik SUP/PPD/JPN. Jika page dalam error, share log di Manage app -> Logs")

# Debug info
with st.expander("Debug - Check Files"):
    st.write("Files in root:", os.listdir("."))
    if os.path.exists("assets"):
        st.write("Assets:", os.listdir("assets"))
    if os.path.exists("pages"):
        st.write("Pages:", os.listdir("pages"))
    st.write("Requirements exist:", os.path.exists("requirements.txt"))
