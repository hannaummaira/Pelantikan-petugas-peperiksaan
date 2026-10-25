
import streamlit as st
import pandas as pd
import datetime
import zipfile, io
from common.supabase_client import get_supa
from common.config import tahun_aktif, PPD_MAP
from common.surat import generate_surat_pdf

def create_zip_pukal(surat_list, kod_ppd):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for s in surat_list:
            pdf = generate_surat_pdf(
                s["nama"], s["ic"], s["jawatan"], s["sekolah_asal"], s.get("nama_sekolah_asal",""),
                s["pusat"], s.get("nama_pusat",""), s["no_surat"], kod_ppd, PPD_MAP.get(kod_ppd,""), 
                str(datetime.date.today()), tahun_aktif()
            )
            fname = f"{s['ic']}_{s['nama'][:20]}.pdf".replace(" ", "_")
            zf.writestr(fname, pdf)
    buffer.seek(0)
    return buffer.getvalue()

def render_ppd():
    supa = get_supa()
    st.subheader(f"Modul PPD - Tahun {tahun_aktif()}")
    kod_ppd = st.selectbox("Pilih PPD", list(PPD_MAP.keys()), format_func=lambda x: f"{x} - {PPD_MAP[x]}")
    
    tab1, tab2 = st.tabs(["📄 Jana Surat (Template JPN + Jata & Tandatangan)", "📊 Ikut Pusat"])
    
    with tab1:
        if st.button(f"Jana Surat PPD {kod_ppd} - Tahun {tahun_aktif()}", type="primary"):
            try:
                res = supa.table("cadangan_sup").select("*").eq("kod_ppd", kod_ppd.lower()).limit(1000).execute()
                data = res.data or []
                if not data:
                    st.warning("Tiada cadangan untuk PPD ini pada tahun ini.")
                    return
                surat_list = []
                for r in data:
                    surat_list.append({
                        "nama": r.get("nama_guru",""), "ic": r.get("ic_guru",""),
                        "jawatan": r.get("jawatan_cadangan",""), "sekolah_asal": r.get("kod_sekolah",""),
                        "nama_sekolah_asal": "", "pusat": r.get("kod_pusat",""), "nama_pusat": "",
                        "no_surat": r.get("no_surat", f"JPN.SPM.{tahun_aktif()}/{kod_ppd}/001")
                    })
                # Kolektif PDF pertama
                if surat_list:
                    pdf_one = generate_surat_pdf(
                        surat_list[0]["nama"], surat_list[0]["ic"], surat_list[0]["jawatan"],
                        surat_list[0]["sekolah_asal"], "", surat_list[0]["pusat"], "",
                        surat_list[0]["no_surat"], kod_ppd, PPD_MAP.get(kod_ppd,""), str(datetime.date.today()), tahun_aktif()
                    )
                    st.download_button("📥 Download Contoh PDF (dengan Jata & Tandatangan)", pdf_one, file_name=f"Contoh_Surat_{kod_ppd}_{tahun_aktif()}.pdf", mime="application/pdf")
                    zip_bytes = create_zip_pukal(surat_list, kod_ppd)
                    st.download_button(f"📦 ZIP Pukal {len(surat_list)} Surat", zip_bytes, file_name=f"ZIP_{kod_ppd}_{tahun_aktif()}.zip", mime="application/zip", type="primary")
                    st.success(f"✅ {len(surat_list)} surat dijana dengan Jata Negara & Tandatangan Pengarah")
            except Exception as e:
                st.error(f"Ralat: {e}")
