
import streamlit as st
import pandas as pd
from common.supabase_client import get_supa, get_supabase_raw, status_migrasi_tahun, SQL_MIGRASI_TAHUN, lajur_tahun_sedia
from common.config import tahun_aktif, TAHUN_PILIHAN, PPD_MAP

def render_jpn():
    supa = get_supa()
    st.subheader(f"Modul JPN Negeri - Tahun {tahun_aktif()}")
    
    tab_status, tab_tahun, tab_template = st.tabs(["⚙️ Status DB", "📅 Urus Tahun", "📝 Template Surat JPN"])
    
    with tab_status:
        st.write("Status Migrasi Lajur Tahun:")
        stat = status_migrasi_tahun()
        cols = st.columns(len(stat))
        for i, (t, ok) in enumerate(stat.items()):
            with cols[i]:
                st.metric(t, "OK" if ok else "BELUM", delta="✅" if ok else "❌")
        if not all(stat.values()):
            st.warning("Jalankan SQL migrasi di bawah di Supabase SQL Editor")
            st.code(SQL_MIGRASI_TAHUN, language="sql")
    
    with tab_tahun:
        st.markdown(f"### Salin Data Tahun (Guru & Pusat)")
        st.caption("Cadangan SUP tidak disalin - setiap tahun mesti kosong dan SUP buat baru. Nombor surat reset setiap tahun.")
        c1, c2 = st.columns(2)
        asal = c1.selectbox("Dari Tahun", TAHUN_PILIHAN, index=0, key="asal")
        tuju = c2.selectbox("Ke Tahun", TAHUN_PILIHAN, index=1, key="tuju")
        jadual = st.multiselect("Jadual", ["guru_master","pusat_master","bilik_kebal_master"], default=["guru_master","pusat_master"])
        timpa = st.checkbox("Ganti data tahun tuju jika sudah ada")
        if st.button(f"📥 Salin {asal} → {tuju}", type="primary"):
            raw = get_supabase_raw()
            for j in jadual:
                if not lajur_tahun_sedia(j):
                    st.error(f"{j}: belum ada lajur tahun")
                    continue
                try:
                    r = raw.table(j).select("*").eq("tahun", asal).limit(2000).execute()
                    data = r.data or []
                    if timpa:
                        raw.table(j).delete().eq("tahun", tuju).execute()
                    to_insert = []
                    for x in data:
                        x = dict(x)
                        x.pop("id", None); x.pop("created_at", None)
                        if j=="pusat_master" and "LOG-SURAT" in str(x.get("no_pusat","")).upper():
                            continue
                        x["tahun"] = tuju
                        to_insert.append(x)
                    for i in range(0, len(to_insert), 500):
                        raw.table(j).insert(to_insert[i:i+500]).execute()
                    st.success(f"{j}: {len(to_insert)} rekod disalin {asal}→{tuju}")
                except Exception as e:
                    st.error(f"{j}: {e}")
    
    with tab_template:
        st.info("Template JPN Selaras - akan guna Jata & Tandatangan yang kau upload. Simpan dalam table surat_templates_jpn")
        try:
            res = supa.table("surat_templates_jpn").select("*").limit(20).execute()
            df = pd.DataFrame(res.data or [])
            st.dataframe(df, use_container_width=True)
        except:
            st.warning("Table surat_templates_jpn belum wujud")
