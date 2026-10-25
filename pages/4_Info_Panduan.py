
import streamlit as st
import os
st.set_page_config(page_title="Info Panduan", layout="wide")
st.title("Info Panduan")
st.markdown("### Sistem 1 Projek - Logo di assets/jata_negara_hd.png")
for p in ["assets/jata_negara_hd.png"]:
    if os.path.exists(p):
        st.image(p, width=120)
st.success("Jika nampak page ini, SyntaxError dah fix!")
