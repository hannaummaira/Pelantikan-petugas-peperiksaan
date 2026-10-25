
import streamlit as st
import os

st.set_page_config(page_title="SPM 2026 Selangor", layout="wide", page_icon="🏫")

st.markdown('''
<style>
.main {background:#f8fafc}
.card {
  background:white;
  border-radius:20px;
  padding:28px;
  box-shadow:0 6px 18px rgba(0,0,0,0.06);
  border:1px solid #eef2f7;
  text-align:center;
  height:280px;
  transition:all 0.2s;
}
.card:hover {transform:translateY(-4px);box-shadow:0 12px 28px rgba(0,0,0,0.10)}
.card h1 {font-size:52px;margin:0}
.card h3 {margin:12px 0 6px 0;color:#0f172a}
.card p {color:#64748b;font-size:14px;margin:2px 0}
.header-box {
  background:linear-gradient(135deg,#1e3a8a,#3b82f6);
  border-radius:20px;
  padding:24px 28px;
  color:white;
  display:flex;
  align-items:center;
  gap:20px;
}
</style>
''', unsafe_allow_html=True)

# Header with logo
logo_path = None
for cand in ["assets/jata_negara_hd.png","assets/jata_negara.png","assets/jata_cropped.png"]:
    if os.path.exists(cand):
        logo_path = cand
        break

col1, col2 = st.columns([1,6])
with col1:
    if logo_path:
        st.image(logo_path, width=90)
with col2:
    st.markdown('<div class="header-box"><div><h2 style="margin:0;color:white">Sistem Pelantikan Petugas Peperiksaan SPM 2026</h2><p style="margin:4px 0 0 0;opacity:0.9">Jabatan Pendidikan Negeri Selangor | 1 Projek Streamlit | 1 Supabase | 1 GitHub | Logo dalam assets/</p></div></div>', unsafe_allow_html=True)

st.write("")
st.write("")

c1,c2,c3,c4 = st.columns(4)

with c1:
    st.markdown('<div class="card"><h1>🏫</h1><h3>SUP</h3><p><b>Penolong Kanan</b></p><p>Sekolah & Pusat Peperiksaan</p><p style="margin-top:12px;color:#2563eb">Kemasukan Guru & Pelantikan</p></div>', unsafe_allow_html=True)
    st.write("")
    st.page_link("pages/1_SUP_Sekolah.py", label="Masuk SUP Sekolah", icon="🏫")

with c2:
    st.markdown('<div class="card"><h1>🏢</h1><h3>PPD</h3><p><b>Pejabat Pendidikan Daerah</b></p><p>Semakan & Pengesahan</p><p style="margin-top:12px;color:#ea580c">Template JPN + ZIP Pukal</p></div>', unsafe_allow_html=True)
    st.write("")
    st.page_link("pages/2_PPD_Daerah.py", label="Masuk PPD Daerah", icon="🏢")

with c3:
    st.markdown('<div class="card"><h1>🏛️</h1><h3>JPN</h3><p><b>Jabatan Pendidikan Negeri</b></p><p>Kelulusan & Surat Lantikan</p><p style="margin-top:12px;color:#16a34a">Dashboard Negeri</p></div>', unsafe_allow_html=True)
    st.write("")
    st.page_link("pages/3_JPN_Negeri.py", label="Masuk JPN Negeri", icon="🏛️")

with c4:
    st.markdown('<div class="card"><h1>ℹ️</h1><h3>INFO</h3><p><b>Panduan Pengguna</b></p><p>Status Sistem & Bantuan</p><p style="margin-top:12px;color:#64748b">Panduan Lengkap</p></div>', unsafe_allow_html=True)
    st.write("")
    st.page_link("pages/4_Info_Panduan.py", label="Lihat Info & Panduan", icon="ℹ️")

st.divider()
st.caption("Logo: assets/jata_negara_hd.png | Tandatangan: assets/tandatangan_pengarah_hd.png | Jika ZIP kosong, pastikan requirements.txt ada xhtml2pdf + reportlab")
