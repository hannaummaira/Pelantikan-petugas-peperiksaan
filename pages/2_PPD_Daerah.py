
import streamlit as st, os
st.set_page_config(layout="wide", page_title="PPD Daerah")
logo = None
for p in ["assets/jata_negara_hd.png","../assets/jata_negara_hd.png","assets/jata_negara.png"]:
    if os.path.exists(p):
        logo = p
        break
if logo:
    st.sidebar.image(logo, width=90)

st.title("🏢 PPD Daerah")
st.success("Page ini OK - tidak import fix4_surat.py lagi, jadi tak Oh no")

st.markdown("""
### Langkah seterusnya
1. Landing 4 kad dah OK
2. Sekarang kita akan masukkan fungsi dari fix4_surat.py sikit-sikit
3. Jangan import terus 8840 baris - itu punca Oh no
""")

# Show if main file exists
if os.path.exists("fix4_surat.py") or os.path.exists("../fix4_surat.py") or os.path.exists("fix4_surat.py"):
    st.info("fix4_surat.py ada di repo - boleh dipanggil fungsi satu per satu nanti")
