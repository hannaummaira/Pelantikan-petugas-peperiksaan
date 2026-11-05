# -*- coding: utf-8 -*-
"""ppd_aliran.py - Aliran lantikan petugas PPD BERPERINGKAT (tidak boleh langkau) + Sah Lantik.

Peringkat (cadangan_sup.status):
  0 DIJANA               "DILANTIK PPD"                                    (selepas Jana / Manual / Zon - kod_pusat ada)
  1 HASIL DISETUJUI      "DILANTIK PPD - HASIL DISETUJUI"                  (butang Setuju di Hasil Janaan)  -> masuk Semakan
  2 SEMAKAN DISAHKAN     "DILANTIK PPD - SEMAKAN DISAHKAN"                 (butang Setuju di Semakan)       -> masuk Kelulusan
  3 KEPUTUSAN DISAHKAN   "DILANTIK PPD - KEPUTUSAN DISAHKAN"              (Kelulusan: Sah Keputusan)       -> masuk Janaan Surat
  4 SURAT DIJANA         "DILANTIK PPD - SURAT DIJANA, MENUNGGU HANTAR"    (Janaan Surat: no surat diberi)  -> masuk Sah Lantik
  5 DIHANTAR             "LULUS PPD - SURAT DIHANTAR KE SEKOLAH ASAL"      (butang Hantar di Sah Lantik)    -> SUP nampak

Semua status baharu mengandungi "DILANTIK" supaya tetap "terkunci" (tidak dijana semula / tidak jadi pool Jana).
Kolum no_surat HANYA diisi apabila surat dihantar; no surat yang dijana disimpan dahulu dalam data.SURAT_NO_JANA
- jadi SUP tidak nampak surat sebelum PPD tekan Hantar.
Setiap peringkat hanya memproses rekod peringkat sebelumnya. Pusat mesti cukup kuota (kelas + 9, ada 1 KP & 1 TKP)
sebelum dibenarkan maju (PPD boleh beri pengecualian secara sedar).
"""
import datetime
import io
import json
import re
import zlib
import no_surat as nsr
import zipfile

import pandas as pd
import streamlit as st

import spm_core as core
from kuota_pusat import kuota_pusat, no_pusat as _no_pusat
from lengkap_petugas import lengkapkan

ST_JANA = "DILANTIK PPD"
ST_HASIL = "DILANTIK PPD - HASIL DISETUJUI"
ST_SEMAK = "DILANTIK PPD - SEMAKAN DISAHKAN"
ST_KEPUTUSAN = "DILANTIK PPD - KEPUTUSAN DISAHKAN"
ST_SURAT = "DILANTIK PPD - SURAT DIJANA, MENUNGGU HANTAR"
ST_HANTAR = "LULUS PPD - SURAT DIHANTAR KE SEKOLAH ASAL"
STATUS_PERINGKAT = [ST_JANA, ST_HASIL, ST_SEMAK, ST_KEPUTUSAN, ST_SURAT, ST_HANTAR]
LABEL = ["Dijana", "Hasil Disetujui", "Semakan Disahkan", "Keputusan Disahkan", "Surat Dijana", "Dihantar ke Sekolah"]
MENU_LABEL = ["Jana", "Hasil Janaan", "Semakan Lantikan", "Kelulusan", "Janaan Surat", "Sah Lantik"]

_BELUM_LANTIK = ("HANTAR KE PPD", "DICADANGKAN", "TERPILIH", "SIMPANAN", "TOLAK", "BARU")


# ============================================================ pembantu asas
def _s(v):
    x = "" if v is None else str(v).strip()
    return "" if x.lower() in ("nan", "none", "null", "nat") else x


def _data(r):
    d = r.get("data") if hasattr(r, "get") else None
    if isinstance(d, dict):
        return dict(d)
    if isinstance(d, str) and d.strip().startswith("{"):
        try:
            return json.loads(d)
        except Exception:
            return {}
    return {}


def _g(r, d, *keys):
    for k in keys:
        for src in (r, d):
            try:
                v = _s(src.get(k))
            except Exception:
                v = ""
            if v:
                return v
    return ""


def _pyid(x):
    try:
        return int(float(str(x)))
    except Exception:
        return x


def idk(x):
    """Kunci id seragam (rentetan) untuk perbandingan."""
    return str(_pyid(x))


def _flash(kind, msg):
    st.session_state["al_flash"] = (kind, msg)


def _show_flash():
    f = st.session_state.pop("al_flash", None)
    if f:
        {"success": st.success, "error": st.error, "warning": st.warning}.get(f[0], st.info)(f[1])


def _clear():
    try:
        st.cache_data.clear()
    except Exception:
        pass
    try:
        core.get_cadangan_df.clear()
    except Exception:
        pass


def _susun_jaw(j):
    j = str(j).upper()
    if "TIMBALAN" in j:
        return 1
    if "KETUA" in j:
        return 0
    if "PENGAWAS" in j:
        return 2
    return 3


def _is_kp(j):
    j = str(j).upper()
    return "KETUA" in j and "TIMBALAN" not in j and "HOSPITAL" not in j


def _is_tkp(j):
    j = str(j).upper()
    return "TIMBALAN" in j and "KETUA" in j and "HOSPITAL" not in j


# ============================================================ data & peringkat
def peringkat(status, pusat, no_col):
    """Pulang 0..5 atau -1 (belum dilantik)."""
    st_ = str(status or "").upper()
    placed = bool(pusat) and not any(x in st_ for x in _BELUM_LANTIK)
    if "DIHANTAR KE SEKOLAH ASAL" in st_ or "LULUS" in st_ or "SURAT_SAMPAI" in st_ or (placed and no_col):
        return 5
    if "SURAT DIJANA" in st_:
        return 4
    if "KEPUTUSAN DISAHKAN" in st_:
        return 3
    if "SEMAKAN DISAHKAN" in st_:
        return 2
    if "HASIL DISETUJUI" in st_:
        return 1
    if placed:
        return 0
    return -1


def muat(kod_ppd):
    """Bacaan segar cadangan_sup PPD ini (tanpa Penyelia Kawasan). Pulang (raw_df, rows)."""
    try:
        raw = pd.DataFrame(core.supa.table("cadangan_sup").select("*").eq("kod_ppd", kod_ppd).limit(5000).execute().data or [])
    except Exception:
        raw = pd.DataFrame()
    if raw.empty:
        return raw, []
    import ppd_penyelia as _pp
    dnp = _pp.tanpa_pk(raw)
    rows = []
    if dnp is None or dnp.empty:
        return raw, rows
    for _, r0 in dnp.iterrows():
        rid = r0.get("id")
        if rid is None or _s(rid) == "":
            continue
        r = lengkapkan(r0, kod_ppd)
        d = _data(r)
        status = _g(r, d, "status", "STATUS")
        pusat = _g(r, d, "kod_pusat", "KOD_PUSAT", "kod_pusat_tugas", "NO_PUSAT_TUGAS").upper()
        no_col = _s(r.get("no_surat") or r.get("NO_SURAT"))
        rk = peringkat(status, pusat, no_col)
        rows.append({
            "id": _pyid(rid), "nama": _g(r, d, "NAMA_GURU", "nama_guru"), "ic": _g(r, d, "IC_GURU", "ic_guru"),
            "jaw": _g(r, d, "JAWATAN_CADANGAN", "jawatan_cadangan", "JAWATAN"),
            "sek": _g(r, d, "KOD_SEKOLAH_ASAL", "kod_sekolah_asal", "KOD_SEKOLAH", "kod_sekolah").upper(),
            "nama_sek": _g(r, d, "NAMA_SEKOLAH_ASAL", "nama_sekolah_asal"), "tel": _g(r, d, "TELEFON_GURU", "telefon_guru"),
            "pusat": pusat if rk >= 0 else "", "status": status, "no_col": no_col,
            "no_jana": _s(d.get("SURAT_NO_JANA")), "tarikh_jana": _s(d.get("SURAT_TARIKH_JANA")),
            "tarikh_hantar": _s(d.get("SURAT_TARIKH_HANTAR")),
            "rank": rk, "data": d, "data_str": isinstance(r0.get("data"), str)})
    return raw, rows


def no_surat_rek(rec):
    return rec["no_col"] or rec["no_jana"]


def pusat_info(kod_ppd):
    out = {}
    try:
        df = core.get_pusat_df()
    except Exception:
        df = None
    if df is None or len(df) == 0:
        return out
    for _, r in df.iterrows():
        no = _no_pusat(r)
        if not no or not no.startswith(str(kod_ppd).upper()):
            continue
        d = _data(r)
        q = kuota_pusat(r)
        out[no] = {"nama": _s(r.get("nama_pusat")) or _s(d.get("NAMA_PUSAT")) or "", "perlu": q["petugas"],
                   "kelas": q["kelas"], "calon": q["calon"]}
    return out


def ringkas_pusat(rows, info):
    """{pusat: {ada, kp, tkp, perlu, nama, lengkap, kurang, bil:[bilangan ikut peringkat]}}"""
    out = {}
    for r in rows:
        if r["rank"] < 0 or not r["pusat"]:
            continue
        e = out.setdefault(r["pusat"], {"ada": 0, "kp": 0, "tkp": 0, "bil": [0] * 6})
        e["ada"] += 1
        e["kp"] += 1 if _is_kp(r["jaw"]) else 0
        e["tkp"] += 1 if _is_tkp(r["jaw"]) else 0
        e["bil"][r["rank"]] += 1
    for p, e in out.items():
        i = info.get(p, {})
        e["nama"] = i.get("nama", "")
        e["perlu"] = int(i.get("perlu", 0) or 0)
        e["kurang"] = max(0, e["perlu"] - e["ada"])
        e["lengkap"] = e["perlu"] > 0 and e["ada"] >= e["perlu"] and e["kp"] >= 1 and e["tkp"] >= 1
    return out


def sebab_tak_lengkap(e):
    s = []
    if e["perlu"] <= 0:
        s.append("kuota pusat belum ditetapkan")
    if e["ada"] < e["perlu"]:
        s.append(f"kurang {e['perlu'] - e['ada']} petugas")
    if e["kp"] < 1:
        s.append("tiada Ketua Pengawas")
    if e["tkp"] < 1:
        s.append("tiada Timbalan KP")
    return ", ".join(s)


# ============================================================ paparan aliran
def bar(rows, aktif):
    """Jalur peringkat + bilangan petugas di setiap peringkat. aktif = indeks peringkat menu semasa (1..5)."""
    cnt = [sum(1 for r in rows if r["rank"] == i) for i in range(6)]
    pil = []
    for i in range(6):
        cur = (i == aktif)
        bg, fg, bd = ("#0d47a1", "#fff", "#0d47a1") if cur else ("#e3f2fd", "#0d47a1", "#90caf9")
        nama = LABEL[i]
        pil.append(f'<div style="flex:1;min-width:120px;background:{bg};color:{fg};border:1px solid {bd};border-radius:10px;padding:8px 10px;text-align:center">'
                   f'<div style="font-size:11px;opacity:.85">{i + 1}. {nama}</div><div style="font-size:20px;font-weight:800">{cnt[i]}</div></div>')
    st.markdown('<div style="display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 12px 0">' + "".join(pil) + "</div>", unsafe_allow_html=True)


def gate(rows, rank_min, menu_ini, langkah_dulu):
    """True jika ada rekod pada peringkat >= rank_min. Jika tidak, paparkan sekatan dan pulang False."""
    if any(r["rank"] >= rank_min for r in rows):
        return True
    menunggu = sum(1 for r in rows if r["rank"] == rank_min - 1)
    st.error(f"🔒 **{menu_ini}** belum boleh digunakan - tiada petugas yang telah melepasi langkah **{langkah_dulu}**.")
    if menunggu:
        st.info(f"Ada **{menunggu}** petugas menunggu di langkah {langkah_dulu}. Sila selesaikan di sana dahulu.")
    else:
        st.info("Aliran: Cadangan SUP → Jana → Hasil Janaan (Setuju) → Semakan Lantikan (Setuju) → Kelulusan (Sah Keputusan) → Janaan Surat → Sah Lantik (Hantar ke Sekolah).")
    return False


# ============================================================ kemas kini DB
def _update_status(ids, status, kosongkan_no_surat=False):
    ok = 0
    ids = [_pyid(i) for i in ids]
    for i in range(0, len(ids), 100):
        b = ids[i:i + 100]
        payloads = [{"status": status, "no_surat": None}] if kosongkan_no_surat else []
        payloads.append({"status": status})
        done = False
        for p in payloads:
            try:
                core.supa.table("cadangan_sup").update(p).in_("id", b).execute()
                done = True
                break
            except Exception:
                continue
        if done:
            ok += len(b)
    return ok


def _update_rekod(rec, status, data_baru=None, no_surat=None, set_no_surat=False):
    """Kemas kini satu rekod: status + (pilihan) data & no_surat."""
    d = dict(rec["data"])
    if data_baru:
        d.update(data_baru)
    dval = json.dumps(d, ensure_ascii=False) if rec["data_str"] else d
    base = {"status": status}
    if set_no_surat:
        base["no_surat"] = no_surat
    tries = []
    if data_baru is not None:
        tries.append({**base, "data": dval})
    tries.append(base)
    tries.append({"status": status})
    for p in tries:
        try:
            core.supa.table("cadangan_sup").update(p).eq("id", rec["id"]).execute()
            return True
        except Exception:
            continue
    return False


# ============================================================ panel maju antara peringkat
def panel_lanjut(kod_ppd, rows, info, dari, kunci, tajuk, label_btn, satu_pusat=False, boleh_balik=True):
    """Majukan petugas dari peringkat `dari` ke `dari+1` ikut pusat. Pusat mesti cukup kuota (pengecualian dibenarkan)."""
    ke = dari + 1
    rp = ringkas_pusat(rows, info)
    menunggu = {p: e for p, e in rp.items() if e["bil"][dari] > 0}
    st.markdown(f"#### {tajuk}")
    if not menunggu:
        st.success(f"✅ Tiada petugas menunggu di peringkat **{LABEL[dari]}**.")
    else:
        tbl = []
        for p, e in sorted(menunggu.items()):
            tbl.append({"PUSAT": p, "NAMA PUSAT": e["nama"][:35], "PERLU": e["perlu"], "ADA": e["ada"], "KP": e["kp"], "TKP": e["tkp"],
                        f"MENUNGGU ({LABEL[dari]})": e["bil"][dari],
                        "STATUS KUOTA": "✅ Lengkap" if e["lengkap"] else "⏳ " + sebab_tak_lengkap(e)})
        st.dataframe(pd.DataFrame(tbl), use_container_width=True, hide_index=True, height=min(380, 40 + 35 * len(tbl)))
        lengkap = [p for p, e in menunggu.items() if e["lengkap"]]
        semua = sorted(menunggu.keys())
        fmt = lambda p: f"{p} - {menunggu[p]['nama'][:28]} ({menunggu[p]['bil'][dari]} petugas){'' if menunggu[p]['lengkap'] else ' ⏳'}"
        if satu_pusat:
            pilih = st.selectbox("Pilih pusat", semua, format_func=fmt, key=f"al_p1_{kunci}_{kod_ppd}")
            pilih = [pilih] if pilih else []
        else:
            pilih = st.multiselect("Pilih pusat (lalai: semua pusat yang cukup kuota)", semua, default=lengkap, format_func=fmt,
                                   key=f"al_pm_{kunci}_{kod_ppd}")
        tak = [p for p in pilih if not menunggu[p]["lengkap"]]
        izin = False
        if tak:
            st.warning(f"⏳ {len(tak)} pusat dipilih belum cukup kuota: " + "; ".join(f"{p} ({sebab_tak_lengkap(menunggu[p])})" for p in tak[:6]))
            izin = st.checkbox("Teruskan juga pusat yang belum cukup kuota (pengecualian PPD)", key=f"al_izin_{kunci}_{kod_ppd}")
        bil = sum(menunggu[p]["bil"][dari] for p in pilih)
        boleh = bool(pilih) and (not tak or izin)
        if st.button(f"{label_btn} ({bil} petugas, {len(pilih)} pusat)", type="primary", disabled=not boleh, key=f"al_btn_{kunci}_{kod_ppd}"):
            ids = [r["id"] for r in rows if r["rank"] == dari and r["pusat"] in set(pilih)]
            ok = _update_status(ids, STATUS_PERINGKAT[ke])
            _clear()
            if ok == len(ids):
                _flash("success", f"✅ {ok} petugas di {len(pilih)} pusat dimajukan ke peringkat «{LABEL[ke]}» → menu {MENU_LABEL[ke]}.")
            else:
                _flash("warning", f"⚠️ {ok}/{len(ids)} petugas berjaya dimajukan. Sila semak semula.")
            st.rerun()
    if boleh_balik and dari + 1 <= 3:
        with st.expander(f"↩️ Tarik balik dari «{LABEL[ke]}» ke «{LABEL[dari]}»", expanded=False):
            tb = {}
            for p, e in rp.items():
                if e["bil"][ke] > 0:
                    tb[p] = e["bil"][ke]
            if not tb:
                st.caption("Tiada petugas di peringkat itu.")
            else:
                pil = st.multiselect("Pusat untuk ditarik balik", sorted(tb), format_func=lambda p: f"{p} ({tb[p]})", key=f"al_tb_{kunci}_{kod_ppd}")
                if st.button("↩️ Tarik balik pusat terpilih", disabled=not pil, key=f"al_tbb_{kunci}_{kod_ppd}"):
                    ids = [r["id"] for r in rows if r["rank"] == ke and r["pusat"] in set(pil)]
                    ok = _update_status(ids, STATUS_PERINGKAT[dari])
                    _clear()
                    _flash("success", f"↩️ {ok} petugas ditarik balik ke «{LABEL[dari]}».")
                    st.rerun()


def render_langkah_hasil(kod_ppd):
    """Dipanggil di atas menu Hasil Janaan."""
    _show_flash()
    _, rows = muat(kod_ppd)
    info = pusat_info(kod_ppd)
    bar(rows, 0)
    with st.expander("✅ Setuju Hasil Janaan → hantar ke Semakan Lantikan", expanded=any(r["rank"] == 0 for r in rows)):
        if st.session_state.get("jana_all_result") or st.session_state.get("jana_pusat_result"):
            st.warning("Ada janaan yang belum disimpan ke pangkalan data (berstatus BELUM DISIMPAN) - ia tidak dikira di sini.")
        panel_lanjut(kod_ppd, rows, info, 0, "hasil", "Setuju dengan hasil janaan",
                     "✅ Setuju & Hantar ke Semakan", satu_pusat=False)


def render_langkah_semakan(kod_ppd, rows=None):
    """Dipanggil dalam menu Semakan Lantikan (selepas gate)."""
    _show_flash()
    if rows is None:
        _, rows = muat(kod_ppd)
    info = pusat_info(kod_ppd)
    bar(rows, 1)
    with st.expander("✅ Setuju Semakan → hantar untuk Keputusan (Kelulusan)", expanded=any(r["rank"] == 1 for r in rows)):
        panel_lanjut(kod_ppd, rows, info, 1, "semak", "Setuju dengan semakan lantikan",
                     "✅ Setuju & Hantar untuk Keputusan", satu_pusat=False)


# ============================================================ KELULUSAN
def render_kelulusan(kod_ppd, fly_cur):
    st.header(f"✅ Kelulusan - PPD {kod_ppd} - {core.PPD_MAP.get(kod_ppd, '')}")
    _show_flash()
    _, rows = muat(kod_ppd)
    bar(rows, 2)
    if not gate(rows, 2, "Kelulusan", "Semakan Lantikan (Setuju & Hantar untuk Keputusan)"):
        return
    info = pusat_info(kod_ppd)
    st.caption("Sahkan keputusan lantikan. Hanya petugas yang telah disahkan semakannya dipaparkan. "
               "Selepas Sah Keputusan, petugas masuk ke Janaan Surat.")
    panel_lanjut(kod_ppd, rows, info, 2, "kel", "Sah Keputusan Lantikan",
                 "✅ Sah Keputusan", satu_pusat=(fly_cur == "pusat"))


# ============================================================ JANAAN SURAT
def _prefix_lalai(kod_ppd, raw, rows):
    """Prefix no surat: ambil daripada no surat terkini (buang /NNNN di hujung) atau lalai."""
    best = ""
    for r in rows:
        n = no_surat_rek(r)
        if n and r["rank"] >= 4 and "/" in n:
            best = n
    if best:
        return re.sub(r"/\s*\d+\s*$", "", best)
    return f"JPN.SPP.HHJH/PPD.{kod_ppd}"


def _max_no(raw):
    mx = 0
    if raw is None or raw.empty:
        return 0
    for _, r in raw.iterrows():
        d = _data(r)
        for n in (_s(r.get("no_surat")), _s(d.get("SURAT_NO_JANA"))):
            if not n:
                continue
            m = re.findall(r"(\d+)", n)
            if m:
                try:
                    mx = max(mx, int(m[-1]))
                except Exception:
                    pass
    return mx


def _pilih_skop(rows_src, info, kunci, mod=None, label_semua="Keseluruhan"):
    """Pilih skop: Keseluruhan / Ikut Pusat / Ikut Jawatan / Ikut Sekolah Asal. Pulang (rows_terpilih, label)."""
    opsyen = ["Keseluruhan", "Ikut Pusat", "Ikut Jawatan", "Ikut Sekolah Asal"]
    idx = {"keseluruhan": 0, "pusat": 1, "jawatan": 2, "sekolah": 3}.get(mod or "", 0)
    pil = st.radio("Skop", opsyen, index=idx, horizontal=True, key=f"al_skop_{kunci}")
    out, label = rows_src, label_semua
    if pil == "Ikut Pusat":
        ada = sorted({r["pusat"] for r in rows_src})
        sel = st.multiselect("Pusat", ada, format_func=lambda p: f"{p} - {info.get(p, {}).get('nama', '')[:30]} ({sum(1 for r in rows_src if r['pusat'] == p)})",
                             key=f"al_sp_{kunci}")
        out = [r for r in rows_src if r["pusat"] in set(sel)]
        label = "Pusat " + ", ".join(sel[:3]) + ("..." if len(sel) > 3 else "") if sel else "Pusat (belum pilih)"
    elif pil == "Ikut Jawatan":
        ada = sorted({r["jaw"] or "-" for r in rows_src}, key=lambda x: (_susun_jaw(x), x))
        sel = st.multiselect("Jawatan", ada, format_func=lambda j: f"{j} ({sum(1 for r in rows_src if (r['jaw'] or '-') == j)})", key=f"al_sj_{kunci}")
        out = [r for r in rows_src if (r["jaw"] or "-") in set(sel)]
        label = "Jawatan " + ", ".join(sel[:2]) if sel else "Jawatan (belum pilih)"
    elif pil == "Ikut Sekolah Asal":
        nm = {r["sek"]: r["nama_sek"] for r in rows_src}
        ada = sorted({r["sek"] for r in rows_src})
        sel = st.multiselect("Sekolah asal", ada, format_func=lambda k: f"{k} - {nm.get(k, '')[:30]} ({sum(1 for r in rows_src if r['sek'] == k)})",
                             key=f"al_ss_{kunci}")
        out = [r for r in rows_src if r["sek"] in set(sel)]
        label = "Sekolah " + ", ".join(sel[:3]) if sel else "Sekolah (belum pilih)"
    return out, label


def _susun(rows):
    return sorted(rows, key=lambda r: (r["pusat"], _susun_jaw(r["jaw"]), r["nama"]))


def render_jana_surat(kod_ppd, fly_cur):
    st.header(f"📄 Janaan Surat Lantikan - PPD {kod_ppd} - {core.PPD_MAP.get(kod_ppd, '')}")
    _show_flash()
    raw, rows = muat(kod_ppd)
    bar(rows, 3)
    if not gate(rows, 3, "Janaan Surat", "Kelulusan (Sah Keputusan)"):
        return
    info = pusat_info(kod_ppd)
    menunggu = [r for r in rows if r["rank"] == 3]
    sudah = [r for r in rows if r["rank"] >= 4]
    c1, c2, c3 = st.columns(3)
    c1.metric("Menunggu surat dijana", len(menunggu))
    c2.metric("Surat dijana (di Sah Lantik)", sum(1 for r in rows if r["rank"] == 4))
    c3.metric("Sudah dihantar ke sekolah", sum(1 for r in rows if r["rank"] == 5))
    if not menunggu:
        st.success("✅ Semua petugas yang telah disahkan sudah dijana suratnya. Pergi ke **Sah Lantik** untuk muat turun / hantar ke sekolah.")
        return

    st.markdown("### 🔐 No Surat")
    a, b, c = st.columns([2, 1, 1])
    pref = a.text_input("No Rujukan Fail", value=st.session_state.get(f"al_ruj_{kod_ppd}") or nsr.ruj_terkini(raw), key=f"al_ruj_in_{kod_ppd}",
                        help="Format: <no rujukan> (1) hingga (100); selepas itu <no rujukan> JLD 2 (1) dan seterusnya. Setiap PPD mempunyai turutan sendiri.")
    mx = nsr.max_no(raw, pref)
    mula = b.number_input("No bermula (turutan)", min_value=1, value=int(mx + 1), step=1, key=f"al_mula_{kod_ppd}_{mx}_{zlib.crc32(pref.encode())}")
    tarikh = c.date_input("Tarikh surat", value=datetime.date.today(), key=f"al_tarikh_{kod_ppd}")
    st.session_state[f"al_ruj_{kod_ppd}"] = pref
    st.caption(f"Turutan terakhir direkod untuk PPD {kod_ppd}: {mx if mx else '-'} | Contoh: {nsr.format_no(pref, int(mula))}")

    mod = {"keseluruhan": "keseluruhan", "pusat": "pusat", "sekolah": "sekolah"}.get(fly_cur or "", "keseluruhan")
    terpilih, label = _pilih_skop(menunggu, info, "js", mod)
    terpilih = _susun(terpilih)
    if not terpilih:
        st.info("Pilih skop / pusat / sekolah untuk dijana.")
        return
    pre = []
    no = int(mula)
    for r in terpilih:
        pre.append({"NO SURAT": nsr.format_no(pref, no), "NAMA": r["nama"], "IC": r["ic"], "JAWATAN": r["jaw"], "PUSAT": r["pusat"],
                    "SEKOLAH ASAL": r["nama_sek"] or r["sek"]})
        no += 1
    st.dataframe(pd.DataFrame(pre), use_container_width=True, hide_index=True, height=min(380, 40 + 35 * len(pre)))
    st.caption("Surat yang dijana TIDAK dihantar kepada sekolah. Ia masuk ke menu **Sah Lantik** untuk muat turun dan penghantaran.")
    if st.button(f"📄 Jana {len(terpilih)} Surat ({label})", type="primary", key=f"al_jana_{kod_ppd}"):
        bar_p = st.progress(0)
        ok, gagal = 0, []
        for i, (r, p) in enumerate(zip(terpilih, pre)):
            good = _update_rekod(r, ST_SURAT, data_baru={"SURAT_NO_JANA": p["NO SURAT"], "SURAT_TARIKH_JANA": str(tarikh), "SURAT_TARIKH_SURAT": str(tarikh)})
            if good:
                ok += 1
            else:
                gagal.append(r["nama"])
            bar_p.progress((i + 1) / len(terpilih))
        _clear()
        if gagal:
            _flash("warning", f"⚠️ {ok} surat dijana; gagal: " + ", ".join(gagal[:5]))
        else:
            _flash("success", f"✅ {ok} surat dijana dan masuk ke Sah Lantik. No surat {pre[0]['NO SURAT']} hingga {pre[-1]['NO SURAT']}.")
        st.rerun()


# ============================================================ SAH LANTIK
def _surat_item(r, info, kod_ppd):
    return {"nama": r["nama"], "ic": r["ic"], "jawatan": r["jaw"], "sekolah_asal": r["sek"], "nama_sekolah_asal": r["nama_sek"] or r["sek"],
            "pusat": r["pusat"], "nama_pusat": info.get(r["pusat"], {}).get("nama", ""), "no_surat": no_surat_rek(r)}


def _hantar(rows_pilih, info, kod_ppd, tarikh):
    ok, gagal = 0, []
    pbar = st.progress(0)
    ppd_name = core.PPD_MAP.get(kod_ppd, "")
    t_str = tarikh.strftime("%d %B %Y")
    for i, r in enumerate(rows_pilih):
        no = no_surat_rek(r)
        it = _surat_item(r, info, kod_ppd)
        html = ""
        try:
            html = core.generate_surat_html(it["nama"], it["ic"], it["jawatan"], it["sekolah_asal"], it["nama_sekolah_asal"], it["pusat"],
                                            it["nama_pusat"], no, kod_ppd, ppd_name, t_str) or ""
        except Exception:
            html = ""
        dn = {"SURAT_DIHANTAR_KE_SEKOLAH_ASAL": True, "SURAT_TARIKH_HANTAR": str(datetime.date.today()), "surat_no": no, "surat_tarikh": str(tarikh)}
        if html:
            dn["surat_html"] = html
        if _update_rekod(r, ST_HANTAR, data_baru=dn, no_surat=no, set_no_surat=True):
            ok += 1
        else:
            gagal.append(r["nama"])
        pbar.progress((i + 1) / max(1, len(rows_pilih)))
    return ok, gagal


def _muat_pdf(items, kod_ppd, bahagian=150):
    out = []
    ppd_name = core.PPD_MAP.get(kod_ppd, "")
    for i in range(0, len(items), bahagian):
        b = items[i:i + bahagian]
        pdf = core.generate_surat_kolektif_pdf_bytes_JPN(b, kod_ppd, ppd_name, "SURAT LANTIKAN")
        if pdf:
            out.append((f"bahagian_{i // bahagian + 1}_({i + 1}-{i + len(b)})", pdf))
    return out


def _muat_zip(items, kod_ppd, bahagian=200):
    out = []
    ppd_name = core.PPD_MAP.get(kod_ppd, "")
    for i in range(0, len(items), bahagian):
        b = items[i:i + bahagian]
        z = core.create_zip_pukal_dari_JPN(b, kod_ppd, ppd_name)
        if z:
            out.append((f"bahagian_{i // bahagian + 1}_({i + 1}-{i + len(b)})", z))
    return out


def _jadual(rows, info):
    out = []
    for r in rows:
        out.append({"PUSAT": r["pusat"], "NAMA PUSAT": info.get(r["pusat"], {}).get("nama", ""), "JAWATAN": r["jaw"], "NAMA": r["nama"], "IC": r["ic"],
                    "SEKOLAH ASAL": r["nama_sek"] or r["sek"], "KOD SEKOLAH": r["sek"], "NO TELEFON": r["tel"], "NO SURAT": no_surat_rek(r),
                    "STATUS": "✅ Dihantar ke sekolah" if r["rank"] == 5 else "⏳ Menunggu hantar"})
    return pd.DataFrame(out)


def render_sah_lantik(kod_ppd, fly_cur):
    fly_cur = fly_cur or "hantar"
    st.header(f"🏅 Sah Lantik - PPD {kod_ppd} - {core.PPD_MAP.get(kod_ppd, '')}")
    _show_flash()
    raw, rows = muat(kod_ppd)
    bar(rows, 4)
    if not gate(rows, 4, "Sah Lantik", "Janaan Surat"):
        return
    info = pusat_info(kod_ppd)
    surat = _susun([r for r in rows if r["rank"] >= 4])
    menunggu = [r for r in surat if r["rank"] == 4]
    dihantar = [r for r in surat if r["rank"] == 5]
    c1, c2, c3 = st.columns(3)
    c1.metric("Surat dijana", len(surat))
    c2.metric("⏳ Menunggu hantar", len(menunggu))
    c3.metric("✅ Sudah dihantar", len(dihantar))

    if fly_cur == "senarai":
        st.markdown("### 👥 Senarai Petugas Disahkan")
        df = _jadual(surat, info)
        f = st.radio("Papar", ["Semua", "Menunggu hantar", "Sudah dihantar"], horizontal=True, key="al_senarai_f")
        if f == "Menunggu hantar":
            df = df[df["STATUS"].str.contains("Menunggu")]
        elif f == "Sudah dihantar":
            df = df[df["STATUS"].str.contains("Dihantar")]
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("📥 Export Senarai (Excel)", core.to_excel(df), file_name=f"sah_lantik_{kod_ppd}_{datetime.date.today()}.xlsx", key="al_dl_senarai")
        return

    if fly_cur == "muat":
        st.markdown("### 📥 Muat Turun Surat & Senarai")
        st.caption("Semua muat turun dikumpul di sini: ikut jawatan, ikut pusat atau keseluruhan. Surat belum dihantar & yang sudah dihantar boleh dimuat turun.")
        sts = st.radio("Status penghantaran", ["Semua", "Menunggu hantar", "Sudah dihantar"], horizontal=True, key="al_muat_st")
        src = surat if sts == "Semua" else (menunggu if sts == "Menunggu hantar" else dihantar)
        terpilih, label = _pilih_skop(src, info, "mt")
        terpilih = _susun(terpilih)
        if not terpilih:
            st.info("Tiada surat dalam pilihan ini.")
            return
        st.metric("Surat dipilih", len(terpilih))
        df = _jadual(terpilih, info)
        st.dataframe(df, use_container_width=True, hide_index=True, height=min(340, 40 + 35 * len(df)))
        sig = "|".join(idk(r["id"]) for r in terpilih)
        st.download_button("📊 Muat Turun Senarai (Excel)", core.to_excel(df), file_name=f"senarai_surat_{kod_ppd}_{datetime.date.today()}.xlsx", key="al_dl_xl")
        items = [_surat_item(r, info, kod_ppd) for r in terpilih]
        b1, b2 = st.columns(2)
        with b1:
            if st.button(f"📄 Jana PDF Kolektif ({len(items)} surat)", key="al_gen_pdf"):
                with st.spinner("Menjana PDF kolektif..."):
                    st.session_state["al_pdf"] = (sig, _muat_pdf(items, kod_ppd))
        with b2:
            if st.button(f"📦 Jana ZIP PDF Individu ({len(items)} surat)", key="al_gen_zip"):
                with st.spinner("Menjana ZIP surat individu..."):
                    st.session_state["al_zip"] = (sig, _muat_zip(items, kod_ppd))
        tag = re.sub(r"[^A-Za-z0-9]+", "_", label)[:30]
        pdf = st.session_state.get("al_pdf")
        if pdf and pdf[0] == sig:
            if not pdf[1]:
                st.error("PDF tidak dapat dijana. Sila semak Semakan Sistem Surat di Janaan Surat.")
            for n, bts in pdf[1]:
                st.download_button(f"📥 PDF Kolektif {n}", bts, file_name=f"Surat_Kolektif_{kod_ppd}_{tag}_{n}.pdf", mime="application/pdf", key=f"al_dlp_{n}")
        z = st.session_state.get("al_zip")
        if z and z[0] == sig:
            if not z[1]:
                st.error("ZIP tidak dapat dijana. Sila semak Semakan Sistem Surat di Janaan Surat.")
            for n, bts in z[1]:
                st.download_button(f"📦 ZIP Individu {n}", bts, file_name=f"Surat_Individu_{kod_ppd}_{tag}_{n}.zip", mime="application/zip", key=f"al_dlz_{n}")
        return

    # ----- hantar (lalai)
    st.markdown("### 📤 Hantar Surat ke Sekolah Asal")
    st.caption("Surat hanya sampai kepada SUP (sekolah asal petugas) selepas anda tekan Hantar. Tidak perlu muat turun dahulu.")
    if not menunggu:
        st.success("✅ Semua surat yang dijana sudah dihantar ke sekolah asal.")
    else:
        terpilih, label = _pilih_skop(menunggu, info, "ht")
        terpilih = _susun(terpilih)
        if terpilih:
            df = _jadual(terpilih, info)
            st.dataframe(df, use_container_width=True, hide_index=True, height=min(340, 40 + 35 * len(df)))
            sek = len({r["sek"] for r in terpilih})
            st.info(f"{len(terpilih)} surat akan dihantar kepada {sek} sekolah asal.")
            tarikh = st.date_input("Tarikh surat", value=datetime.date.today(), key="al_hantar_tarikh")
            yakin = st.checkbox(f"Saya sahkan hantar {len(terpilih)} surat ({label}) ke sekolah asal", key="al_hantar_yakin")
            if st.button(f"📤 Hantar {len(terpilih)} Surat ke Sekolah", type="primary", disabled=not yakin, key="al_btn_hantar"):
                ok, gagal = _hantar(terpilih, info, kod_ppd, tarikh)
                _clear()
                if gagal:
                    _flash("warning", f"⚠️ {ok} surat dihantar; gagal: " + ", ".join(gagal[:5]))
                else:
                    _flash("success", f"✅ {ok} surat berjaya dihantar ke {sek} sekolah asal. SUP boleh melihat & mencetak surat.")
                st.rerun()
        else:
            st.info("Pilih skop / pusat / jawatan / sekolah untuk dihantar.")

    if dihantar:
        with st.expander(f"↩️ Tarik balik penghantaran ({len(dihantar)} sudah dihantar)", expanded=False):
            st.caption("Surat ditarik balik dari sekolah dan kembali ke status Menunggu hantar (no surat dikekalkan).")
            ada = sorted({r["pusat"] for r in dihantar})
            sel = st.multiselect("Pusat", ada, format_func=lambda p: f"{p} ({sum(1 for r in dihantar if r['pusat'] == p)})", key="al_tarik_p")
            if st.button("↩️ Tarik balik pusat terpilih", disabled=not sel, key="al_tarik_btn"):
                n = 0
                for r in dihantar:
                    if r["pusat"] in set(sel):
                        if _update_rekod(r, ST_SURAT, data_baru={"SURAT_NO_JANA": no_surat_rek(r), "SURAT_DIHANTAR_KE_SEKOLAH_ASAL": False},
                                         no_surat=None, set_no_surat=True):
                            n += 1
                _clear()
                _flash("success", f"↩️ {n} surat ditarik balik dari sekolah.")
                st.rerun()
