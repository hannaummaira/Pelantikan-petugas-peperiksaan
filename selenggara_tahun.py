# -*- coding: utf-8 -*-
"""selenggara_tahun.py - Menu JPN: Selenggara Tahun & Data Master.

Sub menu:
  tetapan    : tetapkan tahun peperiksaan semasa (dipaparkan di semua halaman & surat)
  muat_turun : muat turun Master Guru / Pusat / Sekolah (Excel, format sama seperti muat naik)
  muat_naik  : muat naik Master Guru / Pusat / Sekolah (ganti semua atau tambah)
  arkib      : muat turun senarai guru dilantik tahun lepas + kosongkan data lantikan untuk tahun baharu
"""
import io
import json
import datetime
import pandas as pd
import streamlit as st
import spm_core as core
from tahun_sistem import tahun_semasa, tempoh_penyelia, simpan_tetapan

supa = core.supa
PPD_MAP = core.PPD_MAP

FLY_TAHUN = [
    ("tetapan", "📆 Tetapan Tahun"),
    ("muat_turun", "📥 Muat Turun Master"),
    ("muat_naik", "📤 Muat Naik Master"),
    ("arkib", "🗄️ Lantikan Tahun Lepas"),
]

JADUAL_DATA = {
    "guru": ("guru_master", "Master Guru"),
    "pusat": ("pusat_master", "Data Pusat"),
    "sekolah": ("sekolah_master", "Data Sekolah"),
}


# ----------------------------------------------------------------- pembantu data
def _bersih(v):
    s = "" if v is None else str(v).strip()
    return "" if s.lower() in ("nan", "none", "null", "nat") else s


def _json_dict(v):
    if isinstance(v, dict):
        return v
    if isinstance(v, str) and v.strip().startswith("{"):
        try:
            return json.loads(v)
        except Exception:
            return {}
    return {}


def _ambil(r, d, *keys):
    """Nilai pertama yang tidak kosong daripada lajur DB (r) atau JSON data (d)."""
    for k in keys:
        for src in (r, d):
            v = _bersih(src.get(k)) if hasattr(src, "get") else ""
            if v:
                return v
    return ""


def ambil_semua(table, maks=300000):
    """Semua baris jadual (paginasi automatik). Cuba isih ikut id supaya halaman tidak bertindih."""
    for guna_order in (True, False):
        try:
            q = supa.table(table).select("*")
            if guna_order:
                q = q.order("id")
            return q.limit(maks).execute().data or []
        except Exception:
            if not guna_order:
                raise
    return []


def kira(table):
    try:
        return supa.table(table).select("*", count="exact").limit(1).execute().count or 0
    except Exception:
        return None


def kosongkan_jadual(table):
    """Padam semua baris. Pulang bilangan baris yang tinggal (0 = berjaya)."""
    raw = core._RAW
    percubaan = [
        lambda: raw.table(table).delete().gt("id", 0).execute(),
        lambda: raw.table(table).delete().not_.is_("id", "null").execute(),
        lambda: raw.table(table).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute(),
    ]
    for p in percubaan:
        try:
            p()
        except Exception:
            continue
        baki = kira(table)
        if baki == 0:
            return 0
    return kira(table)


def excel_bytes(sheets):
    """sheets: {nama: DataFrame} -> bytes xlsx."""
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        for nama, df in sheets.items():
            df.to_excel(w, index=False, sheet_name=nama[:31])
    return out.getvalue()


# ----------------------------------------------------------------- eksport master
def df_guru(rows):
    out = []
    for r in rows:
        d = _json_dict(r.get("data"))
        out.append({
            "KOD PPD": _ambil(r, d, "kod_ppd", "KOD PPD").upper(),
            "KOD SEKOLAH": _ambil(r, d, "kod_sekolah", "KOD SEKOLAH", "kod_sekolah_asal").upper(),
            "NAMA SEKOLAH": _ambil(r, d, "nama_sekolah_asal", "NAMA SEKOLAH"),
            "NAMA GURU": _ambil(r, d, "nama_guru", "NAMA GURU"),
            "IC": _ambil(r, d, "ic_guru", "IC"),
            "JANTINA": _ambil(r, d, "jantina", "JANTINA"),
            "POSKOD RUMAH": _ambil(r, d, "poskod_rumah", "POSKOD RUMAH", "POSKOD_RUMAH"),
            "ALAMAT RUMAH": _ambil(r, d, "alamat_rumah", "ALAMAT RUMAH", "ALAMAT_RUMAH"),
            "NO TELEFON GURU": _ambil(r, d, "telefon_guru", "NO TELEFON GURU", "TELEFON_GURU"),
            "EMAIL GURU": _ambil(r, d, "email_guru", "EMAIL GURU", "EMAIL_GURU"),
            "PENGALAMAN SPM": _ambil(r, d, "pengalaman_spm", "PENGALAMAN SPM", "PENGALAMAN_SPM"),
        })
    return pd.DataFrame(out)


def df_pusat(rows):
    out = []
    for r in rows:
        d = _json_dict(r.get("data"))
        out.append({
            "KOD PUSAT": _ambil(r, d, "no_pusat", "kod_pusat", "NO_PUSAT", "KOD PUSAT").upper(),
            "NAMA PUSAT": _ambil(r, d, "nama_pusat", "NAMA_PUSAT", "NAMA PUSAT"),
            "KOD PPD": _ambil(r, d, "kod_ppd", "KOD PPD", "KOD_PPD").upper(),
            "PPD": _ambil(r, d, "ppd", "PPD"),
            "KOD_SEKOLAH": _ambil(r, d, "kod_sekolah_tuan_rumah", "kod_sekolah", "KOD_SEKOLAH", "KOD_SEKOLAH_TUAN_RUMAH"),
            "JUMLAH_KELAS": _ambil(r, d, "jumlah_kelas", "bilik", "JUMLAH_KELAS", "BILIK"),
            "JUMLAH_CALON": _ambil(r, d, "jumlah_calon", "calon", "JUMLAH_CALON", "CALON"),
            "POSKOD PUSAT": _ambil(r, d, "poskod_pusat", "POSKOD_PUSAT", "POSKOD PUSAT", "poskod"),
        })
    return pd.DataFrame(out)


def df_sekolah(rows):
    out = []
    for r in rows:
        d = _json_dict(r.get("data"))
        out.append({
            "KOD SEKOLAH": _ambil(r, d, "kod_sekolah", "KOD SEKOLAH", "KOD_SEKOLAH").upper(),
            "NAMA SEKOLAH": _ambil(r, d, "nama_sekolah", "NAMA SEKOLAH", "NAMA_SEKOLAH"),
            "KOD PPD": _ambil(r, d, "kod_ppd", "KOD PPD", "KOD_PPD").upper(),
        })
    return pd.DataFrame(out)


EKSPORT = {"guru": df_guru, "pusat": df_pusat, "sekolah": df_sekolah}


# ----------------------------------------------------------------- import master
def baca_fail(up):
    if up.name.lower().endswith(".csv"):
        try:
            return pd.read_csv(up, dtype=str)
        except Exception:
            up.seek(0)
            return pd.read_csv(up, dtype=str, encoding="latin1")
    return pd.read_excel(up, sheet_name=0, dtype=str)


def _g(row, *keys):
    for k in keys:
        if k in row and _bersih(row.get(k)):
            return _bersih(row.get(k))
    return ""


def baris_guru(row):
    nama = _g(row, "NAMA GURU", "nama_guru", "NAMA_GURU").upper()
    if not nama:
        return None
    d = {k: _bersih(v) for k, v in row.items()}
    kod_sek = _g(row, "KOD SEKOLAH", "kod_sekolah", "KOD_SEKOLAH").upper()
    return {
        "kod_ppd": _g(row, "KOD PPD", "kod_ppd", "KOD_PPD").lower(),
        "kod_sekolah": kod_sek,
        "nama_guru": nama,
        "ic_guru": _g(row, "IC", "ic_guru", "IC_GURU"),
        "jantina": _g(row, "JANTINA", "jantina"),
        "poskod_rumah": _g(row, "POSKOD RUMAH", "POSKOD_RUMAH", "poskod_rumah"),
        "alamat_rumah": _g(row, "ALAMAT RUMAH", "ALAMAT_RUMAH", "alamat_rumah"),
        "telefon_guru": _g(row, "NO TELEFON GURU", "TELEFON_GURU", "telefon_guru"),
        "email_guru": _g(row, "EMAIL GURU", "EMAIL_GURU", "email_guru"),
        "pengalaman_spm": _g(row, "PENGALAMAN SPM", "PENGALAMAN_SPM", "pengalaman_spm"),
        "kod_sekolah_asal": kod_sek,
        "nama_sekolah_asal": _g(row, "NAMA SEKOLAH", "nama_sekolah", "NAMA_SEKOLAH"),
        "no_pusat_asal": _g(row, "NO PUSAT ASAL", "NO_PUSAT_ASAL"),
        "data": d,
    }


def baris_pusat(row):
    d = {k: (" " if not _bersih(v) else _bersih(v)) for k, v in row.items()}
    kod_p = _g(row, "NO_PUSAT", "KOD PUSAT", "KOD_PUSAT", "kod_pusat").upper()
    if not kod_p:
        return None
    kod_ppd = _g(row, "KOD PPD", "KOD_PPD", "PPD_CODE", "kod_ppd").upper() or kod_p[:2]
    nama = _g(row, "NAMA_PUSAT", "NAMA PUSAT", "nama_pusat") or kod_p
    try:
        bilik = int(float(_g(row, "JUMLAH_KELAS", "BILIK", "bilik") or 10))
    except Exception:
        bilik = 10
    try:
        calon = int(float(_g(row, "JUMLAH_CALON", "CALON", "calon") or 200))
    except Exception:
        calon = 200
    return {"kod_pusat": kod_p, "nama_pusat": nama.upper(), "kod_ppd": kod_ppd,
            "ppd": _g(row, "PPD", "ppd") or PPD_MAP.get(kod_ppd, ""),
            "alamat": _g(row, "KOD_SEKOLAH", "ALAMAT PUSAT", "ALAMAT"),
            "bilik": bilik, "calon": calon, "data": d}


def baris_sekolah(row):
    kod = _g(row, "KOD SEKOLAH", "kod_sekolah", "KOD_SEKOLAH").upper()
    if not kod:
        return None
    return {"kod_sekolah": kod, "nama_sekolah": _g(row, "NAMA SEKOLAH", "nama_sekolah", "NAMA_SEKOLAH").upper(),
            "kod_ppd": (_g(row, "KOD PPD", "kod_ppd", "KOD_PPD", "PPD_CODE") or "BH").upper(),
            "data": {k: (" " if not _bersih(v) else _bersih(v)) for k, v in row.items()}}


PEMETA = {"guru": baris_guru, "pusat": baris_pusat, "sekolah": baris_sekolah}
BATCH = {"guru": 500, "pusat": 200, "sekolah": 200}


def import_data(kunci, df, ganti):
    table, label = JADUAL_DATA[kunci]
    pemeta = PEMETA[kunci]
    baris = []
    for rec in df.to_dict("records"):
        try:
            x = pemeta(rec)
        except Exception:
            x = None
        if x:
            baris.append(x)
    if not baris:
        st.error("Tiada baris sah dalam fail. Semak nama lajur.")
        return
    if ganti:
        with st.spinner(f"Memadam data {label} lama..."):
            baki = kosongkan_jadual(table)
        if baki:
            st.error(f"Gagal memadam semua data lama ({baki} baris tinggal). Import dihentikan supaya data tidak bercampur.")
            return
    bar = st.progress(0)
    stat = st.empty()
    ok, gagal = 0, 0
    n = BATCH[kunci]
    for i in range(0, len(baris), n):
        potong = baris[i:i + n]
        try:
            supa.table(table).insert(potong).execute()
            ok += len(potong)
        except Exception as e:
            gagal += len(potong)
            st.warning(f"Kelompok {i}-{i + len(potong)} gagal: {str(e)[:150]}")
        bar.progress(min(1.0, (i + len(potong)) / len(baris)))
        stat.write(f"Dimuat naik {min(i + n, len(baris))}/{len(baris)} | Berjaya {ok} | Gagal {gagal}")
    try:
        st.cache_data.clear()
    except Exception:
        pass
    if gagal:
        st.warning(f"Selesai dengan {gagal} baris gagal. Berjaya: {ok}.")
    else:
        st.success(f"✅ Selesai: {ok} rekod {label} dimuat naik ({'ganti semua' if ganti else 'tambah'}).")


# ----------------------------------------------------------------- lantikan tahun lepas
def _pusat_cad(r):
    d = _json_dict(r.get("data"))
    return _ambil(r, d, "kod_pusat", "KOD_PUSAT", "no_pusat_tugas", "NO_PUSAT_TUGAS").upper()


def _dilantik(r):
    st_ = _bersih(r.get("status") or r.get("STATUS")).upper()
    return bool(_pusat_cad(r)) or any(x in st_ for x in ("LULUS", "DILANTIK", "DITEMPATKAN"))


def df_dilantik(rows):
    out = []
    for r in rows:
        if not _dilantik(r):
            continue
        d = _json_dict(r.get("data"))
        out.append({
            "KOD PPD": _ambil(r, d, "kod_ppd", "KOD_PPD").upper(),
            "KOD PUSAT": _pusat_cad(r),
            "JAWATAN": _ambil(r, d, "jawatan_cadangan", "JAWATAN_CADANGAN", "jawatan"),
            "NAMA GURU": _ambil(r, d, "nama_guru", "NAMA_GURU"),
            "IC": _ambil(r, d, "ic_guru", "IC_GURU"),
            "KOD SEKOLAH ASAL": _ambil(r, d, "kod_sekolah_asal", "KOD_SEKOLAH_ASAL", "kod_sekolah").upper(),
            "NAMA SEKOLAH ASAL": _ambil(r, d, "nama_sekolah_asal", "NAMA_SEKOLAH_ASAL"),
            "NO SURAT": _ambil(r, d, "no_surat", "NO_SURAT"),
            "TELEFON": _ambil(r, d, "telefon_guru", "TELEFON_GURU"),
            "POSKOD RUMAH": _ambil(r, d, "poskod_rumah", "POSKOD_RUMAH"),
            "STATUS": _ambil(r, d, "status", "STATUS"),
        })
    df = pd.DataFrame(out)
    if not df.empty:
        df = df.sort_values(["KOD PPD", "KOD PUSAT", "JAWATAN", "NAMA GURU"]).reset_index(drop=True)
    return df


def df_semua(rows):
    df = pd.DataFrame(rows)
    if "data" in df.columns:
        df["data"] = df["data"].apply(lambda v: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
    return df


# ----------------------------------------------------------------- UI
def render_selenggara_tahun(fly_cur):
    st.header("📆 Selenggara Tahun & Data Master")
    try:
        core.show_flash()
    except Exception:
        pass
    tahun = tahun_semasa()

    # ---------------------------------------------------------- tetapan tahun
    if fly_cur == "tetapan":
        st.subheader("Tahun Peperiksaan Semasa")
        c1, c2 = st.columns([1, 2])
        c1.metric("Tahun sistem sekarang", tahun)
        c2.info("Tahun ini dipaparkan pada semua halaman (header, footer, tajuk), surat lantikan, nombor rujukan lalai dan landing page.")
        baharu = st.number_input("Tahun baharu", min_value=2000, max_value=2100, value=int(tahun), step=1, key="inp_tahun_baharu")
        tempoh = st.text_input("Tempoh bertugas dalam surat Penyelia Kawasan (tanpa tahun)", value=tempoh_penyelia(), key="inp_tempoh_pk",
                               help="Contoh: 14 Julai hingga 16 Julai. Tahun ditambah automatik selepas teks ini dalam surat.")
        _ubah = int(baharu) != int(tahun) or tempoh.strip() != tempoh_penyelia()
        if st.button("💾 Simpan Tetapan", type="primary", key="btn_simpan_tahun", disabled=not _ubah):
            try:
                simpan_tetapan(int(baharu), tempoh)
                st.cache_data.clear()
                core.flash("success", f"✅ Tetapan disimpan: tahun {int(baharu)}, tempoh penyelia '{tempoh.strip()}'.")
                st.rerun()
            except Exception as e:
                st.error(f"Gagal simpan tahun: {e}")
                st.caption("Pastikan jadual `landing_config` sudah dibuat (SQL landing page).")
        st.markdown("---")
        st.markdown("#### Urutan disarankan untuk tahun baharu")
        st.markdown(
            f"1. **Lantikan Tahun Lepas** → muat turun senarai guru dilantik {tahun} (arkib)\n"
            "2. **Lantikan Tahun Lepas** → kosongkan data lantikan\n"
            "3. **Muat Naik Master** → muat naik Master Guru, Data Pusat dan Data Sekolah baharu (pilih *Ganti semua*)\n"
            "4. **Tetapan Tahun** → tetapkan tahun baharu")
        return

    # ---------------------------------------------------------- muat turun master
    if fly_cur == "muat_turun":
        st.subheader("📥 Muat Turun Data Master")
        st.caption("Format lajur sama seperti muat naik, jadi fail boleh dikemas kini dan dimuat naik semula.")
        for kunci, (table, label) in JADUAL_DATA.items():
            with st.container(border=True):
                n = kira(table)
                st.markdown(f"**{label}** ({table}) - {n if n is not None else '?'} rekod")
                kk = f"dl_{kunci}"
                if st.button(f"⚙️ Sediakan fail {label}", key=f"btn_{kk}"):
                    with st.spinner("Menarik data & menyediakan fail (60K guru mungkin ambil 1-2 minit)..."):
                        try:
                            rows = ambil_semua(table)
                            df = EKSPORT[kunci](rows)
                            st.session_state[kk] = {
                                "xlsx": excel_bytes({label: df}),
                                "csv": df.to_csv(index=False).encode("utf-8-sig"),
                                "n": len(df), "t": datetime.datetime.now().strftime("%Y%m%d_%H%M"),
                            }
                        except Exception as e:
                            st.error(f"Gagal: {e}")
                f = st.session_state.get(kk)
                if f:
                    st.success(f"Sedia: {f['n']} rekod")
                    d1, d2 = st.columns(2)
                    d1.download_button("⬇️ Muat turun Excel (.xlsx)", f["xlsx"], file_name=f"{table}_{tahun}_{f['t']}.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"{kk}_x")
                    d2.download_button("⬇️ Muat turun CSV", f["csv"], file_name=f"{table}_{tahun}_{f['t']}.csv", mime="text/csv", key=f"{kk}_c")
        return

    # ---------------------------------------------------------- muat naik master
    if fly_cur == "muat_naik":
        st.subheader("📤 Muat Naik Data Master")
        pilih = st.radio("Pilih data", list(JADUAL_DATA.keys()), format_func=lambda k: JADUAL_DATA[k][1], horizontal=True, key="naik_pilih")
        table, label = JADUAL_DATA[pilih]
        lajur = {
            "guru": "KOD PPD, KOD SEKOLAH, NAMA SEKOLAH, NAMA GURU, IC, JANTINA, POSKOD RUMAH, ALAMAT RUMAH, NO TELEFON GURU, EMAIL GURU, PENGALAMAN SPM",
            "pusat": "KOD PUSAT (atau NO_PUSAT), NAMA PUSAT, KOD PPD, PPD, KOD_SEKOLAH, JUMLAH_KELAS (atau BILIK), JUMLAH_CALON (atau CALON)",
            "sekolah": "KOD SEKOLAH, NAMA SEKOLAH, KOD PPD",
        }[pilih]
        st.caption(f"Lajur dikenali: {lajur}")
        n_semasa = kira(table)
        st.info(f"Data {label} sedia ada dalam sistem: **{n_semasa if n_semasa is not None else '?'}** rekod.")
        mod = st.radio("Mod muat naik",
                       ["🔄 Ganti semua (padam data lama dahulu - untuk tahun baharu)", "➕ Tambah sahaja (data lama dikekalkan)"],
                       key="naik_mod")
        ganti = mod.startswith("🔄")
        up = st.file_uploader(f"Fail {label} (Excel / CSV)", type=["xlsx", "csv"], key=f"naik_fail_{pilih}")
        if up:
            try:
                df = baca_fail(up)
            except Exception as e:
                st.error(f"Fail tidak dapat dibaca: {e}")
                return
            st.write(f"Fail mengandungi **{len(df)}** baris. Pratonton:")
            st.dataframe(df.head(15), use_container_width=True)
            ok_konfirm = True
            if ganti:
                st.warning(f"⚠️ Semua {n_semasa if n_semasa is not None else ''} rekod {label} sedia ada akan DIPADAM dan diganti. "
                           "Disarankan muat turun dahulu di sub menu Muat Turun Master.")
                ok_konfirm = st.checkbox("Saya faham dan mahu ganti semua data", key=f"naik_yakin_{pilih}")
            if st.button(f"🚀 Muat naik {len(df)} baris {label}", type="primary", disabled=not ok_konfirm, key=f"naik_btn_{pilih}"):
                import_data(pilih, df, ganti)
        return

    # ---------------------------------------------------------- arkib & kosongkan lantikan
    if fly_cur == "arkib":
        st.subheader(f"🗄️ Lantikan Tahun {tahun}")
        n_cad = kira("cadangan_sup")
        st.info(f"Rekod cadangan/lantikan dalam sistem: **{n_cad if n_cad is not None else '?'}**")

        st.markdown("#### 1) Muat turun senarai guru dilantik (arkib)")
        if st.button("⚙️ Sediakan fail arkib", key="btn_arkib"):
            with st.spinner("Menarik semua rekod lantikan..."):
                try:
                    rows = ambil_semua("cadangan_sup")
                    dl = df_dilantik(rows)
                    sem = df_semua(rows)
                    ringkas = (dl.groupby(["KOD PPD", "KOD PUSAT"]).size().reset_index(name="BIL PETUGAS")
                               if not dl.empty else pd.DataFrame(columns=["KOD PPD", "KOD PUSAT", "BIL PETUGAS"]))
                    st.session_state["arkib_fail"] = {
                        "xlsx": excel_bytes({"DILANTIK": dl, "RINGKASAN PUSAT": ringkas, "SEMUA CADANGAN": sem}),
                        "n_dilantik": len(dl), "n_semua": len(sem),
                        "t": datetime.datetime.now().strftime("%Y%m%d_%H%M"),
                    }
                except Exception as e:
                    st.error(f"Gagal: {e}")
        f = st.session_state.get("arkib_fail")
        if f:
            st.success(f"Sedia: {f['n_dilantik']} guru dilantik | {f['n_semua']} rekod cadangan keseluruhan")
            st.download_button(f"⬇️ Muat turun Senarai Guru Dilantik {tahun}", f["xlsx"],
                               file_name=f"guru_dilantik_SPM{tahun}_{f['t']}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_arkib")
            st.caption("Fail ada 3 helaian: DILANTIK, RINGKASAN PUSAT, SEMUA CADANGAN.")

        st.markdown("---")
        st.markdown(f"#### 2) Kosongkan data lantikan tahun {tahun}")
        st.warning("Tindakan ini MEMADAM data lantikan terpilih untuk SEMUA PPD dan tidak boleh dibatalkan. Muat turun arkib dahulu.")
        jadual = st.multiselect(
            "Jadual untuk dikosongkan",
            ["cadangan_sup", "surat_hantar_sekolah_asal", "bilik_kebal_master"],
            default=["cadangan_sup", "surat_hantar_sekolah_asal"],
            format_func=lambda t: {"cadangan_sup": "Cadangan & lantikan guru (cadangan_sup)",
                                   "surat_hantar_sekolah_asal": "Rekod surat ke sekolah asal",
                                   "bilik_kebal_master": "Senarai Bilik Kebal (bilik_kebal_master)"}[t],
            key="kosong_jadual")
        sudah_dl = st.checkbox("Saya sudah memuat turun arkib senarai guru dilantik", key="kosong_dl")
        taip = st.text_input('Taip  KOSONGKAN  untuk mengesahkan', key="kosong_taip")
        boleh = bool(jadual) and sudah_dl and taip.strip().upper() == "KOSONGKAN"
        if st.button("🗑️ Kosongkan Data Lantikan", type="primary", disabled=not boleh, key="btn_kosongkan"):
            laporan = []
            for t in jadual:
                with st.spinner(f"Memadam {t}..."):
                    baki = kosongkan_jadual(t)
                laporan.append((t, baki))
            try:
                st.cache_data.clear()
            except Exception:
                pass
            for t, baki in laporan:
                if baki == 0:
                    st.success(f"✅ {t}: dikosongkan")
                elif baki is None:
                    st.warning(f"{t}: tidak dapat disahkan (jadual mungkin tiada)")
                else:
                    st.error(f"{t}: {baki} baris masih tinggal - cuba lagi atau semak kebenaran Supabase")
            st.session_state.pop("arkib_fail", None)
        return
