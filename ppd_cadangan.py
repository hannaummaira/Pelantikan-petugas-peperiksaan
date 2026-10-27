# -*- coding: utf-8 -*-
"""
ppd_cadangan.py - Aliran semakan cadangan SUP oleh PPD.

  Cadangan SUP > Senarai Nama Cadangan : popup  Jawatan -> Sekolah -> Senarai nama (tick = dijana)
                                         Hantar: tick -> status "TERPILIH PPD", tidak tick -> "SIMPANAN PPD"
  Cadangan SUP > Senarai Simpanan      : pilih sekolah, tick untuk pindah semula ke Jana
  Jana Keseluruhan                     : hanya calon TERPILIH PPD (+ yang sudah diproses) masuk pool;
                                         PPD boleh tapis siapa dilantik / tidak dilantik.

Hanya lajur `status` dalam cadangan_sup digunakan (tiada perubahan skema pangkalan data).
"""
import pandas as pd
import streamlit as st
import spm_core as core
from spm_core import get_cadangan_df, supa

ST_TERPILIH = "TERPILIH PPD"
ST_SIMPANAN = "SIMPANAN PPD"
_LOCK = ("DILANTIK", "DITEMPATKAN", "SURAT", "LULUS", "DIJANA")     # sudah diproses - jangan diusik
ORDER_JAWATAN = ["KETUA PENGAWAS", "TIMBALAN KETUA PENGAWAS", "PENYELIA KAWASAN", "PENGAWAS PEPERIKSAAN",
                 "SELENGGARA BILIK KEBAL", "JURU TULIS", "JURU BACA"]


# ------------------------------------------------------------------ pembantu data
def _pick(r, *keys):
    for k in keys:
        try:
            v = r.get(k)
        except Exception:
            v = None
        if v is not None and str(v).strip().lower() not in ("", "nan", "none", "null", "nat"):
            return str(v).strip()
    return ""


def stage_of(status):
    s = str(status or "").upper()
    if "SIMPANAN" in s:
        return "SIMPANAN"
    if "TERPILIH" in s:
        return "TERPILIH"
    if any(x in s for x in _LOCK):
        return "LOCKED"
    return "BARU"                      # DICADANGKAN / HANTAR KE PPD - belum disemak PPD


def normalize(df):
    cols = ["id", "NAMA", "IC", "KOD_SEK", "NAMA_SEK", "JAWATAN", "STATUS", "POSKOD", "STAGE"]
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    for _, r in df.iterrows():
        rid = r.get("id")
        if rid is None or str(rid).strip().lower() in ("", "nan", "none"):
            continue                                           # tanpa id tak boleh dikemas kini
        kod = _pick(r, "KOD_SEKOLAH_ASAL", "kod_sekolah_asal", "KOD_SEKOLAH", "kod_sekolah").upper()
        if not kod:
            continue
        status = _pick(r, "STATUS", "status").upper()
        rows.append({"id": rid, "NAMA": _pick(r, "NAMA_GURU", "nama_guru"), "IC": _pick(r, "IC_GURU", "ic_guru"),
                     "KOD_SEK": kod, "NAMA_SEK": _pick(r, "NAMA_SEKOLAH_ASAL", "nama_sekolah_asal"),
                     "JAWATAN": (_pick(r, "JAWATAN_CADANGAN", "jawatan_cadangan", "JAWATAN") or "TIADA JAWATAN").upper(),
                     "STATUS": status, "POSKOD": _pick(r, "POSKOD_RUMAH", "poskod_rumah"), "STAGE": stage_of(status)})
    return pd.DataFrame(rows, columns=cols)


@st.cache_data(ttl=600, show_spinner=False)
def sekolah_map(kod_ppd):
    """{kod_sekolah: nama_sekolah} - sudah ditapis ikut daerah oleh scoped_db."""
    out = {}
    try:
        res = supa.table("sekolah_master").select("kod_sekolah,nama_sekolah").limit(2000).execute()
        for s in res.data or []:
            k = str(s.get("kod_sekolah") or "").upper().strip()
            if k:
                out[k] = str(s.get("nama_sekolah") or "").upper().strip()
    except Exception:
        pass
    return out


def _nama_sek(kod, row_nama, smap):
    return smap.get(kod) or row_nama or kod


def _pyid(x):
    try:
        return int(float(str(x)))
    except Exception:
        return str(x)


def ppd_set_status(ids, status):
    """Kemas kini status mengikut id (kelompok 100). Pulang (bilangan_ok, senarai_ralat)."""
    ok, err = 0, []
    ids = [_pyid(i) for i in ids if i is not None]
    for i in range(0, len(ids), 100):
        b = ids[i:i + 100]
        try:
            supa.table("cadangan_sup").update({"status": status}).in_("id", b).execute()
            ok += len(b)
        except Exception as e:
            err.append(str(e)[:150])
    try:
        get_cadangan_df.clear()
    except Exception:
        pass
    return ok, err


def _jaw_sorted(vals):
    vals = list(vals)
    return sorted(vals, key=lambda x: (ORDER_JAWATAN.index(x) if x in ORDER_JAWATAN else 99, x))


def _banner(title, sub):
    st.markdown(f"""<div class="sup-box"><div class="sup-card-h"><span class="t">{title}</span></div>
    <div style="padding:8px 14px;font-size:12px;color:#5f6f85">{sub}</div></div>""", unsafe_allow_html=True)


def _flash():
    msg = st.session_state.pop("cad_flash", None)
    if msg:
        st.success(msg)


def _container(height=None):
    try:
        return st.container(height=height) if height else st.container()
    except TypeError:
        return st.container()


def _frag_rerun():
    """Navigasi dalam popup tanpa menutupnya (Streamlit >= 1.37); versi lama: buka semula sekali."""
    try:
        st.rerun(scope="fragment")
    except TypeError:
        st.session_state["nama_reopen"] = True
        st.rerun()


def _counts_strip(df):
    c = df["STAGE"].value_counts().to_dict() if not df.empty else {}
    a, b, c2, d = st.columns(4)
    a.metric("✅ Terpilih (dijana)", c.get("TERPILIH", 0))
    b.metric("📦 Simpanan", c.get("SIMPANAN", 0))
    c2.metric("🆕 Belum disemak", c.get("BARU", 0))
    d.metric("📌 Sudah diproses", c.get("LOCKED", 0))


# ------------------------------------------------------------------ SENARAI NAMA CADANGAN (popup 3 langkah)
try:
    _dlg = st.dialog("📝 Senarai Nama Cadangan", width="large")
except TypeError:
    _dlg = st.dialog("📝 Senarai Nama Cadangan")


@_dlg
def dlg_nama(kod_ppd):
    df = normalize(get_cadangan_df(kod_ppd=kod_ppd))
    if df.empty:
        st.warning("Tiada cadangan.")
        return
    step = st.session_state.get("nama_step", "jawatan")
    if step == "sekolah" and st.session_state.get("nama_jawatan"):
        _step_sekolah(df, kod_ppd)
    elif step == "nama" and st.session_state.get("nama_jawatan") and st.session_state.get("nama_kod_sek"):
        _step_nama(df, kod_ppd)
    else:
        _step_jawatan(df)


def _step_jawatan(df):
    st.markdown("**Langkah 1 / 3 - Pilih Jawatan**")
    cnt = df.groupby("JAWATAN").size().to_dict()
    cols = st.columns(2)
    for i, j in enumerate(_jaw_sorted(cnt)):
        with cols[i % 2]:
            if st.button(f"{j}  ({cnt[j]} nama)", key=f"nj_{i}", use_container_width=True):
                st.session_state.update({"nama_step": "sekolah", "nama_jawatan": j, "nama_kod_sek": None})
                _frag_rerun()


def _step_sekolah(df, kod_ppd):
    j = st.session_state["nama_jawatan"]
    st.markdown(f"**Langkah 2 / 3 - Pilihan Sekolah** &nbsp;·&nbsp; Jawatan: **{j}**")
    if st.button("← Tukar Jawatan", key="nb_jaw"):
        st.session_state.update({"nama_step": "jawatan"})
        _frag_rerun()
    sub = df[df["JAWATAN"] == j]
    smap = sekolah_map(kod_ppd)
    q = st.text_input("Cari sekolah", key="nj_q", placeholder="Kod atau nama sekolah").upper().strip()
    items = []
    for kod, g in sub.groupby("KOD_SEK"):
        nama = _nama_sek(kod, g["NAMA_SEK"].iloc[0], smap)
        if q and q not in kod and q not in nama.upper():
            continue
        s = g["STAGE"].value_counts().to_dict()
        items.append((nama, kod, len(g), s.get("TERPILIH", 0), s.get("SIMPANAN", 0), s.get("BARU", 0)))
    items.sort()
    st.caption(f"{len(items)} sekolah  •  ✅ terpilih  📦 simpanan  🆕 belum disemak")
    with _container(380):
        for nama, kod, n, t, s, b in items:
            if st.button(f"{nama} ({kod}) — {n} nama   [✅{t}  📦{s}  🆕{b}]", key=f"ns_{kod}", use_container_width=True):
                st.session_state.update({"nama_step": "nama", "nama_kod_sek": kod, "nama_selall": None})
                _frag_rerun()


def _step_nama(df, kod_ppd):
    j, kod = st.session_state["nama_jawatan"], st.session_state["nama_kod_sek"]
    smap = sekolah_map(kod_ppd)
    sub = df[(df["JAWATAN"] == j) & (df["KOD_SEK"] == kod)]
    nama_sek = _nama_sek(kod, sub["NAMA_SEK"].iloc[0] if not sub.empty else "", smap)
    st.markdown(f"**Langkah 3 / 3 - Senarai Nama** &nbsp;·&nbsp; {j} &nbsp;·&nbsp; **{nama_sek} ({kod})**")
    if st.button("← Kembali ke Pilihan Sekolah", key="nb_sek"):
        st.session_state.update({"nama_step": "sekolah"})
        _frag_rerun()
    locked = sub[sub["STAGE"] == "LOCKED"]
    edit = sub[sub["STAGE"] != "LOCKED"].reset_index(drop=True)
    if not locked.empty:
        st.caption(f"ℹ️ {len(locked)} nama sudah diproses (dilantik/ditempatkan) - tidak dipaparkan.")
    if edit.empty:
        st.info("Tiada nama untuk disemak.")
        return
    sel_all = st.session_state.get("nama_selall")
    c1, c2, _ = st.columns([1, 1, 2])
    if c1.button("✅ Tanda Semua", key="nm_all"):
        st.session_state["nama_selall"] = True
        _frag_rerun()
    if c2.button("⬜ Kosongkan", key="nm_none"):
        st.session_state["nama_selall"] = False
        _frag_rerun()
    default = (edit["STAGE"] != "SIMPANAN") if sel_all is None else bool(sel_all)
    view = edit[["id", "NAMA", "IC", "POSKOD", "STATUS"]].copy()
    view.insert(0, "JANA", default)
    edited = st.data_editor(
        view, hide_index=True, use_container_width=True, key=f"ed_{kod}_{j}_{sel_all}",
        disabled=["id", "NAMA", "IC", "POSKOD", "STATUS"],
        column_config={"JANA": st.column_config.CheckboxColumn("Jana", help="Tick = dijana. Tidak tick = masuk senarai simpanan."), "id": None})
    if not isinstance(edited, pd.DataFrame):
        edited = view
    t_ids = edited.loc[edited["JANA"] == True, "id"].tolist()          # noqa: E712
    s_ids = edited.loc[edited["JANA"] != True, "id"].tolist()          # noqa: E712
    st.caption("Tick = dijana (masuk Jana Keseluruhan). Tidak tick = masuk Senarai Simpanan apabila Hantar ditekan.")
    if st.button(f"📤 Hantar  ({len(t_ids)} dijana  •  {len(s_ids)} simpanan)", type="primary", use_container_width=True, key="nama_hantar"):
        ok1, e1 = ppd_set_status(t_ids, ST_TERPILIH) if t_ids else (0, [])
        ok2, e2 = ppd_set_status(s_ids, ST_SIMPANAN) if s_ids else (0, [])
        if e1 or e2:
            st.error("Sebahagian gagal dikemas kini: " + " | ".join((e1 + e2)[:2]))
        else:
            st.session_state["cad_flash"] = f"✅ {nama_sek}: {ok1} nama TERPILIH untuk dijana, {ok2} nama masuk SENARAI SIMPANAN."
            st.session_state.update({"nama_step": "sekolah", "nama_kod_sek": None, "nama_reopen": True})
            st.rerun()


def render_senarai_nama(kod_ppd):
    _banner(f"📝 Senarai Nama Cadangan - PPD {kod_ppd}", "Semak nama yang dicadangkan sekolah mengikut jawatan. Tick = dijana, tidak tick = senarai simpanan.")
    _flash()
    df = normalize(get_cadangan_df(kod_ppd=kod_ppd))
    if df.empty:
        st.warning(f"Belum ada cadangan SUP untuk PPD {kod_ppd}")
        return
    _counts_strip(df)
    piv = df.pivot_table(index="JAWATAN", columns="STAGE", values="id", aggfunc="count", fill_value=0)
    for c in ("TERPILIH", "SIMPANAN", "BARU", "LOCKED"):
        if c not in piv.columns:
            piv[c] = 0
    piv = piv[["BARU", "TERPILIH", "SIMPANAN", "LOCKED"]]
    piv.columns = ["Belum disemak", "Terpilih", "Simpanan", "Sudah diproses"]
    piv["Jumlah"] = piv.sum(axis=1)
    st.dataframe(piv.loc[_jaw_sorted(piv.index)], use_container_width=True)
    reopen = st.session_state.pop("nama_reopen", False)
    if st.button("📝 Buka Senarai Nama Cadangan", type="primary", key="btn_open_nama") or reopen:
        if not reopen:
            st.session_state.update({"nama_step": "jawatan", "nama_jawatan": None, "nama_kod_sek": None, "nama_selall": None})
        dlg_nama(kod_ppd)


# ------------------------------------------------------------------ SENARAI SIMPANAN
def render_senarai_simpanan(kod_ppd):
    _banner(f"📦 Senarai Simpanan - PPD {kod_ppd}", "Nama yang tidak ditanda semasa Hantar. Tick dan pindahkan semula ke Jana Keseluruhan bila perlu.")
    _flash()
    df = normalize(get_cadangan_df(kod_ppd=kod_ppd))
    sim = df[df["STAGE"] == "SIMPANAN"] if not df.empty else df
    if sim.empty:
        st.info("Senarai simpanan kosong. Nama yang tidak ditanda di 'Senarai Nama Cadangan' akan masuk ke sini.")
        return
    smap = sekolah_map(kod_ppd)
    a, b, c = st.columns(3)
    a.metric("📦 Jumlah Simpanan", len(sim))
    b.metric("🏫 Sekolah", sim["KOD_SEK"].nunique())
    c.metric("👔 Jawatan", sim["JAWATAN"].nunique())
    opts = {"SEMUA": f"Semua Sekolah ({len(sim)})"}
    for kod, g in sim.groupby("KOD_SEK"):
        opts[kod] = f"{_nama_sek(kod, g['NAMA_SEK'].iloc[0], smap)} ({kod}) - {len(g)}"
    pilih = st.selectbox("🏫 Pilihan Sekolah", list(opts.keys()), format_func=lambda k: opts.get(k, k), key="simp_sek")
    jaw = st.multiselect("Jawatan (kosong = semua)", _jaw_sorted(sim["JAWATAN"].unique()), key="simp_jaw")
    view = sim.copy()
    if pilih != "SEMUA":
        view = view[view["KOD_SEK"] == pilih]
    if jaw:
        view = view[view["JAWATAN"].isin(jaw)]
    view = view.reset_index(drop=True)
    if view.empty:
        st.info("Tiada nama untuk tapisan ini.")
        return
    tbl = view[["id", "NAMA", "IC", "KOD_SEK", "JAWATAN", "POSKOD"]].copy()
    tbl.insert(0, "PINDAH", False)
    edited = st.data_editor(
        tbl, hide_index=True, use_container_width=True, key=f"simp_ed_{pilih}_{'-'.join(jaw)}",
        disabled=["id", "NAMA", "IC", "KOD_SEK", "JAWATAN", "POSKOD"],
        column_config={"PINDAH": st.column_config.CheckboxColumn("Pindah ke Jana"), "id": None})
    if not isinstance(edited, pd.DataFrame):
        edited = tbl
    ids = edited.loc[edited["PINDAH"] == True, "id"].tolist()          # noqa: E712
    if st.button(f"➡️ Pindahkan ke Jana Keseluruhan ({len(ids)})", type="primary", disabled=not ids, key="simp_pindah"):
        ok, err = ppd_set_status(ids, ST_TERPILIH)
        if err:
            st.error("Gagal: " + " | ".join(err[:2]))
        else:
            st.session_state["cad_flash"] = f"✅ {ok} nama dipindahkan ke Jana Keseluruhan (TERPILIH)."
            st.rerun()


# ------------------------------------------------------------------ JANA KESELURUHAN: pool + tapis lantik / tidak
def jana_pool_panel(kod_ppd, df_raw):
    """Pulang df cadangan yang layak dijana. Dipanggil dalam menu Jana Keseluruhan."""
    if df_raw is None or df_raw.empty:
        return df_raw
    stages = df_raw.apply(lambda r: stage_of(_pick(r, "STATUS", "status")), axis=1)
    cnt = stages.value_counts().to_dict()
    _flash()
    a, b, c, d = st.columns(4)
    a.metric("✅ Terpilih (dijana)", cnt.get("TERPILIH", 0))
    b.metric("📦 Simpanan (tidak dijana)", cnt.get("SIMPANAN", 0))
    c.metric("🆕 Belum disemak PPD", cnt.get("BARU", 0))
    d.metric("📌 Sudah diproses", cnt.get("LOCKED", 0))
    inc = st.checkbox("Termasuk cadangan yang belum disemak PPD (cara lama)", key="jana_inc_unrev",
                      help="Biasanya biarkan kosong. Hanya calon yang ditanda di Cadangan SUP > Senarai Nama Cadangan akan dijana.")
    keep = stages.isin(["TERPILIH", "LOCKED"]) | ((stages == "BARU") if inc else False)
    pool = df_raw[keep]
    with st.expander("🎯 Tapis: siapa dilantik / tidak dilantik", expanded=False):
        _tapis_editor(df_raw, inc)
    if pool.empty:
        st.info("Tiada calon untuk dijana. Pergi ke **Cadangan SUP > Senarai Nama Cadangan** dan tanda calon, atau pindahkan dari **Senarai Simpanan**.")
    return pool


def _tapis_editor(df_raw, inc):
    nd = normalize(df_raw)
    nd = nd[(nd["STAGE"] == "TERPILIH") | ((nd["STAGE"] == "BARU") if inc else False)]
    if nd.empty:
        st.caption("Tiada calon terpilih untuk ditapis.")
        return
    smap = sekolah_map(st.session_state.get("kod", ""))
    c1, c2 = st.columns(2)
    sek = c1.multiselect("Sekolah (kosong = semua)", sorted(nd["KOD_SEK"].unique()),
                         format_func=lambda k: f"{_nama_sek(k, '', smap)} ({k})", key="jp_sek")
    jaw = c2.multiselect("Jawatan (kosong = semua)", _jaw_sorted(nd["JAWATAN"].unique()), key="jp_jaw")
    v = nd
    if sek:
        v = v[v["KOD_SEK"].isin(sek)]
    if jaw:
        v = v[v["JAWATAN"].isin(jaw)]
    v = v.reset_index(drop=True)
    if v.empty:
        st.caption("Tiada nama untuk tapisan ini.")
        return
    tbl = v[["id", "NAMA", "IC", "KOD_SEK", "JAWATAN", "STATUS"]].copy()
    tbl.insert(0, "LANTIK", True)
    edited = st.data_editor(
        tbl, hide_index=True, use_container_width=True, key=f"jp_ed_{'-'.join(sek)}_{'-'.join(jaw)}_{inc}",
        disabled=["id", "NAMA", "IC", "KOD_SEK", "JAWATAN", "STATUS"],
        column_config={"LANTIK": st.column_config.CheckboxColumn("Lantik", help="Tick = dilantik (dijana). Tidak tick = tidak dilantik (masuk simpanan)."), "id": None})
    if not isinstance(edited, pd.DataFrame):
        edited = tbl
    yes = edited.loc[edited["LANTIK"] == True, "id"].tolist()          # noqa: E712
    no = edited.loc[edited["LANTIK"] != True, "id"].tolist()           # noqa: E712
    if st.button(f"💾 Simpan Pilihan ({len(yes)} dilantik • {len(no)} tidak dilantik)", type="primary", key="jp_simpan"):
        ok1, e1 = ppd_set_status(yes, ST_TERPILIH) if yes else (0, [])
        ok2, e2 = ppd_set_status(no, ST_SIMPANAN) if no else (0, [])
        if e1 or e2:
            st.error("Sebahagian gagal: " + " | ".join((e1 + e2)[:2]))
        else:
            st.session_state["cad_flash"] = f"✅ {ok1} dilantik (kekal dalam Jana), {ok2} tidak dilantik (dialih ke Senarai Simpanan)."
            st.rerun()
