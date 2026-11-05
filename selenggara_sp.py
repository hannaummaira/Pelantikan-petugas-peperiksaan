# -*- coding: utf-8 -*-
"""selenggara_sp.py - JPN: tambah / edit Sekolah dan Pusat Peperiksaan ikut daerah (PPD).
Menulis terus ke sekolah_master / pusat_master
Versi FIX - buang column 'data' yang tak wujud dalam Supabase
"""
import json
import pandas as pd
import streamlit as st
import spm_core as core
from kuota_pusat import simpan_pusat, kelas_auto, kuota_pusat, no_pusat as _no_pusat, kod_tuan_rumah

FLY_SP = [("sekolah", "🏫 Selenggara Sekolah"), ("pusat", "🏢 Selenggara Pusat")]

def _db():
    return core._RAW

def _s(v):
    x = "" if v is None else str(v).strip()
    return "" if x.lower() in ("nan", "none", "null", "nat") else x

def _data(row):
    # Compat - kalau ada data, pakai. Kalau takde, return {}
    d = row.get("data")
    if isinstance(d, dict):
        return dict(d)
    if isinstance(d, str) and d.strip().startswith("{"):
        try:
            return json.loads(d)
        except Exception:
            return {}
    return {}

def _bungkus(row, d):
    return json.dumps(d, ensure_ascii=False) if isinstance(row.get("data"), str) else d

def _semua(table, kod_ppd):
    out, mula = [], 0
    while True:
        q = _db().table(table).select("*")
        if table == "sekolah_master":
            q = q.eq("kod_ppd", kod_ppd)
        res = q.range(mula, mula + 999).execute().data or []
        out += res
        if len(res) < 1000:
            break
        mula += 1000
    return out

def _pusat_daerah(kod_ppd):
    out, mula = [], 0
    while True:
        res = _db().table("pusat_master").select("*").range(mula, mula + 999).execute().data or []
        out += res
        if len(res) < 1000:
            break
        mula += 1000
    return [r for r in out if (_s(r.get("kod_ppd")).upper() == kod_ppd) or _no_pusat(r).startswith(kod_ppd)]

def _ada(table, lajur, nilai):
    for c in lajur:
        try:
            if _db().table(table).select("*").eq(c, nilai).limit(1).execute().data:
                return True
        except Exception:
            pass
    return False

def _segar():
    try:
        st.cache_data.clear()
    except Exception:
        pass

def _pilih_daerah(kunci):
    ppd = core.PPD_MAP
    kods = sorted(ppd.keys())
    pilih = st.selectbox("Pilih Daerah (PPD)", kods, format_func=lambda k: f"{k} - {ppd.get(k, k)}", key=f"sp_ppd_{kunci}")
    return pilih

# ------------------------------------------------------------------------- sekolah
def _panel_sekolah(kod_ppd):
    rows = _semua("sekolah_master", kod_ppd)
    st.caption(f"{len(rows)} sekolah dalam daerah {kod_ppd} - {core.PPD_MAP.get(kod_ppd, '')}")
    t1, t2 = st.tabs(["✏️ Edit Nama Sekolah", "➕ Tambah Sekolah"])

    with t1:
        if not rows:
            st.info("Tiada sekolah dalam daerah ini.")
        else:
            df = pd.DataFrame([{"KOD SEKOLAH": _s(r.get("kod_sekolah")).upper(), "NAMA SEKOLAH": _s(r.get("nama_sekolah")),
                                "POSKOD": _s(r.get("poskod")) or _s(_data(r).get("POSKOD"))} for r in rows]).sort_values("KOD SEKOLAH")
            st.dataframe(df, use_container_width=True, hide_index=True, height=260)
            peta = {_s(r.get("kod_sekolah")).upper(): r for r in rows}
            kod = st.selectbox("Pilih sekolah untuk diedit", list(df["KOD SEKOLAH"]),
                               format_func=lambda k: f"{k} - {_s(peta[k].get('nama_sekolah'))}", key=f"sp_es_{kod_ppd}")
            r = peta[kod]
            d = _data(r)
            with st.form(f"form_es_{kod_ppd}_{kod}"):
                nama = st.text_input("Nama Sekolah", value=_s(r.get("nama_sekolah")))
                pk = st.text_input("Poskod (pilihan)", value=_s(r.get("poskod")) or _s(d.get("POSKOD")), max_chars=5)
                if st.form_submit_button("💾 Simpan Perubahan Sekolah", type="primary"):
                    nama = nama.strip().upper()
                    if not nama:
                        st.error("Nama sekolah tidak boleh kosong.")
                    else:
                        # FIX: Tak guna column data lagi
                        payload = {"nama_sekolah": nama}
                        # cuba update poskod kalau column tu wujud
                        if pk.strip():
                            payload["poskod"] = pk.strip()
                        try:
                            _db().table("sekolah_master").update(payload).eq("kod_sekolah", _s(r.get("kod_sekolah"))).execute()
                            _segar()
                            st.success(f"✅ {kod} dikemas kini: {nama}")
                        except Exception as e:
                            # kalau error sebab poskod tak wujud, cuba tanpa poskod
                            if "poskod" in str(e).lower():
                                try:
                                    _db().table("sekolah_master").update({"nama_sekolah": nama}).eq("kod_sekolah", _s(r.get("kod_sekolah"))).execute()
                                    _segar()
                                    st.success(f"✅ {kod} dikemas kini: {nama} (tanpa poskod)")
                                except Exception as e2:
                                    st.error(f"Gagal simpan: {str(e2)[:300]}")
                            else:
                                st.error(f"Gagal simpan: {str(e)[:300]}")

    with t2:
        with st.form(f"form_ts_{kod_ppd}", clear_on_submit=True):
            c1, c2 = st.columns(2)
            kod = c1.text_input("Kod Sekolah *", placeholder="cth: BBA1234")
            nama = c2.text_input("Nama Sekolah *")
            pk = c1.text_input("Poskod (pilihan)", max_chars=5)
            st.caption(f"Sekolah akan didaftarkan di bawah PPD {kod_ppd} - {core.PPD_MAP.get(kod_ppd, '')}.")
            if st.form_submit_button("➕ Tambah Sekolah", type="primary"):
                kod, nama = kod.strip().upper(), nama.strip().upper()
                if not kod or not nama:
                    st.error("Kod sekolah dan nama sekolah wajib diisi.")
                elif _ada("sekolah_master", ["kod_sekolah"], kod):
                    st.error(f"Kod sekolah {kod} sudah wujud.")
                else:
                    # FIX: Insert terus ikut column sebenar, TANPA column data
                    # sekolah_master ADA kod_ppd - ikut screenshot kau
                    payload = {
                        "kod_sekolah": kod,
                        "nama_sekolah": nama,
                        "kod_ppd": kod_ppd,
                        "ppd": core.PPD_MAP.get(kod_ppd, "Klang")
                    }
                    # Tambah field tambahan yang mungkin ada dalam table kau
                    # dari gambar kau ada: password, bil_pusat, senarai_pusat
                    payload_extra = {}
                    try:
                        # Check column wujud dengan cuba insert simple dulu
                        # Kita cuba include field standard dari screenshot kau
                        if pk.strip():
                            # poskod - kalau tak wujud, nanti fallback
                            payload["poskod"] = pk.strip()
                        
                        _db().table("sekolah_master").insert(payload).execute()
                        _segar()
                        st.success(f"✅ Sekolah {kod} - {nama} ditambah ke PPD {kod_ppd}.")
                    except Exception as e:
                        err = str(e).lower()
                        # Kalau gagal sebab poskod tak wujud, retry tanpa poskod
                        if "poskod" in err or "pgrst204" in err:
                            try:
                                payload.pop("poskod", None)
                                payload.pop("kod_ppd_text", None)
                                _db().table("sekolah_master").insert(payload).execute()
                                _segar()
                                st.success(f"✅ Sekolah {kod} - {nama} ditambah ke PPD {kod_ppd}.")
                            except Exception as e2:
                                st.error(f"Gagal tambah: {str(e2)[:500]}")
                        else:
                            st.error(f"Gagal tambah: {str(e)[:500]}")


# ------------------------------------------------------------------------- pusat
def _panel_pusat(kod_ppd):
    rows = _pusat_daerah(kod_ppd)
    st.caption(f"{len(rows)} pusat peperiksaan dalam daerah {kod_ppd} - {core.PPD_MAP.get(kod_ppd, '')}")
    sek = {_s(r.get("kod_sekolah")).upper(): _s(r.get("nama_sekolah")) for r in _semua("sekolah_master", kod_ppd)}
    t1, t2 = st.tabs(["✏️ Edit Pusat", "➕ Tambah Pusat"])

    with t1:
        if not rows:
            st.info("Tiada pusat dalam daerah ini.")
        else:
            lst = []
            for r in rows:
                q = kuota_pusat(r)
                d = _data(r)
                tuan = sorted(kod_tuan_rumah(r))
                lst.append({"NO PUSAT": _no_pusat(r), "NAMA PUSAT": _s(r.get("nama_pusat")) or _s(d.get("NAMA_PUSAT")),
                            "KOD SEKOLAH": tuan[0] if tuan else "", "BIL CALON": q["calon"], "KELAS": q["kelas"],
                            "POSKOD": _s(d.get("POSKOD_PUSAT")) or _s(d.get("POSKOD")) or _s(r.get("poskod"))})
            df = pd.DataFrame(lst).sort_values("NO PUSAT")
            st.dataframe(df, use_container_width=True, hide_index=True, height=260)
            peta = {_no_pusat(r): r for r in rows}
            no = st.selectbox("Pilih pusat untuk diedit", list(df["NO PUSAT"]),
                              format_func=lambda k: f"{k} - {_s(peta[k].get('nama_pusat'))}", key=f"sp_ep_{kod_ppd}")
            r = peta[no]
            baris = df[df["NO PUSAT"] == no].iloc[0]
            with st.form(f"form_ep_{kod_ppd}_{no}"):
                nama = st.text_input("Nama Pusat", value=str(baris["NAMA PUSAT"]))
                c1, c2, c3 = st.columns(3)
                ks = c1.text_input("Kod Sekolah (tuan rumah)", value=str(baris["KOD SEKOLAH"]))
                calon = c2.number_input("Bil Calon", min_value=0, max_value=3000, value=int(baris["BIL CALON"]), step=1)
                kelas = c3.number_input("Kelas (kosongkan = auto calon/20)", min_value=0, max_value=200, value=int(baris["KELAS"]), step=1)
                pk = st.text_input("Poskod Pusat", value=str(baris["POSKOD"]), max_chars=5)
                if st.form_submit_button("💾 Simpan Perubahan Pusat", type="primary"):
                    nama, ks = nama.strip().upper(), ks.strip().upper()
                    if not nama:
                        st.error("Nama pusat tidak boleh kosong.")
                    else:
                        try:
                            col = "no_pusat" if r.get("no_pusat") else "kod_pusat"
                            payload = {"nama_pusat": nama}
                            # tambah column lain kalau ada
                            if ks:
                                payload["kod_sekolah_tuan_rumah"] = ks
                                # cuba update semua kemungkinan nama column alamat
                                payload["alamat_pusat"] = ks
                                if "alamat" in r:
                                    payload["alamat"] = ks
                            if pk.strip() and "poskod" in r:
                                payload["poskod"] = pk.strip()
                            
                            _db().table("pusat_master").update(payload).eq(col, no).execute()
                            simpan_pusat(_db(), no, int(calon), int(kelas))
                            _segar()
                            st.success(f"✅ Pusat {no} dikemas kini. Petugas perlu: {int(kelas) + 9}.")
                        except Exception as e:
                            st.error(f"Gagal simpan: {str(e)[:500]}")

    with t2:
        with st.form(f"form_tp_{kod_ppd}", clear_on_submit=True):
            c1, c2 = st.columns(2)
            no = c1.text_input("No Pusat Peperiksaan *", placeholder=f"cth: {kod_ppd}101")
            nama = c2.text_input("Nama Pusat *")
            ks = c1.text_input("Kod Sekolah (tuan rumah) *")
            calon = c2.number_input("Bil Calon *", min_value=0, max_value=3000, value=0, step=1)
            pk = c1.text_input("Poskod Pusat", max_chars=5)
            st.caption(f"Kelas = CEIL(calon/20); petugas = kelas + 9. Pusat didaftarkan di bawah PPD {kod_ppd}.")
            if st.form_submit_button("➕ Tambah Pusat", type="primary"):
                no, nama, ks = no.strip().upper(), nama.strip().upper(), ks.strip().upper()
                if not no or not nama or not ks:
                    st.error("No pusat, nama pusat dan kod sekolah wajib diisi.")
                elif not no.startswith(kod_ppd):
                    st.error(f"No pusat mesti bermula dengan kod PPD ({kod_ppd}) supaya dipaparkan di PPD ini.")
                elif _ada("pusat_master", ["kod_pusat", "no_pusat"], no):
                    st.error(f"No pusat {no} sudah wujud.")
                else:
                    kelas = kelas_auto(calon)
                    # FIX FINAL: pusat_master TIADA kod_ppd/ppd - guna column sebenar je dari screenshot
                    payload = {
                        "no_pusat": no,
                        "kod_pusat": no,
                        "nama_pusat": nama,
                        "kod_sekolah_tuan_rumah": ks,
                        "nama_sekolah_tuan_rumah": sek.get(ks, nama),
                        "jumlah_calon": int(calon),
                        "jumlah_kelas": kelas,
                        "calon": int(calon),
                        "bilik": kelas,
                        "alamat_pusat": ks
                    }
                    try:
                        _db().table("pusat_master").insert(payload).execute()
                        simpan_pusat(_db(), no, int(calon), kelas)
                        _segar()
                        msg = f"✅ Pusat {no} - {nama} ditambah ({int(calon)} calon, {kelas} kelas, petugas perlu {kelas + 9})."
                        if ks not in sek:
                            msg += f" Nota: kod sekolah {ks} belum ada dalam senarai sekolah PPD {kod_ppd}."
                        st.success(msg)
                    except Exception as e:
                        # Fallback - cuba dengan column minimal kalau table lain structure
                        try:
                            fallback = {
                                "kod_pusat": no,
                                "no_pusat": no,
                                "nama_pusat": nama,
                                "kod_sekolah_tuan_rumah": ks
                            }
                            _db().table("pusat_master").insert(fallback).execute()
                            simpan_pusat(_db(), no, int(calon), kelas)
                            _segar()
                            st.success(f"✅ Pusat {no} - {nama} ditambah (fallback).")
                        except Exception as e2:
                            st.error(f"Gagal tambah: {str(e2)[:500]}")


def render_selenggara_sp(fly_cur):
    fly_cur = fly_cur or "sekolah"
    st.header("🛠️ Selenggara Sekolah & Pusat Peperiksaan")
    st.caption("Perubahan di sini terus masuk ke data PPD dan SUP serta dipaparkan di halaman hadapan PPD.")
    kod_ppd = _pilih_daerah(fly_cur)
    if fly_cur == "pusat":
        _panel_pusat(kod_ppd)
    else:
        _panel_sekolah(kod_ppd)
