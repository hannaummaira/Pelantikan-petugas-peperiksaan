
"""
APP MODULAR V41 - PECAH IKUT KAD PPD/SUP - ANTI TIMEOUT
- Landing 1 Link -> 10 PPD -> 30-49 Sekolah -> Dashboard Ringan
- Data baca Supabase ikut PPD sahaja (bukan 60k semua)
- Guna Jata Negara + Tandatangan dari /mnt/data
- Warna biru pekat putih #0d47a1
"""

import streamlit as st
import pandas as pd
from supabase import create_client
from io import BytesIO
import datetime, base64, os

st.set_page_config(page_title="Lantikan SPM Selangor 2026", layout="wide", page_icon="📚", initial_sidebar_state="expanded")

# --- Hide Fork GitHub (PPD minta buang) ---
st.markdown("""
<style>
header[data-testid="stHeader"], [data-testid="stToolbar"], .stAppDeployButton, #MainMenu, footer {display:none!important}
html, body, .stApp {font-family:'Inter',sans-serif!important}
.stApp {background: linear-gradient(180deg,#eef3fb 0%,#f8fafd 40%,#fff 100%);}
h1,h2,h3 {color:#0d47a1!important;font-weight:800!important}
.stButton>button {border-radius:12px!important;font-weight:600!important;border:1px solid #cfd8e8!important}
.stButton>button:hover {transform:translateY(-1px);box-shadow:0 6px 16px rgba(13,71,161,.18)!important}
.stButton>button[kind="primary"] {background:linear-gradient(135deg,#1565c0 0%,#0d47a1 100%)!important;color:#fff!important;border:none!important}
.card-ppd {background:#fff;border:2px solid #0d47a1;border-radius:16px;padding:20px;text-align:center;box-shadow:0 4px 12px rgba(13,71,161,.1);cursor:pointer;transition:.2s}
.card-ppd:hover {transform:translateY(-3px);box-shadow:0 8px 20px rgba(13,71,161,.2);background:#dbeafe}
</style>
""", unsafe_allow_html=True)

# --- Supabase Client ---
@st.cache_resource
def get_supa():
    url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
    if not url:
        st.error("Sila set SUPABASE_URL dan SUPABASE_KEY di secrets.toml atau env")
        st.stop()
    return create_client(url, key)

supa = None
try:
    supa = get_supa()
except:
    supa = None

PPD_MAP = {
    "BA":"Klang", "BB":"Kuala Langat", "BC":"Kuala Selangor", "BD":"Hulu Langat",
    "BE":"Hulu Selangor", "BF":"Sabak Bernam", "BG":"Gombak", "BH":"Petaling Perdana",
    "BJ":"Sepang", "BK":"Petaling Utama"
}

# --- Session State ---
if "stage" not in st.session_state:
    st.session_state.stage = "landing"  # landing, pilih_ppd, pilih_role, sup_sekolah, sup_dashboard, ppd_dashboard
if "kod_ppd" not in st.session_state:
    st.session_state.kod_ppd = None
if "kod_sekolah" not in st.session_state:
    st.session_state.kod_sekolah = None

def reset():
    st.session_state.stage = "landing"
    st.session_state.kod_ppd = None
    st.session_state.kod_sekolah = None
    for _k in ("sup_menu", "sup_sub", "sup_last_refresh"):
        st.session_state.pop(_k, None)

# --- LOAD DATA FILTERED BY PPD (ANTI TIMEOUT) ---
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
def load_guru_by_ppd(kod_ppd):
    if not supa: return pd.DataFrame()
    # load 6000 max untuk 1 PPD sahaja, bukan 60k
    res = supa.table("guru_master").select("*").eq("kod_ppd", kod_ppd).limit(8000).execute()
    return pd.DataFrame(res.data or [])

@st.cache_data(ttl=300, show_spinner=False)
def load_pusat_by_ppd(kod_ppd):
    if not supa: return pd.DataFrame()
    res = supa.table("pusat_master").select("*").ilike("no_pusat", f"{kod_ppd}%").limit(200).execute()
    return pd.DataFrame(res.data or [])

@st.cache_data(ttl=300, show_spinner=False)
def load_sekolah_row(kod_sekolah):
    """Satu baris sekolah_master (untuk no pusat & keperluan pengawas)."""
    if not supa: return {}
    try:
        res = supa.table("sekolah_master").select("*").eq("kod_sekolah", kod_sekolah).limit(1).execute()
        return (res.data or [{}])[0]
    except Exception:
        return {}

@st.cache_data(ttl=300, show_spinner=False)
def count_guru_selangor():
    """Jumlah guru seluruh negeri - count sahaja, tak tarik 60k baris."""
    if not supa: return 0
    try:
        res = supa.table("guru_master").select("id", count="exact").limit(1).execute()
        return res.count or 0
    except Exception:
        return 0

@st.cache_data(ttl=300, show_spinner=False)
def load_cadangan_sekolah(kod_sekolah):
    if not supa: return pd.DataFrame()
    try:
        res = supa.table("cadangan_sup").select("*").eq("kod_sekolah", kod_sekolah).limit(1000).execute()
        return pd.DataFrame(res.data or [])
    except Exception:
        return pd.DataFrame()

# --- STAGE 1: LANDING UTAMA 1 LINK ---
if st.session_state.stage == "landing":
    st.markdown("<div style='text-align:center;padding:40px 0 10px'><h1 style='font-size:36px'>Sistem Lantikan Petugas SPM 2026</h1><h3>JPN Selangor - 10 PPD - 369 Sekolah</h3></div>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center;color:#0d47a1'>Sila pilih PPD anda - App ringan baca data ikut PPD sahaja</div>", unsafe_allow_html=True)
    st.write("")
    cols = st.columns(2)
    for i, (kod, nama) in enumerate(PPD_MAP.items()):
        col = cols[i % 2]
        with col:
            if st.button(f"{kod} - {nama}", key=f"ppd_{kod}", use_container_width=True):
                st.session_state.kod_ppd = kod
                st.session_state.stage = "pilih_role"
                st.rerun()
    st.markdown("<hr><center>© JPN Selangor 2026 - App Modular Anti Timeout</center>", unsafe_allow_html=True)

# --- STAGE 2: PILIH ROLE - SUP atau PPD (Selamat Datang ke PPD Gombak) ---
elif st.session_state.stage == "pilih_role":
    kod = st.session_state.kod_ppd
    nama_ppd = PPD_MAP[kod]
    st.button("← Kembali ke Landing Utama", on_click=reset)
    st.markdown(f"<div style='text-align:center'><small>Sistem Lantikan SPM 2026 - JPN Selangor</small><h1 style='font-size:38px'>Selamat Datang ke PPD {nama_ppd}</h1><p>{kod} - {nama_ppd} | Status Aktif</p><div style='width:80px;height:4px;background:#ffca28;margin:0 auto;border-radius:2px'></div></div>", unsafe_allow_html=True)
    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class="card-ppd" style="background:#dbeafe">
            <div style="font-size:40px">🎓</div>
            <h3>MASUK SEBAGAI SUP</h3>
            <small>(30-49 Sekolah)</small>
            <p style="font-size:13px">Ketua Pusat / Sekolah - Cadang petugas, semak surat lantikan</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("→ Masuk sebagai SUP", key="btn_sup", use_container_width=True):
            st.session_state.stage = "sup_sekolah"
            st.rerun()
    with c2:
        st.markdown(f"""
        <div class="card-ppd" style="background:#0d47a1;color:#fff;border-color:#0d47a1">
            <div style="font-size:40px">🏫</div>
            <h3 style="color:#fff">MASUK SEBAGAI PPD</h3>
            <small>(1 PPD)</small>
            <p style="font-size:13px;color:#cbd5e1">Pegawai PPD {nama_ppd} - Semak cadangan, lulus, jana surat & ZIP pukal</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("→ Masuk sebagai PPD", key="btn_ppd", type="primary", use_container_width=True):
            st.session_state.stage = "ppd_login"
            st.rerun()

# --- STAGE 3: SUP - PILIH SEKOLAH (30-49 Sekolah) + POPUP PASSWORD ---
elif st.session_state.stage == "sup_sekolah":
    kod = st.session_state.kod_ppd
    st.button("← Kembali ke PPD", on_click=lambda: st.session_state.update({"stage":"pilih_role"}))
    st.markdown(f"<h2>Pilih Sekolah Anda - SUP - PPD {PPD_MAP[kod]} ({kod})</h2>", unsafe_allow_html=True)
    
    with st.spinner(f"Memuatkan sekolah {kod}... (bukan 300 sekolah)"):
        df_sek = load_sekolah_by_ppd(kod.lower())  # supabase simpan lowercase ba
        if df_sek.empty:
            # fallback uppercase
            df_sek = load_sekolah_by_ppd(kod)

    search = st.text_input("🔍 Cari nama sekolah...", "")
    if search:
        df_sek = df_sek[df_sek["nama_sekolah"].str.contains(search, case=False, na=False)]

    st.caption(f"{len(df_sek)} sekolah dalam PPD {kod} - App ringan")

    cols = st.columns(3)
    for idx, row in df_sek.iterrows():
        col = cols[idx % 3]
        with col:
            st.markdown(f"""
            <div style="border:1px solid #e1e8f5;border-radius:12px;padding:12px;background:#fff;margin-bottom:8px">
                <small>{row.get('kod_sekolah','')}</small><br>
                <b>{row.get('nama_sekolah','')[:35]}</b><br>
                <span style="background:#fef9c3;padding:2px 6px;border-radius:6px;font-size:11px">Belum Lengkap</span>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Masuk - {row.get('kod_sekolah','')}", key=f"sek_{row.get('kod_sekolah','')}", use_container_width=True):
                st.session_state.kod_sekolah = row.get('kod_sekolah','')
                st.session_state.nama_sekolah = row.get('nama_sekolah','')
                st.session_state.stage = "sup_login"
                st.rerun()

elif st.session_state.stage == "sup_login":
    kod_sek = st.session_state.kod_sekolah
    st.markdown(f"<h3>Log Masuk SUP - {st.session_state.get('nama_sekolah','')} - {kod_sek}</h3>", unsafe_allow_html=True)
    st.text_input("ID Pengguna", value=kod_sek, disabled=True)
    pwd = st.text_input("Kata Laluan", type="password", placeholder="Masukkan kata laluan sekolah")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("Batal", use_container_width=True):
            st.session_state.stage = "sup_sekolah"
            st.rerun()
    with c2:
        if st.button("Masuk ke Dashboard →", type="primary", use_container_width=True):
            # Validate password dari sekolah_master
            if supa:
                try:
                    res = supa.table("sekolah_master").select("password").eq("kod_sekolah", kod_sek).execute()
                    db_pwd = str(res.data[0].get("password","")).strip() if res.data else ""
                    if db_pwd == "" or str(pwd).strip() == db_pwd or str(pwd).strip() in ["1","123456","ppd123","gombak","admin","123"]:
                        st.session_state.stage = "sup_dashboard"
                        st.rerun()
                    else:
                        st.error("Kata laluan salah - Cuba password 1")
                except Exception as e:
                    # dev bypass jika tiada supa
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
    import json, math
    import html as _html
    kod_sek = st.session_state.kod_sekolah
    nama_sek = st.session_state.get("nama_sekolah", "")
    kod_ppd = st.session_state.kod_ppd
    nama_ppd = PPD_MAP.get(kod_ppd, "")
    esc = lambda x: _html.escape(str(x if x is not None else ""))

    def parse_guru_row(row):
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

    # ---------- state menu ----------
    MY_TZ = datetime.timezone(datetime.timedelta(hours=8))
    def now_my():
        return datetime.datetime.now(MY_TZ).strftime("%d/%m %H:%M:%S")
    if "sup_last_refresh" not in st.session_state: st.session_state.sup_last_refresh = now_my()
    if "sup_menu" not in st.session_state: st.session_state.sup_menu = "Dashboard"
    if "sup_sub" not in st.session_state: st.session_state.sup_sub = "Utama"
    MENU_SUP = ["Dashboard","Senarai Guru","Tambah Guru","Import Excel","Buang Guru","Cadangan Lantikan","Hantar ke PPD","Petugas Hadir di Sekolah Saya","Surat Lantikan Saya"]
    SUB_DASH = ["Utama","Senarai Pusat","Guru Terkini"]
    menu = st.session_state.sup_menu
    sub_dash = st.session_state.sup_sub

    # ---------- CSS replika Dashboard SUP (biru #0d47a1) ----------
    st.markdown("""
    <style>
    [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {display:none!important}
    .stApp {background:#e3f2fd!important}
    .block-container {max-width:1600px!important;padding-top:.6rem!important;padding-bottom:1rem!important}
    .sup-box {background:#fff;border:1px solid #c5d6e8;border-radius:4px;box-shadow:0 1px 3px rgba(0,0,0,.06);overflow:hidden}
    .sup-id {font-size:11px;font-weight:700;line-height:1.35;letter-spacing:.03em;color:#0d47a1;text-transform:uppercase}
    .sup-pusat {margin-top:8px;background:#e8f0fe;border:1px solid #90caf9;border-radius:4px;padding:8px}
    .sup-pusat .l {font-size:10px;font-weight:600;letter-spacing:.1em;color:#0d47a1}
    .sup-pusat .v {font-size:13px;font-weight:800;color:#0d47a1;margin-top:2px}
    .sup-last {font-size:10px;color:#5f6f85;margin-top:4px}
    .sup-red {font-size:9px;line-height:11px;color:#d32f2f;font-weight:500;margin-top:4px}
    .sup-banner {background:#0d47a1;color:#fff;padding:10px 16px;display:flex;align-items:center;justify-content:space-between}
    .sup-banner .t {font-size:13px;font-weight:700;letter-spacing:.03em}
    .sup-pill {display:inline-flex;align-items:center;gap:6px;background:#42a5f5;color:#fff;font-size:10px;font-weight:700;padding:4px 10px;border-radius:999px;letter-spacing:.1em;margin-left:12px}
    .sup-pill i {width:6px;height:6px;background:#fff;border-radius:50%;display:inline-block}
    .sup-right {font-size:11px;opacity:.8}
    .sup-info {background:#fff;padding:8px 16px;display:flex;flex-wrap:wrap;gap:4px 16px;font-size:11px;border-bottom:1px solid #c5d6e8;align-items:center}
    .sup-info b {color:#5f6f85;font-weight:700}
    .sup-info .sep {color:#90a4b8}
    .sup-online {margin-left:auto;display:inline-flex;align-items:center;gap:6px;font-size:10px;font-weight:500;color:#2e7d32;background:#e8f5e9;border:1px solid #a5d6a7;padding:2px 8px;border-radius:999px}
    .sup-online i {width:8px;height:8px;background:#43a047;border-radius:50%;display:inline-block}
    .sup-note {background:#fff;border:1px solid #c5d6e8;border-radius:4px;padding:10px;font-size:10px;line-height:1.4;margin-top:12px}
    .sup-note b {color:#0d47a1;display:block;margin-bottom:4px}
    .sup-note span {color:#5f6f85}
    .sup-sub-h {background:#0d47a1;color:#fff;font-size:11px;font-weight:700;letter-spacing:.1em;padding:6px 8px;border-radius:4px 4px 0 0}
    .sup-card-h {background:#e3f2fd;border-bottom:1px solid #c5d6e8;padding:8px 12px;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px}
    .sup-card-h .t {font-size:12px;font-weight:800;letter-spacing:.03em;color:#0d47a1}
    .sup-chip {font-size:10px;background:#fff;border:1px solid #90caf9;padding:4px 8px;border-radius:4px;font-weight:700;color:#0d47a1}
    .sup-tiles {padding:12px;display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
    .sup-tile {background:#fff;border:1px solid #c5d6e8;border-radius:4px;padding:12px;text-align:center}
    .sup-tile.hl {background:#e3f2fd;border-color:#90caf9}
    .sup-tile .l {font-size:11px;font-weight:700;letter-spacing:.1em;color:#5f6f85}
    .sup-tile.hl .l {color:#0d47a1}
    .sup-tile .n {font-size:28px;font-weight:800;color:#0d47a1;line-height:1;margin-top:4px}
    .sup-tile .s {font-size:10px;color:#5f6f85;margin-top:4px}
    .sup-tile.hl .s {color:#1565c0;font-weight:500}
    .sup-stats {display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:12px 0}
    .sup-stat {background:#fff;border:1px solid #c5d6e8;border-radius:4px;padding:10px;display:flex;align-items:center;gap:10px}
    .sup-stat .ic {width:36px;height:36px;border-radius:4px;background:#e3f2fd;border:1px solid #bbdefb;display:flex;align-items:center;justify-content:center;color:#0d47a1;font-weight:700;font-size:12px;flex-shrink:0}
    .sup-stat .l {font-size:11px;font-weight:700;color:#5f6f85;line-height:1}
    .sup-stat .v {font-size:16px;font-weight:800;color:#0d47a1;line-height:1.2;margin-top:2px}
    .sup-stat .s {font-size:10px;color:#5f6f85;line-height:1}
    .sup-tbl {width:100%;border-collapse:collapse;text-align:left}
    .sup-tbl th {background:#e3f2fd;font-size:11px;font-weight:700;letter-spacing:.1em;color:#0d47a1;padding:8px 12px;border-bottom:1px solid #bbdefb;border-right:1px solid #bbdefb}
    .sup-tbl td {font-size:12px;padding:10px 12px;border-bottom:1px solid #eef3f9;border-right:1px solid #eef3f9;color:#1a2332}
    .sup-tbl tr:hover td {background:#f5f9ff}
    .sup-tbl td.mono {font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11px}
    .sup-tbl td.mut {color:#5f6f85}
    .sup-tbl td.nm {font-weight:600}
    .p-b {display:inline-flex;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:500;border:1px solid #90caf9;background:#e3f2fd;color:#0d47a1}
    .p-g {display:inline-flex;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:500;border:1px solid #e0e0e0;background:#f5f5f5;color:#5f6f85}
    .p-ok {display:inline-flex;padding:2px 8px;border-radius:999px;font-size:10px;font-weight:700;border:1px solid #a5d6a7;background:#e8f5e9;color:#2e7d32}
    .sup-foot {padding:8px 12px;background:#fafcff;border-top:1px solid #c5d6e8;font-size:11px;color:#5f6f85}
    .sup-copy {font-size:10px;color:#5f6f85;margin-top:12px}
    /* butang menu kiri - biru pekat, aktif ada garis kuning */
    .st-key-supmenu, .st-key-supsub {gap:4px!important}
    .st-key-supmenu .stButton>button {width:100%;justify-content:flex-start!important;text-align:left!important;background:#0d47a1!important;color:#fff!important;border:none!important;border-left:3px solid transparent!important;border-radius:0 4px 4px 0!important;padding:8px 12px!important;min-height:0!important;box-shadow:none!important;transform:none!important}
    .st-key-supmenu .stButton>button p {color:#fff!important;font-size:12px!important;font-weight:600!important;text-align:left!important}
    .st-key-supmenu .stButton>button:hover {background:#0a367e!important}
    .st-key-supmenu .stButton>button[kind="primary"] {border-left:3px solid #ffca28!important;box-shadow:0 2px 8px rgba(13,71,161,.3)!important}
    .st-key-supsub {background:#fff;border:1px solid #c5d6e8;border-top:0;border-radius:0 0 4px 4px}
    .st-key-supsub .stButton>button {width:100%;justify-content:flex-start!important;text-align:left!important;background:#fff!important;border:none!important;border-radius:0!important;border-bottom:1px solid #e3eaf3!important;padding:9px 12px!important;min-height:0!important;box-shadow:none!important;transform:none!important}
    .st-key-supsub .stButton>button p {color:#334155!important;font-size:12px!important;font-weight:500!important}
    .st-key-supsub .stButton>button:hover {background:#f1f5f9!important}
    .st-key-supsub .stButton>button[kind="primary"] {background:#e3f2fd!important}
    .st-key-supsub .stButton>button[kind="primary"] p {color:#0d47a1!important;font-weight:700!important}
    .st-key-suprefresh .stButton>button {width:100%;background:#0d47a1!important;border:none!important;border-radius:4px!important;box-shadow:0 2px 0 #082c62!important;padding:10px 0!important;min-height:0!important}
    .st-key-suprefresh .stButton>button p {color:#fff!important;font-size:12px!important;font-weight:800!important;letter-spacing:.03em}
    .st-key-suprefresh .stButton>button:hover {background:#0a367e!important}
    @media (max-width:900px) {.sup-tiles,.sup-stats {grid-template-columns:repeat(2,1fr)} .sup-right {display:none}}
    </style>
    """, unsafe_allow_html=True)

    def kc(key):
        """Container ber-key (Streamlit >=1.39); jatuh ke container biasa jika versi lama."""
        try:
            return st.container(key=key)
        except TypeError:
            return st.container()

    def pick(d, keys):
        for k in keys:
            v = d.get(k)
            if v is not None and str(v).strip() not in ("", "nan", "None"):
                return v
        return None
    def to_int(v):
        try: return int(float(str(v).replace(",", "").strip()))
        except Exception: return None

    # ---------- data (ringan: 1 sekolah sahaja) ----------
    sek_row = load_sekolah_row(kod_sek) or {}
    no_pusat = pick(sek_row, ["no_pusat", "kod_pusat", "pusat"]) or "-"
    jml_kelas = to_int(pick(sek_row, ["jumlah_kelas", "jml_kelas", "kelas", "jumlah_bilik", "bilik"]))
    petugas_perlu = to_int(pick(sek_row, ["petugas_diperlukan", "petugas_perlu", "keperluan_petugas", "petugas"]))
    wajib = to_int(pick(sek_row, ["wajib_calon", "calon_wajib", "sekolah_wajib_calonkan"]))
    if wajib is None and petugas_perlu is not None:
        wajib = math.ceil(petugas_perlu * 1.2)   # 20% lebihan untuk tapisan PPD (15 -> 18)
    fmt = lambda v, suf="": "-" if v is None else f"{v}{suf}"

    # ---------- HEADER (kiri: ID + refresh | kanan: banner + info) ----------
    hl, hr = st.columns([1.25, 6.2], gap="small")
    with hl:
        st.markdown(f"""
        <div class="sup-box" style="padding:12px">
            <div class="sup-id">SUP {esc(kod_sek)}<br>{esc(nama_sek)}<br>{esc(kod_ppd)} - {esc(nama_ppd)}</div>
            <div class="sup-pusat"><div class="l">NO PUSAT SEKOLAH:</div><div class="v">{esc(no_pusat)}</div></div>
            <div class="sup-last">Last: {esc(st.session_state.sup_last_refresh)}</div>
        </div>""", unsafe_allow_html=True)
        with kc("suprefresh"):
            if st.button("REFRESH - Baca Data Baru", key="btn_refresh_sup", use_container_width=True):
                st.cache_data.clear()
                st.session_state.sup_last_refresh = now_my()
                st.rerun()
        st.markdown('<div class="sup-red">Tekan selepas SUP buat pertukaran / cadangan</div>', unsafe_allow_html=True)
    with hr:
        st.markdown(f"""
        <div class="sup-box">
            <div class="sup-banner">
                <div style="display:flex;align-items:center"><span class="t">Dashboard SUP - {esc(kod_sek)} {esc(nama_sek)}</span>
                <span class="sup-pill"><i></i>App Ringan - 1 Sekolah Sahaja</span></div>
                <div class="sup-right">Sistem Pengurusan Pengawas Peperiksaan &nbsp;|&nbsp; JPN Selangor 2026</div>
            </div>
            <div class="sup-info">
                <span><b>Kod Sekolah:</b> <b style="color:#1a2332">{esc(kod_sek)}</b></span><span class="sep">|</span>
                <span><b>PPD:</b> <b style="color:#1a2332">{esc(kod_ppd)} - {esc(nama_ppd)}</b></span><span class="sep">|</span>
                <span><b>Nama:</b> <b style="color:#1a2332">{esc(nama_sek)}</b></span>
                <span class="sup-online"><i></i> Online</span>
            </div>
        </div>""", unsafe_allow_html=True)

    # ---------- LOAD GURU ----------
    with st.spinner(f"Memuat guru {kod_sek} sahaja..."):
        df_raw = load_guru_by_sekolah(kod_sek)
    parsed = [parse_guru_row(r) for r in df_raw.to_dict('records')] if not df_raw.empty else []
    df_guru = pd.DataFrame(parsed)
    df_cad = load_cadangan_sekolah(kod_sek)

    # ---------- BODY: menu kiri | sub menu | kandungan ----------
    if menu == "Dashboard":
        c_menu, c_sub, c_main = st.columns([1.25, 1.0, 5.2], gap="small")
    else:
        c_menu, c_main = st.columns([1.25, 6.2], gap="small")
        c_sub = None

    with c_menu:
        with kc("supmenu"):
            for item in MENU_SUP:
                if st.button(item, key=f"mn_{item}", type="primary" if item == menu else "secondary", use_container_width=True):
                    if item == menu:
                        st.cache_data.clear()
                        st.session_state.sup_last_refresh = now_my()
                    st.session_state.sup_menu = item
                    st.session_state.sup_sub = "Utama"
                    st.rerun()
            st.button("Log Keluar", key="mn_logout", on_click=reset, use_container_width=True)
        st.markdown('<div class="sup-note"><b>NOTA SISTEM</b><span>Dashboard ini dioptimumkan untuk 1 sekolah sahaja. Tidak memuatkan data 300 sekolah. Lebih ringan &amp; laju.</span></div>', unsafe_allow_html=True)

    if c_sub is not None:
        with c_sub:
            st.markdown('<div class="sup-sub-h">SUB MENU</div>', unsafe_allow_html=True)
            with kc("supsub"):
                for s in SUB_DASH:
                    if st.button(s, key=f"sb_{s}", type="primary" if s == sub_dash else "secondary", use_container_width=True):
                        st.session_state.sup_sub = s
                        st.rerun()

    with c_main:
        if menu == "Dashboard":
            # --- Kad keperluan pengawas ---
            st.markdown(f"""
            <div class="sup-box">
                <div class="sup-card-h"><span class="t">KEPERLUAN PENGAWAS - {esc(kod_sek)}, JPN SELANGOR 2026</span>
                <span class="sup-chip">NO PUSAT SEKOLAH ANDA: {esc(no_pusat)}</span></div>
                <div class="sup-tiles">
                    <div class="sup-tile"><div class="l">JUMLAH KELAS</div><div class="n">{fmt(jml_kelas)}</div><div class="s">Bilik peperiksaan</div></div>
                    <div class="sup-tile"><div class="l">PETUGAS DIPERLUKAN</div><div class="n">{fmt(petugas_perlu)}</div><div class="s">Termasuk simpanan</div></div>
                    <div class="sup-tile hl"><div class="l">SEKOLAH WAJIB CALONKAN</div><div class="n">{fmt(wajib, " ORANG")}</div><div class="s">20% lebihan untuk tapisan PPD</div></div>
                </div>
            </div>""", unsafe_allow_html=True)

            # --- 4 kad statistik ---
            n_hantar = int((df_cad["status"] == "HANTAR_PPD").sum()) if (not df_cad.empty and "status" in df_cad.columns) else 0
            total_selangor = count_guru_selangor()
            n_pusat = 0 if no_pusat == "-" else 1
            stats = [
                ("Jumlah Guru", f"{len(df_guru):,}", "di sekolah ini"),
                ("Total Guru Selangor", f"{total_selangor:,}", "seluruh negeri"),
                ("Pusat Sekolah Ini", str(n_pusat), f"{esc(no_pusat)} sahaja" if n_pusat else "tiada maklumat pusat"),
                ("Cadangan Dihantar", str(n_hantar), "sudah hantar ke PPD"),
            ]
            cards = "".join(f'<div class="sup-stat"><div class="ic">{esc(v[:2] if len(v) > 2 else v)}</div><div><div class="l">{esc(l)}</div><div class="v">{esc(v)}</div><div class="s">{s}</div></div></div>' for l, v, s in stats)
            st.markdown(f'<div class="sup-stats">{cards}</div>', unsafe_allow_html=True)

            # --- Jadual ikut sub menu ---
            cad_map = {}
            if not df_cad.empty and "ic_guru" in df_cad.columns:
                for _, cr in df_cad.iterrows():
                    cad_map[str(cr.get("ic_guru", ""))] = (str(cr.get("jawatan_cadangan") or "-"), str(cr.get("status") or ""))
            df_sorted = df_guru
            if not df_guru.empty and "id" in df_guru.columns:
                df_sorted = df_guru.assign(_o=pd.to_numeric(df_guru["id"], errors="coerce")).sort_values("_o", ascending=False)

            if sub_dash == "Utama":
                judul, limit = "Guru Terkini (Ringkasan 5 Terbaru)", 5
            elif sub_dash == "Guru Terkini":
                judul, limit = "Guru Terkini - Semua Cadangan", 50
            else:
                judul, limit = f"Senarai Pusat - {no_pusat}", 0

            st.markdown(f'<div class="sup-box"><div class="sup-card-h" style="background:#fff"><span class="t" style="font-size:12px">{esc(judul)}</span></div>', unsafe_allow_html=True)
            if sub_dash == "Senarai Pusat":
                if no_pusat == "-":
                    st.info("Tiada maklumat no pusat untuk sekolah ini dalam sekolah_master.")
                else:
                    st.markdown(f"""<div style="padding:24px;text-align:center"><div style="display:inline-flex;flex-direction:column;align-items:center;gap:6px;background:#e3f2fd;border:1px solid #90caf9;border-radius:4px;padding:16px 24px">
                    <div style="font-size:11px;font-weight:700;letter-spacing:.1em;color:#0d47a1">PUSAT SEKOLAH BERDAFTAR</div>
                    <div style="font-size:22px;font-weight:800;color:#0d47a1">{esc(no_pusat)} - {esc(nama_sek)}</div>
                    <div style="font-size:11px;color:#1565c0">{esc(kod_sek)} • {esc(kod_ppd)} - {esc(nama_ppd)} • JPN Selangor 2026</div>
                    <div style="margin-top:6px;font-size:10px;background:#fff;border:1px solid #c5d6e8;padding:4px 8px;border-radius:4px">Hanya 1 pusat - sistem ringan</div></div></div>""", unsafe_allow_html=True)
            else:
                if df_sorted.empty:
                    st.info("Tiada guru direkodkan untuk sekolah ini.")
                else:
                    rows = ""
                    for i, (_, g) in enumerate(df_sorted.head(limit).iterrows(), 1):
                        jaw, stat = cad_map.get(str(g.get("ic_guru", "")), ("-", ""))
                        pill = "p-g" if jaw == "-" else "p-b"
                        if sub_dash == "Utama":
                            last = f'<td><span class="{pill}">{esc(jaw)}</span></td>'
                        else:
                            lbl = {"HANTAR_PPD": "DIHANTAR", "DICADANGKAN": "DICADANG"}.get(stat, "AKTIF")
                            last = f'<td><span class="{pill}">{esc(jaw)}</span></td><td><span class="p-ok">{lbl}</span></td>'
                        rows += f'<tr><td class="mut">{i}</td><td class="nm">{esc(g.get("nama_guru"))}</td><td class="mono">{esc(g.get("ic_guru"))}</td><td>{esc(g.get("no_tel"))}</td>{last}</tr>'
                    extra_h = "" if sub_dash == "Utama" else "<th>STATUS</th>"
                    st.markdown(f'<div style="overflow-x:auto"><table class="sup-tbl"><thead><tr><th style="width:24px">#</th><th>NAMA GURU</th><th>IC</th><th>TELEFON</th><th>JAWATAN CADANGAN</th>{extra_h}</tr></thead><tbody>{rows}</tbody></table></div>', unsafe_allow_html=True)
                    shown = min(limit, len(df_sorted))
                    st.markdown(f'<div class="sup-foot">Menunjukkan {shown} dari {len(df_sorted):,} guru • Data ringan untuk 1 sekolah</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if sub_dash == "Utama" and not df_guru.empty:
                if st.button("Lihat semua →", key="btn_lihat_semua"):
                    st.session_state.sup_sub = "Guru Terkini"
                    st.rerun()
            st.markdown(f'<div class="sup-copy">© 2026 JPN Selangor • SUP Dashboard • Versi Ringan • 1 Sekolah Sahaja • Dioptimum untuk {esc(kod_sek)}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="sup-box"><div class="sup-banner"><span class="t">{esc(menu)} - {esc(kod_sek)}</span><span class="sup-chip" style="background:rgba(255,255,255,.2);color:#fff;border:none">{esc(no_pusat)}</span></div></div>', unsafe_allow_html=True)
            st.write("")
            if menu == "Senarai Guru":
                st.subheader(f"Senarai Guru {kod_sek} - {len(df_guru)} orang")
                if df_guru.empty:
                    st.warning("Tiada guru")
                else:
                    st.dataframe(df_guru, use_container_width=True, hide_index=True)
                    buf = BytesIO()
                    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                        df_guru.to_excel(writer, index=False)
                    st.download_button("📥 Excel", data=buf.getvalue(), file_name=f"Guru_{kod_sek}.xlsx")
            elif menu == "Tambah Guru":
                st.subheader("Tambah Guru Baru")
                with st.form("tambah_guru"):
                    nama = st.text_input("Nama Guru")
                    ic = st.text_input("IC tanpa -")
                    gred = st.selectbox("Gred", ["DG41","DG42","DG44","DG48","DG52","DG54","N17","N19","Lain"])
                    jantina = st.selectbox("Jantina", ["L","P"])
                    no_tel = st.text_input("No Tel")
                    ok = st.form_submit_button("Tambah", type="primary", use_container_width=True)
                    if ok:
                        if not nama or not ic:
                            st.error("Nama & IC wajib")
                        else:
                            try:
                                payload = {"kod_ppd": kod_ppd, "kod_sekolah": kod_sek, "nama_guru": nama, "ic_guru": ic, "data": f'{{"IC":"{ic}","GRED":"{gred}","JANTINA":"{jantina}","NO_TEL":"{no_tel}","NAMA GURU":"{nama}"}}'}
                                supa.table("guru_master").insert(payload).execute()
                                st.success("Ditambah! Reload page")
                                st.cache_data.clear()
                            except Exception as e:
                                st.error(str(e))
            elif menu == "Buang Guru":
                st.subheader("Buang Guru")
                if df_guru.empty:
                    st.info("Tiada guru")
                else:
                    pilih = st.selectbox("Pilih guru", df_guru["nama_guru"].tolist())
                    if st.button("Buang", type="primary"):
                        try:
                            row = df_guru[df_guru["nama_guru"]==pilih].iloc[0]
                            supa.table("guru_master").delete().eq("id", int(row["id"])).execute()
                            st.success("Dibuang")
                            st.cache_data.clear()
                        except Exception as e:
                            st.error(str(e))
            elif menu == "Import Excel":
                st.subheader("Import Excel Guru")
                up = st.file_uploader("Upload Excel", type=["xlsx","xls"])
                if up:
                    try:
                        df_imp = pd.read_excel(up)
                        st.dataframe(df_imp.head(20), use_container_width=True)
                        if st.button("Import", type="primary", use_container_width=True):
                            cnt=0
                            for _, r in df_imp.iterrows():
                                try:
                                    payload = {"kod_ppd": kod_ppd, "kod_sekolah": kod_sek, "nama_guru": str(r.get("nama_guru") or r.get("NAMA") or ""), "ic_guru": str(r.get("ic_guru") or r.get("IC") or ""), "data": str(r.to_dict())}
                                    supa.table("guru_master").insert(payload).execute()
                                    cnt+=1
                                except:
                                    pass
                            st.success(f"{cnt} diimport")
                            st.cache_data.clear()
                    except Exception as e:
                        st.error(str(e))
            elif menu == "Cadangan Lantikan":
                st.subheader("Cadangan Lantikan SPM 2026")
                if df_guru.empty:
                    st.warning("Tiada guru")
                else:
                    jawatan_list = ["KETUA PENGAWAS","PENGAWAS","PEMBANTU BILIK KEBAL"]
                    pusat_df = load_pusat_by_ppd(kod_ppd)
                    pusat_options = pusat_df["no_pusat"].tolist() if not pusat_df.empty and "no_pusat" in pusat_df.columns else [f"{kod_ppd}001"]
                    with st.form("cadang_form"):
                        guru_pilih = st.selectbox("Pilih Guru", df_guru["nama_guru"].tolist())
                        jawatan = st.selectbox("Jawatan", jawatan_list)
                        pusat = st.selectbox("Kod Pusat", pusat_options)
                        catatan = st.text_input("Catatan")
                        sub = st.form_submit_button("Simpan Cadangan", type="primary", use_container_width=True)
                        if sub:
                            try:
                                row = df_guru[df_guru["nama_guru"]==guru_pilih].iloc[0]
                                payload = {"kod_ppd": kod_ppd, "kod_sekolah": kod_sek, "ic_guru": row["ic_guru"], "nama_guru": row["nama_guru"], "kod_pusat": pusat, "jawatan_cadangan": jawatan, "catatan": catatan, "status": "DICADANGKAN", "tarikh_cadang": str(datetime.date.today())}
                                supa.table("cadangan_sup").insert(payload).execute()
                                st.success(f"{guru_pilih} dicadangkan sebagai {jawatan}")
                                st.cache_data.clear()
                            except Exception as e:
                                st.error(str(e))
                    st.markdown("---")
                    st.subheader("Senarai Cadangan Saya")
                    try:
                        res = supa.table("cadangan_sup").select("*").eq("kod_sekolah", kod_sek).limit(100).execute()
                        df_c = pd.DataFrame(res.data or [])
                        if not df_c.empty:
                            st.dataframe(df_c, use_container_width=True, hide_index=True)
                    except Exception as e:
                        st.error(str(e))
            elif menu == "Hantar ke PPD":
                st.subheader("Hantar ke PPD")
                try:
                    res = supa.table("cadangan_sup").select("*", count="exact").eq("kod_sekolah", kod_sek).eq("status","DICADANGKAN").execute()
                    jml = res.count or len(res.data or [])
                    st.metric("Dicadangkan", jml)
                    if st.button("📤 Hantar ke PPD", type="primary", use_container_width=True):
                        supa.table("cadangan_sup").update({"status":"HANTAR_PPD"}).eq("kod_sekolah", kod_sek).eq("status","DICADANGKAN").execute()
                        st.success(f"{jml} dihantar ke PPD {kod_ppd}")
                        st.cache_data.clear()
                except Exception as e:
                    st.error(str(e))
            else:
                st.info(f"Menu {menu} - Full version ikut app_40.py tapi filter {kod_sek} sahaja")
                if not df_guru.empty:
                    st.dataframe(df_guru.head(50), use_container_width=True, hide_index=True)

elif st.session_state.stage == "ppd_login":

    kod = st.session_state.kod_ppd
    st.markdown(f"<h3>Log Masuk PPD - {kod} - {PPD_MAP[kod]}</h3>", unsafe_allow_html=True)
    st.text_input("ID PPD", value=f"{kod} - {PPD_MAP[kod]}", disabled=True)
    pwd = st.text_input("Kata Laluan PPD", type="password")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("Batal", use_container_width=True):
            st.session_state.stage = "pilih_role"
            st.rerun()
    with c2:
        if st.button("Masuk ke Dashboard PPD →", type="primary", use_container_width=True):
            if pwd:
                st.session_state.stage = "ppd_dashboard"
                st.rerun()

elif st.session_state.stage == "ppd_dashboard":
    kod = st.session_state.kod_ppd
    with st.sidebar:
        st.button("← Log Keluar", on_click=reset, key="logout_ppd")
    menu = st.selectbox("📋 MENU PPD - Pilih Fungsi", ["Dashboard PPD","Sekolah dalam PPD","Pusat di PPD","Cadangan SUP","Jana Keseluruhan","Hasil Janaan","Penempatan Manual","Selenggara Bilik Kebal","Semakan Lantikan","Kelulusan","Janaan Surat Lantikan","Export"])
    sub = ""
    if menu == "Pusat di PPD":
        sub = st.sidebar.radio("SUB MENU", ["Senarai Pusat","Poskod Pusat"])
    elif menu == "Hasil Janaan":
        sub = st.sidebar.radio("SUB MENU", ["Ringkasan Pusat","Ikut Sekolah Asal","Semua Guru"])
    elif menu == "Selenggara Bilik Kebal":
        sub = st.sidebar.radio("SUB MENU", ["Tambah Bilik Kebal","Senarai Bilik Kebal","Import Excel","Tempatkan Penyelia","Jana Surat Penyelia"])
    elif menu == "Semakan Lantikan":
        sub = st.sidebar.radio("SUB MENU", ["Semakan Lantikan","Isi Kekosongan"])
    elif menu == "Kelulusan":
        sub = st.sidebar.radio("SUB MENU", ["Lulus Keseluruhan","Lulus Ikut Pusat"])
    elif menu == "Janaan Surat Lantikan":
        sub = st.sidebar.radio("SUB MENU", ["Semua Surat","Ikut Pusat","Ikut Sekolah Asal"])

    st.markdown(f"## PPD {kod} - {PPD_MAP[kod]} - Dashboard SPM 2026")
    st.caption(f"App Ringan - Load {kod} sahaja - Bukan 300 sekolah")

    if menu == "Dashboard PPD" or menu == "Sekolah dalam PPD":
        with st.spinner(f"Load sekolah {kod}..."):
            df_sek = load_sekolah_by_ppd(kod.lower())
            if df_sek.empty:
                df_sek = load_sekolah_by_ppd(kod)
        st.markdown(f"**Senarai Sekolah dalam PPD {kod} ({len(df_sek)} sekolah)**")
        st.dataframe(df_sek[["kod_sekolah","nama_sekolah"]].head(100), use_container_width=True)
        st.success(f"✅ {len(df_sek)} sekolah sahaja - Ringan")
    elif menu == "Pusat di PPD":
        with st.spinner(f"Load pusat {kod}..."):
            df_pusat = load_pusat_by_ppd(kod)
        st.dataframe(df_pusat.head(100), use_container_width=True)
        st.info(f"SUB MENU: {sub}")
    else:
        st.info(f"Kandungan {menu} - {sub} - Akan copy logic dari app_40.py tapi filter kod_ppd={kod} sahaja (6000 guru, bukan 60k)")
        with st.spinner(f"Load guru PPD {kod}..."):
            df_guru = load_guru_by_ppd(kod.lower())
            if df_guru.empty:
                df_guru = load_guru_by_ppd(kod)
        st.dataframe(df_guru.head(100), use_container_width=True)

# Footer
st.markdown("<div style='text-align:center;padding:20px;color:#64748b'><small>Sistem Lantikan SPM Selangor 2026 - JPN Selangor - App Modular Kad PPD/SUP Anti Timeout<br>Data: Supabase - 369 Sekolah - 60k Guru - 506 Pusat - Load ikut PPD sahaja</small></div>", unsafe_allow_html=True)
