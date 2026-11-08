# -*- coding: utf-8 -*-
"""sandaran.py - Sandaran Data (JPN): muat turun semua jadual sistem sebagai fail ZIP (CSV).
Baca sahaja. Berguna untuk simpanan di komputer sendiri dan sebelum pindah pangkalan data."""
import datetime
import io
import json
import zipfile

import pandas as pd
import streamlit as st

import spm_core as core
import ui_theme as ui

JADUAL = ["sekolah_master", "pusat_master", "guru_master", "cadangan_sup", "surat_templates_jpn", "landing_config", "zon_bilik_kebal",
          "penyelia_kawasan", "tahun_sistem", "tetapan_ppd", "log_aktiviti"]


def _baca_jadual(nama):
    """Pulang (DataFrame | None, mesej). None bila jadual tiada / tidak boleh dibaca."""
    out, a = [], 0
    try:
        while True:
            rows = core.supa.table(nama).select("*").range(a, a + 999).execute().data or []
            out += rows
            if len(rows) < 1000 or a > 200000:
                break
            a += 1000
    except Exception as e:
        try:
            out = core.supa.table(nama).select("*").limit(10000).execute().data or []
        except Exception:
            return None, str(e)[:80]
    return pd.DataFrame(out), ""


def _rata(df):
    d = df.copy()
    for c in d.columns:
        d[c] = d[c].apply(lambda v: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
    return d


def render_sandaran():
    st.header("💾 Sandaran Data")
    st.caption("Muat turun salinan semua jadual sistem (CSV dalam satu fail ZIP). Simpan di komputer / pemacu luaran. Ini bacaan sahaja dan tidak mengubah data.")
    pilih = st.multiselect("Jadual yang disandarkan", JADUAL, default=JADUAL[:6], key="sd_jadual")
    tambah = st.text_input("Jadual lain (asingkan dengan koma)", key="sd_lain", help="Contoh: jadual tambahan yang anda cipta sendiri.")
    senarai = list(pilih) + [x.strip() for x in tambah.split(",") if x.strip()]
    if st.button("💾 Sediakan sandaran", type="primary", disabled=not senarai, key="sd_btn"):
        buf = io.BytesIO()
        ringkas = []
        pb = st.progress(0)
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for i, t in enumerate(senarai):
                df, mesej = _baca_jadual(t)
                if df is None:
                    ringkas.append({"JADUAL": t, "BARIS": "-", "STATUS": f"tidak dibaca ({mesej})"})
                else:
                    z.writestr(f"{t}.csv", _rata(df).to_csv(index=False).encode("utf-8-sig"))
                    ringkas.append({"JADUAL": t, "BARIS": len(df), "STATUS": "✅ disandarkan"})
                pb.progress((i + 1) / len(senarai))
            z.writestr("RINGKASAN.txt", "Sandaran sistem pelantikan petugas\nTarikh: %s\n\n%s\n" % (
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "\n".join(f"{r['JADUAL']}: {r['BARIS']} baris - {r['STATUS']}" for r in ringkas)))
        st.session_state["sd_zip"] = (buf.getvalue(), ringkas)
    h = st.session_state.get("sd_zip")
    if h:
        data, ringkas = h
        st.dataframe(pd.DataFrame(ringkas), use_container_width=True, hide_index=True)
        st.download_button("📥 Muat turun ZIP sandaran", data, file_name=f"sandaran_spm_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.zip", mime="application/zip", key="sd_dl")
        st.success("Simpan fail ini di tempat selamat. Lajur JSON (contoh `data`) disimpan sebagai teks dalam CSV.")
