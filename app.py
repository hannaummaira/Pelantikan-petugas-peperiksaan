
import streamlit as st
import os

st.set_page_config(page_title="SPM 2026 Selangor", layout="wide", page_icon="🏫")

# Inject CSS for 4 cards
st.markdown("""
<style>
.card {
  background:white;
  border-radius:20px;
  padding:28px;
  box-shadow:0 6px 18px rgba(0,0,0,0.06);
  border:1px solid #eef2f7;
  text-align:center;
  height:300px;
}
.card h1 {font-size:48px;margin:0}
.header-box {
  background:linear-gradient(135deg,#1e3a8a,#3b82f6);
  border-radius:16px;
  padding:20px 24px;
  color:white;
}
</style>
""", unsafe_allow_html=True)

logo = None
for p in ["assets/jata_negara_hd.png","assets/jata_negara.png"]:
    if os.path.exists(p):
        logo = p
        break

cL, cT = st.columns([1,6])
with cL:
    if logo: st.image(logo, width=85)
with cT:
    st.markdown('<div class="header-box"><h2 style="margin:0;color:white">Sistem Pelantikan Petugas SPM 2026 - Selangor</h2><p style="margin:4px 0 0 0;opacity:0.9">1 Projek | 1 Supabase | 1 GitHub | Main: fix4_surat.py | Assets: jata + tandatangan</p></div>', unsafe_allow_html=True)

st.write("")
c1,c2,c3,c4 = st.columns(4)
with c1:
    st.markdown('<div class="card"><h1>🏫</h1><h3>SUP</h3><p>Penolong Kanan<br>Sekolah & Pusat</p><p style="color:#2563eb;margin-top:10px">Pilih Pusat Tugas</p></div>', unsafe_allow_html=True)
    st.page_link("pages/1_SUP_Sekolah.py", label="Masuk SUP", icon="🏫")
with c2:
    st.markdown('<div class="card"><h1>🏢</h1><h3>PPD</h3><p>Pejabat Pendidikan Daerah<br>Semakan & Pengesahan</p><p style="color:#ea580c;margin-top:10px">Template + ZIP Pukal</p></div>', unsafe_allow_html=True)
    st.page_link("pages/2_PPD_Daerah.py", label="Masuk PPD", icon="🏢")
with c3:
    st.markdown('<div class="card"><h1>🏛️</h1><h3>JPN</h3><p>Jabatan Pendidikan Negeri<br>Kelulusan & Surat</p><p style="color:#16a34a;margin-top:10px">Dashboard Negeri</p></div>', unsafe_allow_html=True)
    st.page_link("pages/3_JPN_Negeri.py", label="Masuk JPN", icon="🏛️")
with c4:
    st.markdown('<div class="card"><h1>ℹ️</h1><h3>INFO</h3><p>Panduan & Status<br>Sistem</p><p style="color:#64748b;margin-top:10px">Bantuan</p></div>', unsafe_allow_html=True)
    st.page_link("pages/4_Info_Panduan.py", label="Info Panduan", icon="ℹ️")

st.divider()
st.caption("Main file asal dikekalkan: fix4_surat.py | Logo dicari di assets/ | Jika ZIP kosong, pastikan requirements ada xhtml2pdf")
