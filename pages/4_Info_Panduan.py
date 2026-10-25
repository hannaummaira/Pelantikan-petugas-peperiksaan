
import streamlit as st, os
st.set_page_config(page_title="Info", layout="wide")
st.title("ℹ️ Info Panduan - SPM 2026")
p="assets/jata_negara_hd.png"
if os.path.exists(p): st.image(p, width=100)
st.markdown('''
- **1 GitHub Repo**: semua kod
- **1 Supabase**: data sekolah/pusat/guru
- **1 Streamlit App**: app.py + pages/ + assets/
- **Logo** mesti dalam `assets/jata_negara_hd.png`
- **Tandatangan** dalam `assets/tandatangan_pengarah_hd.png`
- Jika ZIP kosong: cek requirements.txt ada xhtml2pdf, reportlab, pypdf
- Jika SyntaxError: jangan edit file 622KB di web GitHub, guna file kecil ini
''')
st.success("Muka depan 4 kad dah restore!")
