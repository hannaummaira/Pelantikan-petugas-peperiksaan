
import streamlit as st, os
st.set_page_config(page_title="SUP Sekolah", layout="wide")
logo = "assets/jata_negara_hd.png" if os.path.exists("assets/jata_negara_hd.png") else None
if logo: st.sidebar.image(logo, width=90)
st.title("🏫 SUP - Sekolah")
st.info("Modul SUP akan diisi semula selepas landing 4 kad stabil. Buat masa ni landing dah betul.")
st.write("Upload fail asal fix4_surat.py ke root jika perlu fungsi penuh, tapi jangan copy 8800 baris terus ke pages/ - itu punca SyntaxError.")
