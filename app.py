
import streamlit as st
import pandas as pd
from supabase import create_client
from io import BytesIO
import datetime, os, json

st.set_page_config(page_title="Lantikan SPM Selangor 2026 - SUP Tetap", layout="wide", initial_sidebar_state="collapsed")

# --- HIDE ALL DEFAULT STREAMLIT CHROME + SIDEBAR ASAL ---
st.markdown("""
<style>
header[data-testid="stHeader"], [data-testid="stToolbar"], .stAppDeployButton, #MainMenu, footer {display:none!important}
[data-testid="stSidebar"], [data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"] {display:none!important}

/* SIDEBAR TETAP KITA SENDIRI - REPLIKA BFT0003 */
.sidebar-tetap {
    position: fixed !important;
    left: 0 !important;
    top: 0 !important;
    width: 280px !important;
    height: 100vh !important;
    background: linear-gradient(180deg, #0d47a1 0%, #0b3d91 50%, #1565c0 100%) !important;
    padding: 0 !important;
    z-index: 9999 !important;
    overflow-y: auto !important;
    box-shadow: 4px 0 20px rgba(0,0,0,0.2) !important;
}
.sidebar-header {
    padding: 24px 20px;
    background: rgba(0,0,0,0.15);
    border-bottom: 2px solid #ffca28;
}
.sidebar-header h2 {
    color: #fff !important;
    font-size: 18px !important;
    font-weight: 800 !important;
    margin: 0 !important;
    line-height: 1.2 !important;
}
.sidebar-header small {
    color: #bbdefb !important;
    font-size: 12px !important;
}
.sidebar-menu {
    padding: 12px 0 !important;
}
.sidebar-menu .stRadio > label {display:none!important}
.sidebar-menu .stRadio div[role="radiogroup"] {
    flex-direction: column !important;
    gap: 2px !important;
}
.sidebar-menu .stRadio div[role="radiogroup"] label {
    background: transparent !important;
    color: #e3f2fd !important;
    padding: 12px 20px !important;
    border-radius: 0 !important;
    border-left: 4px solid transparent !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    transition: all 0.2s !important;
    width: 100% !important;
}
.sidebar-menu .stRadio div[role="radiogroup"] label:hover {
    background: rgba(255,255,255,0.1) !important;
    border-left-color: #ffca28 !important;
    color: #fff !important;
}
.sidebar-menu .stRadio div[role="radiogroup"] label:has(input:checked) {
    background: #fff !important;
    color: #0d47a1 !important;
    border-left-color: #ffca28 !important;
    font-weight: 700 !important;
    box-shadow: inset 0 0 0 1px rgba(0,0,0,0.05) !important;
}
.main-content {
    margin-left: 280px !important;
    padding: 24px 32px !important;
    min-height: 100vh !important;
    background: linear-gradient(180deg,#eef3fb 0%,#f8fafd 40%,#fff 100%) !important;
}
@media (max-width: 768px) {
    .sidebar-tetap {width: 100% !important; height: auto !important; position: relative !important;}
    .main-content {margin-left: 0 !important;}
}
h1,h2,h3 {color:#0d47a1!important;font-weight:800!important}
.stButton>button {border-radius:12px!important;font-weight:600!important}
.stButton>button[kind="primary"] {background:linear-gradient(135deg,#1565c0 0%,#0d47a1 100%)!important;color:#fff!important;border:none!important}
</style>
""", unsafe_allow_html=True)

# Supabase
@st.cache_resource
def get_supa():
    url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
    if not url:
        st.error("Set SUPABASE_URL dan KEY di secrets")
        st.stop()
    return create_client(url, key)

supa = None
try:
    supa = get_supa()
except:
    supa = None

PPD_MAP = {"BA":"Klang","BB":"Kuala Langat","BC":"Kuala Selangor","BD":"Hulu Langat","BE":"Hulu Selangor","BF":"Sabak Bernam","BG":"Gombak","BH":"Petaling Perdana","BJ":"Sepang","BK":"Petaling Utama"}

if "stage" not in st.session_state:
    st.session_state.stage = "landing"
if "kod_ppd" not in st.session_state:
    st.session_state.kod_ppd = None
if "kod_sekolah" not in st.session_state:
    st.session_state.kod_sekolah = None
if "sup_menu" not in st.session_state:
    st.session_state.sup_menu = "Dashboard"

def reset():
    st.session_state.stage = "landing"
    st.session_state.kod_ppd = None
    st.session_state.kod_sekolah = None

@st.cache_data(ttl=300, show_spinner=False)
def load_sekolah_by_ppd(kod_ppd):
    if not supa: return pd.DataFrame()
    res = supa.table("sekolah_master").select("*").eq("kod_ppd", kod_ppd).execute()
    return pd.DataFrame(res.data or [])

@st.cache_data(ttl=300, show_spinner=False)
def load_guru_by_sekolah(kod_sekolah):
    if not supa: return pd.DataFrame()
    res = supa.table("guru_master").select("*").eq("kod_sekolah", kod_sekolah).limit(2000).execute()
    return pd.DataFrame(res.data or [])

@st.cache_data(ttl=300, show_spinner=False)
def load_pusat_by_ppd(kod_ppd):
    if not supa: return pd.DataFrame()
    res = supa.table("pusat_master").select("*").ilike("no_pusat", f"{kod_ppd}%").limit(200).execute()
    return pd.DataFrame(res.data or [])

def parse_guru_row(row, kod_ppd, kod_sek):
    d = row.get('data') or '{}'
    try:
        j = json.loads(d) if isinstance(d, str) else (d if isinstance(d, dict) else {})
    except:
        j = {}
    return {
        'id': row.get('id'),
        'kod_ppd': row.get('kod_ppd') or j.get('KOD PPD') or kod_ppd,
        'kod_sekolah': row.get('kod_sekolah') or j.get('KOD SEKOLAH') or kod_sek,
        'nama_guru': row.get('nama_guru') or j.get('NAMA GURU') or j.get('NAMA_GURU') or '',
        'ic_guru': row.get('ic_guru') or j.get('IC') or '',
        'gred': j.get('GRED') or row.get('gred') or '',
        'jantina': j.get('JANTINA') or row.get('jantina') or '',
        'no_tel': j.get('NO_TEL') or row.get('no_tel') or '',
    }

# LANDING
if st.session_state.stage == "landing":
    st.markdown("<div style='text-align:center;padding:40px 0 10px'><h1 style='font-size:36px'>Sistem Lantikan Petugas SPM 2026</h1><h3>JPN Selangor - 10 PPD - 369 Sekolah</h3></div>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center;color:#0d47a1'>Sila pilih PPD anda - App ringan baca data ikut PPD sahaja</div>", unsafe_allow_html=True)
    cols = st.columns(2)
    for i, (kod, nama) in enumerate(PPD_MAP.items()):
        col = cols[i % 2]
        with col:
            if st.button(f"{kod} - {nama}", key=f"ppd_{kod}", use_container_width=True):
                st.session_state.kod_ppd = kod
                st.session_state.stage = "pilih_role"
                st.rerun()
    st.markdown("<hr><center>© JPN Selangor 2026 - App Modular Anti Timeout - Sidebar Tetap Replica</center>", unsafe_allow_html=True)

elif st.session_state.stage == "pilih_role":
    kod = st.session_state.kod_ppd
    nama_ppd = PPD_MAP[kod]
    if st.button("← Kembali ke Landing Utama"):
        reset()
        st.rerun()
    st.markdown(f"<div style='text-align:center'><h1>Selamat Datang ke PPD {nama_ppd}</h1><p>{kod} - {nama_ppd}</p><div style='width:80px;height:4px;background:#ffca28;margin:0 auto;border-radius:2px'></div></div>", unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        if st.button("→ Masuk sebagai SUP", use_container_width=True):
            st.session_state.stage = "sup_sekolah"
            st.rerun()
    with c2:
        if st.button("→ Masuk sebagai PPD", type="primary", use_container_width=True):
            st.session_state.stage = "ppd_login"
            st.rerun()

elif st.session_state.stage == "sup_sekolah":
    kod = st.session_state.kod_ppd
    st.button("← Kembali", on_click=lambda: setattr(st.session_state, 'stage', 'pilih_role'))
    st.markdown(f"### Pilih Sekolah - PPD {kod} - {PPD_MAP[kod]}")
    df = load_sekolah_by_ppd(kod)
    if df.empty:
        df = load_sekolah_by_ppd(kod.lower())
    if df.empty:
        st.warning("Tiada sekolah")
    else:
        for _, row in df.iterrows():
            if st.button(f"{row.get('kod_sekolah')} - {row.get('nama_sekolah')}", key=f"sek_{row.get('kod_sekolah')}", use_container_width=True):
                st.session_state.kod_sekolah = row.get('kod_sekolah','')
                st.session_state.nama_sekolah = row.get('nama_sekolah','')
                st.session_state.stage = "sup_login"
                st.rerun()

elif st.session_state.stage == "sup_login":
    kod_sek = st.session_state.kod_sekolah
    st.markdown(f"<h3>Log Masuk SUP - {st.session_state.get('nama_sekolah','')} - {kod_sek}</h3>", unsafe_allow_html=True)
    st.text_input("ID Pengguna", value=kod_sek, disabled=True)
    pwd = st.text_input("Kata Laluan (test guna 1)", type="password", placeholder="Masukkan 1")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("Batal", use_container_width=True):
            st.session_state.stage = "sup_sekolah"
            st.rerun()
    with c2:
        if st.button("Masuk ke Dashboard →", type="primary", use_container_width=True):
            if supa:
                try:
                    res = supa.table("sekolah_master").select("password").eq("kod_sekolah", kod_sek).execute()
                    db_pwd = str(res.data[0].get("password","")).strip() if res.data else ""
                    if db_pwd == "" or str(pwd).strip() == db_pwd or str(pwd).strip() in ["1","123456","ppd123","gombak","admin"]:
                        st.session_state.stage = "sup_dashboard"
                        st.rerun()
                    else:
                        st.error("Kata laluan salah - Cuba 1")
                except Exception as e:
                    if pwd:
                        st.session_state.stage = "sup_dashboard"
                        st.rerun()
                    else:
                        st.error(str(e))
            else:
                if pwd:
                    st.session_state.stage = "sup_dashboard"
                    st.rerun()

elif st.session_state.stage == "sup_dashboard":
    kod_sek = st.session_state.kod_sekolah
    nama_sek = st.session_state.get("nama_sekolah","")
    kod_ppd = st.session_state.kod_ppd
    
    # SIDEBAR TETAP HTML START
    st.markdown('<div class="sidebar-tetap">', unsafe_allow_html=True)
    st.markdown(f'<div class="sidebar-header"><h2>🏫 {kod_sek}</h2><small>{nama_sek[:30]}</small><br><small style="color:#ffca28">SUP - {kod_ppd} {PPD_MAP[kod_ppd]}</small></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-menu">', unsafe_allow_html=True)
    menu = st.radio("MENU", ["Dashboard","Senarai Guru","Tambah Guru","Import Excel","Buang Guru","Cadangan Lantikan","Hantar ke PPD","Surat Lantikan"], key="menu_tetap", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div style="padding:16px">', unsafe_allow_html=True)
    if st.button("← Log Keluar", use_container_width=True, key="logout_fixed"):
        reset()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # MAIN CONTENT
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.markdown(f"### SUP {kod_sek} - {nama_sek} - {kod_ppd}")
    
    df_raw = load_guru_by_sekolah(kod_sek)
    parsed = [parse_guru_row(r, kod_ppd, kod_sek) for r in df_raw.to_dict('records')] if not df_raw.empty else []
    df_guru = pd.DataFrame(parsed)
    
    if menu == "Dashboard":
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Jumlah Guru", len(df_guru))
        c2.metric("Kod PPD", kod_ppd)
        c3.metric("Kod Sekolah", kod_sek)
        c4.metric("Status", "Tetap - 1 Sekolah")
        if not df_guru.empty:
            st.dataframe(df_guru[["nama_guru","ic_guru","gred","jantina"]].head(100), use_container_width=True, hide_index=True)
        st.success(f"✅ Sidebar tetap - Load {len(df_guru)} guru sahaja!")
    elif menu == "Senarai Guru":
        st.subheader(f"Senarai Guru {kod_sek} - {len(df_guru)} orang")
        st.dataframe(df_guru, use_container_width=True, hide_index=True)
    elif menu == "Tambah Guru":
        st.subheader("Tambah Guru Baru")
        with st.form("tambah"):
            nama = st.text_input("Nama Guru")
            ic = st.text_input("IC")
            gred = st.selectbox("Gred", ["DG41","DG42","DG44","DG48","DG52"])
            jantina = st.selectbox("Jantina", ["L","P"])
            ok = st.form_submit_button("Tambah", type="primary")
            if ok:
                try:
                    payload = {"kod_ppd": kod_ppd, "kod_sekolah": kod_sek, "nama_guru": nama, "ic_guru": ic, "data": f'{{"IC":"{ic}","GRED":"{gred}","JANTINA":"{jantina}","NAMA GURU":"{nama}"}}'}
                    supa.table("guru_master").insert(payload).execute()
                    st.success("Ditambah!")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(str(e))
    elif menu == "Cadangan Lantikan":
        st.subheader("Cadangan Lantikan")
        if not df_guru.empty:
            jawatan_list = ["KETUA PENGAWAS","PENGAWAS","PEMBANTU BILIK KEBAL"]
            pusat_df = load_pusat_by_ppd(kod_ppd)
            pusat_options = pusat_df["no_pusat"].tolist() if not pusat_df.empty else [f"{kod_ppd}001"]
            with st.form("cadang"):
                guru_pilih = st.selectbox("Pilih Guru", df_guru["nama_guru"].tolist())
                jawatan = st.selectbox("Jawatan", jawatan_list)
                pusat = st.selectbox("Kod Pusat", pusat_options)
                sub = st.form_submit_button("Simpan Cadangan", type="primary")
                if sub:
                    try:
                        row = df_guru[df_guru["nama_guru"]==guru_pilih].iloc[0]
                        payload = {"kod_ppd": kod_ppd, "kod_sekolah": kod_sek, "ic_guru": row["ic_guru"], "nama_guru": row["nama_guru"], "kod_pusat": pusat, "jawatan_cadangan": jawatan, "status": "DICADANGKAN", "tarikh_cadang": str(datetime.date.today())}
                        supa.table("cadangan_sup").insert(payload).execute()
                        st.success("Disimpan!")
                    except Exception as e:
                        st.error(str(e))
    elif menu == "Hantar ke PPD":
        st.subheader("Hantar ke PPD")
        try:
            res = supa.table("cadangan_sup").select("*", count="exact").eq("kod_sekolah", kod_sek).eq("status","DICADANGKAN").execute()
            jml = res.count or len(res.data or [])
            st.metric("Dicadangkan", jml)
            if st.button("📤 Hantar ke PPD", type="primary"):
                supa.table("cadangan_sup").update({"status":"HANTAR_PPD"}).eq("kod_sekolah", kod_sek).eq("status","DICADANGKAN").execute()
                st.success("Dihantar!")
        except Exception as e:
            st.error(str(e))
    else:
        st.info(f"Menu {menu}")
    
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.stage == "ppd_login":
    kod = st.session_state.kod_ppd
    st.markdown(f"<h3>Log Masuk PPD - {kod}</h3>", unsafe_allow_html=True)
    pwd = st.text_input("Kata Laluan PPD", type="password")
    if st.button("Masuk ke Dashboard PPD →", type="primary"):
        if pwd:
            st.session_state.stage = "ppd_dashboard"
            st.rerun()

elif st.session_state.stage == "ppd_dashboard":
    kod = st.session_state.kod_ppd
    # Sidebar tetap PPD juga
    st.markdown('<div class="sidebar-tetap">', unsafe_allow_html=True)
    st.markdown(f'<div class="sidebar-header"><h2>🏫 PPD {kod}</h2><small>{PPD_MAP[kod]}</small></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-menu">', unsafe_allow_html=True)
    menu = st.radio("MENU PPD", ["Dashboard PPD","Sekolah dalam PPD","Pusat di PPD","Cadangan SUP"], key="menu_ppd_tetap", label_visibility="collapsed")
    st.markdown('</div><div style="padding:16px">', unsafe_allow_html=True)
    if st.button("← Log Keluar", key="logout_ppd_tetap", use_container_width=True):
        reset()
        st.rerun()
    st.markdown('</div></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.markdown(f"## PPD {kod} - {PPD_MAP[kod]} - Dashboard SPM 2026")
    if menu == "Dashboard PPD" or menu == "Sekolah dalam PPD":
        df_sek = load_sekolah_by_ppd(kod)
        if df_sek.empty:
            df_sek = load_sekolah_by_ppd(kod.lower())
        st.dataframe(df_sek[["kod_sekolah","nama_sekolah"]].head(100), use_container_width=True)
    elif menu == "Pusat di PPD":
        df_pusat = load_pusat_by_ppd(kod)
        st.dataframe(df_pusat.head(100), use_container_width=True)
    else:
        try:
            df_guru = supa.table("guru_master").select("*").eq("kod_ppd", kod).limit(100).execute()
            st.dataframe(pd.DataFrame(df_guru.data or []).head(100), use_container_width=True)
        except Exception as e:
            st.error(str(e))
    st.markdown('</div>', unsafe_allow_html=True)
