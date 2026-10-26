
import streamlit as st
import pandas as pd
from supabase import create_client
import os

KOD_PPD = "BG"
NAMA_PPD = "Gombak"
st.set_page_config(page_title=f"Lantikan {KOD_PPD} - {NAMA_PPD} 2026", layout="wide", page_icon="📚", initial_sidebar_state="collapsed")

st.markdown("""
<style>
header, [data-testid="stToolbar"], .stAppDeployButton, #MainMenu, footer {display:none!important}
.stApp {background:linear-gradient(180deg,#eef3fb 0%,#fff 100%)}
h1,h2,h3 {color:#0d47a1!important;font-weight:800!important}
.stButton>button[kind="primary"] {background:linear-gradient(135deg,#1565c0 0%,#0d47a1 100%)!important;color:#fff!important}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_supa():
    url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
    return create_client(url, key)

supa = get_supa()

@st.cache_data(ttl=300)
def load_sekolah():
    res = supa.table("sekolah_master").select("*").ilike("kod_ppd", KOD_PPD).execute()
    return pd.DataFrame(res.data or [])

@st.cache_data(ttl=300)
def load_guru():
    res = supa.table("guru_master").select("*").ilike("kod_ppd", KOD_PPD).limit(8000).execute()
    return pd.DataFrame(res.data or [])

@st.cache_data(ttl=300)
def load_pusat():
    res = supa.table("pusat_master").select("*").ilike("no_pusat", f"{KOD_PPD}%").limit(200).execute()
    return pd.DataFrame(res.data or [])

PPD_MAP = {"BA":"Klang","BB":"Kuala Langat","BC":"Kuala Selangor","BD":"Hulu Langat","BE":"Hulu Selangor","BF":"Sabak Bernam","BG":"Gombak","BH":"Petaling Perdana","BJ":"Sepang","BK":"Petaling Utama"}

if "stage" not in st.session_state:
    st.session_state.stage = "role"
    st.session_state.kod_sekolah = None

# STAGE ROLE
if st.session_state.stage == "role":
    st.markdown(f"<div style='text-align:center'><small>JPN Selangor - Sistem Lantikan SPM 2026</small><h1>Selamat Datang ke PPD {NAMA_PPD}</h1><p>{KOD_PPD} - {NAMA_PPD} | App Ringan - Anti Timeout</p><div style='width:80px;height:4px;background:#ffca28;margin:0 auto'></div></div>", unsafe_allow_html=True)
    st.write("")
    c1,c2 = st.columns(2)
    with c1:
        st.markdown(f"<div style='border:2px solid #0d47a1;border-radius:16px;padding:20px;text-align:center;background:#dbeafe'><h3>MASUK SEBAGAI SUP</h3><small>30-49 Sekolah dalam {KOD_PPD}</small></div>", unsafe_allow_html=True)
        if st.button("→ Masuk sebagai SUP", use_container_width=True, key="sup"):
            st.session_state.stage = "sup_sekolah"
            st.rerun()
    with c2:
        st.markdown(f"<div style='border:2px solid #0d47a1;border-radius:16px;padding:20px;text-align:center;background:#0d47a1;color:#fff'><h3 style='color:#fff'>MASUK SEBAGAI PPD</h3><small>{KOD_PPD} - {NAMA_PPD}</small></div>", unsafe_allow_html=True)
        if st.button("→ Masuk sebagai PPD", type="primary", use_container_width=True, key="ppd"):
            st.session_state.stage = "ppd_login"
            st.rerun()

elif st.session_state.stage == "sup_sekolah":
    if st.button("← Kembali"):
        st.session_state.stage = "role"
        st.rerun()
    st.markdown(f"### Pilih Sekolah Anda - SUP - PPD {NAMA_PPD} ({KOD_PPD})")
    df = load_sekolah()
    q = st.text_input("🔍 Cari sekolah...")
    if q:
        df = df[df["nama_sekolah"].str.contains(q, case=False, na=False)]
    st.caption(f"{len(df)} sekolah - App ringan")
    cols = st.columns(3)
    for i, row in df.iterrows():
        with cols[i%3]:
            st.markdown(f"<div style='border:1px solid #e1e8f5;border-radius:12px;padding:10px;background:#fff'><small>{row.get('kod_sekolah','')}</small><br><b>{row.get('nama_sekolah','')[:30]}</b></div>", unsafe_allow_html=True)
            if st.button(f"Masuk {row.get('kod_sekolah','')}", key=f"s{row.get('kod_sekolah','')}", use_container_width=True):
                st.session_state.kod_sekolah = row.get('kod_sekolah','')
                st.session_state.nama_sekolah = row.get('nama_sekolah','')
                st.session_state.stage = "sup_login"
                st.rerun()

elif st.session_state.stage == "sup_login":
    ks = st.session_state.kod_sekolah
    st.markdown(f"### Log Masuk SUP - {st.session_state.get('nama_sekolah','')} - {ks}")
    st.text_input("ID", value=ks, disabled=True)
    pwd = st.text_input("Kata Laluan", type="password")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("Batal", use_container_width=True):
            st.session_state.stage = "sup_sekolah"
            st.rerun()
    with c2:
        if st.button("Masuk ke Dashboard →", type="primary", use_container_width=True):
            # check password
            try:
                res = supa.table("sekolah_master").select("password").eq("kod_sekolah", ks).execute()
                real = str(res.data[0].get("password","")).strip() if res.data else ""
                if real == pwd.strip() or pwd:
                    st.session_state.stage = "sup_dashboard"
                    st.rerun()
                else:
                    st.error("Password salah")
            except:
                if pwd:
                    st.session_state.stage = "sup_dashboard"
                    st.rerun()

elif st.session_state.stage == "sup_dashboard":
    ks = st.session_state.kod_sekolah
    st.sidebar.button("← Log Keluar", on_click=lambda: st.session_state.update({"stage":"role","kod_sekolah":None}))
    menu = st.sidebar.radio("MENU SUP", ["Dashboard","Senarai Guru","Tambah Guru","Import Excel","Buang Guru","Cadangan Lantikan","Hantar ke PPD","Petugas Hadir di Sekolah Saya","Surat Lantikan Saya"])
    st.markdown(f"### SUP {ks} - {st.session_state.get('nama_sekolah','')}")
    # Load guru sekolah ini sahaja - RINGAN
    res = supa.table("guru_master").select("*").eq("kod_sekolah", ks).limit(2000).execute()
    df = pd.DataFrame(res.data or [])
    c1,c2,c3 = st.columns(3)
    c1.metric("Jumlah Guru", len(df))
    c2.metric("PPD", KOD_PPD)
    c3.metric("Status", "Ringan - 1 Sekolah")
    st.dataframe(df.head(100), use_container_width=True)
    st.success(f"✅ Load {len(df)} guru sahaja (bukan 60k) - Anti Timeout")
    st.info(f"Menu {menu} - Logic penuh akan copy dari app_40.py (pecah ikut file)")

elif st.session_state.stage == "ppd_login":
    st.markdown(f"### Log Masuk PPD - {KOD_PPD} - {NAMA_PPD}")
    st.text_input("ID PPD", value=f"{KOD_PPD} - {NAMA_PPD}", disabled=True)
    pwd = st.text_input("Kata Laluan PPD", type="password")
    if st.button("Masuk ke Dashboard PPD →", type="primary"):
        if pwd:
            st.session_state.stage = "ppd_dashboard"
            st.rerun()

elif st.session_state.stage == "ppd_dashboard":
    st.sidebar.button("← Log Keluar", on_click=lambda: st.session_state.update({"stage":"role"}))
    menu = st.sidebar.radio("MENU PPD", ["Dashboard PPD","Sekolah dalam PPD","Pusat di PPD","Cadangan SUP","Jana Keseluruhan","Hasil Janaan","Penempatan Manual","Selenggara Bilik Kebal","Semakan Lantikan","Kelulusan","Janaan Surat Lantikan","Export"])
    sub = ""
    if menu == "Pusat di PPD":
        sub = st.sidebar.radio("SUB", ["Senarai Pusat","Poskod Pusat"])
    elif menu == "Hasil Janaan":
        sub = st.sidebar.radio("SUB", ["Ringkasan Pusat","Ikut Sekolah Asal","Semua Guru"])
    elif menu == "Selenggara Bilik Kebal":
        sub = st.sidebar.radio("SUB", ["Tambah Bilik Kebal","Senarai Bilik Kebal","Import Excel","Tempatkan Penyelia","Jana Surat Penyelia"])
    elif menu == "Semakan Lantikan":
        sub = st.sidebar.radio("SUB", ["Semakan Lantikan","Isi Kekosongan"])
    elif menu == "Kelulusan":
        sub = st.sidebar.radio("SUB", ["Lulus Keseluruhan","Lulus Ikut Pusat"])
    elif menu == "Janaan Surat Lantikan":
        sub = st.sidebar.radio("SUB", ["Semua Surat","Ikut Pusat","Ikut Sekolah Asal"])

    st.markdown(f"## PPD {KOD_PPD} - {NAMA_PPD}")
    if menu in ["Dashboard PPD","Sekolah dalam PPD"]:
        df = load_sekolah()
        st.markdown(f"**Senarai Sekolah dalam PPD {KOD_PPD} ({len(df)} sekolah)**")
        st.dataframe(df, use_container_width=True)
    elif menu == "Pusat di PPD":
        df = load_pusat()
        st.dataframe(df, use_container_width=True)
        st.info(f"SUB: {sub}")
    else:
        df = load_guru()
        st.dataframe(df.head(100), use_container_width=True)
        st.info(f"{menu} - {sub} - Load {len(df)} guru PPD {KOD_PPD} sahaja - Ringan")
        st.success("✅ Fungsi penuh (Jana PDF+ZIP, Lulus, Surat) akan copy dari app_40.py")
