
import streamlit as st

st.set_page_config(
    page_title="SPM 2026 - Selangor",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Hide Streamlit branding like original
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&family=Inter:wght@400;500;600&display=swap');
header[data-testid="stHeader"], [data-testid="stToolbar"], .stAppDeployButton, #MainMenu, footer {display:none !important;}
.stApp { background: radial-gradient(1200px 600px at 20% -10%, #E8F0FE 0%, #f8fafd 40%, #ffffff 100%); }
.block-container { padding-top: 1rem !important; max-width: 1280px; }
.hero { text-align:center; padding: 24px 20px 10px 20px; }
.hero h2 { font-family:'Poppins'; color:#1565c0; font-size:14px; font-weight:600; letter-spacing:1.5px; margin:0; }
.hero h1 { font-family:'Poppins'; color:#0d47a1; font-size:30px; font-weight:700; line-height:1.2; margin:8px 0 0 0; }
.hero p { font-family:'Inter'; color:#5f6b7a; font-size:14px; max-width:720px; margin:12px auto 0 auto; line-height:1.6; }
.card { background:white; border:1px solid #e1e8f5; border-radius:20px; padding:24px; box-shadow:0 4px 18px rgba(13,71,161,.08); height:260px; display:flex; flex-direction:column; transition: all .22s ease; }
.card:hover { transform: translateY(-4px); box-shadow:0 14px 32px rgba(13,71,161,.16); border-color:#1565c0; }
.card h3 { font-family:'Poppins'; color:#0d47a1; font-size:18px; margin:0 0 6px 0; }
.card p { font-family:'Inter'; color:#5f6b7a; font-size:12.5px; line-height:1.6; flex-grow:1; }
.badge { display:inline-flex; align-items:center; font-family:'Inter'; font-size:10px; font-weight:700; letter-spacing:.5px; padding:5px 12px; border-radius:20px; margin-bottom:12px; width:fit-content; }
.btn-desc { font-size:11px; color:#8a96ad; margin-top:8px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <h2>JABATAN PENDIDIKAN NEGERI SELANGOR</h2>
    <h1>SISTEM PELANTIKAN PETUGAS<br>PEPERIKSAAN SPM TAHUN 2026</h1>
    <p>Selamat Datang ke Portal Pelantikan. Sila pilih kategori petugas untuk log masuk. Sistem ini untuk urusan pelantikan petugas peperiksaan SPM 2026 bagi negeri Selangor sahaja.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

c1,c2,c3,c4 = st.columns(4, gap="medium")

with c1:
    st.markdown("""
    <div class="card">
        <div class="badge" style="background:#E8F0FE; color:#0d47a1;">1 • SEKOLAH</div>
        <h3>🏫 SUP</h3>
        <p><b>Superintendent / Ketua Pusat Peperiksaan Sekolah</b><br><br>Pilih daerah PPD anda, kemudian pilih sekolah anda dan masukkan kata laluan yang dibekalkan oleh PPD.<br><br>Sekolah Berdaftar</p>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/1_SUP_Sekolah.py", label="Log Masuk SUP →", icon="🏫", use_container_width=True)
    st.caption("Klik nama sekolah untuk log masuk SUP")

with c2:
    st.markdown("""
    <div class="card" style="border-top:3px solid #ff9800;">
        <div class="badge" style="background:#FFF3E0; color:#e65100;">2 • DAERAH</div>
        <h3>🏢 PPD</h3>
        <p><b>Log Masuk PPD</b><br><br>Pilih PPD anda dan log masuk menggunakan kata laluan PPD untuk pengesahan pelantikan daerah.<br><br>PPD Berdaftar: HULU SELANGOR, KUALA SELANGOR dll</p>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/2_PPD_Daerah.py", label="Log Masuk PPD →", icon="🏢", use_container_width=True)
    st.caption("Template JPN + ZIP Pukal")

with c3:
    st.markdown("""
    <div class="card" style="border-top:3px solid #0d47a1;">
        <div class="badge" style="background:#0d47a1; color:white;">3 • NEGERI</div>
        <h3>🏛️ JPN</h3>
        <p><b>Pentadbir Negeri Selangor</b><br><br>Akses pentadbiran utama JPN Selangor untuk pemantauan keseluruhan SPM 2026. Termasuk Template Surat Selaras + ZIP Pukal.</p>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/3_JPN_Negeri.py", label="Log Masuk JPN →", icon="🏛️", use_container_width=True)
    st.caption("Dashboard Negeri + Export")

with c4:
    st.markdown("""
    <div class="card" style="background: linear-gradient(180deg, #f8fafd, #ffffff);">
        <div class="badge" style="background:#E8F5E9; color:#2e7d32;">INFO</div>
        <h3>ℹ️ Info Sistem</h3>
        <p>Sistem ini dibangunkan untuk memudahkan pelantikan petugas peperiksaan dengan telus dan sistematik.<br><br>• 1 Repo GitHub<br>• 1 Supabase Project<br>• 1 Projek Streamlit<br>• 8800+ baris kod asal kekal<br><br><b>JPN Selangor 2026</b></p>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/4_Info_Panduan.py", label="Panduan →", icon="ℹ️", use_container_width=True)
    st.caption("Kata laluan dibekalkan PPD/JPN")

st.markdown("<br><br><div style='text-align:center; color:#9aa6bd; font-size:11px; font-family:Inter;'>Sistem Pelantikan Petugas SPM Selangor 2026 · Jabatan Pendidikan Negeri Selangor<br>1 GitHub Repo · 1 Supabase Project · 1 Streamlit Project · 8800 baris asal kekal</div>", unsafe_allow_html=True)
