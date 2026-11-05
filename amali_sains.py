# -*- coding: utf-8 -*-
"""amali_sains.py - Pelantikan Ujian Amali Sains (selari dengan pelantikan petugas SPM).

 * Pusat Amali Sains (287 daripada 504 pusat SPM) ditanda PPD / JPN: pusat_master.data["AMALI_SAINS"] = true (tiada SQL baharu).
 * Petugas SPM di pusat Amali turut dilantik menjaga Amali:
     - Ketua Pengawas  -> surat "Ketua Pengawas Amali Sains"
     - Timbalan KP     -> surat "Timbalan Ketua Pengawas Amali Sains"
     - Penyelia Kawasan (orang & bilik kebal sama) -> surat "Penyelia Kawasan Amali Sains"
   Surat tambahan ini disimpan pada rekod petugas yang sama (data.AMALI_NO / AMALI_JAWATAN / AMALI_STATUS) - TIADA rekod pendua.
 * Jawatan baharu (guru sekolah asal, dicadangkan SUP): Penyelia Kanan Sains (PKS), Penyelia Mata Pelajaran (PMP: Biologi, Kimia, Fizik, Sains Tambahan), Pembantu Makmal (PM).
   Ditempatkan di pusat Amali, melalui aliran biasa (Hasil -> Semakan -> Kelulusan) dan Janaan Surat Amali.
 * No surat Amali dalam siri berasingan daripada SPM (no rujukan fail lain; jilid 100 surat seperti biasa).
"""
import datetime
import json
import re

import pandas as pd
import streamlit as st

import spm_core as core
import no_surat as nsr
import ppd_aliran as al
from kuota_pusat import _data as _kdata, no_pusat as _no_pusat, kod_tuan_rumah
from lengkap_petugas import lengkapkan

AMALI_KP = "Ketua Pengawas Amali Sains"
AMALI_TKP = "Timbalan Ketua Pengawas Amali Sains"
AMALI_PK = "Penyelia Kawasan Amali Sains"
J_PKS = "Penyelia Kanan Sains"
J_PMP = "Penyelia Mata Pelajaran"      # lama / tanpa mata pelajaran (kekal untuk keserasian)
J_PMP_BIO = "Penyelia Mata Pelajaran Biologi"
J_PMP_KIM = "Penyelia Mata Pelajaran Kimia"
J_PMP_FIZ = "Penyelia Mata Pelajaran Fizik"
J_PMP_ST = "Penyelia Mata Pelajaran Sains Tambahan"
PMP_LIST = [J_PMP_BIO, J_PMP_KIM, J_PMP_FIZ, J_PMP_ST]
J_PM = "Pembantu Makmal"
JAWATAN_BARU = [J_PKS] + PMP_LIST + [J_PM]
JAWATAN_LEDGER = [AMALI_KP, AMALI_TKP, AMALI_PK]
JAWATAN_AMALI = JAWATAN_LEDGER + JAWATAN_BARU + [J_PMP]
RUJ_AMALI_LALAI = "JPNS.SPP 600-7/1/2"

_KUNCI_BARU = ("PENYELIA KANAN SAINS", "PENYELIA MATA PELAJARAN", "PEMBANTU MAKMAL")


def is_amali_jaw(j):
    """Jawatan khas Amali (3 jawatan baharu atau tajuk surat Amali)."""
    j = " ".join(str(j or "").upper().split())
    return "AMALI SAINS" in j or any(k in j for k in _KUNCI_BARU)


def _s(v):
    x = "" if v is None else str(v).strip()
    return "" if x.lower() in ("nan", "none", "null", "nat") else x


# ============================================================ templat lalai (JPN boleh ubah di Template Surat)
def default_template(jawatan):
    j = _s(jawatan).upper()
    tajuk = {"KETUA PENGAWAS AMALI SAINS": "KETUA PENGAWAS UJIAN AMALI SAINS",
             "TIMBALAN KETUA PENGAWAS AMALI SAINS": "TIMBALAN KETUA PENGAWAS UJIAN AMALI SAINS",
             "PENYELIA KAWASAN AMALI SAINS": "PENYELIA KAWASAN UJIAN AMALI SAINS",
             "PENYELIA KANAN SAINS": "PENYELIA KANAN SAINS (PKS) UJIAN AMALI SAINS",
             "PENYELIA MATA PELAJARAN": "PENYELIA MATA PELAJARAN (PMP) UJIAN AMALI SAINS",
             "PENYELIA MATA PELAJARAN BIOLOGI": "PENYELIA MATA PELAJARAN (PMP) BIOLOGI UJIAN AMALI SAINS",
             "PENYELIA MATA PELAJARAN KIMIA": "PENYELIA MATA PELAJARAN (PMP) KIMIA UJIAN AMALI SAINS",
             "PENYELIA MATA PELAJARAN FIZIK": "PENYELIA MATA PELAJARAN (PMP) FIZIK UJIAN AMALI SAINS",
             "PENYELIA MATA PELAJARAN SAINS TAMBAHAN": "PENYELIA MATA PELAJARAN (PMP) SAINS TAMBAHAN UJIAN AMALI SAINS",
             "PEMBANTU MAKMAL": "PEMBANTU MAKMAL UJIAN AMALI SAINS"}.get(j, j + " UJIAN AMALI SAINS")
    return ("<div style='font-family:Arial; padding:25px; border:1px solid #000;'><table style='width:100%; border:none;'><tr>"
            "<td style='width:80px; vertical-align:top; border:none;'><img src='https://upload.wikimedia.org/wikipedia/commons/2/2a/Coat_of_arms_of_Malaysia.svg' style='width:70px;'></td>"
            "<td style='vertical-align:top; border:none; text-align:left;'><b>KEMENTERIAN PENDIDIKAN MALAYSIA</b><br>JABATAN PENDIDIKAN NEGERI SELANGOR<br>"
            "<small>Persiaran Tengku Ampuan Rahimah, Seksyen 20, 40300 Shah Alam, Selangor</small></td></tr></table>"
            "<hr style='border:2px solid #000; margin:10px 0;'><div style='text-align:right; font-size:10pt;'>Ruj. Kami: {{NO_SURAT}}<br>Tarikh: {{TARIKH}}</div>"
            "<div style='font-size:10pt; margin-top:12px;'><b>{{NAMA}}</b><br>Melalui:<br>PENGETUA<br><b>{{NAMA_SEKOLAH_ASAL}}</b><br>{{PPD}}<br><br>Tuan/Puan,<br>"
            f"<b>UJIAN AMALI SAINS SPM {{{{TAHUN}}}} : PELANTIKAN SEBAGAI {tajuk}</b><br><br>"
            "2. Dengan ini tuan/puan dilantik sebagai <b>{{JAWATAN}}</b> Ujian Amali Sains SPM {{TAHUN}} di {{PUSAT}} - {{NAMA_PUSAT}}<br>"
            "Bilik Kebal: {{BILIK_KEBAL}}<br>Sekolah Asal: {{SEKOLAH_ASAL}} - {{NAMA_SEKOLAH_ASAL}}<br>No Surat: {{NO_SURAT}}<br><br>"
            "3. Sulit - Akta Rahsia Rasmi 1972<br><br>MALAYSIA MADANI<br>BERKHIDMAT UNTUK NEGARA<br><br>(DATIN WAN NOR ASHIKIN)<br>Pengarah JPN Selangor</div></div>")


# ============================================================ pusat Amali
def _benar(v):
    return v is True or str(v).strip().lower() in ("1", "true", "ya", "yes", "y", "amali")


def amali_set(kod_ppd=None):
    """Set no pusat yang ditanda Amali Sains (pilihan: hanya satu PPD)."""
    out = set()
    try:
        df = core.get_pusat_df()
    except Exception:
        df = None
    if df is None or len(df) == 0:
        return out
    kp = str(kod_ppd or "").upper()
    for _, r in df.iterrows():
        no = _no_pusat(r)
        if not no or (kp and not no.startswith(kp)):
            continue
        if _benar(_kdata(r).get("AMALI_SAINS")):
            out.add(no)
    return out


def set_pusat_amali(no, flag):
    """Tanda / buang tanda Amali pada satu pusat. Pulang True jika dijumpai."""
    for col in ("no_pusat", "kod_pusat"):
        try:
            rows = core.supa.table("pusat_master").select("*").eq(col, no).limit(1).execute().data or []
        except Exception:
            continue
        if not rows:
            continue
        row = rows[0]
        d = dict(_kdata(row))
        if flag:
            d["AMALI_SAINS"] = True
        else:
            d.pop("AMALI_SAINS", None)
        val = json.dumps(d, ensure_ascii=False) if isinstance(row.get("data"), str) else d
        core.supa.table("pusat_master").update({"data": val}).eq(col, no).execute()
        return True
    return False


def _segar():
    al._clear()


def render_tetapan_pusat(kod_ppd, kunci="ppd"):
    """Jadual tick Pusat Amali Sains untuk satu PPD."""
    info = al.pusat_info(kod_ppd)
    ams = amali_set(kod_ppd)
    st.markdown("#### 🔬 Pusat Amali Sains")
    st.caption("Tick pusat yang menjalankan Ujian Amali Sains. Hanya pusat bertanda ini menerima surat Amali dan penempatan PKS / PMP / PM.")
    if not info:
        st.info("Tiada pusat dalam PPD ini.")
        return
    df = pd.DataFrame([{"AMALI SAINS": no in ams, "NO PUSAT": no, "NAMA PUSAT": i["nama"], "CALON": i["calon"]} for no, i in sorted(info.items())])
    c1, c2 = st.columns(2)
    c1.metric("Pusat SPM", len(df))
    c2.metric("Pusat Amali Sains", int(df["AMALI SAINS"].sum()))
    ed = st.data_editor(df, use_container_width=True, hide_index=True, height=min(520, 60 + 35 * len(df)), key=f"am_ed_{kunci}_{kod_ppd}",
                        disabled=["NO PUSAT", "NAMA PUSAT", "CALON"],
                        column_config={"AMALI SAINS": st.column_config.CheckboxColumn("🔬 Amali Sains")})
    ubah = []
    for (_, a), (_, b) in zip(df.iterrows(), ed.iterrows()):
        if bool(a["AMALI SAINS"]) != bool(b["AMALI SAINS"]):
            ubah.append((a["NO PUSAT"], bool(b["AMALI SAINS"])))
    if st.button(f"💾 Simpan Pusat Amali Sains ({len(ubah)} perubahan)", type="primary", disabled=not ubah, key=f"am_save_{kunci}_{kod_ppd}"):
        ok = sum(1 for no, f in ubah if set_pusat_amali(no, f))
        _segar()
        st.success(f"✅ {ok} pusat dikemas kini.")
        st.rerun()


def terap_senarai(kod_ppd_list, nombor, kosongkan_lain=False):
    """JPN: tanda pusat Amali daripada senarai no pusat. Pulang (ditanda, tidak_jumpa, dibuang)."""
    nombor = {str(x).strip().upper() for x in nombor if str(x).strip()}
    ok, tiada, buang = 0, [], 0
    if kosongkan_lain:
        for no in amali_set():
            if no not in nombor:
                if set_pusat_amali(no, False):
                    buang += 1
    for no in sorted(nombor):
        if set_pusat_amali(no, True):
            ok += 1
        else:
            tiada.append(no)
    _segar()
    return ok, tiada, buang


def render_jpn_amali():
    """Halaman JPN: muat naik senarai pusat Amali + tick ikut daerah."""
    st.header("🔬 Pusat Amali Sains")
    st.caption("Muat naik senarai pusat Amali Sains (Excel / CSV, lajur NO PUSAT) atau tick ikut daerah.")
    with st.expander("📤 Muat naik senarai pusat Amali Sains", expanded=True):
        f = st.file_uploader("Fail Excel / CSV (lajur: NO PUSAT)", type=["xlsx", "xls", "csv"], key="am_up")
        ganti = st.checkbox("Kosongkan tanda Amali pada pusat yang tiada dalam senarai ini (ganti penuh)", key="am_up_ganti")
        if f is not None:
            try:
                df = pd.read_csv(f, dtype=str) if f.name.lower().endswith(".csv") else pd.read_excel(f, dtype=str)
                col = next((c for c in df.columns if re.sub(r"[^A-Z]", "", str(c).upper()) in ("NOPUSAT", "KODPUSAT", "PUSAT")), df.columns[0])
                nombor = [x for x in df[col].dropna().astype(str)]
                st.info(f"{len(set(n.strip().upper() for n in nombor))} no pusat dibaca daripada lajur «{col}».")
                if st.button("✅ Tanda pusat Amali Sains", type="primary", key="am_up_btn"):
                    ok, tiada, buang = terap_senarai(None, nombor, ganti)
                    st.success(f"✅ {ok} pusat ditanda Amali." + (f" {buang} tanda dibuang." if buang else ""))
                    if tiada:
                        st.warning(f"{len(tiada)} no pusat tidak dijumpai: " + ", ".join(tiada[:15]))
            except Exception as e:
                st.error(f"Gagal baca fail: {str(e)[:120]}")
    total = len(amali_set())
    st.metric("Jumlah pusat Amali Sains (seluruh negeri)", total)
    ppd = core.PPD_MAP
    kod = st.selectbox("Tick ikut daerah", sorted(ppd), format_func=lambda k: f"{k} - {ppd.get(k, k)}", key="am_jpn_ppd")
    render_tetapan_pusat(kod, "jpn")


# ============================================================ MENU PPD: Lantikan Petugas Amali
FLY_AMALI = [("pusat", "🔬 Pilih Pusat Amali"), ("tempat", "📍 Tempatkan PKS/PMP/PM"), ("sahkan", "✔️ Sahkan Petugas"), ("lantik", "👤 Lantik"),
             ("semak", "🔍 Semak"), ("jana", "📄 Jana Surat"), ("cetak", "🖨️ Cetak Surat"), ("hantar", "📤 Hantar ke Sekolah")]
STAGE_NAMA = {-1: "Calon", 1: "Disahkan", 2: "Dilantik", 3: "Disemak", 4: "Surat dijana", 5: "Dihantar ke sekolah"}
_PK_STATUS_BUANG = ("TERPILIH", "SIMPANAN", "BATAL")


def _jenis(jaw):
    j = " ".join(str(jaw or "").upper().split())
    if "KANAN SAINS" in j:
        return "PKS"
    if "MATA PELAJARAN" in j:
        return "PMP"
    if "MAKMAL" in j:
        return "PM"
    if "PENYELIA" in j:
        return "PK"
    if "TIMBALAN" in j and "KETUA" in j and "HOSPITAL" not in j:
        return "TKP"
    if "KETUA" in j and "HOSPITAL" not in j:
        return "KP"
    return ""


def _pmp_kanon(jaw):
    """Nama kanonik PMP ikut mata pelajaran (Biologi/Kimia/Fizik/Sains Tambahan)."""
    j = " ".join(str(jaw or "").upper().split())
    if "TAMBAHAN" in j:
        return J_PMP_ST
    for k, n in (("BIOLOGI", J_PMP_BIO), ("KIMIA", J_PMP_KIM), ("FIZIK", J_PMP_FIZ)):
        if k in j:
            return n
    return J_PMP


_JAW_AMALI = {"KP": AMALI_KP, "TKP": AMALI_TKP, "PK": AMALI_PK, "PKS": J_PKS, "PMP": J_PMP, "PM": J_PM}


def _list(v):
    if isinstance(v, (list, tuple)):
        return [_s(x).upper() for x in v if _s(x)]
    if isinstance(v, str):
        return [x.strip().upper() for x in v.split(",") if x.strip()]
    return []


def muat_semua(kod_ppd, ams=None):
    """Semua petugas PPD yang layak ke Amali (ledger dalam data). Pulang (raw, rows)."""
    ams = ams if ams is not None else amali_set(kod_ppd)
    try:
        raw = pd.DataFrame(core.supa.table("cadangan_sup").select("*").eq("kod_ppd", kod_ppd).limit(5000).execute().data or [])
    except Exception:
        raw = pd.DataFrame()
    rows = []
    if raw.empty:
        return raw, rows
    for _, r0 in raw.iterrows():
        if _s(r0.get("id")) == "":
            continue
        r = lengkapkan(r0, kod_ppd)
        d = _kdata(r)
        jaw = al._g(r, d, "JAWATAN_CADANGAN", "jawatan_cadangan", "JAWATAN")
        jn = _jenis(jaw)
        if not jn:
            continue
        status = al._g(r, d, "status", "STATUS")
        spm_pusat = al._g(r, d, "kod_pusat", "KOD_PUSAT", "kod_pusat_tugas", "NO_PUSAT_TUGAS").upper()
        no_col = _s(r.get("no_surat") or r.get("NO_SURAT"))
        spm_rank = al.peringkat(status, spm_pusat, no_col)
        pusat, bk, jaga = "", "", []
        if jn in ("KP", "TKP"):
            pusat = spm_pusat if spm_rank >= 0 else ""
        elif jn == "PK":
            bk = al._g(r, d, "kod_bilik_kebal_explicit", "kod_bilik_kebal", "KOD_BILIK_KEBAL").upper() or spm_pusat
            jaga = _list(d.get("pusat_jagaan") or d.get("pusat_jagaan_str") or r.get("pusat_jagaan") or r.get("pusat_bawah_bilik_kebal"))
            if any(x in status.upper() for x in _PK_STATUS_BUANG) or not bk:
                bk = ""
            pusat = bk
        else:
            pusat = _s(d.get("AMALI_PUSAT")).upper()
        try:
            stg = int(d.get("AMALI_STAGE")) if _s(d.get("AMALI_STAGE")) != "" else -1
        except Exception:
            stg = -1
        pusat_kira = pusat if jn != "PK" else next((x for x in jaga if x in ams), "")
        # layak Amali: KP/TKP di pusat Amali; PK yang menjaga sekurang-kurangnya satu pusat Amali; PKS/PMP/PM yang ditempatkan di pusat Amali
        layak = bool(pusat) and ((pusat in ams) if jn in ("KP", "TKP", "PKS", "PMP", "PM") else bool(pusat_kira))
        rows.append({"id": al._pyid(r0.get("id")), "nama": al._g(r, d, "NAMA_GURU", "nama_guru"), "ic": al._g(r, d, "IC_GURU", "ic_guru"),
                     "jn": jn, "jaw_spm": jaw, "jaw": (_pmp_kanon(jaw) if jn == "PMP" else _JAW_AMALI[jn]),
                     "sek": al._g(r, d, "KOD_SEKOLAH_ASAL", "kod_sekolah_asal", "KOD_SEKOLAH", "kod_sekolah").upper(),
                     "nama_sek": al._g(r, d, "NAMA_SEKOLAH_ASAL", "nama_sekolah_asal"), "tel": al._g(r, d, "TELEFON_GURU", "telefon_guru"),
                     "pusat": pusat, "layak": layak, "spm_rank": spm_rank, "status": status, "stage": stg if (layak or stg >= 0) else -1,
                     "data": d, "data_str": isinstance(r0.get("data"), str), "no": _s(d.get("AMALI_NO")), "tarikh": _s(d.get("AMALI_TARIKH")),
                     "tarikh_hantar": _s(d.get("AMALI_TARIKH_HANTAR"))})
    return raw, rows


def _kemas(rec, baru):
    d = dict(rec["data"])
    d.update(baru)
    val = json.dumps(d, ensure_ascii=False) if rec["data_str"] else d
    try:
        core.supa.table("cadangan_sup").update({"data": val}).eq("id", rec["id"]).execute()
        return True
    except Exception:
        return False


def _info_bk(info, p):
    return info.get(p, {}).get("nama", "")


def _bar(rows):
    c = {k: 0 for k in (-1, 1, 2, 3, 4, 5)}
    for r in rows:
        if r["layak"] or r["stage"] >= 0:
            c[r["stage"] if r["stage"] in c else -1] += 1
    cols = st.columns(6)
    for col, k in zip(cols, (-1, 1, 2, 3, 4, 5)):
        col.metric(STAGE_NAMA[k], c[k])


def _ada_amali(kod_ppd):
    ams = amali_set(kod_ppd)
    if not ams:
        st.warning("Belum ada pusat Amali Sains. Tick di submenu **🔬 Pilih Pusat Amali** dahulu.")
    return ams


def _jadual(rows, info):
    return pd.DataFrame([{"JAWATAN AMALI": r["jaw"], "PUSAT/BK": r["pusat"], "NAMA PUSAT/BK": _info_bk(info, r["pusat"]), "NAMA": r["nama"], "IC": r["ic"],
                          "SEKOLAH ASAL": r["nama_sek"] or r["sek"], "NO TELEFON": r["tel"], "NO SURAT": r["no"],
                          "PERINGKAT": STAGE_NAMA.get(r["stage"], "Calon")} for r in rows])


def _skop_pilih(rows, info, kunci):
    """Penapis jawatan + pusat + pilih baris. Pulang senarai rec terpilih."""
    if not rows:
        return []
    jaws = [j for j in JAWATAN_AMALI if any(r["jaw"] == j for r in rows)]
    c1, c2 = st.columns(2)
    jf = c1.multiselect("Jawatan", jaws, default=[], key=f"am_jf_{kunci}", format_func=lambda j: f"{j} ({sum(1 for r in rows if r['jaw'] == j)})")
    pusat_ada = sorted({r["pusat"] for r in rows})
    pf = c2.multiselect("Pusat / Bilik Kebal", pusat_ada, default=[], key=f"am_pf_{kunci}")
    sub = [r for r in rows if (not jf or r["jaw"] in jf) and (not pf or r["pusat"] in pf)]
    sub = sorted(sub, key=lambda r: (r["pusat"], JAWATAN_AMALI.index(r["jaw"]), r["nama"]))
    st.caption(f"{len(sub)} dipaparkan" + ("" if jf or pf else " (semua - tapis jawatan/pusat jika perlu)"))
    if not sub:
        return []
    semua = st.checkbox(f"Pilih SEMUA {len(sub)} yang dipaparkan", key=f"am_all_{kunci}_{len(sub)}")
    if semua:
        st.dataframe(_jadual(sub, info), use_container_width=True, hide_index=True, height=min(360, 40 + 35 * len(sub)))
        return sub
    ev = st.dataframe(_jadual(sub, info), use_container_width=True, hide_index=True, height=min(360, 40 + 35 * len(sub)),
                      on_select="rerun", selection_mode="multi-row", key=f"am_tbl_{kunci}_{len(sub)}")
    return [sub[i] for i in (ev.selection.rows if ev and ev.selection else []) if i < len(sub)]


def _semula():
    al._clear()


# ---------------------------------------------------------------- 1. Pilih Pusat Amali
def render_pusat(kod_ppd):
    st.header(f"🔬 Lantikan Petugas Amali - Pilih Pusat Amali - PPD {kod_ppd} - {core.PPD_MAP.get(kod_ppd, '')}")
    al._show_flash()
    render_tetapan_pusat(kod_ppd, "ppd")


# ---------------------------------------------------------------- 2. Tempatkan PKS / PMP / PM
def render_penempatan(kod_ppd):
    st.header(f"🔬 Lantikan Petugas Amali - Tempatkan PKS/PMP/PM - PPD {kod_ppd}")
    al._show_flash()
    ams = amali_set(kod_ppd)
    info = al.pusat_info(kod_ppd)
    ams = {p for p in ams if p in info}
    if not ams:
        _ada_amali(kod_ppd)
        return
    _, rows = muat_semua(kod_ppd, ams)
    st.caption("PKS, PMP dan PM ialah guru sekolah asal yang dicadangkan SUP. KP, TKP dan Penyelia Kawasan Amali ialah petugas SPM sedia ada di pusat Amali - tidak perlu ditempatkan di sini.")
    pusat = st.selectbox("Pusat Amali Sains", sorted(ams), format_func=lambda p: f"{p} - {info[p]['nama'][:35]}", key="am_pl_pusat")
    jaw = st.radio("Jawatan", JAWATAN_BARU, horizontal=True, key="am_pl_jaw")
    cols = st.columns(len(JAWATAN_BARU))
    for c, jn in zip(cols, JAWATAN_BARU):
        c.metric(f"{jn} di {pusat}", sum(1 for r in rows if r["pusat"] == pusat and r["jaw"] == jn))
    ada = [r for r in rows if r["pusat"] == pusat and r["jaw"] == jaw]
    st.markdown(f"#### 📋 {jaw} di {pusat}")
    if not ada:
        st.info("Belum ada.")
    for r in sorted(ada, key=lambda x: x["nama"]):
        a, b, c = st.columns([4, 3, 1.3])
        a.markdown(f"**{r['nama']}**  \n<span style='font-size:12px;color:#455a64'>{r['ic']} | 📞 {r['tel'] or '-'}</span>", unsafe_allow_html=True)
        b.markdown(f"{r['nama_sek'] or r['sek']}  \n<span style='font-size:12px;color:#455a64'>{r['sek']} | {STAGE_NAMA.get(r['stage'], 'Calon')}</span>", unsafe_allow_html=True)
        if c.button("🗑️ Batal", key=f"am_pl_b_{r['id']}", disabled=r["stage"] >= 4, use_container_width=True):
            _kemas(r, {"AMALI_PUSAT": "", "AMALI_STAGE": "", "AMALI_NO": "", "AMALI_TARIKH": "", "AMALI_TARIKH_HANTAR": ""})
            _semula()
            al._flash("success", f"🗑️ {r['nama']} dibatalkan dan kembali ke ruang belum ditempatkan.")
            st.rerun()
    st.markdown(f"#### ➕ {jaw} belum ditempatkan - klik baris untuk pilih")
    pool = [r for r in rows if r["jaw"] == jaw and not r["pusat"]]
    cari = st.text_input("🔍 Cari nama / sekolah", key="am_pl_cari")
    if cari.strip():
        q = cari.strip().lower()
        pool = [r for r in pool if q in r["nama"].lower() or q in (r["nama_sek"] or "").lower() or q in r["sek"].lower()]
    pool = sorted(pool, key=lambda r: (r["nama_sek"] or r["sek"], r["nama"]))
    st.caption(f"{len(pool)} calon {jaw} belum ditempatkan")
    if not pool:
        st.warning("Tiada calon. SUP perlu mencadangkan jawatan ini dan menghantar ke PPD.")
        return
    df = pd.DataFrame([{"NAMA": r["nama"], "SEKOLAH ASAL": r["nama_sek"] or r["sek"], "KOD": r["sek"], "NO TELEFON": r["tel"]} for r in pool])
    ev = st.dataframe(df, use_container_width=True, hide_index=True, height=min(480, 60 + 35 * len(df)), on_select="rerun",
                      selection_mode="multi-row", key=f"am_pl_tbl_{pusat}_{jaw}")
    sel = [pool[i] for i in (ev.selection.rows if ev and ev.selection else []) if i < len(pool)]
    if st.button(f"✅ Tempatkan {len(sel)} {jaw} di {pusat}", type="primary", disabled=not sel, key="am_pl_ok"):
        ok = sum(1 for r in sel if _kemas(r, {"AMALI_PUSAT": pusat}))
        _semula()
        al._flash("success", f"✅ {ok} {jaw} ditempatkan di {pusat}. Teruskan di Sahkan Petugas.")
        st.rerun()


# ---------------------------------------------------------------- 3-5. Sahkan / Lantik / Semak
_TAHAP = {"sahkan": (-1, 1, "Sahkan Petugas", "✔️", "Calon petugas Amali: KP/TKP/PK SPM di pusat Amali dan PKS/PMP/PM yang telah ditempatkan."),
          "lantik": (1, 2, "Lantik", "👤", "Petugas yang telah disahkan. Lantik untuk meneruskan ke semakan."),
          "semak": (2, 3, "Semak", "🔍", "Semak senarai lantikan. Selepas disemak, ia boleh dijana suratnya.")}


def render_tahap(kod_ppd, kunci):
    dari, ke, tajuk, ikon, nota = _TAHAP[kunci]
    st.header(f"🔬 Lantikan Petugas Amali - {tajuk} - PPD {kod_ppd}")
    al._show_flash()
    ams = _ada_amali(kod_ppd)
    if not ams:
        return
    info = al.pusat_info(kod_ppd)
    _, rows = muat_semua(kod_ppd, ams)
    _bar(rows)
    st.caption(nota)
    if dari > 0 and not any(r["stage"] >= dari for r in rows):
        st.warning(f"Belum ada petugas di peringkat sebelumnya. Selesaikan dahulu langkah sebelum **{tajuk}**.")
    pool = [r for r in rows if r["layak"] and r["stage"] == dari]
    if not pool:
        st.success("✅ Tiada petugas menunggu di peringkat ini.")
    else:
        terpilih = _skop_pilih(pool, info, f"t_{kunci}")
        if st.button(f"{ikon} {tajuk} {len(terpilih)} petugas", type="primary", disabled=not terpilih, key=f"am_btn_{kunci}"):
            baru = {"AMALI_STAGE": ke, "AMALI_JAWATAN": ""}
            ok = 0
            for r in terpilih:
                b = {"AMALI_STAGE": ke, "AMALI_JAWATAN": r["jaw"]}
                if r["jn"] in ("KP", "TKP", "PK"):
                    b["AMALI_PUSAT"] = r["pusat"]
                if _kemas(r, b):
                    ok += 1
            _semula()
            al._flash("success", f"✅ {ok} petugas: {tajuk} selesai.")
            st.rerun()
    sudah = [r for r in rows if r["stage"] == ke]
    if sudah:
        with st.expander(f"↩️ Undur {len(sudah)} petugas di peringkat '{STAGE_NAMA[ke]}'"):
            sel = _skop_pilih(sudah, info, f"u_{kunci}")
            if st.button(f"↩️ Undur {len(sel)} petugas", disabled=not sel, key=f"am_und_{kunci}"):
                ok = 0
                for r in sel:
                    b = {"AMALI_STAGE": dari if dari > 0 else ""}
                    if r["jn"] in ("KP", "TKP", "PK"):
                        b["AMALI_JAWATAN"] = "" if dari < 0 else r["jaw"]
                    ok += 1 if _kemas(r, b) else 0
                _semula()
                al._flash("success", f"↩️ {ok} petugas diundur.")
                st.rerun()


# ---------------------------------------------------------------- 6. Jana Surat
def render_jana(kod_ppd):
    st.header(f"🔬 Lantikan Petugas Amali - Jana Surat - PPD {kod_ppd} - {core.PPD_MAP.get(kod_ppd, '')}")
    al._show_flash()
    ams = _ada_amali(kod_ppd)
    if not ams:
        return
    raw, rows = muat_semua(kod_ppd, ams)
    info = al.pusat_info(kod_ppd)
    _bar(rows)
    menunggu = [r for r in rows if r["layak"] and r["stage"] == 3]
    if not menunggu:
        if any(r["stage"] >= 4 for r in rows):
            st.success("✅ Semua petugas yang telah disemak sudah dijana suratnya. Pergi ke **Cetak Surat** / **Hantar ke Sekolah**.")
        else:
            st.warning("Belum ada petugas yang telah disemak. Selesaikan **Sahkan → Lantik → Semak** dahulu.")
        return
    jaw = st.selectbox("Pilih Jawatan Surat", ["(semua jawatan)"] + [j for j in JAWATAN_AMALI if any(r["jaw"] == j for r in menunggu)],
                       key="am_jana_jaw", format_func=lambda j: j if j.startswith("(") else f"{j} ({sum(1 for r in menunggu if r['jaw'] == j)})")
    src = menunggu if jaw.startswith("(") else [r for r in menunggu if r["jaw"] == jaw]
    st.markdown("### 🔐 No Surat Amali (siri berasingan daripada SPM)")
    a, b, c = st.columns([2, 1, 1])
    pref = a.text_input("No Rujukan Fail Amali", value=st.session_state.get(f"am_ruj_{kod_ppd}") or nsr.ruj_terkini(raw, amali=True),
                        key=f"am_ruj_in_{kod_ppd}", help="Mesti berbeza daripada no rujukan fail SPM.")
    mx = nsr.max_no(raw, pref, amali=True)
    mula = b.number_input("No bermula (turutan)", min_value=1, value=int(mx + 1), step=1, key=f"am_mula_{kod_ppd}_{mx}_{abs(hash(pref)) % 99991}")
    tarikh = c.date_input("Tarikh surat", value=datetime.date.today(), key=f"am_tarikh_{kod_ppd}")
    st.session_state[f"am_ruj_{kod_ppd}"] = pref
    if pref.strip() == nsr.ruj_terkini(raw, amali=False) and nsr._senarai_no(raw, False):
        st.error("No rujukan Amali sama dengan siri SPM. Tukar supaya berbeza.")
    st.caption(f"Turutan terakhir Amali: {mx if mx else '-'} | Contoh: {nsr.format_no(pref, int(mula))}")
    terpilih = _skop_pilih(src, info, "jana")
    terpilih = sorted(terpilih, key=lambda r: (JAWATAN_AMALI.index(r["jaw"]), r["pusat"], r["nama"]))
    if not terpilih:
        st.info("Pilih petugas (atau 'Pilih SEMUA') untuk dijana.")
        return
    nos = [nsr.format_no(pref, int(mula) + i) for i in range(len(terpilih))]
    st.caption(f"No surat: {nos[0]} hingga {nos[-1]}")
    if st.button(f"📄 Jana {len(terpilih)} Surat Amali", type="primary", key=f"am_jana_btn_{kod_ppd}"):
        ok, gagal = 0, []
        pb = st.progress(0)
        for i, (r, no) in enumerate(zip(terpilih, nos)):
            good = _kemas(r, {"AMALI_STAGE": 4, "AMALI_NO": no, "AMALI_JAWATAN": r["jaw"], "AMALI_TARIKH": str(tarikh),
                              **({"AMALI_PUSAT": r["pusat"]} if r["jn"] in ("KP", "TKP", "PK") else {})})
            ok += 1 if good else 0
            if not good:
                gagal.append(r["nama"])
            pb.progress((i + 1) / len(terpilih))
        _semula()
        al._flash("warning" if gagal else "success", (f"⚠️ {ok} dijana; gagal: " + ", ".join(gagal[:5])) if gagal else f"✅ {ok} surat dijana ({nos[0]} - {nos[-1]}). Cetak / hantar di submenu seterusnya.")
        st.rerun()


# ---------------------------------------------------------------- 7. Cetak Surat
def _item(r, info):
    return {"nama": r["nama"], "ic": r["ic"], "jawatan": r["jaw"], "sekolah_asal": r["sek"], "nama_sekolah_asal": r["nama_sek"] or r["sek"],
            "pusat": r["pusat"], "nama_pusat": _info_bk(info, r["pusat"]), "no_surat": r["no"]}


def render_cetak(kod_ppd):
    st.header(f"🔬 Lantikan Petugas Amali - Cetak Surat - PPD {kod_ppd} - {core.PPD_MAP.get(kod_ppd, '')}")
    al._show_flash()
    ams = _ada_amali(kod_ppd)
    if not ams:
        return
    _, rows = muat_semua(kod_ppd, ams)
    info = al.pusat_info(kod_ppd)
    surat = [r for r in rows if r["stage"] >= 4 and r["no"]]
    if not surat:
        st.info("Belum ada surat Amali dijana.")
        return
    st.caption("Muat turun ikut jawatan, ikut pusat atau keseluruhan. Muat turun tidak menghantar surat ke sekolah.")
    terpilih = _skop_pilih(surat, info, "cetak")
    terpilih = sorted(terpilih, key=lambda r: (JAWATAN_AMALI.index(r["jaw"]), r["pusat"], r["nama"]))
    if not terpilih:
        st.info("Pilih petugas atau 'Pilih SEMUA'.")
        return
    sig = "|".join(str(r["id"]) for r in terpilih)
    st.download_button("📊 Muat Turun Senarai (Excel)", core.to_excel(_jadual(terpilih, info)), file_name=f"senarai_amali_{kod_ppd}_{datetime.date.today()}.xlsx", key="am_dl_xl")
    items = [_item(r, info) for r in terpilih]
    b1, b2 = st.columns(2)
    if b1.button(f"📄 Jana PDF Kolektif ({len(items)})", key="am_gen_pdf"):
        with st.spinner("Menjana PDF..."):
            st.session_state["am_pdf"] = (sig, al._muat_pdf(items, kod_ppd))
    if b2.button(f"📦 Jana ZIP Individu ({len(items)})", key="am_gen_zip"):
        with st.spinner("Menjana ZIP..."):
            st.session_state["am_zip"] = (sig, al._muat_zip(items, kod_ppd))
    p = st.session_state.get("am_pdf")
    if p and p[0] == sig:
        for n, bts in p[1]:
            st.download_button(f"📥 PDF Kolektif {n}", bts, file_name=f"Surat_Amali_Kolektif_{kod_ppd}_{n}.pdf", mime="application/pdf", key=f"am_dlp_{n}")
    z = st.session_state.get("am_zip")
    if z and z[0] == sig:
        for n, bts in z[1]:
            st.download_button(f"📦 ZIP Individu {n}", bts, file_name=f"Surat_Amali_Individu_{kod_ppd}_{n}.zip", mime="application/zip", key=f"am_dlz_{n}")


# ---------------------------------------------------------------- 8. Hantar ke Sekolah
def render_hantar(kod_ppd):
    st.header(f"🔬 Lantikan Petugas Amali - Hantar ke Sekolah - PPD {kod_ppd} - {core.PPD_MAP.get(kod_ppd, '')}")
    al._show_flash()
    ams = _ada_amali(kod_ppd)
    if not ams:
        return
    _, rows = muat_semua(kod_ppd, ams)
    info = al.pusat_info(kod_ppd)
    surat = [r for r in rows if r["stage"] >= 4 and r["no"]]
    if not surat:
        st.info("Belum ada surat Amali dijana.")
        return
    tunggu = [r for r in surat if r["stage"] == 4]
    hantar = [r for r in surat if r["stage"] == 5]
    c1, c2 = st.columns(2)
    c1.metric("⏳ Menunggu hantar", len(tunggu))
    c2.metric("✅ Sudah dihantar", len(hantar))
    if tunggu:
        terpilih = _skop_pilih(tunggu, info, "hantar")
        if terpilih:
            yakin = st.checkbox(f"Saya sahkan hantar {len(terpilih)} surat Amali ke sekolah asal", key="am_ht_yakin")
            if st.button(f"📤 Hantar {len(terpilih)} Surat ke Sekolah", type="primary", disabled=not yakin, key="am_ht_btn"):
                ok = sum(1 for r in terpilih if _kemas(r, {"AMALI_STAGE": 5, "AMALI_TARIKH_HANTAR": str(datetime.date.today())}))
                _semula()
                al._flash("success", f"✅ {ok} surat Amali dihantar ke sekolah asal.")
                st.rerun()
    else:
        st.success("✅ Semua surat Amali sudah dihantar.")
    if hantar:
        with st.expander(f"↩️ Tarik balik penghantaran ({len(hantar)})"):
            sel = _skop_pilih(hantar, info, "tarik")
            if st.button(f"↩️ Tarik balik {len(sel)} surat", disabled=not sel, key="am_tb_btn"):
                ok = sum(1 for r in sel if _kemas(r, {"AMALI_STAGE": 4, "AMALI_TARIKH_HANTAR": ""}))
                _semula()
                al._flash("success", f"↩️ {ok} surat ditarik balik.")
                st.rerun()
    if tunggu:
        with st.expander("🗑️ Padam surat dijana (untuk jana semula)"):
            sel = _skop_pilih(tunggu, info, "padam")
            if st.button(f"🗑️ Padam {len(sel)} surat", disabled=not sel, key="am_pd_btn"):
                ok = sum(1 for r in sel if _kemas(r, {"AMALI_STAGE": 3, "AMALI_NO": "", "AMALI_TARIKH": ""}))
                _semula()
                al._flash("success", f"🗑️ {ok} surat dipadam; kembali ke peringkat Disemak.")
                st.rerun()


# ---------------------------------------------------------------- penghantar menu
def render_menu(kod_ppd, fly_cur):
    f = fly_cur or "pusat"
    if f == "pusat":
        render_pusat(kod_ppd)
    elif f == "tempat":
        render_penempatan(kod_ppd)
    elif f in _TAHAP:
        render_tahap(kod_ppd, f)
    elif f == "jana":
        render_jana(kod_ppd)
    elif f == "cetak":
        render_cetak(kod_ppd)
    else:
        render_hantar(kod_ppd)


# ============================================================ SUP: surat Lantikan - sub menu SPM / Amali
def render_surat_sup(kod_sekolah, kod_ppd, df_cad):
    """Surat Lantikan Amali yang telah dihantar ke sekolah ini (sub menu Amali)."""
    items = []
    if df_cad is not None and len(df_cad):
        for _, r in df_cad.iterrows():
            d = _kdata(r)
            try:
                stg = int(d.get("AMALI_STAGE"))
            except Exception:
                stg = -1
            if stg == 5 and _s(d.get("AMALI_NO")):
                bk = _s(d.get("AMALI_PUSAT"))
                items.append({"nama": _s(r.get("NAMA_GURU") or r.get("nama_guru")), "ic": _s(r.get("IC_GURU") or r.get("ic_guru")),
                              "jawatan": _s(d.get("AMALI_JAWATAN")), "sekolah_asal": _s(r.get("KOD_SEKOLAH_ASAL") or r.get("kod_sekolah_asal") or kod_sekolah),
                              "nama_sekolah_asal": _s(r.get("NAMA_SEKOLAH_ASAL") or r.get("nama_sekolah_asal")),
                              "pusat": bk, "nama_pusat": "", "no_surat": _s(d.get("AMALI_NO")), "tel": _s(r.get("TELEFON_GURU") or r.get("telefon_guru"))})
    st.markdown("#### 🔬 Surat Lantikan Ujian Amali Sains")
    if not items:
        st.info("Belum ada surat lantikan Amali Sains yang dihantar PPD ke sekolah ini.")
        return
    st.dataframe(pd.DataFrame([{"NAMA": i["nama"], "JAWATAN": i["jawatan"], "PUSAT/BK": i["pusat"], "NO SURAT": i["no_surat"]} for i in items]),
                 use_container_width=True, hide_index=True)
    ppd_name = core.PPD_MAP.get(kod_ppd, "")
    if st.button("📦 Jana ZIP Surat Amali", key=f"am_sup_zip_{kod_sekolah}"):
        z = core.create_zip_pukal_dari_JPN(items, kod_ppd, ppd_name)
        if z:
            st.session_state[f"am_sup_z_{kod_sekolah}"] = z
    if st.session_state.get(f"am_sup_z_{kod_sekolah}"):
        st.download_button("📥 Muat Turun ZIP Surat Amali", st.session_state[f"am_sup_z_{kod_sekolah}"],
                           file_name=f"Surat_Amali_{kod_sekolah}.zip", mime="application/zip", key=f"am_sup_dl_{kod_sekolah}")
