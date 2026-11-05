# -*- coding: utf-8 -*-
"""lengkap_petugas.py - lengkapkan NAMA SEKOLAH ASAL dan NO TELEFON petugas untuk Hasil Janaan & Semakan Lantikan.

Rekod cadangan / janaan kadangkala tidak membawa nama sekolah (hanya kod) atau no telefon (disimpan dalam JSON `data`
atau hanya ada dalam guru_master). Fungsi di sini mengisi yang kosong daripada sekolah_master dan guru_master.
"""
import json
import re
import streamlit as st

_KOSONG = ("", "nan", "none", "null", "nat", "-", "n/a")


def _s(v):
    x = "" if v is None else str(v).strip()
    return "" if x.lower() in _KOSONG else x


def _ic(v):
    return re.sub(r"\D", "", str(v or ""))


def _data(r):
    d = r.get("data") if hasattr(r, "get") else None
    if isinstance(d, dict):
        return d
    if isinstance(d, str) and d.strip().startswith("{"):
        try:
            return json.loads(d)
        except Exception:
            return {}
    return {}


def _cari(r, d, *keys):
    for k in keys:
        for src in (r, d):
            try:
                v = _s(src.get(k))
            except Exception:
                v = ""
            if v:
                return v
    return ""


@st.cache_data(ttl=300, show_spinner=False)
def _peta(kod_ppd):
    """(peta_sekolah {kod: nama}, peta_telefon {ic: telefon}) untuk daerah ini."""
    import spm_core as core
    sek, tel = {}, {}
    try:
        for r in core.supa.table("sekolah_master").select("kod_sekolah,nama_sekolah").limit(5000).execute().data or []:
            k = _s(r.get("kod_sekolah")).upper()
            if k:
                sek[k] = _s(r.get("nama_sekolah")).upper()
    except Exception:
        pass
    try:
        for r in core.supa.table("guru_master").select("*").limit(50000).execute().data or []:
            d = _data(r)
            ic = _ic(_cari(r, d, "ic_guru", "IC_GURU", "IC", "ic", "NO_KP"))
            t = _cari(r, d, "telefon_guru", "TELEFON_GURU", "TELEFON", "telefon", "no_telefon", "NO TELEFON GURU")
            if ic and t and ic not in tel:
                tel[ic] = t
    except Exception:
        pass
    return sek, tel


def lengkapkan(row, kod_ppd):
    """Pulang salinan `row` (Series/dict) dengan NAMA_SEKOLAH_ASAL & TELEFON_GURU diisi jika kosong."""
    import pandas as pd
    out = dict(row)
    sek, tel = _peta(str(kod_ppd))
    d = _data(out)
    kod = _cari(out, d, "KOD_SEKOLAH_ASAL", "kod_sekolah_asal", "kod_sekolah", "KOD_SEKOLAH").upper()
    nama = _cari(out, d, "NAMA_SEKOLAH_ASAL", "nama_sekolah_asal", "NAMA_SEKOLAH", "nama_sekolah")
    if kod and (not nama or nama.upper() == kod):
        nama = sek.get(kod, nama) or nama
    if nama:
        out["NAMA_SEKOLAH_ASAL"] = nama
        out["nama_sekolah_asal"] = nama
    if kod and not _s(out.get("KOD_SEKOLAH_ASAL")):
        out["KOD_SEKOLAH_ASAL"] = kod
        out["kod_sekolah_asal"] = kod
    telefon = _cari(out, d, "TELEFON_GURU", "telefon_guru", "TELEFON", "telefon", "no_telefon", "NO TELEFON GURU")
    if not telefon:
        telefon = tel.get(_ic(_cari(out, d, "IC_GURU", "ic_guru", "IC", "ic")), "")
    if telefon:
        out["TELEFON_GURU"] = telefon
        out["telefon_guru"] = telefon
    return pd.Series(out) if isinstance(row, pd.Series) else out


def lengkapkan_df(df, kod_ppd):
    """Sama seperti lengkapkan() tetapi untuk DataFrame."""
    import pandas as pd
    if df is None or len(df) == 0:
        return df
    return pd.DataFrame([lengkapkan(r, kod_ppd) for _, r in df.iterrows()])
