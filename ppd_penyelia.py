# -*- coding: utf-8 -*-
"""
ppd_penyelia.py - Aliran LANTIK PENYELIA KAWASAN (PK) untuk PPD.

Menu PPD > Lantik Penyelia Kawasan (sub menu):
  1. Cadangan SUP      : senarai PK yang dihantar SUP. Tick = TERPILIH PPD, tidak tick = SIMPANAN PPD.
  2. Simpanan PK       : PK yang tidak dipilih. Boleh dipindah semula ke TERPILIH.
  3. Tempatkan PK      : klik bilik kebal -> pilih pusat di bawahnya -> pilih seorang PK + pusat yang diawasi
                         -> Simpan -> Hantar (masuk Kelulusan).
  4. Kelulusan & Surat : tetapkan no surat + tarikh, semak nama, jana surat (templat JPN), download,
                         Hantar ke sekolah asal PK untuk dicetak.

Aliran status (lajur `status` cadangan_sup, tiada perubahan skema):
  (SUP hantar) -> TERPILIH PPD | SIMPANAN PPD -> DITEMPATKAN BILIK KEBAL -> DITEMPATKAN BILIK KEBAL - HANTAR
  -> LULUS PPD - SURAT PK DIHANTAR KE SEKOLAH ASAL (ada no surat -> masuk menu Sah Lantik)

Batal Pelantikan PK: butang "Batal Pelantikan Penyelia Kawasan" (render_batal_pelantikan) di Kelulusan & Surat dan Sah Lantik
  -> membatalkan PK pada mana-mana peringkat (termasuk yang sudah ada surat) dan memulangkannya ke TERPILIH PPD / SIMPANAN PPD.

PK TIDAK lagi muncul di menu Cadangan SUP / Jana Keseluruhan / Kelulusan biasa (guna tanpa_pk()).
Nama PK untuk setiap pusat boleh dipakai dalam surat Ketua Pengawas melalui pk_placeholders():
  {{NAMA_PK}} {{TELEFON_PK}} {{SEKOLAH_PK}} {{BILIK_KEBAL_PK}}
"""
import datetime
import html as _html
import io
import json
import re
import time
import zipfile
import zlib

import pandas as pd
import streamlit as st

import spm_core as core
import ppd_cadangan as pc
import no_surat as _nsr
from spm_core import get_cadangan_df, supa, PPD_MAP
from tahun_sistem import tahun_semasa
from lengkap_petugas import lengkapkan

ST_TERPILIH = pc.ST_TERPILIH
ST_SIMPANAN = pc.ST_SIMPANAN
ST_TEMPAT = "DITEMPATKAN BILIK KEBAL"
ST_HANTAR = "DITEMPATKAN BILIK KEBAL - HANTAR"          # sengaja TIDAK mengandungi perkataan LULUS
ST_LULUS = "LULUS PPD - SURAT PK DIHANTAR KE SEKOLAH ASAL"
STAGE_TEMPAT = ("TEMPAT", "HANTAR", "LULUS")
_KOSONG = ("", "nan", "none", "null", "nat", "-")


# ====================================================================== pembantu asas
def _s(v):
    if v is None:
        return ""
    try:
        if isinstance(v, float) and pd.isna(v):
            return ""
    except Exception:
        pass
    t = str(v).strip()
    return "" if t.lower() in _KOSONG else t


def _g(r, *keys):
    """Nilai pertama yang tidak kosong daripada beberapa kunci (baris Series / dict)."""
    for k in keys:
        try:
            v = r.get(k)
        except Exception:
            v = None
        t = _s(v)
        if t:
            return t
    return ""


def _e(x):
    return _html.escape(str(x if x is not None else ""))


def _list(v):
    if v is None:
        return []
    if isinstance(v, (list, tuple, set)):
        return [str(x).strip().upper() for x in v if _s(x)]
    t = _s(v)
    if not t:
        return []
    if t.startswith("["):
        try:
            return _list(json.loads(t))
        except Exception:
            pass
    return [x.strip().upper() for x in re.split(r"[,;]", t) if x.strip()]


def jawatan_of(r):
    return _g(r, "JAWATAN_CADANGAN", "jawatan_cadangan", "JAWATAN", "jawatan").upper()


def is_pk(r):
    return "PENYELIA" in jawatan_of(r)


def tanpa_pk(df):
    """Buang baris Penyelia Kawasan (PK diurus di menu Lantik Penyelia Kawasan sahaja)."""
    if df is None or df.empty:
        return df
    return df[~df.apply(is_pk, axis=1)].copy()


def hanya_pk(df):
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df
    return df[df.apply(is_pk, axis=1)].copy()


def status_of(r):
    return _g(r, "STATUS", "status").upper()


def pk_stage(r):
    """BARU | TERPILIH | SIMPANAN | TEMPAT (disimpan) | HANTAR (dihantar ke kelulusan) | LULUS (ada no surat)."""
    s = status_of(r)
    if "SIMPANAN" in s:
        return "SIMPANAN"
    if s.startswith("LULUS") or "SURAT PK" in s or _g(r, "no_surat", "NO_SURAT"):
        return "LULUS"
    if "DITEMPATKAN" in s:
        return "HANTAR" if s.endswith("HANTAR") else "TEMPAT"
    if "TERPILIH" in s:
        return "TERPILIH"
    return "BARU"


def pk_info(r, bk_codes=None):
    """{'bk','pusat','bawah'} - hanya bermakna untuk PK yang sudah ditempatkan."""
    kosong = {"bk": "", "pusat": [], "bawah": []}
    if pk_stage(r) not in STAGE_TEMPAT:
        return kosong
    bk = _g(r, "kod_bilik_kebal_explicit", "kod_bilik_kebal", "KOD_BILIK_KEBAL").upper()
    pusat = _list(r.get("pusat_jagaan")) or _list(r.get("pusat_jagaan_str"))
    kp = _g(r, "kod_pusat", "KOD_PUSAT").upper()
    if kp:
        if bk_codes and kp in bk_codes:
            bk = bk or kp                      # data lama: kod_pusat memegang kod bilik kebal
        elif not pusat:
            pusat = _list(kp)
    return {"bk": bk, "pusat": pusat, "bawah": _list(r.get("pusat_bawah_bilik_kebal"))}


def _peta_sek(kod_ppd):
    try:
        return pc.sekolah_map(kod_ppd)
    except Exception:
        return {}


def muat_bk(kod_ppd):
    """DataFrame bilik kebal PPD: kolum KOD, NAMA, ALAMAT."""
    cols = ["KOD", "NAMA", "ALAMAT"]
    try:
        raw = pd.DataFrame(supa.table("bilik_kebal_master").select("*").eq("kod_ppd", kod_ppd).limit(10000).execute().data or [])
    except Exception as e:
        st.error(f"Gagal baca bilik_kebal_master: {e}")
        return pd.DataFrame(columns=cols)
    if raw.empty:
        return pd.DataFrame(columns=cols)
    smap = _peta_sek(kod_ppd)
    rows = []
    for _, b in raw.iterrows():
        kod = _g(b, "kod_bilik_kebal", "KOD_BILIK_KEBAL").upper()
        if not kod:
            continue
        nama = _g(b, "nama_bilik_kebal", "NAMA_BILIK_KEBAL", "nama", "NAMA")
        if (not nama or nama.upper() == kod) and isinstance(b.get("data"), dict):
            nama = next((str(b["data"].get(k)).strip() for k in ("nama_bilik_kebal", "NAMA_BILIK_KEBAL", "nama", "NAMA", "nama_sekolah")
                         if b["data"].get(k) and str(b["data"].get(k)).strip().upper() != kod), nama)
        if not nama or nama.upper() == kod:
            try:
                import penyelia_surat as _psn
                nama = smap.get(kod) or _psn.nama_bk_cari(kod_ppd, kod, nama) or kod
            except Exception:
                nama = smap.get(kod, nama or kod)
        rows.append({"KOD": kod, "NAMA": nama, "ALAMAT": _g(b, "alamat", "ALAMAT")})
    return pd.DataFrame(rows, columns=cols).drop_duplicates("KOD").sort_values("KOD").reset_index(drop=True)


REKOD_COLS = ["id", "NAMA", "IC", "KOD_SEK", "NAMA_SEK", "TELEFON", "POSKOD", "STATUS", "STAGE", "BK", "PUSAT", "BAWAH", "NO_SURAT"]


def muat_pk(kod_ppd, bk_codes=None, df=None):
    """Semua PK PPD ini sebagai DataFrame rekod ringkas (satu baris satu PK)."""
    if df is None:
        df = get_cadangan_df(kod_ppd=kod_ppd)
    if df is None or df.empty:
        return pd.DataFrame(columns=REKOD_COLS)
    smap = _peta_sek(kod_ppd)
    rows = []
    for _, r in df.iterrows():
        if not is_pk(r):
            continue
        rid = r.get("id")
        if _s(rid) == "":
            continue
        kod_sek = _g(r, "KOD_SEKOLAH_ASAL", "kod_sekolah_asal", "KOD_SEKOLAH", "kod_sekolah").upper()
        if not kod_sek:
            continue
        info = pk_info(r, bk_codes)
        rows.append({
            "id": rid, "NAMA": _g(r, "NAMA_GURU", "nama_guru"), "IC": _g(r, "IC_GURU", "ic_guru"),
            "KOD_SEK": kod_sek, "NAMA_SEK": smap.get(kod_sek) or _g(r, "NAMA_SEKOLAH_ASAL", "nama_sekolah_asal") or kod_sek,
            "TELEFON": _g(r, "TELEFON_GURU", "telefon_guru"), "POSKOD": _g(r, "POSKOD_RUMAH", "poskod_rumah"),
            "STATUS": status_of(r), "STAGE": pk_stage(r), "BK": info["bk"], "PUSAT": info["pusat"], "BAWAH": info["bawah"],
            "NO_SURAT": _g(r, "no_surat", "NO_SURAT"),
        })
    return pd.DataFrame(rows, columns=REKOD_COLS)


# ====================================================================== tulis ke pangkalan data
_PK_MAP = {}          # cache ringkas {kod_ppd: (masa, {pusat: [rekod]})} untuk placeholder surat


def _bersih_cache():
    try:
        get_cadangan_df.clear()
    except Exception:
        pass
    _PK_MAP.clear()


def _data_db(pid):
    """JSON `data` semasa dari pangkalan data (supaya kemas kini TIDAK memadam maklumat asal guru)."""
    try:
        res = supa.table("cadangan_sup").select("data").eq("id", pc._pyid(pid)).limit(1).execute()
        d = (res.data or [{}])[0].get("data") or {}
        if isinstance(d, str):
            d = json.loads(d)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _tulis(pid, payloads):
    last = None
    for p in payloads:
        try:
            supa.table("cadangan_sup").update(p).eq("id", pc._pyid(pid)).execute()
            return True, ""
        except Exception as e:
            last = e
    return False, str(last)[:200]


_KUNCI_TEMPAT = ("kod_bilik_kebal", "kod_bilik_kebal_explicit", "pusat_jagaan", "pusat_jagaan_str", "pusat_bawah_bilik_kebal")


def simpan_tempatan(pid, kod_bk, pusat_list, pusat_bawah):
    data = _data_db(pid)
    data.update({"kod_bilik_kebal": kod_bk, "kod_bilik_kebal_explicit": kod_bk, "pusat_jagaan": list(pusat_list),
                 "pusat_jagaan_str": ",".join(pusat_list), "pusat_bawah_bilik_kebal": list(pusat_bawah)})
    kp = ",".join(pusat_list)
    ok, err = _tulis(pid, [
        {"kod_bilik_kebal": kod_bk, "kod_pusat": kp, "status": ST_TEMPAT, "data": data},
        {"kod_pusat": kp, "status": ST_TEMPAT, "data": data},
        {"kod_bilik_kebal": kod_bk, "status": ST_TEMPAT, "data": data},
        {"status": ST_TEMPAT, "data": data},
    ])
    return ok, err


def batal_tempatan(pid, ke_status=ST_TERPILIH):
    """Batal penempatan satu PK: kosongkan bilik kebal/pusat/no surat, kembali ke TERPILIH PPD."""
    data = _data_db(pid)
    for k in _KUNCI_TEMPAT:
        data.pop(k, None)
    for k in ("surat_html", "surat_tarikh", "surat_no", "SURAT_DIHANTAR_KE_SEKOLAH_ASAL", "jenis", "bilik_kebal"):
        data.pop(k, None)
    return _tulis(pid, [
        {"kod_bilik_kebal": None, "kod_pusat": None, "no_surat": None, "status": ke_status, "data": data},
        {"kod_pusat": None, "no_surat": None, "status": ke_status, "data": data},
        {"kod_pusat": "", "no_surat": None, "status": ke_status, "data": data},
        {"status": ke_status, "no_surat": None, "data": data},
        {"status": ke_status},
    ])


def _masih_ada_surat(pid):
    """True jika baris PK masih ada no surat / status LULUS (pengesahan selepas batal)."""
    try:
        res = supa.table("cadangan_sup").select("no_surat,status").eq("id", pc._pyid(pid)).limit(1).execute()
        r = (res.data or [{}])[0]
        return bool(_s(r.get("no_surat"))) or _s(r.get("status")).upper().startswith("LULUS")
    except Exception:
        return False


def batal_pelantikan(kod_ppd, rekods, ke_status=ST_TERPILIH):
    """BATAL PELANTIKAN Penyelia Kawasan pada mana-mana peringkat (disimpan / dihantar / surat sudah dihantar).

    rekods : senarai dict daripada muat_pk() (perlu kunci id, NAMA, IC, STAGE).
    Untuk PK yang sudah ada surat: no surat + surat_html + penanda 'dihantar ke sekolah asal' dibuang,
    dan rekod log di jadual surat_hantar_sekolah_asal (jika ada) dipadam supaya sekolah asal tidak lagi nampak surat itu.
    Pulang (senarai_ok, senarai_gagal[str]).
    """
    ok, gagal, ics_surat = [], [], []
    for rec in rekods:
        pid = rec["id"]
        berjaya, err = batal_tempatan(pid, ke_status)
        if berjaya and _masih_ada_surat(pid):
            _tulis(pid, [{"status": ke_status, "no_surat": None}, {"no_surat": None}])
            if _masih_ada_surat(pid):
                berjaya, err = False, "no surat masih ada selepas cubaan batal"
        if berjaya:
            ok.append(rec)
            if rec.get("STAGE") == "LULUS" and _s(rec.get("IC")):
                ics_surat.append(_s(rec.get("IC")))
        else:
            gagal.append(f"{rec.get('NAMA', pid)}: {err}")
    try:                                              # jadual log surat ke sekolah asal (pilihan)
        for i in range(0, len(ics_surat), 100):
            supa.table("surat_hantar_sekolah_asal").delete().in_("ic_guru", ics_surat[i:i + 100]).execute()
    except Exception:
        pass
    st.session_state.pop(f"pk_surat_{kod_ppd}", None)  # surat janaan dalam sesi yang sudah tidak sah
    _bersih_cache()
    return ok, gagal


def hantar_kelulusan(ids):
    ok, err = pc.ppd_set_status(ids, ST_HANTAR)
    _bersih_cache()
    return ok, err


# ====================================================================== UI kecil
def _banner(judul, sub=""):
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#0d47a1 0%,#1565c0 100%);padding:18px 20px;border-radius:12px;'
        f'color:white;margin-bottom:16px;border:2px solid #002171"><h2 style="margin:0;color:white">{_e(judul)}</h2>'
        f'<p style="margin:5px 0 0 0;color:#bbdefb">{_e(sub)}</p></div>', unsafe_allow_html=True)


def _flash():
    m = st.session_state.pop("pk_flash", None)
    if m:
        st.success(m)


def _fmt_pusat(peta):
    def f(x):
        n = (peta.get(x) or {}).get("nama", "")
        return f"{x} - {n[:30]}" if n else x
    return f


def _peta_pusat(kod_ppd):
    import penyelia_surat as _ps
    return _ps._peta_pusat(kod_ppd)


def _tick_editor(tbl, key, tajuk_lajur, nilai_awal):
    """data_editor dengan satu lajur tick. Pulang (edited_df)."""
    t = tbl.copy()
    t.insert(0, tajuk_lajur, nilai_awal)
    cfg = {tajuk_lajur: st.column_config.CheckboxColumn(tajuk_lajur), "id": None}
    ed = st.data_editor(t, hide_index=True, use_container_width=True, key=key,
                        disabled=[c for c in t.columns if c != tajuk_lajur], column_config=cfg)
    return ed if isinstance(ed, pd.DataFrame) else t


# ====================================================================== 1. CADANGAN SUP (PK)
def render_cadangan(kod_ppd):
    _banner(f"📋 Cadangan SUP (Penyelia Kawasan) - PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')}",
            "Senarai nama Penyelia Kawasan yang dihantar oleh SUP. Tick nama untuk dilantik; yang tidak ditick masuk Simpanan.")
    _flash()
    dfk = muat_pk(kod_ppd)
    if dfk.empty:
        st.info("Belum ada cadangan Penyelia Kawasan daripada SUP.")
        return
    cnt = dfk["STAGE"].value_counts().to_dict()
    a, b, c, d = st.columns(4)
    a.metric("🆕 Baru dihantar SUP", cnt.get("BARU", 0))
    b.metric("✅ Terpilih (tunggu tempat)", cnt.get("TERPILIH", 0))
    c.metric("📦 Simpanan", cnt.get("SIMPANAN", 0))
    d.metric("📍 Ditempatkan / Lulus", cnt.get("TEMPAT", 0) + cnt.get("HANTAR", 0) + cnt.get("LULUS", 0))

    baru = dfk[dfk["STAGE"] == "BARU"]
    if baru.empty:
        st.info("Tiada cadangan baharu. Semua nama sudah disemak - lihat sub menu Simpanan PK atau Tempatkan PK.")
    else:
        opts = {"SEMUA": f"Semua sekolah ({len(baru)} nama)"}
        for kod, g in baru.groupby("KOD_SEK"):
            opts[kod] = f"{g['NAMA_SEK'].iloc[0]} ({kod}) - {len(g)} nama"
        pilih = st.selectbox("🏫 Pilih Sekolah", list(opts.keys()), format_func=lambda k: opts.get(k, k), key="pk_cad_sek")
        view = baru if pilih == "SEMUA" else baru[baru["KOD_SEK"] == pilih]
        view = view.reset_index(drop=True)
        semua = st.checkbox("Tick semua nama dipaparkan", key=f"pk_cad_semua_{pilih}")
        tbl = view[["id", "NAMA", "IC", "KOD_SEK", "NAMA_SEK", "TELEFON", "POSKOD"]]
        ed = _tick_editor(tbl, f"pk_cad_ed_{pilih}_{int(semua)}", "LANTIK", bool(semua))
        yes = ed.loc[ed["LANTIK"] == True, "id"].tolist()          # noqa: E712
        no = ed.loc[ed["LANTIK"] != True, "id"].tolist()
        st.caption(f"✅ {len(yes)} dilantik (ke Tempatkan PK)  •  📦 {len(no)} tidak ditick (ke Simpanan)")
        if st.button(f"📤 Hantar: {len(yes)} Dilantik | {len(no)} ke Simpanan", type="primary", use_container_width=True,
                     disabled=view.empty, key="pk_cad_hantar"):
            ok1, e1 = pc.ppd_set_status(yes, ST_TERPILIH) if yes else (0, [])
            ok2, e2 = pc.ppd_set_status(no, ST_SIMPANAN) if no else (0, [])
            _bersih_cache()
            if e1 or e2:
                st.error("Sebahagian gagal: " + " | ".join((e1 + e2)[:2]))
            else:
                st.session_state["pk_flash"] = f"✅ {ok1} PK dilantik (sedia ditempatkan), {ok2} PK masuk Simpanan."
                st.rerun()

    terpilih = dfk[dfk["STAGE"] == "TERPILIH"].reset_index(drop=True)
    if not terpilih.empty:
        with st.expander(f"✅ Terpilih - menunggu penempatan ({len(terpilih)})", expanded=False):
            ed2 = _tick_editor(terpilih[["id", "NAMA", "IC", "KOD_SEK", "NAMA_SEK", "TELEFON"]], "pk_cad_terpilih_ed", "KE SIMPANAN", False)
            ids2 = ed2.loc[ed2["KE SIMPANAN"] == True, "id"].tolist()      # noqa: E712
            if st.button(f"📦 Pindah {len(ids2)} nama ke Simpanan", disabled=not ids2, key="pk_cad_ke_simpanan"):
                pc.ppd_set_status(ids2, ST_SIMPANAN)
                _bersih_cache()
                st.session_state["pk_flash"] = f"✅ {len(ids2)} nama dipindahkan ke Simpanan."
                st.rerun()


# ====================================================================== 2. SIMPANAN PK
def render_simpanan(kod_ppd):
    _banner(f"📦 Simpanan Penyelia Kawasan - PPD {kod_ppd}", "Nama PK yang tidak dipilih. Tick dan lantik semula bila perlu.")
    _flash()
    dfk = muat_pk(kod_ppd)
    sim = dfk[dfk["STAGE"] == "SIMPANAN"] if not dfk.empty else dfk
    if sim.empty:
        st.info("Senarai simpanan kosong. Nama yang tidak ditick di Cadangan SUP akan masuk ke sini.")
        return
    st.metric("📦 Jumlah Simpanan", len(sim))
    opts = {"SEMUA": f"Semua sekolah ({len(sim)})"}
    for kod, g in sim.groupby("KOD_SEK"):
        opts[kod] = f"{g['NAMA_SEK'].iloc[0]} ({kod}) - {len(g)}"
    pilih = st.selectbox("🏫 Pilih Sekolah", list(opts.keys()), format_func=lambda k: opts.get(k, k), key="pk_sim_sek")
    view = (sim if pilih == "SEMUA" else sim[sim["KOD_SEK"] == pilih]).reset_index(drop=True)
    ed = _tick_editor(view[["id", "NAMA", "IC", "KOD_SEK", "NAMA_SEK", "TELEFON", "POSKOD"]], f"pk_sim_ed_{pilih}", "LANTIK", False)
    ids = ed.loc[ed["LANTIK"] == True, "id"].tolist()          # noqa: E712
    if st.button(f"➡️ Lantik {len(ids)} nama (ke Tempatkan PK)", type="primary", disabled=not ids, key="pk_sim_lantik"):
        ok, err = pc.ppd_set_status(ids, ST_TERPILIH)
        _bersih_cache()
        if err:
            st.error("Gagal: " + " | ".join(err[:2]))
        else:
            st.session_state["pk_flash"] = f"✅ {ok} nama dipindahkan ke Tempatkan PK (TERPILIH)."
            st.rerun()


# ====================================================================== 3. TEMPATKAN PK
def render_batal_pelantikan(kod_ppd, df, key):
    """Butang BATAL PELANTIKAN PENYELIA KAWASAN (boleh dipanggil dari mana-mana sub menu PK).

    df  : DataFrame daripada muat_pk() (baris yang layak sahaja akan dipaparkan: TEMPAT / HANTAR / LULUS).
    key : awalan unik untuk widget (elak pertembungan key antara sub menu).
    """
    if df is None or df.empty:
        return
    df = df[df["STAGE"].isin(STAGE_TEMPAT)].reset_index(drop=True)
    if df.empty:
        return
    label = {"TEMPAT": "💾 Disimpan", "HANTAR": "📤 Menunggu kelulusan", "LULUS": "✅ Surat dihantar"}
    with st.expander(f"🗑️ Batal Pelantikan Penyelia Kawasan ({len(df)})", expanded=False):
        st.caption("Membatalkan lantikan PK yang dipilih: bilik kebal, pusat yang diawasi dan no surat dikosongkan. "
                   "PK dipulangkan ke senarai supaya boleh ditempatkan semula atau digantikan.")
        ids = df["id"].tolist()

        def fmt(x):
            r = df[df["id"] == x].iloc[0]
            t = f"{str(r['NAMA'])[:28]} | {r['BK'] or '-'} | {label.get(r['STAGE'], r['STAGE'])}"
            return t + (f" | {r['NO_SURAT']}" if r["NO_SURAT"] else "")
        pil = st.multiselect("Pilih Penyelia Kawasan yang dibatalkan", ids, format_func=fmt, key=f"{key}_pil")
        ke = st.radio("Selepas dibatalkan, PK dipulangkan ke:", [ST_TERPILIH, ST_SIMPANAN], horizontal=True, key=f"{key}_ke",
                      format_func=lambda s: "Terpilih PPD (boleh ditempatkan semula)" if s == ST_TERPILIH else "Simpanan PK")
        dipilih = df[df["id"].isin(pil)]
        n_surat = int((dipilih["STAGE"] == "LULUS").sum()) if not dipilih.empty else 0
        if n_surat:
            st.warning(f"⚠️ {n_surat} PK sudah ada surat lantikan. No surat akan dipadam dan surat itu tidak lagi dipaparkan "
                       f"kepada sekolah asal. Surat baharu perlu dijana semula jika PK ditempatkan semula.")
        sah = st.checkbox("Ya, saya pasti mahu membatalkan pelantikan PK yang dipilih", key=f"{key}_sah", disabled=not pil)
        if st.button(f"🗑️ BATAL PELANTIKAN ({len(pil)} PK)", type="primary", use_container_width=True,
                     disabled=not (pil and sah), key=f"{key}_btn"):
            ok, gagal = batal_pelantikan(kod_ppd, dipilih.to_dict("records"), ke)
            tujuan = "Terpilih PPD" if ke == ST_TERPILIH else "Simpanan PK"
            msg = f"✅ {len(ok)} pelantikan PK dibatalkan (dipulangkan ke {tujuan})."
            if gagal:
                msg += f" ⚠️ {len(gagal)} gagal: " + "; ".join(gagal[:2])
            st.session_state["pk_flash"] = msg
            for k in (f"{key}_pil", f"{key}_sah"):
                try:
                    del st.session_state[k]
                except Exception:
                    pass
            st.rerun()


def render_tempatkan(kod_ppd):
    import penyelia_surat as _ps
    _banner(f"📍 Tempatkan Penyelia Kawasan - PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')}",
            "Klik bilik kebal → pilih pusat di bawahnya → pilih seorang PK + pusat yang diawasi → Simpan → Hantar ke Kelulusan.")
    _flash()
    df_bk = muat_bk(kod_ppd)
    if df_bk.empty:
        st.warning("Belum ada bilik kebal. Daftar dahulu di menu Selenggara Bilik Kebal.")
        return
    codes = set(df_bk["KOD"])
    dfk = muat_pk(kod_ppd, codes)
    peta = _peta_pusat(kod_ppd)
    fmt = _fmt_pusat(peta)

    # ---------- STEP 1: senarai bilik kebal (klik)
    st.markdown("#### 1️⃣ Pilih Bilik Kebal")
    sel = st.session_state.get("pk_bk_sel")
    cols = st.columns(3)
    for i, (_, b) in enumerate(df_bk.iterrows()):
        n = int(((dfk["BK"] == b["KOD"]) & dfk["STAGE"].isin(STAGE_TEMPAT)).sum()) if not dfk.empty else 0
        if cols[i % 3].button(f"{'✅ ' if n else ''}{b['KOD']} - {b['NAMA'][:24]}  ({n} PK)", key=f"pk_bk_btn_{b['KOD']}",
                              type="primary" if b["KOD"] == sel else "secondary", use_container_width=True):
            st.session_state["pk_bk_sel"] = b["KOD"]
            st.rerun()
    if sel not in codes:
        st.info("Klik satu bilik kebal di atas untuk mula.")
        _ringkasan_bk(kod_ppd, df_bk, dfk)
        return

    bk = df_bk[df_bk["KOD"] == sel].iloc[0]
    st.markdown(f"##### 🔐 Bilik Kebal **{sel}** - {bk['NAMA']}" + (f"  \n📍 {bk['ALAMAT']}" if bk["ALAMAT"] else ""))
    di_bk = dfk[(dfk["BK"] == sel) & dfk["STAGE"].isin(STAGE_TEMPAT)] if not dfk.empty else dfk

    # ---------- STEP 2: pusat di bawah bilik kebal
    st.markdown("#### 2️⃣ Pilih Pusat di Bawah Bilik Kebal Ini")
    opsi = sorted(peta.keys())
    try:
        zp = [p for p in _ps.pusat_zon(kod_ppd, sel) if p in opsi]
    except Exception:
        zp = []
    simpan_bawah = sorted({p for lst in di_bk["BAWAH"] for p in lst}) if not di_bk.empty else []
    asal = [p for p in (simpan_bawah or zp) if p in opsi]
    if zp and not simpan_bawah:
        st.caption(f"🗺️ {len(zp)} pusat dipilih automatik daripada Zon {sel} (Penempatan Zon). Boleh tambah / buang.")
    bawah = st.multiselect("Pusat di bawah bilik kebal ini", opsi, default=asal, format_func=fmt, key=f"pk_bawah_{sel}")

    # ---------- STEP 3: pilih seorang PK + pusat yang diawasi
    st.markdown("#### 3️⃣ Pilih Seorang Penyelia Kawasan & Pusat Yang Diawasi")
    pool = dfk[(dfk["STAGE"] == "TERPILIH") | ((dfk["BK"] == sel) & dfk["STAGE"].isin(["TEMPAT", "HANTAR"]))] if not dfk.empty else dfk
    if pool.empty:
        st.info("Tiada PK terpilih. Lantik dahulu di sub menu Cadangan SUP (atau Simpanan PK).")
    else:
        ids = pool["id"].tolist()

        def fmt_pk(x):
            r = pool[pool["id"] == x].iloc[0]
            tanda = " ✔ (sudah di bilik kebal ini)" if r["BK"] == sel else ""
            return f"{r['NAMA'][:30]} | {r['KOD_SEK']} | {r['TELEFON']}{tanda}"
        pid = st.selectbox("Penyelia Kawasan", ids, format_func=fmt_pk, key=f"pk_pilih_{sel}")
        rec = pool[pool["id"] == pid].iloc[0]
        # Pusat TERBUKA: beberapa PK dalam bilik kebal yang sama boleh mengawasi pusat yang sama.
        opsi_p = list(bawah)
        semasa = [p for p in (rec["PUSAT"] if rec["BK"] == sel else []) if p in opsi_p]
        lain = {}
        if not di_bk.empty:
            for _, r in di_bk[di_bk["id"] != pid].iterrows():
                for p in r["PUSAT"]:
                    lain.setdefault(p, []).append(r["NAMA"].split(" ")[0] if r["NAMA"] else "-")
        if lain:
            st.caption("ℹ️ Pusat ini sudah diawasi PK lain di " + sel + " (boleh dipilih juga, pusat terbuka kepada semua PK dalam bilik kebal ini): "
                       + "; ".join(f"{p} ({', '.join(v)})" for p, v in sorted(lain.items())))
        pusat_pilih = st.multiselect("Pusat yang akan diawasi oleh PK ini", opsi_p, default=semasa, format_func=fmt,
                                     key=f"pk_pusat_{sel}_{pid}")
        if rec["STAGE"] == "HANTAR":
            st.warning("PK ini sudah dihantar ke Kelulusan. Jika disimpan semula, ia perlu dihantar sekali lagi.")
        if st.button(f"💾 Simpan - {rec['NAMA'][:30]} ke {sel} ({len(pusat_pilih)} pusat)", type="primary",
                     use_container_width=True, disabled=not pusat_pilih, key=f"pk_simpan_{sel}"):
            ok, err = simpan_tempatan(pid, sel, pusat_pilih, bawah)
            _bersih_cache()
            if ok:
                st.session_state["pk_flash"] = f"✅ {rec['NAMA']} disimpan di {sel} dengan {len(pusat_pilih)} pusat. Klik Hantar bila siap."
                st.rerun()
            else:
                st.error(f"Gagal simpan: {err}")

    # ---------- PK di bilik kebal ini + Hantar / Batal
    st.markdown("#### 4️⃣ PK Di Bilik Kebal Ini")
    if di_bk.empty:
        st.info("Belum ada PK ditempatkan di bilik kebal ini.")
    else:
        label = {"TEMPAT": "💾 Disimpan", "HANTAR": "📤 Dihantar ke Kelulusan", "LULUS": "✅ Surat dihantar"}
        st.dataframe(pd.DataFrame([{"NAMA PK": r["NAMA"], "SEKOLAH ASAL": r["NAMA_SEK"], "TELEFON": r["TELEFON"],
                                    "PUSAT DIAWASI": ", ".join(r["PUSAT"]), "BIL": len(r["PUSAT"]), "STATUS": label.get(r["STAGE"], r["STAGE"])}
                                   for _, r in di_bk.iterrows()]), use_container_width=True, hide_index=True)
        belum = [p for p in bawah if p not in {x for l in di_bk["PUSAT"] for x in l}]
        if belum:
            st.warning(f"⚠️ {len(belum)} pusat di bawah {sel} belum ada PK: {', '.join(belum)}")
        siap = di_bk[di_bk["STAGE"] == "TEMPAT"]
        c1, c2 = st.columns(2)
        if c1.button(f"📤 Hantar {len(siap)} PK ({sel}) ke Kelulusan", type="primary", disabled=siap.empty,
                     use_container_width=True, key=f"pk_hantar_{sel}"):
            ok, err = hantar_kelulusan(siap["id"].tolist())
            if err:
                st.error("Gagal: " + " | ".join(err[:2]))
            else:
                st.session_state["pk_flash"] = f"✅ {ok} PK dihantar ke Kelulusan & Janaan Surat."
                st.rerun()
        boleh_batal = di_bk[di_bk["STAGE"].isin(["TEMPAT", "HANTAR"])]
        with c2.expander(f"🗑️ Batal penempatan ({len(boleh_batal)})"):
            if boleh_batal.empty:
                st.caption("Tiada penempatan yang boleh dibatal di sini. PK yang sudah ada surat dibatal melalui Sah Lantik atau Kelulusan & Surat > Batal Pelantikan Penyelia Kawasan.")
            else:
                pil = st.multiselect("Pilih PK", boleh_batal["id"].tolist(), key=f"pk_batal_pil_{sel}",
                                     format_func=lambda x: boleh_batal[boleh_batal["id"] == x].iloc[0]["NAMA"])
                if st.button(f"🗑️ Batal {len(pil)} penempatan", disabled=not pil, key=f"pk_batal_btn_{sel}"):
                    gagal = [x for x in pil if not batal_tempatan(x)[0]]
                    _bersih_cache()
                    st.session_state["pk_flash"] = f"✅ {len(pil) - len(gagal)} penempatan dibatalkan (PK kembali ke Terpilih)." + (f" ⚠️ {len(gagal)} gagal." if gagal else "")
                    st.rerun()

    allsiap = dfk[dfk["STAGE"] == "TEMPAT"] if not dfk.empty else dfk
    if not allsiap.empty:
        st.markdown("---")
        if st.button(f"📤 Hantar SEMUA {len(allsiap)} PK (semua bilik kebal) ke Kelulusan", use_container_width=True, key="pk_hantar_semua"):
            ok, err = hantar_kelulusan(allsiap["id"].tolist())
            st.session_state["pk_flash"] = f"✅ {ok} PK dihantar ke Kelulusan." if not err else "Gagal: " + " | ".join(err[:2])
            st.rerun()
    _ringkasan_bk(kod_ppd, df_bk, dfk)


def _ringkasan_bk(kod_ppd, df_bk, dfk):
    rows = []
    for _, b in df_bk.iterrows():
        sub = dfk[(dfk["BK"] == b["KOD"]) & dfk["STAGE"].isin(STAGE_TEMPAT)] if not dfk.empty else dfk
        if sub.empty:
            rows.append({"BILIK KEBAL": b["KOD"], "NAMA": b["NAMA"], "NAMA PK": "-", "SEKOLAH ASAL": "-", "PUSAT DIAWASI": "-", "STATUS": "Belum ada PK"})
        for _, r in sub.iterrows():
            rows.append({"BILIK KEBAL": b["KOD"], "NAMA": b["NAMA"], "NAMA PK": r["NAMA"], "SEKOLAH ASAL": r["NAMA_SEK"],
                         "PUSAT DIAWASI": ", ".join(r["PUSAT"]), "STATUS": {"TEMPAT": "Disimpan", "HANTAR": "Dihantar", "LULUS": "Lulus"}.get(r["STAGE"], "")})
    if rows:
        with st.expander("📊 Ringkasan semua bilik kebal", expanded=False):
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button("📥 Export Ringkasan (Excel)", core.to_excel(df), file_name=f"ringkasan_pk_bilik_kebal_{kod_ppd}_{datetime.date.today()}.xlsx",
                               key="pk_ringkas_dl")


# ====================================================================== 4. KELULUSAN & JANAAN SURAT
def _max_no(kod_ppd):
    mx = 0
    try:
        df = get_cadangan_df(kod_ppd=kod_ppd)
        for ns in (df["no_surat"].tolist() if df is not None and not df.empty and "no_surat" in df.columns else []):
            ns = _s(ns)
            digit = "".join(ch for ch in ns.split("/")[-1] if ch.isdigit()) if ns else ""
            if digit:
                mx = max(mx, int(digit))
    except Exception:
        pass
    return mx


def _raw_row(raw, pid):
    m = raw[raw["id"].astype(str) == str(pid)]
    return None if m.empty else m.iloc[0]


def _jana_surat(kod_ppd, rekods, df_bk, raw, prefix, no_mula, tarikh, no_tetap=None):
    import penyelia_surat as _ps
    tarikh_str = tarikh.strftime("%d %B %Y")
    hasil, no = [], int(no_mula)
    for _, rec in rekods.iterrows():
        row = _raw_row(raw, rec["id"])
        if row is None:
            continue
        r = lengkapkan(row, kod_ppd)
        nama = _g(r, "NAMA_GURU", "nama_guru")
        ic = _g(r, "IC_GURU", "ic_guru")
        sek = _g(r, "KOD_SEKOLAH_ASAL", "kod_sekolah_asal")
        nama_sek = _g(r, "NAMA_SEKOLAH_ASAL", "nama_sekolah_asal") or sek
        tel = _g(r, "TELEFON_GURU", "telefon_guru") or rec["TELEFON"]
        kod_bk = rec["BK"]
        b = df_bk[df_bk["KOD"] == kod_bk]
        nama_bk = b.iloc[0]["NAMA"] if not b.empty else kod_bk
        alamat_bk = b.iloc[0]["ALAMAT"] if not b.empty else ""
        no_surat = no_tetap or _nsr.format_no(prefix, no)
        no += 1
        html, extra = _ps.jana_html(core, nama=nama, ic=ic, sek_asal=sek, nama_sek_asal=nama_sek, telefon=tel, kod_bk=kod_bk,
                                    nama_bk=nama_bk, alamat_bk=alamat_bk, pusat_jagaan=rec["PUSAT"], no_surat=no_surat,
                                    kod_ppd=kod_ppd, ppd_name=PPD_MAP.get(kod_ppd, ""), tarikh=tarikh_str)
        dari_templat = bool(html)
        if not html:                                   # sandaran jika templat JPN belum disimpan
            fn = getattr(core, "generate_surat_penyelia_kawasan_html", None)
            html = fn(nama=nama, ic=ic, sek_asal=sek, nama_sek_asal=nama_sek, telefon=tel, kod_bilik_kebal=kod_bk,
                      nama_bilik_kebal=nama_bk, alamat_bilik_kebal=alamat_bk, pusat_jagaan_list=rec["PUSAT"], no_surat=no_surat,
                      kod_ppd=kod_ppd, ppd_name=PPD_MAP.get(kod_ppd, ""), tarikh=tarikh_str) if fn else ""
        pdf = None
        try:
            pdf = core.html_to_pdf_bytes(html) if html else None
        except Exception:
            pdf = None
        hasil.append({"id": rec["id"], "nama": nama, "ic": ic, "sekolah_asal": sek, "nama_sek": nama_sek, "bilik_kebal": kod_bk,
                      "pusat_jagaan": list(rec["PUSAT"]), "no_surat": no_surat, "html": html, "pdf": pdf, "dari_templat": dari_templat})
    return hasil


def _hantar_sekolah_asal(senarai):
    ok, gagal = 0, []
    for s in senarai:
        data = _data_db(s["id"])
        data.update({"surat_html": s["html"], "surat_tarikh": str(datetime.date.today()), "surat_no": s["no_surat"],
                     "SURAT_DIHANTAR_KE_SEKOLAH_ASAL": True, "jenis": "Penyelia Kawasan", "bilik_kebal": s["bilik_kebal"],
                     "pusat_jagaan": s["pusat_jagaan"]})
        ok_, err = _tulis(s["id"], [
            {"status": ST_LULUS, "no_surat": s["no_surat"], "data": data},
            {"status": ST_LULUS, "no_surat": s["no_surat"]},
            {"status": "SURAT PK DIHANTAR", "no_surat": s["no_surat"]},
        ])
        if ok_:
            ok += 1
        else:
            gagal.append(f"{s['nama']}: {err}")
    _bersih_cache()
    return ok, gagal


_PH_ASAS = {"NAMA", "NAMA_GURU", "IC", "IC_GURU", "JAWATAN", "JAWATAN_CADANGAN", "SEKOLAH_ASAL", "KOD_SEKOLAH_ASAL", "NAMA_SEKOLAH_ASAL",
            "SEKOLAH_ASAL_PENUH", "PUSAT", "KOD_PUSAT", "NO_PUSAT", "NAMA_PUSAT", "PUSAT_PENUH", "BILIK_KEBAL", "KOD_BILIK_KEBAL",
            "NO_SURAT", "PPD", "KOD_PPD", "PPD_NAME", "NAMA_PPD", "TARIKH", "LOGO", "TANDATANGAN", "TANDA_TANGAN", "TAHUN"}


def render_semak_placeholder(kod_ppd, df_bk, dfk):
    """Panel diagnostik: nilai placeholder PK dan placeholder dalam templat JPN yang tidak dikenali."""
    import re
    import penyelia_surat as _ps
    with st.expander("🔍 Semak placeholder surat PK (jika nama bilik kebal / pusat / tahun tidak keluar)", expanded=False):
        tmpl = ""
        try:
            tmpl = core.get_jpn_template_for_jawatan(_ps.JAWATAN_TEMPLAT) or ""
        except Exception as e:
            st.error(f"Gagal baca templat: {e}")
        if not tmpl:
            st.error(f"Templat JPN '{_ps.JAWATAN_TEMPLAT}' TIADA dalam surat_templates_jpn - surat guna susun atur sandaran (bukan templat JPN). "
                     "JPN perlu simpan templat di menu Template Surat JPN.")
            return
        ph = sorted({m.upper() for m in re.findall(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}", tmpl)})
        if dfk is not None and not dfk.empty and not dfk[dfk["STAGE"].isin(["HANTAR", "LULUS"])].empty:
            rec = dfk[dfk["STAGE"].isin(["HANTAR", "LULUS"])].iloc[0]
            kod_bk, pusat = rec["BK"], list(rec["PUSAT"])
            sumber = f"PK: {rec['NAMA']}"
        elif not df_bk.empty:
            kod_bk, pusat, sumber = df_bk.iloc[0]["KOD"], [], "bilik kebal pertama (tiada PK dihantar lagi)"
        else:
            st.info("Tiada bilik kebal untuk diuji.")
            return
        b = df_bk[df_bk["KOD"] == kod_bk]
        nama_bk = b.iloc[0]["NAMA"] if not b.empty else kod_bk
        ex = _ps.bina_extra(kod_ppd, kod_bk, nama_bk, b.iloc[0]["ALAMAT"] if not b.empty else "", "", pusat)
        st.caption(f"Diuji dengan {sumber} | bilik kebal {kod_bk} | nama dalam jadual: '{nama_bk}'")
        rows = []
        for k in ph:
            if k in ex:
                v, st_ = str(ex[k]), "✅ dikenali"
            elif k in _PH_ASAS:
                v, st_ = "(diisi semasa jana)" if k not in ("TAHUN",) else str(tahun_semasa()), "✅ dikenali"
            else:
                v, st_ = "", "❌ TIDAK DIKENALI - tidak akan diganti"
            rows.append({"PLACEHOLDER DALAM TEMPLAT": "{{" + k + "}}", "STATUS": st_, "NILAI": v[:80]})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        hilang = [k for k in ("BILIK_KEBAL_PENUH", "SENARAI_PUSAT_MERAH", "TAHUN") if k not in ph]
        if hilang:
            st.warning("Templat JPN yang DISIMPAN tidak mengandungi: " + ", ".join("{{" + k + "}}" for k in hilang)
                       + ". Templat yang awak tampal mungkin belum disimpan di menu Template Surat JPN (11 Jawatan).")
        if not ex.get("SENARAI_PUSAT_MERAH") or ex.get("SENARAI_PUSAT_MERAH") == "-":
            st.info("Pusat jagaan kosong untuk contoh ini. Surat sebenar akan papar pusat yang dipilih semasa Tempatkan PK.")


def render_surat(kod_ppd):
    import penyelia_surat as _ps
    _banner(f"✅ Kelulusan & Janaan Surat Penyelia Kawasan - PPD {kod_ppd}",
            "Tetapkan no surat & tarikh → semak nama PK → Jana surat (templat JPN) → Download → Hantar ke sekolah asal untuk dicetak.")
    _flash()
    df_bk = muat_bk(kod_ppd)
    raw = get_cadangan_df(kod_ppd=kod_ppd)
    dfk = muat_pk(kod_ppd, set(df_bk["KOD"]) if not df_bk.empty else None, df=raw)
    tunggu = dfk[dfk["STAGE"] == "HANTAR"].reset_index(drop=True) if not dfk.empty else dfk
    lulus = dfk[dfk["STAGE"] == "LULUS"] if not dfk.empty else dfk
    if not df_bk.empty:
        tanpa_nama = [k for k, n in zip(df_bk["KOD"], df_bk["NAMA"]) if not n or str(n).upper() == str(k).upper()]
        if tanpa_nama:
            st.warning("⚠️ Bilik kebal ini tiada nama (surat hanya papar kod): " + ", ".join(tanpa_nama)
                       + ". Isi nama di menu Selenggara Bilik Kebal, atau pastikan kod bilik kebal sama dengan kod sekolah dalam senarai sekolah.")
    a, b = st.columns(2)
    a.metric("📤 Menunggu kelulusan / surat", len(tunggu))
    b.metric("✅ Surat telah dihantar", len(lulus))
    render_semak_placeholder(kod_ppd, df_bk, dfk)

    if tunggu.empty:
        st.info("Tiada PK menunggu kelulusan. Tempatkan PK dan klik Hantar di sub menu Tempatkan PK.")
    else:
        st.markdown("#### 🔢 No Surat & Tarikh")
        c1, c2, c3 = st.columns(3)
        prefix = c1.text_input("No Rujukan Fail", value=_nsr.ruj_terkini(raw), key="pk_ruj_fail",
                               help="Format: <no rujukan> (1) hingga (100); selepas itu JLD 2 (1) dan seterusnya. Setiap PPD mempunyai turutan sendiri.")
        mx = _nsr.max_no(raw, prefix)
        no_mula = c2.number_input("No Mula (turutan)", min_value=1, value=mx + 1, key=f"pk_no_mula_{mx}_{zlib.crc32(prefix.encode())}")
        tarikh = c3.date_input("Tarikh Surat", value=datetime.date.today(), key="pk_tarikh")
        st.caption(f"Turutan terakhir di PPD {kod_ppd}: {mx if mx else '-'} | Surat PK bermula: {_nsr.format_no(prefix, no_mula)}")
        if _ps.ada_templat():
            st.success("✅ Surat dijana daripada TEMPLAT JPN (jawatan PENYELIA KAWASAN).")
        else:
            st.warning("⚠️ Templat JPN untuk PENYELIA KAWASAN belum disimpan - surat lama digunakan sementara.")

        st.markdown("#### 🔍 Semak Nama PK")
        tbl = tunggu[["id", "NAMA", "IC", "NAMA_SEK", "BK", "PUSAT"]].copy()
        tbl["PUSAT"] = tbl["PUSAT"].apply(lambda l: ", ".join(l))
        tbl = tbl.rename(columns={"NAMA_SEK": "SEKOLAH ASAL", "BK": "BILIK KEBAL"})
        ed = _tick_editor(tbl, "pk_surat_ed", "JANA", True)
        ids = ed.loc[ed["JANA"] == True, "id"].tolist()           # noqa: E712
        if st.button(f"📄 Jana {len(ids)} Surat Penyelia Kawasan", type="primary", use_container_width=True, disabled=not ids, key="pk_btn_jana"):
            with st.spinner("Menjana surat..."):
                hasil = _jana_surat(kod_ppd, tunggu[tunggu["id"].isin(ids)], df_bk, raw, prefix, no_mula, tarikh)
            st.session_state[f"pk_surat_{kod_ppd}"] = hasil
            st.rerun()

    hasil = st.session_state.get(f"pk_surat_{kod_ppd}") or []
    hasil = [h for h in hasil if str(h["id"]) in {str(x) for x in (tunggu["id"].tolist() if not tunggu.empty else [])}]
    if hasil:
        st.markdown("---")
        st.markdown(f"### 📄 {len(hasil)} Surat Telah Dijana ({hasil[0]['no_surat']} - {hasil[-1]['no_surat']})")
        html_all = "\n<div style='page-break-after:always'></div>\n".join(h["html"] for h in hasil)
        st.components.v1.html(html_all[:15000], height=600, scrolling=True)
        d1, d2, d3 = st.columns(3)
        d1.download_button("📥 Semua Surat (HTML)", html_all.encode("utf-8"), file_name=f"Surat_Penyelia_Kawasan_{kod_ppd}_{datetime.date.today()}.html",
                           mime="text/html", use_container_width=True, key="pk_dl_html")
        dfx = pd.DataFrame([{"NAMA": h["nama"], "IC": h["ic"], "SEKOLAH ASAL": h["nama_sek"], "BILIK KEBAL": h["bilik_kebal"],
                             "PUSAT": ", ".join(h["pusat_jagaan"]), "NO SURAT": h["no_surat"]} for h in hasil])
        d2.download_button("📥 Senarai (Excel)", core.to_excel(dfx), file_name=f"Senarai_Surat_PK_{kod_ppd}.xlsx", use_container_width=True, key="pk_dl_xlsx")
        if all(h["pdf"] for h in hasil):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for h in hasil:
                    safe = "".join(c if c.isalnum() else "_" for c in h["nama"])[:25]
                    zf.writestr(f"{h['no_surat'].replace('/', '_')}_{safe}.pdf", h["pdf"])
            d3.download_button("📥 ZIP PDF Individu", buf.getvalue(), file_name=f"Surat_PK_{kod_ppd}_{datetime.date.today()}.zip",
                               mime="application/zip", use_container_width=True, key="pk_dl_zip")
        else:
            d3.caption("PDF tidak dapat dijana (enjin PDF tiada) - guna HTML.")
        st.info("Selepas download, klik **Hantar** supaya surat sampai ke sekolah asal PK untuk dicetak. No surat disimpan ketika Hantar.")
        if st.button(f"📤 Hantar {len(hasil)} Surat ke Sekolah Asal PK", type="primary", use_container_width=True, key="pk_btn_hantar_surat"):
            ok, gagal = _hantar_sekolah_asal(hasil)
            st.session_state.pop(f"pk_surat_{kod_ppd}", None)
            st.session_state["pk_flash"] = f"✅ {ok} surat PK dihantar ke sekolah asal. Nama PK kini ada di menu Sah Lantik." + (f" ⚠️ Gagal: {'; '.join(gagal[:2])}" if gagal else "")
            st.rerun()

    if not lulus.empty:
        with st.expander(f"✅ Surat yang telah dihantar ({len(lulus)})", expanded=False):
            st.dataframe(pd.DataFrame([{"NO SURAT": r["NO_SURAT"], "NAMA": r["NAMA"], "SEKOLAH ASAL": r["NAMA_SEK"], "BILIK KEBAL": r["BK"],
                                        "PUSAT": ", ".join(r["PUSAT"])} for _, r in lulus.iterrows()]), use_container_width=True, hide_index=True)

    st.markdown("---")
    render_batal_pelantikan(kod_ppd, dfk[dfk["STAGE"].isin(["HANTAR", "LULUS"])] if not dfk.empty else dfk, key="pk_bp_surat")


# ====================================================================== dispatcher menu Lantik PK
def render_penyelia(kod_ppd, fly_cur):
    if fly_cur == "simpanan":
        render_simpanan(kod_ppd)
    elif fly_cur == "tempat":
        render_tempatkan(kod_ppd)
    elif fly_cur == "surat":
        render_surat(kod_ppd)
    else:
        render_cadangan(kod_ppd)


# ====================================================================== PAPARAN: PK ikut BILIK KEBAL
def render_pk_ikut_bk(kod_ppd, mod="hasil"):
    """mod: 'hasil' (Hasil Janaan), 'semak' (Semakan Lantikan), 'sah' (Sah Lantik - hanya yang ada no surat)."""
    judul = {"hasil": "🔐 Hasil Janaan - Penyelia Kawasan Ikut Bilik Kebal",
             "semak": "🔍 Semakan Lantikan - Penyelia Kawasan Ikut Bilik Kebal",
             "sah": "🏅 Sah Lantik - Penyelia Kawasan Ikut Bilik Kebal"}[mod]
    sub = {"hasil": "Senarai nama PK di bawah setiap bilik kebal.", "semak": "Pilih bilik kebal untuk semak nama PK dan pusat yang diawasi.",
           "sah": "PK yang sudah ada no surat lantikan."}[mod]
    _banner(f"{judul} - PPD {kod_ppd}", sub)
    _flash()
    df_bk = muat_bk(kod_ppd)
    dfk = muat_pk(kod_ppd, set(df_bk["KOD"]) if not df_bk.empty else None)
    stages = ("LULUS",) if mod == "sah" else STAGE_TEMPAT
    dfk = dfk[dfk["STAGE"].isin(stages)] if not dfk.empty else dfk
    if dfk.empty:
        st.info("Belum ada PK yang " + ("disahkan lantik." if mod == "sah" else "ditempatkan ke bilik kebal."))
        return
    nama_bk = dict(zip(df_bk["KOD"], df_bk["NAMA"])) if not df_bk.empty else {}
    kod_ada = sorted({k for k in dfk["BK"] if k})
    opts = {"SEMUA": f"Semua bilik kebal ({len(dfk)} PK)"}
    for k in kod_ada:
        opts[k] = f"{k} - {nama_bk.get(k, '')[:30]} ({int((dfk['BK'] == k).sum())} PK)"
    pilih = st.selectbox("🔐 Bilik Kebal", list(opts.keys()), format_func=lambda k: opts.get(k, k), key=f"pk_bk_papar_{mod}")
    view = dfk if pilih == "SEMUA" else dfk[dfk["BK"] == pilih]
    a, b, c = st.columns(3)
    a.metric("Bilik kebal", view["BK"].nunique())
    b.metric("Penyelia Kawasan", len(view))
    c.metric("Pusat diawasi", sum(len(l) for l in view["PUSAT"]))
    rows = []
    for _, r in view.sort_values(["BK", "NAMA"]).iterrows():
        rows.append({"BILIK KEBAL": r["BK"], "NAMA BILIK KEBAL": nama_bk.get(r["BK"], ""), "NAMA PK": r["NAMA"], "IC": r["IC"],
                     "SEKOLAH ASAL": r["NAMA_SEK"], "TELEFON": r["TELEFON"], "PUSAT DIAWASI": ", ".join(r["PUSAT"]),
                     "BIL PUSAT": len(r["PUSAT"]), "NO SURAT": r["NO_SURAT"] or "-", "STATUS": r["STATUS"]})
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    if mod == "semak" and pilih != "SEMUA":
        bawah = sorted({p for l in view["BAWAH"] for p in l})
        belum = [p for p in bawah if p not in {x for l in view["PUSAT"] for x in l}]
        if belum:
            st.warning(f"⚠️ Pusat di bawah {pilih} yang belum ada PK: {', '.join(belum)}")
        elif bawah:
            st.success(f"Semua {len(bawah)} pusat di bawah {pilih} sudah ada PK.")
    st.download_button("📥 Export (Excel)", core.to_excel(df), file_name=f"pk_ikut_bilik_kebal_{mod}_{kod_ppd}_{datetime.date.today()}.xlsx", key=f"pk_bk_dl_{mod}")
    if mod == "sah":
        render_pk_muat_turun(kod_ppd)
        render_batal_pelantikan(kod_ppd, view, key="pk_bp_sah")


# ====================================================================== PAPARAN: petugas lain ikut PUSAT
_ORDER = ("KETUA PENGAWAS", "TIMBALAN", "PENGAWAS PEPERIKSAAN")


def _susun_jaw(j):
    j = str(j).upper()
    if "TIMBALAN" in j:
        return 1
    if "KETUA" in j:
        return 0
    if "PENGAWAS" in j:
        return 2
    return 3


def render_ikut_pusat(kod_ppd, df_rows, mod="hasil"):
    """KP, TKP & petugas lain ikut pusat. df_rows = baris petugas (tanpa PK)."""
    judul = {"hasil": "👥 Hasil Janaan - KP, TKP & Petugas Lain Ikut Pusat", "sah": "🏅 Sah Lantik - Petugas Ikut Pusat"}[mod]
    _banner(f"{judul} - PPD {kod_ppd}", "Pilih pusat untuk lihat senarai nama petugas di pusat itu." if mod == "hasil"
            else "Petugas yang sudah ada no surat lantikan.")
    if df_rows is None or df_rows.empty:
        st.info("Belum ada petugas.")
        return
    peta = _peta_pusat(kod_ppd)
    rows = []
    for _, r in df_rows.iterrows():
        if is_pk(r):
            continue
        ns = _g(r, "no_surat", "NO_SURAT")
        if mod == "sah" and not ns:
            continue
        pusat = _g(r, "kod_pusat", "KOD_PUSAT", "kod_pusat_tugas", "KOD_PUSAT_TUGAS", "NO_PUSAT_TUGAS", "no_pusat_tugas").upper()
        rows.append({"PUSAT": pusat or "-", "NAMA PUSAT": (peta.get(pusat) or {}).get("nama", ""), "JAWATAN": jawatan_of(r) or "-",
                     "NAMA": _g(r, "NAMA_GURU", "nama_guru"), "IC": _g(r, "IC_GURU", "ic_guru"),
                     "SEKOLAH ASAL": _g(r, "NAMA_SEKOLAH_ASAL", "nama_sekolah_asal") or _g(r, "KOD_SEKOLAH_ASAL", "kod_sekolah_asal"),
                     "TELEFON": _g(r, "TELEFON_GURU", "telefon_guru"), "NO SURAT": ns or "-",
                     "STATUS": _g(r, "STATUS", "status"), "_o": _susun_jaw(jawatan_of(r))})
    if not rows:
        st.info("Tiada petugas" + (" yang ada no surat." if mod == "sah" else "."))
        return
    df = pd.DataFrame(rows)
    pusat_ada = sorted(set(df["PUSAT"]))
    opts = {"SEMUA": f"Semua pusat ({len(df)} petugas)"}
    for p in pusat_ada:
        n = (peta.get(p) or {}).get("nama", "")
        opts[p] = f"{p} - {n[:30]} ({int((df['PUSAT'] == p).sum())})"
    pilih = st.selectbox("📍 Pusat", list(opts.keys()), format_func=lambda k: opts.get(k, k), key=f"pusat_papar_{mod}")
    jawlist = sorted(set(df["JAWATAN"]), key=lambda x: (_susun_jaw(x), x))
    jaw = st.multiselect("Jawatan (kosong = semua)", jawlist, key=f"pusat_jaw_{mod}")
    view = df if pilih == "SEMUA" else df[df["PUSAT"] == pilih]
    if jaw:
        view = view[view["JAWATAN"].isin(jaw)]
    view = view.sort_values(["PUSAT", "_o", "NAMA"]).drop(columns="_o")
    a, b, c, d = st.columns(4)
    a.metric("Petugas", len(view))
    b.metric("Ketua Pengawas", int(view["JAWATAN"].str.contains("KETUA", na=False).sum() - view["JAWATAN"].str.contains("TIMBALAN", na=False).sum()))
    c.metric("Timbalan KP", int(view["JAWATAN"].str.contains("TIMBALAN", na=False).sum()))
    d.metric("Pusat", view["PUSAT"].nunique())
    st.dataframe(view, use_container_width=True, hide_index=True)
    st.download_button("📥 Export (Excel)", core.to_excel(view), file_name=f"petugas_ikut_pusat_{mod}_{kod_ppd}_{datetime.date.today()}.xlsx", key=f"pusat_dl_{mod}")


# ====================================================================== SAH LANTIK
def _data_baris(r):
    d = r.get("data") if hasattr(r, "get") else None
    if isinstance(d, dict):
        return dict(d)
    if isinstance(d, str) and d.strip().startswith("{"):
        try:
            return json.loads(d)
        except Exception:
            return {}
    return {}


def html_pk_dari_baris(r, kod_ppd=""):
    """HTML surat PK untuk SUP: guna surat yang SAMA seperti muat turun PPD (data.surat_html). Jika tiada, jana dengan templat JPN terkini."""
    d = _data_baris(r)
    h = _s(r.get("surat_html")) or _s(d.get("surat_html"))
    if h:
        return h
    try:
        import penyelia_surat as _ps
        kod_ppd = (kod_ppd or _g(r, "kod_ppd", "KOD_PPD")).upper()
        bk = (_g(d, "kod_bilik_kebal_explicit", "kod_bilik_kebal") or _g(r, "kod_bilik_kebal", "KOD_BILIK_KEBAL")).upper()
        pusat = _list(d.get("pusat_jagaan")) or _list(d.get("pusat_jagaan_str")) or _list(r.get("kod_pusat"))
        alamat = ""
        try:
            rb = supa.table("bilik_kebal_master").select("*").eq("kod_bilik_kebal", bk).limit(1).execute().data or []
            alamat = _g(rb[0], "alamat", "ALAMAT") if rb else ""
        except Exception:
            pass
        nama_bk = _ps.nama_bk_cari(kod_ppd, bk, "")
        sek = _g(r, "KOD_SEKOLAH_ASAL", "kod_sekolah_asal")
        t = _s(d.get("surat_tarikh")) or _s(r.get("surat_tarikh"))
        try:
            tarikh = pd.Timestamp(t).strftime("%d %B %Y") if t else datetime.date.today().strftime("%d %B %Y")
        except Exception:
            tarikh = datetime.date.today().strftime("%d %B %Y")
        html, _ = _ps.jana_html(core, nama=_g(r, "NAMA_GURU", "nama_guru"), ic=_g(r, "IC_GURU", "ic_guru"), sek_asal=sek,
                                nama_sek_asal=_g(r, "NAMA_SEKOLAH_ASAL", "nama_sekolah_asal") or sek,
                                telefon=_g(r, "TELEFON_GURU", "telefon_guru"), kod_bk=bk, nama_bk=nama_bk, alamat_bk=alamat,
                                pusat_jagaan=pusat, no_surat=_g(r, "no_surat", "NO_SURAT"), kod_ppd=kod_ppd,
                                ppd_name=PPD_MAP.get(kod_ppd, ""), tarikh=tarikh)
        return html or ""
    except Exception:
        return ""


def pdf_pk_dari_baris(r, kod_ppd=""):
    h = html_pk_dari_baris(r, kod_ppd)
    if not h:
        return None
    try:
        return core.html_to_pdf_bytes(h)
    except Exception:
        return None


def html_surat_sup(r, kod_ppd=""):
    """Surat PK untuk SUP = surat yang SAMA seperti muat turun PPD (data.surat_html; jana jika tiada).
    Jawatan lain: '' - SUP guna penjana yang sama seperti muat turun PPD tetapi dengan nama pusat diisi."""
    return html_pk_dari_baris(r, kod_ppd) if is_pk(r) else ""


def pdf_surat_sup(r, kod_ppd=""):
    h = html_surat_sup(r, kod_ppd)
    if not h:
        return None
    try:
        return core.html_to_pdf_bytes(h)
    except Exception:
        return None


def _html_pk_disimpan(raw, pid):
    """HTML surat PK yang disimpan semasa Hantar (data.surat_html), atau '' jika tiada."""
    row = _raw_row(raw, pid) if raw is not None and not raw.empty else None
    h = ""
    tarikh = ""
    if row is not None:
        d = _data_baris(row)
        h = _s(row.get("surat_html")) or _s(d.get("surat_html"))
        tarikh = _s(d.get("surat_tarikh")) or _s(row.get("surat_tarikh"))
    if not h:
        d = _data_db(pid)
        h = _s(d.get("surat_html"))
        tarikh = tarikh or _s(d.get("surat_tarikh"))
    return h, tarikh


def _jana_semula_pk(kod_ppd, rec, df_bk, raw, tarikh_iso):
    """Jana semula surat PK dengan no surat SEDIA ADA (templat JPN terkini). Pulang html."""
    try:
        t = pd.Timestamp(tarikh_iso) if tarikh_iso else pd.Timestamp.now()
    except Exception:
        t = pd.Timestamp.now()
    hasil = _jana_surat(kod_ppd, pd.DataFrame([rec]), df_bk, raw, "", 0, t, no_tetap=rec["NO_SURAT"])
    return hasil[0]["html"] if hasil else ""


def render_pk_muat_turun(kod_ppd):
    """Muat turun surat Penyelia Kawasan yang sudah dihantar (Sah Lantik > Muat Turun). Boleh jana semula."""
    st.markdown("---")
    st.markdown("### 🔐 Muat Turun Surat Penyelia Kawasan")
    df_bk = muat_bk(kod_ppd)
    raw = get_cadangan_df(kod_ppd=kod_ppd)
    dfk = muat_pk(kod_ppd, set(df_bk["KOD"]) if not df_bk.empty else None, df=raw)
    lulus = dfk[dfk["STAGE"] == "LULUS"].reset_index(drop=True) if not dfk.empty else dfk
    if lulus.empty:
        st.info("Belum ada surat Penyelia Kawasan yang dihantar.")
        return
    nama_bk = dict(zip(df_bk["KOD"], df_bk["NAMA"])) if not df_bk.empty else {}
    opts = {"SEMUA": f"Semua bilik kebal ({len(lulus)} PK)"}
    for k in sorted({x for x in lulus["BK"] if x}):
        opts[k] = f"{k} - {nama_bk.get(k, '')[:30]} ({int((lulus['BK'] == k).sum())} PK)"
    pilih = st.selectbox("🔐 Bilik Kebal", list(opts.keys()), format_func=lambda k: opts.get(k, k), key="pk_mt_bk")
    view = lulus if pilih == "SEMUA" else lulus[lulus["BK"] == pilih]
    dfx = pd.DataFrame([{"NO SURAT": r["NO_SURAT"], "NAMA": r["NAMA"], "IC": r["IC"], "SEKOLAH ASAL": r["NAMA_SEK"],
                         "BILIK KEBAL": r["BK"], "PUSAT": ", ".join(r["PUSAT"])} for _, r in view.iterrows()])
    st.dataframe(dfx, use_container_width=True, hide_index=True)
    st.download_button("📊 Muat Turun Senarai PK (Excel)", core.to_excel(dfx), file_name=f"Senarai_PK_{kod_ppd}_{datetime.date.today()}.xlsx", key="pk_mt_xlsx")
    baru = st.checkbox("♻️ Jana semula surat guna templat JPN terkini (no surat kekal sama)", value=False, key="pk_mt_baru",
                       help="Guna jika templat dikemas kini atau surat tersimpan tiada/rosak. No surat dan tarikh asal dikekalkan.")
    if st.button(f"📄 Sediakan {len(view)} Surat PK untuk Muat Turun", type="primary", use_container_width=True, key="pk_mt_btn"):
        out, gagal = [], []
        with st.spinner("Menyediakan surat..."):
            for _, rec in view.iterrows():
                h, tarikh = _html_pk_disimpan(raw, rec["id"])
                if baru or not h:
                    try:
                        h = _jana_semula_pk(kod_ppd, rec, df_bk, raw, tarikh) or h
                    except Exception as e:
                        gagal.append(f"{rec['NAMA']}: {str(e)[:80]}")
                if not h:
                    gagal.append(f"{rec['NAMA']}: tiada surat")
                    continue
                try:
                    pdf = core.html_to_pdf_bytes(h)
                except Exception:
                    pdf = None
                out.append({"nama": rec["NAMA"], "no_surat": rec["NO_SURAT"], "html": h, "pdf": pdf})
        st.session_state[f"pk_mt_{kod_ppd}"] = (out, gagal)
    sedia = st.session_state.get(f"pk_mt_{kod_ppd}")
    if sedia:
        out, gagal = sedia
        if gagal:
            st.warning("⚠️ " + "; ".join(gagal[:3]))
        if out:
            html_all = "\n<div style='page-break-after:always'></div>\n".join(h["html"] for h in out)
            c1, c2 = st.columns(2)
            c1.download_button("📥 Semua Surat PK (HTML)", html_all.encode("utf-8"), file_name=f"Surat_Penyelia_Kawasan_{kod_ppd}_{datetime.date.today()}.html",
                               mime="text/html", use_container_width=True, key="pk_mt_html")
            if all(h["pdf"] for h in out):
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for h in out:
                        safe = "".join(c if c.isalnum() else "_" for c in h["nama"])[:25]
                        zf.writestr(f"{h['no_surat'].replace('/', '_')}_{safe}.pdf", h["pdf"])
                c2.download_button("📥 ZIP PDF Individu", buf.getvalue(), file_name=f"Surat_PK_{kod_ppd}_{datetime.date.today()}.zip",
                                   mime="application/zip", use_container_width=True, key="pk_mt_zip")
            else:
                c2.caption("PDF tidak dapat dijana (enjin PDF tiada) - guna HTML.")


def render_sah_lantik(kod_ppd, fly_cur):
    if fly_cur == "pk":
        render_pk_ikut_bk(kod_ppd, mod="sah")
    else:
        import ppd_aliran as _al          # aliran berperingkat: hantar / muat turun / senarai
        _al.render_sah_lantik(kod_ppd, fly_cur)
        if fly_cur == "muat":
            render_pk_muat_turun(kod_ppd)


# ====================================================================== PLACEHOLDER SURAT (KETUA PENGAWAS dsb.)
def _peta_pk(kod_ppd):
    hit = _PK_MAP.get(kod_ppd)
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    out = {}
    try:
        dfk = muat_pk(kod_ppd)
        if not dfk.empty:
            for _, r in dfk[dfk["STAGE"].isin(STAGE_TEMPAT)].iterrows():
                for p in r["PUSAT"]:
                    out.setdefault(p, []).append(r.to_dict())
    except Exception:
        out = {}
    _PK_MAP[kod_ppd] = (time.time(), out)
    return out


def pk_placeholders(kod_ppd, pusat):
    """Placeholder PK yang bertanggungjawab ke atas `pusat` - untuk surat Ketua Pengawas / petugas lain."""
    kosong = {"NAMA_PK": "-", "TELEFON_PK": "-", "SEKOLAH_PK": "-", "BILIK_KEBAL_PK": "-"}
    p, k = _s(pusat).upper(), _s(kod_ppd).upper()
    if not p or not k:
        return kosong
    lst = _peta_pk(k).get(p)
    if not lst:
        return kosong
    j = lambda f: "; ".join(x for x in dict.fromkeys(_s(f(x)) for x in lst) if x) or "-"
    return {"NAMA_PK": j(lambda x: x["NAMA"]), "TELEFON_PK": j(lambda x: x["TELEFON"]),
            "SEKOLAH_PK": j(lambda x: x["NAMA_SEK"]), "BILIK_KEBAL_PK": j(lambda x: x["BK"])}
