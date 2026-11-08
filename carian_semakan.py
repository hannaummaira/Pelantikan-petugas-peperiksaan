# -*- coding: utf-8 -*-
"""carian_semakan.py - Carian Petugas dan Semakan Data (baca sahaja)."""
import datetime
import re

import pandas as pd
import streamlit as st

import spm_core as core
import ppd_aliran as al
from kemajuan import muat_rekod, _spm, ui


def _ic_bersih(x):
    return re.sub(r"\D", "", str(x or ""))


def _peringkat(r):
    if r["rank"] < 0:
        return "Belum ditempatkan"
    return al.LABEL[r["rank"]] if 0 <= r["rank"] < len(al.LABEL) else ""


_AM = {-1: "", 1: "Disemak", 2: "Dilantik", 4: "Surat dijana", 5: "Dihantar"}


def _jadual(rows):
    out = []
    for r in rows:
        out.append({"PPD": r["ppd"], "NAMA": r["nama"], "IC": r["ic"], "NO TELEFON": r["tel"], "JAWATAN": r["jaw"], "SEKOLAH ASAL": r["nama_sek"] or r["sek"],
                    "PUSAT/BK": r["pusat"], "PERINGKAT SPM": _peringkat(r), "NO SURAT SPM": r["no"],
                    "AMALI SAINS": (f"{r['am_jaw']} · {_AM.get(r['am_stage'], '')} · {r['am_no']}" if r["am_stage"] >= 0 and r["am_jaw"] else ""),
                    "UJIAN MENDENGAR": (f"{r['um_jaw']} · {_AM.get(r['um_stage'], '')} · {r['um_no']}" if r["um_stage"] >= 0 and r["um_jaw"] else "")})
    return pd.DataFrame(out)


def render_carian(kod_ppd=None):
    st.header("🔎 Carian Petugas" + (f" - PPD {kod_ppd}" if kod_ppd else " - Seluruh Negeri"))
    st.caption("Cari ikut nama, no kad pengenalan, no telefon, kod / nama sekolah asal atau no pusat. Paparan menunjukkan status SPM, Amali Sains dan Ujian Mendengar dalam satu baris.")
    q = st.text_input("🔍 Kata carian (sekurang-kurangnya 3 aksara)", key=f"cs_q_{kod_ppd or 'jpn'}").strip()
    rows = muat_rekod(kod_ppd)
    c1, c2 = st.columns(2)
    jaw_semua = sorted({r["jaw"] for r in rows if r["jaw"]})
    jf = c1.multiselect("Tapis jawatan", jaw_semua, key=f"cs_j_{kod_ppd or 'jpn'}")
    sf = c2.selectbox("Tapis peringkat SPM", ["Semua", "Belum ditempatkan", "Ditempatkan (belum surat)", "Surat dijana", "Dihantar ke sekolah"], key=f"cs_s_{kod_ppd or 'jpn'}")
    if len(q) < 3 and not jf and sf == "Semua":
        st.info(f"Taip nama / IC / sekolah untuk mencari, atau pilih tapisan. ({len(rows)} rekod dalam skop anda)")
        return
    ql = q.lower()
    qd = _ic_bersih(q)
    hasil = []
    for r in rows:
        if jf and r["jaw"] not in jf:
            continue
        if sf == "Belum ditempatkan" and r["rank"] >= 0:
            continue
        if sf == "Ditempatkan (belum surat)" and not (0 <= r["rank"] < 4):
            continue
        if sf == "Surat dijana" and r["rank"] != 4:
            continue
        if sf == "Dihantar ke sekolah" and r["rank"] != 5:
            continue
        if len(q) >= 3:
            hay = " ".join([r["nama"], r["sek"], r["nama_sek"], r["pusat"], r["jaw"], r["no"]]).lower()
            if not (ql in hay or (len(qd) >= 4 and (qd in _ic_bersih(r["ic"]) or qd in _ic_bersih(r["tel"])))):
                continue
        hasil.append(r)
    st.markdown(f'<span class="kmj-pill">{len(hasil)} padanan</span>', unsafe_allow_html=True)
    if not hasil:
        st.warning("Tiada rekod sepadan.")
        return
    df = _jadual(hasil[:2000])
    st.dataframe(df, use_container_width=True, hide_index=True, height=min(560, 60 + 35 * len(df)))
    if len(hasil) > 2000:
        st.caption("Hanya 2000 baris pertama dipaparkan. Muat turun untuk senarai penuh.")
    st.download_button("📊 Muat turun hasil carian (Excel)", core.to_excel(_jadual(hasil)), file_name=f"carian_petugas_{datetime.date.today()}.xlsx", key=f"cs_dl_{kod_ppd or 'jpn'}")


def _semak(rows):
    """Senarai semakan: [(tajuk, tahap, penerangan, DataFrame)]."""
    s = _spm(rows)
    aktif = [r for r in s if r["rank"] >= 0 and r["pusat"]]
    keluar = []
    # 1. IC sama di lebih daripada satu pusat berbeza
    by_ic = {}
    for r in aktif:
        ic = _ic_bersih(r["ic"])
        if len(ic) >= 6 and "PENYELIA" not in r["jaw"].upper():
            by_ic.setdefault(ic, []).append(r)
    dup = [r for lst in by_ic.values() if len({x["pusat"] for x in lst}) > 1 for r in lst]
    keluar.append(("IC sama ditempatkan di lebih daripada satu pusat", "bad", "Seorang petugas tidak boleh bertugas di dua pusat berbeza.", _jadual(dup)))
    # 2. Tiada telefon
    tel = [r for r in aktif if len(_ic_bersih(r["tel"])) < 9]
    keluar.append(("Petugas ditempatkan tanpa no telefon sah", "warn", "No telefon diperlukan untuk dihubungi dan di paparan Petugas Hadir.", _jadual(tel)))
    # 3. No surat berganda (SPM / Amali / UM)
    bg = []
    for tajuk, key in (("SPM", "no"), ("Amali", "am_no"), ("Ujian Mendengar", "um_no")):
        cnt = {}
        for r in rows:
            n = r[key]
            if n:
                cnt.setdefault(n, []).append(r)
        for n, lst in cnt.items():
            if len({_ic_bersih(x["ic"]) + "|" + (x["am_jaw"] if key == "am_no" else x["um_jaw"] if key == "um_no" else x["jaw"]) for x in lst}) > 1:
                bg += lst
    keluar.append(("No surat berganda", "bad", "No surat yang sama dipakai oleh lebih daripada seorang petugas dalam siri yang sama.", _jadual(bg)))
    # 4. Surat dijana belum dihantar
    tg = [r for r in s if r["rank"] == 4] + [r for r in rows if r["am_stage"] == 4 and r["am_no"]] + [r for r in rows if r["um_stage"] == 4 and r["um_no"]]
    seen, tg2 = set(), []
    for r in tg:
        if id(r) not in seen:
            seen.add(id(r)); tg2.append(r)
    keluar.append(("Surat sudah dijana tetapi belum dihantar ke sekolah", "warn", "Hantar di Sah Lantik (SPM), atau submenu Hantar di Amali / Ujian Mendengar.", _jadual(tg2)))
    # 5. Tiada pusat tetapi sudah bersurat / rank tinggi
    anom = [r for r in s if r["rank"] >= 1 and not r["pusat"] and "PENYELIA" not in r["jaw"].upper()]
    keluar.append(("Peringkat lanjut tetapi tiada pusat", "bad", "Rekod di peringkat Hasil atau lebih tetapi tiada kod pusat - sila semak penempatan.", _jadual(anom)))
    # 6. Tiada sekolah asal
    ts = [r for r in s if not r["sek"]]
    keluar.append(("Tiada kod sekolah asal", "warn", "Surat tidak dapat dihantar tanpa sekolah asal.", _jadual(ts)))
    return keluar


def render_semakan(kod_ppd=None):
    st.header("🧪 Semakan Data" + (f" - PPD {kod_ppd}" if kod_ppd else " - Seluruh Negeri"))
    st.caption("Semakan automatik untuk mengesan ralat sebelum surat dihantar. Baca sahaja - tiada data diubah.")
    rows = muat_rekod(kod_ppd)
    if not rows:
        st.info("Belum ada data.")
        return
    hasil = _semak(rows)
    jum = sum(len(x[3]) for x in hasil)
    ui.kmj_grid([(t[:34] + ("…" if len(t) > 34 else ""), len(df), "", "ok" if len(df) == 0 else tone) for t, tone, _, df in hasil])
    if jum == 0:
        st.success("✅ Tiada isu dikesan.")
    for tajuk, tone, ket, df in hasil:
        ikon = "✅" if len(df) == 0 else ("🔴" if tone == "bad" else "🟠")
        with st.expander(f"{ikon} {tajuk} - {len(df)}", expanded=len(df) > 0 and tone == "bad"):
            st.caption(ket)
            if len(df):
                st.dataframe(df, use_container_width=True, hide_index=True, height=min(380, 60 + 35 * len(df)))
    if jum:
        buf = []
        for tajuk, tone, ket, df in hasil:
            if len(df):
                d = df.copy()
                d.insert(0, "ISU", tajuk)
                buf.append(d)
        st.download_button("📊 Muat turun semua isu (Excel)", core.to_excel(pd.concat(buf, ignore_index=True)), file_name=f"semakan_data_{kod_ppd or 'negeri'}_{datetime.date.today()}.xlsx", key=f"sm_dl_{kod_ppd or 'jpn'}")
