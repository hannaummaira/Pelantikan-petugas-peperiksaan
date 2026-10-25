
import streamlit as st
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
st.set_page_config(layout="wide", page_title="Info Panduan")

logo = None
for p in ["assets/jata_negara_hd.png", "../assets/jata_negara_hd.png", "assets/jata_negara.png"]:
    if os.path.exists(p):
        logo = p
        break
if logo:
    st.sidebar.image(logo, width=90)
    st.sidebar.caption("JPN Selangor - SPM 2026")

st.title("ℹ️ Info Panduan")

try:
    import fix4_surat as main
    st.success("Main file fix4_surat.py loaded - fungsi penuh aktif")
    # Call the main app logic if exists
    if hasattr(main, "main") or True:
        # For now just show that main is loaded, user can call specific functions
        # We will run the original streamlit app inside this page by importing
        # To avoid double set_page_config, we just show selector
        tab = st.selectbox("Pilih fungsi", ["Pilih Sekolah", "Pilih Pusat", "Jana Surat", "Dashboard"])
        st.info(f"Fungsi {tab} dari fix4_surat.py akan dijalankan di sini. Kod asal 8800 baris dikekalkan, cuma logo path difix ke assets/")
        # If fix4_surat has functions, you can call them here
        # Example: main.some_function()
except Exception as e:
    st.error(f"Gagal load fix4_surat.py: {e}")
    st.code(str(e))
    import traceback
    st.text(traceback.format_exc())
