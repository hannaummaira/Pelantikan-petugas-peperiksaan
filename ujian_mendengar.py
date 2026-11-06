# -*- coding: utf-8 -*-
"""ujian_mendengar.py - Pelantikan Petugas Ujian Mendengar (selari dengan SPM bertulis).

Orang dan pusat SAMA seperti SPM (tiada pemilihan pusat). Hanya surat berbeza:
   Penyelia Kawasan  -> "Penyelia Kawasan Ujian Mendengar"
   Ketua Pengawas    -> "Ketua Pengawas Ujian Mendengar"
   Timbalan KP       -> "Timbalan Ketua Pengawas Ujian Mendengar"
   Pengawas Peperiksaan -> "Pengawas Ujian Mendengar"
Surat disimpan pada rekod petugas SPM yang sama (data.UM_STAGE / UM_NO / UM_JAWATAN / UM_TARIKH / UM_TARIKH_HANTAR / UM_KECUAL / UM_PUSAT)
- tiada rekod pendua, tiada jadual baharu. No surat dalam siri sendiri (berasingan daripada SPM dan Amali Sains).
Peringkat: Belum disemak (-1) -> Disemak (1) -> Dilantik (2) -> Surat dijana (4) -> Dihantar ke sekolah asal (5).
"""
import datetime
import json

import pandas as pd
import streamlit as st

import spm_core as core
import no_surat as nsr
import ppd_aliran as al
from kuota_pusat import _data as _kdata
from lengkap_petugas import lengkapkan

UM_PK = "Penyelia Kawasan Ujian Mendengar"
UM_KP = "Ketua Pengawas Ujian Mendengar"
UM_TKP = "Timbalan Ketua Pengawas Ujian Mendengar"
UM_PP = "Pengawas Ujian Mendengar"
JAWATAN_UM = [UM_PK, UM_KP, UM_TKP, UM_PP]
_JAW = {"PK": UM_PK, "KP": UM_KP, "TKP": UM_TKP, "PP": UM_PP}
STAGE_NAMA = {-1: "Belum disemak", 1: "Disemak", 2: "Dilantik", 4: "Surat dijana", 5: "Dihantar ke sekolah"}
FLY_UM = [("semak", "🔍 Semak Petugas"), ("lantik", "👤 Lantik Petugas"), ("jana", "📄 Jana Surat"),
          ("cetak", "🖨️ Cetak / Muat Turun Surat"), ("hantar", "📤 Hantar ke Sekolah")]
_PK_BUANG = ("TERPILIH", "SIMPANAN", "BATAL")


def _s(v):
    x = "" if v is None else str(v).strip()
    return "" if x.lower() in ("nan", "none", "null", "nat") else x


def is_um_jaw(j):
    return "UJIAN MENDENGAR" in " ".join(str(j or "").upper().split())


def default_template(jawatan):
    j = " ".join(str(jawatan or "").upper().split())
    return ("<div style='font-family:Arial; padding:25px; border:1px solid #000;'><table style='width:100%; border:none;'><tr>"
            "<td style='width:80px; vertical-align:top; border:none;'><img src='https://upload.wikimedia.org/wikipedia/commons/2/2a/Coat_of_arms_of_Malaysia.svg' style='width:70px;'></td>"
            "<td style='vertical-align:top; border:none; text-align:left;'><b>KEMENTERIAN PENDIDIKAN MALAYSIA</b><br>JABATAN PENDIDIKAN NEGERI SELANGOR<br>"
            "<small>Persiaran Tengku Ampuan Rahimah, Seksyen 20, 40300 Shah Alam, Selangor</small></td></tr></table>"
            "<hr style='border:2px solid #000; margin:10px 0;'><div style='text-align:right; font-size:10pt;'>Ruj. Kami: {{NO_SURAT}}<br>Tarikh: {{TARIKH}}</div>"
            "<div style='font-size:10pt; margin-top:12px;'><b>{{NAMA}}</b><br>Melalui:<br>PENGETUA<br><b>{{NAMA_SEKOLAH_ASAL}}</b><br>{{PPD}}<br><br>Tuan/Puan,<br>"
            f"<b>UJIAN MENDENGAR SPM {{{{TAHUN}}}} : PELANTIKAN SEBAGAI {j}</b><br><br>"
            "2. Dengan ini tuan/puan dilantik sebagai <b>{{JAWATAN}}</b> Ujian Mendengar SPM {{TAHUN}} di {{PUSAT}} - {{NAMA_PUSAT}}<br>"
            "Bilik Kebal: {{BILIK_KEBAL}}<br>Sekolah Asal: {{SEKOLAH_ASAL}} - {{NAMA_SEKOLAH_ASAL}}<br>No Surat: {{NO_SURAT}}<br><br>"
            "3. Sulit - Akta Rahsia Rasmi 1972<br><br>MALAYSIA MADANI<br>BERKHIDMAT UNTUK NEGARA<br><br>(DATIN WAN NOR ASHIKIN)<br>Pengarah JPN Selangor</div></div>")


def _jenis(jaw):
    j = " ".join(str(jaw or "").upper().split())
    if not j or "AMALI" in j or "KANAN SAINS" in j or "MATA PELAJARAN" in j or "MAKMAL" in j or "HOSPITAL" in j or "PENGIRING" in j or "UJIAN MENDENGAR" in j:
        return ""
    if "PENYELIA" in j:
        return "PK"
    if "TIMBALAN" in j and "KETUA" in j:
        return "TKP"
    if "KETUA" in j and "PENGAWAS" in j:
        return "KP"
    if "PENGAWAS" in j and "PEPERIKSAAN" in j:
        return "PP"
    return ""


def _list(v):
    if isinstance(v, (list, tuple)):
        return [_s(x).upper() for x in v if _s(x)]
    if isinstance(v, str):
        return [x.strip().upper() for x in v.split(",") if x.strip()]
    return []


def _benar(v):
    return str(v).strip().lower() in ("1", "true", "ya")


def muat_semua(kod_ppd):
    """Petugas SPM PPD yang layak ke Ujian Mendengar. Pulang (raw, rows)."""
    try:
        raw = pd.DataFrame(core.supa.table("cadangan_sup").select("*").eq("kod_ppd", kod_ppd).limit(10000).execute().data or [])
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
        ov = _s(d.get("UM_PUSAT")).upper()
        if jn == "PK":
            bk = al._g(r, d, "kod_bilik_kebal_explicit", "kod_bilik_kebal", "KOD_BILIK_KEBAL").upper() or spm_pusat
            if any(x in status.upper() for x in _PK_BUANG):
                bk = ""
            pusat = ov or bk
        else:
            pusat = ov or (spm_pusat if spm_rank >= 0 else "")
        kecuali = _benar(d.get("UM_KECUAL"))
        layak = bool(pusat) and not kecuali
        try:
            stg = int(d.get("UM_STAGE")) if _s(d.get("UM_STAGE")) != "" else -1
        except Exception:
            stg = -1
        rows.append({"id": al._pyid(r0.get("id")), "nama": al._g(r, d, "NAMA_GURU", "nama_guru"), "ic": al._g(r, d, "IC_GURU", "ic_guru"),
                     "jn": jn, "jaw_spm": jaw, "jaw": _JAW[jn],
                     "sek": al._g(r, d, "KOD_SEKOLAH_ASAL", "kod_sekolah_asal", "KOD_SEKOLAH", "kod_sekolah").upper(),
                     "nama_sek": al._g(r, d, "NAMA_SEKOLAH_ASAL", "nama_sekolah_asal"), "tel": al._g(r, d, "TELEFON_GURU", "telefon_guru"),
                     "pusat": pusat, "layak": layak, "kecuali": kecuali, "spm_rank": spm_rank, "stage": stg if layak else -1,
                     "data": d, "data_str": isinstance(r0.get("data"), str), "no": _s(d.get("UM_NO")),
                     "tarikh": _s(d.get("UM_TARIKH")), "tarikh_hantar": _s(d.get("UM_TARIKH_HANTAR"))})
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


def _semula():
    al._clear()


def _bar(rows):
    c = {k: 0 for k in (-1, 1, 2, 4, 5)}
    for r in rows:
        if r["layak"]:
            c[r["stage"] if r["stage"] in c else -1] += 1
    cols = st.columns(5)
    for col, k in zip(cols, (-1, 1, 2, 4, 5)):
        col.metric(STAGE_NAMA[k], c[k])


def _jadual(rows, info):
    return pd.DataFrame([{"JAWATAN SURAT": r["jaw"], "PUSAT/BK": r["pusat"], "NAMA PUSAT/BK": info.get(r["pusat"], {}).get("nama", ""), "NAMA": r["nama"],
                          "IC": r["ic"], "SEKOLAH ASAL": r["nama_sek"] or r["sek"], "NO TELEFON": r["tel"], "NO SURAT": r["no"],
                          "PERINGKAT": STAGE_NAMA.get(r["stage"], "Belum disemak")} for r in rows])


def _skop_pilih(rows, info, kunci):
    if not rows:
        return []
    jaws = [j for j in JAWATAN_UM if any(r["jaw"] == j for r in rows)]
    c1, c2 = st.columns(2)
    jf = c1.multiselect("Jawatan", jaws, default=[], key=f"um_jf_{kunci}", format_func=lambda j: f"{j} ({sum(1 for r in rows if r['jaw'] == j)})")
    pf = c2.multiselect("Pusat / Bilik Kebal", sorted({r["pusat"] for r in rows}), default=[], key=f"um_pf_{kunci}")
    sub = sorted([r for r in rows if (not jf or r["jaw"] in jf) and (not pf or r["pusat"] in pf)],
                 key=lambda r: (r["pusat"], JAWATAN_UM.index(r["jaw"]), r["nama"]))
    st.caption(f"{len(sub)} dipaparkan" + ("" if jf or pf else " (semua - tapis jawatan/pusat jika perlu)"))
    if not sub:
        return []
    if st.checkbox(f"Pilih SEMUA {len(sub)} yang dipaparkan", key=f"um_all_{kunci}_{len(sub)}"):
        st.dataframe(_jadual(sub, info), use_container_width=True, hide_index=True, height=min(360, 40 + 35 * len(sub)))
        return sub
    ev = st.dataframe(_jadual(sub, info), use_container_width=True, hide_index=True, height=min(360, 40 + 35 * len(sub)),
                      on_select="rerun", selection_mode="multi-row", key=f"um_tbl_{kunci}_{len(sub)}")
    return [sub[i] for i in (ev.selection.rows if ev and ev.selection else []) if i < len(sub)]


def _ringkas(rows, info):
    out = []
    for p in sorted({r["pusat"] for r in rows if r["layak"]}):
        ada = [r for r in rows if r["layak"] and r["pusat"] == p]
        d = {"PUSAT/BK": p, "NAMA": info.get(p, {}).get("nama", "")}
        for jn in ("PK", "KP", "TKP", "PP"):
            d[jn] = sum(1 for r in ada if r["jn"] == jn)
        d["JUMLAH"] = len(ada)
        out.append(d)
    return pd.DataFrame(out)


def _tajuk(teks, kod_ppd):
    st.header(f"🎧 Lantikan Petugas Ujian Mendengar - {teks} - PPD {kod_ppd} - {core.PPD_MAP.get(kod_ppd, '')}")
    al._show_flash()


# ---------------------------------------------------------------- Semak Petugas (boleh ubah)
def render_semak(kod_ppd):
    _tajuk("Semak Petugas", kod_ppd)
    info = al.pusat_info(kod_ppd)
    _, rows = muat_semua(kod_ppd)
    _bar(rows)
    st.caption("Petugas SPM (Penyelia Kawasan, KP, TKP dan Pengawas Peperiksaan) di pusat yang sama terus ditarik. Semak, dan ubah / ganti jika perlu, kemudian Lantik.")
    belum = [r for r in rows if r["layak"] and r["stage"] == -1]
    sudah = [r for r in rows if r["layak"] and r["stage"] == 1]
    kel = [r for r in rows if r["kecuali"]]
    t1, t2, t3 = st.tabs([f"🔍 Semak ({len(belum)})", "✏️ Ubah / Ganti", f"↩️ Dikeluarkan / Disemak ({len(kel) + len(sudah)})"])
    with t1:
        rs = _ringkas(rows, info)
        if len(rs):
            with st.expander("📋 Ringkasan ikut pusat"):
                st.dataframe(rs, use_container_width=True, hide_index=True)
        if not belum:
            st.success("✅ Tiada petugas menunggu semakan." if rows else "Belum ada petugas SPM yang ditempatkan.")
        else:
            terpilih = _skop_pilih(belum, info, "semak")
            if st.button(f"🔍 Tandakan {len(terpilih)} petugas sebagai disemak", type="primary", disabled=not terpilih, key="um_sm_ok"):
                ok = sum(1 for r in terpilih if _kemas(r, {"UM_STAGE": 1, "UM_JAWATAN": r["jaw"], "UM_PUSAT": r["pusat"]}))
                _semula()
                al._flash("success", f"✅ {ok} petugas disemak.")
                st.rerun()
    with t2:
        st.markdown("##### 🗑️ Keluarkan petugas daripada Ujian Mendengar")
        boleh = [r for r in rows if r["layak"] and r["stage"] in (-1, 1)]
        if not boleh:
            st.info("Tiada petugas yang boleh dikeluarkan.")
        else:
            sel = _skop_pilih(boleh, info, "kel")
            if st.button(f"🗑️ Keluarkan {len(sel)} petugas", disabled=not sel, key="um_kel_btn"):
                ok = sum(1 for r in sel if _kemas(r, {"UM_KECUAL": True, "UM_STAGE": ""}))
                _semula()
                al._flash("success", f"🗑️ {ok} petugas dikeluarkan (kekal sebagai petugas SPM). Boleh dipulihkan atau digantikan.")
                st.rerun()
        st.markdown("##### ➕ Ganti / tambah petugas")
        jn_pilih = st.radio("Jawatan", ["PK", "KP", "TKP", "PP"], horizontal=True, key="um_gt_jn",
                            format_func=lambda x: {"PK": "Penyelia Kawasan", "KP": "Ketua Pengawas", "TKP": "Timbalan KP", "PP": "Pengawas"}[x])
        pusat_semua = sorted({r["pusat"] for r in rows if r["pusat"]})
        pusat_t = st.selectbox("Pusat / Bilik Kebal", pusat_semua, format_func=lambda p: f"{p} - {info.get(p, {}).get('nama', '')[:35]}", key="um_gt_pusat") if pusat_semua else None
        pool = [r for r in rows if r["jn"] == jn_pilih and (not r["layak"])]
        cari = st.text_input("🔍 Cari nama / sekolah", key="um_gt_cari")
        if cari.strip():
            q = cari.strip().lower()
            pool = [r for r in pool if q in r["nama"].lower() or q in (r["nama_sek"] or "").lower()]
        pool = sorted(pool, key=lambda r: (r["nama_sek"] or r["sek"], r["nama"]))
        st.caption(f"{len(pool)} petugas SPM jawatan ini yang belum di Ujian Mendengar (belum ditempatkan atau dikeluarkan)")
        if pool and pusat_t:
            df = pd.DataFrame([{"NAMA": r["nama"], "SEKOLAH ASAL": r["nama_sek"] or r["sek"], "NO TELEFON": r["tel"],
                                "STATUS": "Dikeluarkan" if r["kecuali"] else "Belum ditempatkan SPM"} for r in pool])
            ev = st.dataframe(df, use_container_width=True, hide_index=True, height=min(380, 60 + 35 * len(df)), on_select="rerun",
                              selection_mode="multi-row", key=f"um_gt_tbl_{jn_pilih}_{len(pool)}")
            sel = [pool[i] for i in (ev.selection.rows if ev and ev.selection else []) if i < len(pool)]
            if st.button(f"✅ Tambah {len(sel)} petugas ke {pusat_t}", type="primary", disabled=not sel, key="um_gt_ok"):
                ok = sum(1 for r in sel if _kemas(r, {"UM_KECUAL": False, "UM_STAGE": "", "UM_PUSAT": pusat_t}))
                _semula()
                al._flash("success", f"✅ {ok} petugas ditambah. Semak semula di tab Semak.")
                st.rerun()
    with t3:
        if kel:
            st.markdown("##### Dikeluarkan daripada Ujian Mendengar")
            sel = _skop_pilih([dict(r, layak=True) for r in kel], info, "pulih")
            if st.button(f"↩️ Pulihkan {len(sel)} petugas", disabled=not sel, key="um_pulih"):
                ok = sum(1 for r in sel if _kemas(r, {"UM_KECUAL": False, "UM_STAGE": ""}))
                _semula()
                al._flash("success", f"↩️ {ok} petugas dipulihkan.")
                st.rerun()
        if sudah:
            st.markdown("##### Telah disemak (boleh diundur)")
            sel = _skop_pilih(sudah, info, "undur_sm")
            if st.button(f"↩️ Undur {len(sel)} ke belum disemak", disabled=not sel, key="um_undur_sm"):
                ok = sum(1 for r in sel if _kemas(r, {"UM_STAGE": ""}))
                _semula()
                al._flash("success", f"↩️ {ok} petugas diundur.")
                st.rerun()
        if not kel and not sudah:
            st.info("Tiada petugas dikeluarkan atau disemak.")


# ---------------------------------------------------------------- Lantik Petugas
def render_lantik(kod_ppd):
    _tajuk("Lantik Petugas", kod_ppd)
    info = al.pusat_info(kod_ppd)
    _, rows = muat_semua(kod_ppd)
    _bar(rows)
    if not any(r["layak"] and r["stage"] >= 1 for r in rows):
        st.warning("Belum ada petugas yang disemak. Selesaikan **Semak Petugas** dahulu.")
    pool = [r for r in rows if r["layak"] and r["stage"] == 1]
    if not pool:
        st.success("✅ Tiada petugas menunggu untuk dilantik.")
    else:
        terpilih = _skop_pilih(pool, info, "lantik")
        if st.button(f"👤 Lantik {len(terpilih)} petugas", type="primary", disabled=not terpilih, key="um_lantik_btn"):
            ok = sum(1 for r in terpilih if _kemas(r, {"UM_STAGE": 2, "UM_JAWATAN": r["jaw"], "UM_PUSAT": r["pusat"]}))
            _semula()
            al._flash("success", f"✅ {ok} petugas dilantik. Teruskan ke Jana Surat.")
            st.rerun()
    sudah = [r for r in rows if r["layak"] and r["stage"] == 2]
    if sudah:
        with st.expander(f"↩️ Undur {len(sudah)} petugas yang dilantik"):
            sel = _skop_pilih(sudah, info, "undur_lt")
            if st.button(f"↩️ Undur {len(sel)} petugas", disabled=not sel, key="um_undur_lt"):
                ok = sum(1 for r in sel if _kemas(r, {"UM_STAGE": 1}))
                _semula()
                al._flash("success", f"↩️ {ok} petugas diundur ke Disemak.")
                st.rerun()


# ---------------------------------------------------------------- Jana Surat
def render_jana(kod_ppd):
    _tajuk("Jana Surat", kod_ppd)
    raw, rows = muat_semua(kod_ppd)
    info = al.pusat_info(kod_ppd)
    _bar(rows)
    menunggu = [r for r in rows if r["layak"] and r["stage"] == 2]
    if not menunggu:
        _l = [r for r in rows if r["layak"]]
        if _l:
            _n = lambda k: sum(1 for r in _l if r["stage"] == k)
            st.info(f"Belum disemak: {_n(-1)} → **Semak Petugas**. Disemak: {_n(1)} → **Lantik Petugas**. Jana hanya untuk yang **Dilantik** ({_n(2)}).")
        elif not rows:
            st.info("Tiada petugas SPM yang ditempatkan. Siapkan penempatan SPM dahulu.")
        if any(r["stage"] >= 4 for r in rows):
            st.success("✅ Semua petugas yang dilantik sudah dijana suratnya. Pergi ke **Cetak / Muat Turun** atau **Hantar ke Sekolah**.")
        return
    jaw = st.selectbox("Pilih Jawatan Surat", ["(semua jawatan)"] + [j for j in JAWATAN_UM if any(r["jaw"] == j for r in menunggu)],
                       key="um_jana_jaw", format_func=lambda j: j if j.startswith("(") else f"{j} ({sum(1 for r in menunggu if r['jaw'] == j)})")
    src = menunggu if jaw.startswith("(") else [r for r in menunggu if r["jaw"] == jaw]
    st.markdown("### 🔐 No Surat Ujian Mendengar (siri berasingan daripada SPM dan Amali Sains)")
    a, b, c = st.columns([2, 1, 1])
    pref = a.text_input("No Rujukan Fail Ujian Mendengar", value=st.session_state.get(f"um_ruj_{kod_ppd}") or nsr.ruj_terkini_um(raw),
                        key=f"um_ruj_in_{kod_ppd}", help="Mesti berbeza daripada no rujukan fail SPM dan Amali Sains.")
    mx = nsr.max_no_um(raw, pref)
    mula = b.number_input("No bermula (turutan)", min_value=1, value=int(mx + 1), step=1, key=f"um_mula_{kod_ppd}_{mx}_{abs(hash(pref)) % 99991}")
    tarikh = c.date_input("Tarikh surat", value=datetime.date.today(), key=f"um_tarikh_{kod_ppd}")
    st.session_state[f"um_ruj_{kod_ppd}"] = pref
    ps = pref.strip()
    if ps in (nsr.ruj_terkini(raw, amali=False) if nsr._senarai_no(raw, False) else None, nsr.ruj_terkini(raw, amali=True) if nsr._senarai_no(raw, True) else None):
        st.error("No rujukan sama dengan siri SPM atau Amali Sains. Tukar supaya berbeza.")
    st.caption(f"Turutan terakhir Ujian Mendengar: {mx if mx else '-'} | Contoh: {nsr.format_no(pref, int(mula))}")
    terpilih = sorted(_skop_pilih(src, info, "jana"), key=lambda r: (JAWATAN_UM.index(r["jaw"]), r["pusat"], r["nama"]))
    if not terpilih:
        st.info("Pilih petugas (atau 'Pilih SEMUA') untuk dijana.")
        return
    nos = [nsr.format_no(pref, int(mula) + i) for i in range(len(terpilih))]
    st.caption(f"No surat: {nos[0]} hingga {nos[-1]}")
    if st.button(f"📄 Jana {len(terpilih)} Surat Ujian Mendengar", type="primary", key=f"um_jana_btn_{kod_ppd}"):
        ok, gagal = 0, []
        pb = st.progress(0)
        for i, (r, no) in enumerate(zip(terpilih, nos)):
            good = _kemas(r, {"UM_STAGE": 4, "UM_NO": no, "UM_JAWATAN": r["jaw"], "UM_TARIKH": str(tarikh), "UM_PUSAT": r["pusat"]})
            ok += 1 if good else 0
            if not good:
                gagal.append(r["nama"])
            pb.progress((i + 1) / len(terpilih))
        _semula()
        al._flash("warning" if gagal else "success", (f"⚠️ {ok} dijana; gagal: " + ", ".join(gagal[:5])) if gagal else f"✅ {ok} surat dijana ({nos[0]} - {nos[-1]}).")
        st.rerun()


# ---------------------------------------------------------------- Cetak / Muat Turun
def _item(r, info):
    return {"nama": r["nama"], "ic": r["ic"], "jawatan": r["jaw"], "sekolah_asal": r["sek"], "nama_sekolah_asal": r["nama_sek"] or r["sek"],
            "pusat": r["pusat"], "nama_pusat": info.get(r["pusat"], {}).get("nama", ""), "no_surat": r["no"]}


def render_cetak(kod_ppd):
    _tajuk("Cetak / Muat Turun Surat", kod_ppd)
    _, rows = muat_semua(kod_ppd)
    info = al.pusat_info(kod_ppd)
    surat = [r for r in rows if r["stage"] >= 4 and r["no"]]
    if not surat:
        st.info("Belum ada surat Ujian Mendengar dijana.")
        return
    st.caption("Muat turun ikut jawatan, ikut pusat atau keseluruhan. Muat turun tidak menghantar surat ke sekolah.")
    terpilih = sorted(_skop_pilih(surat, info, "cetak"), key=lambda r: (JAWATAN_UM.index(r["jaw"]), r["pusat"], r["nama"]))
    if not terpilih:
        st.info("Pilih petugas atau 'Pilih SEMUA'.")
        return
    sig = "|".join(str(r["id"]) for r in terpilih)
    st.download_button("📊 Muat Turun Senarai (Excel)", core.to_excel(_jadual(terpilih, info)), file_name=f"senarai_ujian_mendengar_{kod_ppd}_{datetime.date.today()}.xlsx", key="um_dl_xl")
    items = [_item(r, info) for r in terpilih]
    b1, b2 = st.columns(2)
    if b1.button(f"📄 Jana PDF Kolektif ({len(items)})", key="um_gen_pdf"):
        with st.spinner("Menjana PDF..."):
            st.session_state["um_pdf"] = (sig, al._muat_pdf(items, kod_ppd))
    if b2.button(f"📦 Jana ZIP Individu ({len(items)})", key="um_gen_zip"):
        with st.spinner("Menjana ZIP..."):
            st.session_state["um_zip"] = (sig, al._muat_zip(items, kod_ppd))
    p = st.session_state.get("um_pdf")
    if p and p[0] == sig:
        for n, bts in p[1]:
            st.download_button(f"📥 PDF Kolektif {n}", bts, file_name=f"Surat_UM_Kolektif_{kod_ppd}_{n}.pdf", mime="application/pdf", key=f"um_dlp_{n}")
    z = st.session_state.get("um_zip")
    if z and z[0] == sig:
        for n, bts in z[1]:
            st.download_button(f"📦 ZIP Individu {n}", bts, file_name=f"Surat_UM_Individu_{kod_ppd}_{n}.zip", mime="application/zip", key=f"um_dlz_{n}")


# ---------------------------------------------------------------- Hantar ke Sekolah Asal
def render_hantar(kod_ppd):
    _tajuk("Hantar ke Sekolah", kod_ppd)
    _, rows = muat_semua(kod_ppd)
    info = al.pusat_info(kod_ppd)
    surat = [r for r in rows if r["stage"] >= 4 and r["no"]]
    if not surat:
        st.info("Belum ada surat Ujian Mendengar dijana.")
        return
    tunggu = [r for r in surat if r["stage"] == 4]
    hantar = [r for r in surat if r["stage"] == 5]
    c1, c2 = st.columns(2)
    c1.metric("⏳ Menunggu hantar", len(tunggu))
    c2.metric("✅ Sudah dihantar", len(hantar))
    if tunggu:
        terpilih = _skop_pilih(tunggu, info, "hantar")
        if terpilih:
            yakin = st.checkbox(f"Saya sahkan hantar {len(terpilih)} surat Ujian Mendengar ke sekolah asal", key="um_ht_yakin")
            if st.button(f"📤 Hantar {len(terpilih)} Surat ke Sekolah Asal", type="primary", disabled=not yakin, key="um_ht_btn"):
                ok = sum(1 for r in terpilih if _kemas(r, {"UM_STAGE": 5, "UM_TARIKH_HANTAR": str(datetime.date.today())}))
                _semula()
                al._flash("success", f"✅ {ok} surat dihantar ke sekolah asal.")
                st.rerun()
    else:
        st.success("✅ Semua surat Ujian Mendengar sudah dihantar.")
    if hantar:
        with st.expander(f"↩️ Tarik balik penghantaran ({len(hantar)})"):
            sel = _skop_pilih(hantar, info, "tarik")
            if st.button(f"↩️ Tarik balik {len(sel)} surat", disabled=not sel, key="um_tb_btn"):
                ok = sum(1 for r in sel if _kemas(r, {"UM_STAGE": 4, "UM_TARIKH_HANTAR": ""}))
                _semula()
                al._flash("success", f"↩️ {ok} surat ditarik balik.")
                st.rerun()
    if tunggu:
        with st.expander("🗑️ Padam surat dijana (untuk jana semula)"):
            sel = _skop_pilih(tunggu, info, "padam")
            if st.button(f"🗑️ Padam {len(sel)} surat", disabled=not sel, key="um_pd_btn"):
                ok = sum(1 for r in sel if _kemas(r, {"UM_STAGE": 2, "UM_NO": "", "UM_TARIKH": ""}))
                _semula()
                al._flash("success", f"🗑️ {ok} surat dipadam; kembali ke peringkat Dilantik.")
                st.rerun()


def render_menu(kod_ppd, fly_cur):
    f = fly_cur or "semak"
    if f == "semak":
        render_semak(kod_ppd)
    elif f == "lantik":
        render_lantik(kod_ppd)
    elif f == "jana":
        render_jana(kod_ppd)
    elif f == "cetak":
        render_cetak(kod_ppd)
    else:
        render_hantar(kod_ppd)


# ============================================================ SUP: surat Ujian Mendengar yang dihantar ke sekolah asal
def render_surat_sup(kod_sekolah, kod_ppd, df_cad):
    items = []
    if df_cad is not None and len(df_cad):
        for _, r in df_cad.iterrows():
            d = dict(_kdata(r))
            for _k in ("UM_STAGE", "UM_NO", "UM_JAWATAN", "UM_PUSAT"):      # get_cadangan_df menggabung data ke lajur biasa
                if _s(d.get(_k)) == "" and _s(r.get(_k)) != "":
                    d[_k] = r.get(_k)
            try:
                stg = int(d.get("UM_STAGE"))
            except Exception:
                stg = -1
            if stg == 5 and _s(d.get("UM_NO")):
                items.append({"nama": _s(r.get("NAMA_GURU") or r.get("nama_guru")), "ic": _s(r.get("IC_GURU") or r.get("ic_guru")),
                              "jawatan": _s(d.get("UM_JAWATAN")), "sekolah_asal": _s(r.get("KOD_SEKOLAH_ASAL") or r.get("kod_sekolah_asal") or kod_sekolah),
                              "nama_sekolah_asal": _s(r.get("NAMA_SEKOLAH_ASAL") or r.get("nama_sekolah_asal")),
                              "pusat": _s(d.get("UM_PUSAT")), "nama_pusat": "", "no_surat": _s(d.get("UM_NO")), "tel": _s(r.get("TELEFON_GURU") or r.get("telefon_guru"))})
    st.markdown("#### 🎧 Surat Lantikan Ujian Mendengar")
    if not items:
        st.info("Belum ada surat lantikan Ujian Mendengar yang dihantar PPD ke sekolah ini.")
        return
    st.dataframe(pd.DataFrame([{"NAMA": i["nama"], "JAWATAN": i["jawatan"], "PUSAT/BK": i["pusat"], "NO SURAT": i["no_surat"]} for i in items]),
                 use_container_width=True, hide_index=True)
    ppd_name = core.PPD_MAP.get(kod_ppd, "")
    if st.button("📦 Jana ZIP Surat Ujian Mendengar", key=f"um_sup_zip_{kod_sekolah}"):
        z = core.create_zip_pukal_dari_JPN(items, kod_ppd, ppd_name)
        if z:
            st.session_state[f"um_sup_z_{kod_sekolah}"] = z
    if st.session_state.get(f"um_sup_z_{kod_sekolah}"):
        st.download_button("📥 Muat Turun ZIP Surat Ujian Mendengar", st.session_state[f"um_sup_z_{kod_sekolah}"],
                           file_name=f"Surat_UM_{kod_sekolah}.zip", mime="application/zip", key=f"um_sup_dl_{kod_sekolah}")
