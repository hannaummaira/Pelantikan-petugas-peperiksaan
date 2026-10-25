
import streamlit as st
import os
st.set_page_config(page_title="JPN Sekolah", layout="wide")
st.title("JPN - Negeri")
logo = None
for p in ["assets/jata_negara_hd.png","assets/jata_negara.png","../assets/jata_negara_hd.png"]:
    if os.path.exists(p):
        logo = p
        break
if logo:
    st.sidebar.image(logo, width=100)
st.info("Modul JPN - Pilih sekolah dan pusat")
