# -*- coding: utf-8 -*-
"""kemajuan.py - Papan Kemajuan (baca sahaja): kemajuan SPM, Amali Sains dan Ujian Mendengar untuk PPD dan JPN.
Tiada tulis ke pangkalan data. Pemuat data `muat_rekod` turut dipakai oleh carian_semakan.py."""
import datetime
import json

import pandas as pd
import streamlit as st

import spm_core as core
import ppd_aliran as al
import amali_sains as am
import ujian_mendengar as um
import ui_theme as ui
from kuota_pusat import _data as _kdata

KOD_DAERAH = list(getattr(core, "KOD_DAERAH", ["BA", "BB", "BC", "BD", "BE", "BF", "BG", "BH", "BJ", "BK"]))


def _s(v):
    x = "" if v is None else str(v).strip()
    return "" if x.lower() in ("nan", "none", "null", "nat") else x


def _int(v, lalai=-1):
    try:
        return int(v) if _s(v) != "" else lalai
    except Exception:
        return lalai


def _baca(res_fn):
    """Baca semua baris (halaman 1000) - jatuh balik ke limit biasa jika range tidak disokong."""
    out, a = [], 0
    while True:
        try:
            rows = res_fn(a, a + 999).execute().data or []
        except Exception:
            return None
        out += rows
        if len(rows) < 1000 or a > 40000:
            return out
        a += 1000


@st.cache_data(ttl=90, show_spinner=False)
def muat_rekod(kod_ppd=None):
    """Senarai rekod petugas dalam bentuk rata (SPM + ledger Amali + ledger Ujian Mendengar)."""
    def q(a, b):
        t = core.supa.table("cadangan_sup").select("*")
        if kod_ppd:
            t = t.eq("kod_ppd", kod_ppd)
        return t.range(a, b)
    data = _baca(q)
    if data is None:
        try:
            t = core.supa.table("cadangan_sup").select("*")
            if kod_ppd:
                t = t.eq("kod_ppd", kod_ppd)
            data = t.limit(10000).execute().data or []
        except Exception:
            data = []
    out = []
    for r in data:
        d = _kdata(r)
        jaw = al._g(r, d, "JAWATAN_CADANGAN", "jawatan_cadangan", "JAWATAN")
        status = al._g(r, d, "status", "STATUS")
        pusat = al._g(r, d, "kod_pusat", "KOD_PUSAT").upper()
        no_col = _s(r.get("no_surat") or r.get("NO_SURAT"))
        ppd = (_s(r.get("kod_ppd")) or al._g(r, d, "KOD_PPD", "kod_ppd")).upper()
        out.append({"id": r.get("id"), "ppd": ppd, "nama": al._g(r, d, "NAMA_GURU", "nama_guru"), "ic": al._g(r, d, "IC_GURU", "ic_guru"),
                    "tel": al._g(r, d, "TELEFON_GURU", "telefon_guru"), "jaw": jaw, "sek": al._g(r, d, "KOD_SEKOLAH_ASAL", "kod_sekolah_asal", "KOD_SEKOLAH", "kod_sekolah").upper(),
                    "nama_sek": al._g(r, d, "NAMA_SEKOLAH_ASAL", "nama_sekolah_asal"), "pusat": pusat, "status": status, "no": no_col,
                    "rank": al.peringkat(status, pusat, no_col), "amali_jaw": am.is_amali_jaw(jaw),
                    "am_stage": _int(d.get("AMALI_STAGE")), "am_jaw": _s(d.get("AMALI_JAWATAN")), "am_no": _s(d.get("AMALI_NO")),
                    "um_stage": _int(d.get("UM_STAGE")), "um_jaw": _s(d.get("UM_JAWATAN")), "um_no": _s(d.get("UM_NO")),
                    "simpanan": "SIMPANAN" in status.upper() or "TERPILIH" in status.upper()})
    return out


def _spm(rows):
    """Rekod SPM sebenar (bukan PKS/PMP/PM Amali, bukan simpanan)."""
    return [r for r in rows if not r["amali_jaw"] and not r["simpanan"]]


def _kira(rows):
    s = _spm(rows)
    k = {"cadang": len(s), "tempat": sum(1 for r in s if r["rank"] >= 0)}
    for n, lbl in ((1, "hasil"), (2, "semak"), (3, "putus"), (4, "jana"), (5, "hantar")):
        k[lbl] = sum(1 for r in s if r["rank"] >= n)
    k["am_jana"] = sum(1 for r in rows if r["am_stage"] >= 4 and r["am_no"])
    k["am_hantar"] = sum(1 for r in rows if r["am_stage"] == 5 and r["am_no"])
    k["um_jana"] = sum(1 for r in rows if r["um_stage"] >= 4 and r["um_no"])
    k["um_hantar"] = sum(1 for r in rows if r["um_stage"] == 5 and r["um_no"])
    return k


def render_ppd(kod_ppd):
    st.header(f"📈 Papan Kemajuan - PPD {kod_ppd} - {core.PPD_MAP.get(kod_ppd, '')}")
    rows = muat_rekod(kod_ppd)
    if not rows:
        st.info("Belum ada data cadangan petugas untuk PPD ini.")
        return
    k = _kira(rows)
    info = al.pusat_info(kod_ppd)
    al_rows = al.muat(kod_ppd)[1]
    rp = al.ringkas_pusat(al_rows, info)
    n_pusat = len(info)
    lengkap = sum(1 for e in rp.values() if e["lengkap"])
    perlu_semua = sum(int(i.get("perlu", 0) or 0) for i in info.values())
    ui.kmj_sec("Ringkasan SPM")
    ui.kmj_grid([("Pusat SPM", n_pusat, f"{len(rp)} sudah ada petugas", ""),
                 ("Pusat lengkap", lengkap, f"daripada {n_pusat}", "ok" if n_pusat and lengkap == n_pusat else "warn"),
                 ("Petugas dicadangkan", k["cadang"], f"perlu {perlu_semua} (kuota)", ""),
                 ("Ditempatkan", k["tempat"], "", ""),
                 ("Surat dijana", k["jana"], "", ""),
                 ("Dihantar ke sekolah", k["hantar"], "", "ok" if k["cadang"] and k["hantar"] >= k["cadang"] else "")])
    st.caption("Kemajuan petugas SPM mengikut peringkat (setiap bar = peratus daripada jumlah petugas dicadangkan).")
    t = max(k["cadang"], 1)
    for lbl, key in (("1. Ditempatkan di pusat", "tempat"), ("2. Hasil disetujui", "hasil"), ("3. Semakan disahkan", "semak"), ("4. Keputusan disahkan", "putus"),
                     ("5. Surat dijana", "jana"), ("6. Dihantar ke sekolah asal", "hantar")):
        ui.kmj_bar(lbl, k[key], t)

    ui.kmj_sec("🔬 Amali Sains")
    ams = {p for p in am.amali_set(kod_ppd) if p in info}
    if not ams:
        st.caption("Belum ada pusat Amali Sains ditanda.")
    else:
        _, ar = am.muat_semua(kod_ppd, ams)
        lay = [r for r in ar if r["layak"]]
        tt = max(len(lay), 1)
        c = {s_: sum(1 for r in lay if r["stage"] >= s_) for s_ in (1, 2, 4, 5)}
        ui.kmj_grid([("Pusat Amali", len(ams), "", ""), ("Petugas Amali", len(lay), "", ""), ("Surat dijana", c[4], "", ""), ("Dihantar", c[5], "", "ok" if lay and c[5] >= len(lay) else "")])
        for lbl, s_ in (("Disemak", 1), ("Dilantik", 2), ("Surat dijana", 4), ("Dihantar ke sekolah", 5)):
            ui.kmj_bar(lbl, c[s_], tt)

    ui.kmj_sec("🎧 Ujian Mendengar")
    _, ur = um.muat_semua(kod_ppd)
    lay = [r for r in ur if r["layak"]]
    if not lay:
        st.caption("Belum ada petugas SPM yang ditempatkan untuk Ujian Mendengar.")
    else:
        tt = len(lay)
        c = {s_: sum(1 for r in lay if r["stage"] >= s_) for s_ in (1, 2, 4, 5)}
        ui.kmj_grid([("Petugas", tt, "", ""), ("Surat dijana", c[4], "", ""), ("Dihantar", c[5], "", "ok" if c[5] >= tt else "")])
        for lbl, s_ in (("Disemak", 1), ("Dilantik", 2), ("Surat dijana", 4), ("Dihantar ke sekolah", 5)):
            ui.kmj_bar(lbl, c[s_], tt)

    ui.kmj_sec("Pusat yang masih tidak lengkap")
    kurang = [{"NO PUSAT": p, "NAMA PUSAT": e["nama"], "ADA": e["ada"], "PERLU": e["perlu"], "SEBAB": al.sebab_tak_lengkap(e)} for p, e in sorted(rp.items()) if not e["lengkap"]]
    belum = [{"NO PUSAT": p, "NAMA PUSAT": i["nama"], "ADA": 0, "PERLU": int(i.get("perlu", 0) or 0), "SEBAB": "belum ada petugas"} for p, i in sorted(info.items()) if p not in rp]
    gab = kurang + belum
    if not gab:
        st.success("✅ Semua pusat lengkap.")
    else:
        df = pd.DataFrame(gab)
        st.dataframe(df, use_container_width=True, hide_index=True, height=min(420, 60 + 35 * len(df)))
        st.download_button("📊 Muat turun senarai pusat tidak lengkap", core.to_excel(df), file_name=f"pusat_tidak_lengkap_{kod_ppd}_{datetime.date.today()}.xlsx", key="kmj_dl_kurang")
    st.caption("Data dikemas kini setiap ±90 saat. Tekan REFRESH di sebelah kiri atas untuk bacaan baharu.")


def render_jpn():
    st.header("📈 Kemajuan Negeri - Semua PPD")
    rows = muat_rekod(None)
    if not rows:
        st.info("Belum ada data cadangan.")
        return
    try:
        pdf = core.get_pusat_df()
        pc = {}
        if pdf is not None and len(pdf):
            for _, r in pdf.iterrows():
                no = _s(r.get("no_pusat") or r.get("kod_pusat")).upper()
                if no:
                    pc[no[:2]] = pc.get(no[:2], 0) + 1
    except Exception:
        pc = {}
    tab = []
    jum = {}
    for ppd in KOD_DAERAH:
        rr = [r for r in rows if r["ppd"] == ppd]
        k = _kira(rr)
        tab.append({"PPD": f"{ppd} - {core.PPD_MAP.get(ppd, '')}", "PUSAT": pc.get(ppd, 0), "CADANGAN": k["cadang"], "DITEMPATKAN": k["tempat"],
                    "SURAT DIJANA": k["jana"], "DIHANTAR": k["hantar"], "% DIHANTAR": round(100 * k["hantar"] / k["cadang"]) if k["cadang"] else 0,
                    "AMALI DIJANA": k["am_jana"], "AMALI DIHANTAR": k["am_hantar"], "UM DIJANA": k["um_jana"], "UM DIHANTAR": k["um_hantar"]})
        for x, v in k.items():
            jum[x] = jum.get(x, 0) + v
    ui.kmj_sec("Jumlah Negeri")
    ui.kmj_grid([("Petugas dicadangkan", jum["cadang"], "", ""), ("Ditempatkan", jum["tempat"], "", ""), ("Surat SPM dijana", jum["jana"], "", ""),
                 ("Dihantar ke sekolah", jum["hantar"], "", "ok" if jum["cadang"] and jum["hantar"] >= jum["cadang"] else ""),
                 ("Surat Amali dijana", jum["am_jana"], f"{jum['am_hantar']} dihantar", ""), ("Surat UM dijana", jum["um_jana"], f"{jum['um_hantar']} dihantar", "")])
    t = max(jum["cadang"], 1)
    for lbl, key in (("Ditempatkan", "tempat"), ("Hasil disetujui", "hasil"), ("Semakan disahkan", "semak"), ("Keputusan disahkan", "putus"), ("Surat dijana", "jana"), ("Dihantar ke sekolah", "hantar")):
        ui.kmj_bar(lbl, jum[key], t)
    ui.kmj_sec("Ikut PPD")
    for r in tab:
        ui.kmj_bar(r["PPD"], r["DIHANTAR"], r["CADANGAN"])
    df = pd.DataFrame(tab)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("📊 Muat turun jadual kemajuan (Excel)", core.to_excel(df), file_name=f"kemajuan_negeri_{datetime.date.today()}.xlsx", key="kmj_dl_jpn")
