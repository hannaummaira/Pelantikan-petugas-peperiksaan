# -*- coding: utf-8 -*-
"""Peranan PPD - bacaan dari cadangan_sup (satu daerah)."""
from tahun_sistem import tahun_semasa
from lengkap_petugas import lengkapkan as _lengkapkan
from tetapan_ppd import max_per_sekolah, simpan_max, MAX_MIN, MAX_MAKS
from kuota_pusat import kuota_pusat, kuota_ikut_sekolah, selaras_edit_pusat, simpan_pusat, kelas_auto
import spm_core as _core
import ui_theme as _ui
globals().update({k: v for k, v in vars(_core).items() if not k.startswith("__")})
globals().update({k: v for k, v in vars(_ui).items() if not k.startswith("__")})
from ppd_cadangan import render_senarai_nama, render_senarai_simpanan, jana_pool_panel, hasil_lookup, hasil_row
from ppd_zon import render_penempatan_zon
import ppd_penyelia as _pp
import ppd_aliran as _al
from surat_tools import surat_panel, surat_aset_panel


# ---------------------------------------------------------------------------
# Sumber data LANTIKAN yang SAMA untuk "Hasil Janaan" dan "Semakan Lantikan"
# ---------------------------------------------------------------------------
def _t_bersih(v):
    s_ = "" if v is None else str(v).strip()
    return "" if s_.lower() in ("", "nan", "none", "null", "nat") else s_.upper()


def _t_kunci(r):
    i = _t_bersih(r.get("id"))
    return f"ID:{i}" if i else "IC:" + re.sub(r"\D", "", str(r.get("IC_GURU") or r.get("ic_guru") or ""))


def _t_ambil_pusat(row):
    for k in ("kod_pusat", "KOD_PUSAT", "kod_pusat_tugas", "KOD_PUSAT_TUGAS", "NO_PUSAT_TUGAS", "no_pusat_tugas", "NO_PUSAT", "no_pusat", "pusat", "PUSAT"):
        v = row.get(k)
        if v:
            bv = _t_bersih(v)
            if bv:
                return bv
    try:
        d = row.get("data")
        if isinstance(d, dict):
            for k in ("kod_pusat", "KOD_PUSAT", "NO_PUSAT_TUGAS"):
                if d.get(k):
                    bv = _t_bersih(d.get(k))
                    if bv:
                        return bv
    except Exception:
        pass
    return ""


def bina_tugas(df_cad_all):
    """{kunci_guru: {"pusat": kod, "row": Series, "pending": bool}} - DB + janaan belum simpan (sesi)."""
    tugas = {}
    if df_cad_all is not None and not df_cad_all.empty:
        for _, c in df_cad_all.iterrows():
            if _pp.is_pk(c):
                continue          # PK diurus di Lantik Penyelia Kawasan (ikut bilik kebal)
            p_db = _t_ambil_pusat(c)
            if p_db:
                tugas[_t_kunci(c)] = {"pusat": p_db, "row": _lengkapkan(c, st.session_state.get("kod")), "pending": False}
    pending_rows = list(st.session_state.get("jana_all_result", []) or [])
    if st.session_state.get("jana_pusat_no"):
        pending_rows += list(st.session_state.get("jana_pusat_result", []) or [])
    for p in pending_rows:
        p_baru = _t_bersih(p.get("NO_PUSAT_TUGAS"))
        if not p_baru:
            continue
        tugas[_t_kunci(p)] = {"pusat": p_baru, "row": _lengkapkan(pd.Series(p), st.session_state.get("kod")), "pending": True}
    return tugas, pending_rows


def baris_semakan(rec):
    """Seragamkan satu rekod lantikan (huruf besar/kecil) kepada kunci huruf kecil untuk Semakan."""
    row = rec["row"]
    d = {str(k): v for k, v in dict(row).items()}
    for k, v in list(d.items()):
        if k.lower() not in d:
            d[k.lower()] = v
    if rec.get("pending"):
        d["id"] = "PENDING:" + (re.sub(r"\D", "", str(d.get("ic_guru") or "")) or str(len(d)))
        d["status"] = "BELUM DISIMPAN"
    return d

def render_ppd():
    kod_ppd = st.session_state.kod
    MAXS = max_per_sekolah(kod_ppd)  # maksimum guru satu sekolah asal bertugas di satu pusat (tetapan PPD)
    if SCOPE["ppd"] and kod_ppd != SCOPE["ppd"]:
        st.session_state.clear(); st.rerun()
    MENU_PPD = [('dashboard', '📊 Dashboard PPD'), ('sekolah', '🏫 Sekolah dalam PPD'), ('pusat', '🏫 Pusat di PPD'),
                    ('selenggara', '🔐 Selenggara Bilik Kebal'), ('penyelia', '🔐 Lantik Penyelia Kawasan'), ('cadangan', '📋 Cadangan SUP'), ('jana', '🚀 Jana Keseluruhan'),
                    ('manual', '📌 Penempatan Manual'), ('zon', '🗺️ Penempatan Zon'), ('hasil', '📋 Hasil Janaan'),
                    ('semakan', '🔍 Semakan Lantikan'), ('kelulusan', '✅ Kelulusan'), ('jana_surat', '📄 Janaan Surat Lantikan'),
                    ('sah', '🏅 Sah Lantik'), ('amali', '🔬 Lantikan Petugas Amali'), ('um', '🎧 Lantikan Petugas Ujian Mendengar'), ('batal', '🗑️ Batal Semua'), ('export', '📥 Export'), ('keluar', '🚪 Log Keluar')]
    # Sub menu: "Status Pusat" (dashboard) dipindah ke Pusat di PPD dan dinamakan "Selenggara Pusat"
    FLY_PPD_X = dict(FLY_PPD)
    FLY_PPD_X['dashboard'] = [x for x in FLY_PPD.get('dashboard', []) if x[0] not in ('status', 'berwarna')]
    FLY_PPD_X['pusat'] = list(FLY_PPD.get('pusat', [])) + [('selenggara', '🛠️ Selenggara Pusat')]
    # Penyelia Kawasan dikeluarkan daripada Selenggara Bilik Kebal -> menu utama sendiri (selepas Selenggara Bilik Kebal)
    FLY_PPD_X['selenggara'] = [x for x in FLY_PPD.get('selenggara', []) if x[0] not in ('penyelia', 'surat')]
    # Lantik Penyelia Kawasan: Cadangan SUP (PK sahaja) -> Simpanan -> Tempatkan PK -> Kelulusan & Surat
    FLY_PPD_X['penyelia'] = [('cadangan', '📋 Cadangan SUP'), ('simpanan', '📦 Simpanan PK'),
                             ('tempat', '📍 Tempatkan PK'), ('surat', '✅ Kelulusan & Janaan Surat')]
    # Hasil Janaan: 2 paparan ikut jawatan (PK ikut bilik kebal, KP/TKP/lain ikut pusat)
    FLY_PPD_X['hasil'] = list(FLY_PPD.get('hasil', [])) + [('pk_bk', '🔐 PK Ikut Bilik Kebal'), ('jawatan_pusat', '👑 KP/TKP & Lain Ikut Pusat')]
    # Semakan Lantikan: PK ikut bilik kebal, petugas lain ikut pusat
    FLY_PPD_X['semakan'] = list(FLY_PPD.get('semakan', [])) + [('pk', '🔐 Semakan PK (Bilik Kebal)')]
    # Sah Lantik: semua petugas yang sudah ada no surat
    FLY_PPD_X['kelulusan'] = [('keseluruhan', '✅ Sah Keseluruhan'), ('pusat', '🏫 Sah Ikut Pusat')]
    FLY_PPD_X['sah'] = [('hantar', '📤 Hantar ke Sekolah'), ('muat', '📥 Muat Turun'), ('senarai', '👥 Senarai Disahkan'), ('pk', '🔐 Penyelia Kawasan (Bilik Kebal)')]
    import amali_sains as _amali
    FLY_PPD_X['amali'] = _amali.FLY_AMALI
    import ujian_mendengar as _um
    FLY_PPD_X['um'] = _um.FLY_UM
    shell_header_ppd(kod_ppd)
    menu, fly_cur, col_main = shell_layout("ppd_menu_sel", MENU_PPD, FLY_PPD_X, None, "fly_ppd")

    with col_main:
        if menu == "keluar":
            st.session_state.clear()
            st.rerun()

        elif menu == "dashboard" or (menu == "pusat" and fly_cur == "selenggara"):
            if menu == "pusat":
                st.header(f"🛠️ Selenggara Pusat - PPD {kod_ppd}")
                fly_cur = "status"  # guna panel Status Pusat sedia ada
            show_flash()

            try:
                # Load data
                df_pusat_raw = get_pusat_df()
                df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)
                df_sekolah_raw = supa.table("sekolah_master").select("*").eq("kod_ppd", kod_ppd).limit(2000).execute()
                df_sekolah_list = pd.DataFrame(df_sekolah_raw.data or [])

                # Parse pusat
                pusat_list = []
                for _, r in df_pusat_raw.iterrows():
                    d = r.get("data") if isinstance(r.get("data"), dict) else {}
                    if isinstance(d, str):
                        try: d = json.loads(d)
                        except: d = {}
                    no_pusat = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or d.get("NO PUSAT") or "").upper().strip()
                    if not no_pusat.startswith(kod_ppd.upper()):
                        continue
                    nama_pusat = str(r.get("nama_pusat") or d.get("NAMA_PUSAT") or d.get("NAMA PUSAT") or "").upper().strip()
                    kod_tuan = str(r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or d.get("KOD_SEKOLAH_TUAN_RUMAH") or "").upper().strip()
                    _q = kuota_pusat(r)   # satu sumber kebenaran (termasuk suntingan PPD)
                    jc, jk = _q["calon"], _q["kelas"]
                    petugas_sep = _q["petugas"]

                    # Kira berapa petugas telah dicadangkan untuk pusat ini
                    # Cari dalam cadangan_sup yang kod_pusat / no_pusat_asal / no_pusat_tugas == no_pusat ini
                    dicadangkan = 0
                    if not df_cad_all.empty:
                        # Check multiple columns
                        for _, c_row in df_cad_all.iterrows():
                            c_no_pusat = str(c_row.get("kod_pusat") or c_row.get("no_pusat_asal") or c_row.get("NO_PUSAT_ASAL") or c_row.get("KOD_PUSAT") or "").upper().strip()
                            # Also check data dict
                            c_data = c_row.get("data") or {}
                            if isinstance(c_data, str):
                                try: c_data = json.loads(c_data)
                                except: c_data = {}
                            c_no_pusat2 = str(c_data.get("NO_PUSAT_ASAL") or c_data.get("KOD_PUSAT") or "").upper().strip()
                            if c_no_pusat == no_pusat or c_no_pusat2 == no_pusat:
                                dicadangkan += 1
                        # If no specific assignment yet, distribute proportionally? For now show 0, but total will show overall

                    pusat_list.append({
                        "NO_PUSAT": no_pusat,
                        "NAMA_PUSAT": nama_pusat,
                        "KOD_TUAN_RUMAH": kod_tuan,
                        "CALON": jc,
                        "KELAS": jk,
                        "SEPATUTNYA": petugas_sep,
                        "DICADANGKAN": dicadangkan
                    })

                df_pusat_ppd = pd.DataFrame(pusat_list)

                if df_pusat_ppd.empty:
                    st.warning(f"⚠️ Tiada pusat dijumpai untuk PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')}. Sila import pusat di JPN > Pusat Master")
                else:
                    if fly_cur == "ringkasan":
                        # Summary metrics
                        total_pusat = len(df_pusat_ppd)
                        total_calon = int(df_pusat_ppd["CALON"].sum())
                        total_kelas = int(df_pusat_ppd["KELAS"].sum())
                        total_sepatutnya = int(df_pusat_ppd["SEPATUTNYA"].sum())
                        total_dicadangkan = len(df_cad_all) if not df_cad_all.empty else 0
                        kekurangan = total_sepatutnya - total_dicadangkan

                        # Color logic for total
                        if total_dicadangkan == 0:
                            color_total = "#0d47a1"
                            bg_total = "#bbdefb"
                            icon_total = "🔴"
                        elif total_dicadangkan < total_sepatutnya:
                            color_total = "#0d47a1"
                            bg_total = "#e3f2fd"
                            icon_total = "🟡"
                        else:
                            color_total = "#0d47a1"
                            bg_total = "#ffffff"
                            icon_total = "🟢"

                        st.markdown(jpn_status_meter(total_pusat, total_calon, total_kelas, total_sepatutnya, total_dicadangkan, kod_ppd), unsafe_allow_html=True)

                        c1, c2, c3, c4, c5, c6 = st.columns(6)
                        c1.metric("🏫 Pusat", total_pusat)
                        c2.metric("👨‍🎓 Calon", total_calon)
                        c3.metric("🏫 Kelas", total_kelas)
                        c4.metric("📋 Perlu", total_sepatutnya)
                        c5.metric("✅ Dicadangkan", total_dicadangkan)
                        c6.metric("⚠️ Kurang", kekurangan if kekurangan > 0 else 0, delta=f"{'Cukup' if kekurangan <=0 else f'-{kekurangan}'}", delta_color="normal" if kekurangan <=0 else "inverse")

                    if fly_cur == "status":
                        st.markdown("---")
                        st.markdown("### 📍 Selenggara Pusat - Status Petugas (PPD Boleh Edit)")
                        st.caption("🔴 Merah = Belum Ada (0) | 🟡 Kuning = Belum Cukup (< sepatutnya) | 🟢 Hijau = Cukup / Lebih (>= sepatutnya) | ✏️ PPD boleh edit BIL CALON, KELAS, PERLU ikut keperluan")
                        st.info("💡 **Cara Edit:** Klik pada angka CALON / KELAS / PERLU dalam table di bawah, tukar ikut keperluan, kemudian tekan **💾 Simpan Perubahan**")

                    # Build editable table
                    # Prepare data for data_editor with BIL, editable columns
                    editable_rows = []
                    for idx, p in enumerate(df_pusat_ppd.sort_values("NO_PUSAT").iterrows()):
                        p_data = p[1]
                        no_p = p_data["NO_PUSAT"]
                        dic = p_data["DICADANGKAN"]
                        sep = p_data["SEPATUTNYA"]

                        if dic == 0:
                            status_icon = "🔴"
                            status_text = "Belum Ada"
                        elif dic < sep:
                            status_icon = "🟡"
                            status_text = f"Belum Cukup"
                        else:
                            status_icon = "🟢"
                            status_text = f"Cukup"

                        editable_rows.append({
                            "BIL": idx + 1,
                            "NO_PUSAT": no_p,
                            "NAMA_PUSAT": p_data["NAMA_PUSAT"][:35],
                            "KOD_TUAN": p_data["KOD_TUAN_RUMAH"],
                            "BIL_CALON": p_data["CALON"],
                            "KELAS": p_data["KELAS"],
                            "PERLU_K9": sep,
                            "DICADANGKAN": dic,
                            "STATUS": f"{status_icon} {status_text}",
                            "KEKURANGAN": max(0, sep - dic)
                        })

                    df_editable = pd.DataFrame(editable_rows)

                    if fly_cur == "status":
                        # Data editor - PPD boleh edit BIL_CALON dan KELAS; PERLU (petugas) = KELAS + 9 dikira automatik
                        st.markdown("#### ✏️ Edit Data Pusat (PPD)")
                        st.caption("20 calon = 1 kelas. Ubah BIL CALON → KELAS dikira semula (CEIL(calon/20)). "
                                   "Ubah KELAS terus jika perlu → PERLU (petugas) = KELAS + 9. "
                                   "Selepas simpan, Dashboard PPD, Dashboard SUP, Hasil Janaan dan halaman pilih sekolah ikut berubah.")
                        _ver_sp = st.session_state.get(f"ver_selpusat_{kod_ppd}", 0)
                        edited_df = st.data_editor(
                            df_editable,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "BIL": st.column_config.NumberColumn("BIL", width="small", disabled=True),
                                "NO_PUSAT": st.column_config.TextColumn("NO PUSAT", width="medium", disabled=True),
                                "NAMA_PUSAT": st.column_config.TextColumn("NAMA PUSAT", width="large", disabled=True),
                                "KOD_TUAN": st.column_config.TextColumn("KOD TUAN RUMAH", width="medium", disabled=True),
                                "BIL_CALON": st.column_config.NumberColumn("BIL CALON", help="Edit ikut keperluan sebenar", min_value=0, max_value=2000, step=1, required=True),
                                "KELAS": st.column_config.NumberColumn("KELAS", help="Auto: CEIL(Calon/20). Boleh edit terus.", min_value=0, max_value=100, step=1, required=True),
                                "PERLU_K9": st.column_config.NumberColumn("PERLU (K+9)", help="Auto: KELAS + 9", disabled=True),
                                "DICADANGKAN": st.column_config.NumberColumn("DICADANGKAN", disabled=True),
                                "STATUS": st.column_config.TextColumn("STATUS", disabled=True),
                                "KEKURANGAN": st.column_config.NumberColumn("KEKURANGAN", help="Auto kira: PERLU - DICADANGKAN", disabled=True),
                            },
                            key=f"ppd_edit_{kod_ppd}_{_ver_sp}",
                            num_rows="fixed"
                        )

                        _ubah_sp = selaras_edit_pusat(df_editable, edited_df)
                        if _ubah_sp:
                            st.markdown("**Pratonton perubahan (belum disimpan):**")
                            st.dataframe(pd.DataFrame([{
                                "NO_PUSAT": u["no"],
                                "CALON": f'{u["calon_lama"]} → {u["calon"]}',
                                "KELAS": f'{u["kelas_lama"]} → {u["kelas"]}',
                                "PETUGAS PERLU (K+9)": f'{u["perlu_lama"]} → {u["perlu"]}',
                                "KUOTA SEKOLAH (K+12)": f'{u["kelas_lama"] + 12} → {u["kelas"] + 12}',
                            } for u in _ubah_sp]), use_container_width=True, hide_index=True)

                        col_save, col_reset, col_info = st.columns([1, 1, 2])
                        with col_save:
                            if st.button("💾 Simpan Perubahan Pusat", type="primary", use_container_width=True,
                                         key=f"save_pusat_{kod_ppd}", disabled=not _ubah_sp):
                                _ok_n, _gagal_n = 0, []
                                for u in _ubah_sp:
                                    try:
                                        if simpan_pusat(supa, u["no"], u["calon"], u["kelas"]):
                                            _ok_n += 1
                                        else:
                                            _gagal_n.append(u["no"])
                                    except Exception as e:
                                        _gagal_n.append(f'{u["no"]} ({str(e)[:60]})')
                                try:
                                    st.cache_data.clear()
                                except Exception:
                                    pass
                                st.session_state[f"ver_selpusat_{kod_ppd}"] = _ver_sp + 1
                                if _ok_n:
                                    flash("success", f"✅ {_ok_n} pusat disimpan. Kuota petugas dikemas kini di semua paparan.")
                                if _gagal_n:
                                    flash("error", "Gagal simpan: " + ", ".join(_gagal_n[:5]))
                                st.rerun()

                        with col_reset:
                            if st.button("🔄 Kelas Auto (CEIL calon/20)", use_container_width=True, key=f"reset_auto_{kod_ppd}"):
                                _n_reset = 0
                                for _, _rw in df_editable.iterrows():
                                    try:
                                        _c = int(_rw["BIL_CALON"])
                                        if int(_rw["KELAS"]) != kelas_auto(_c) and simpan_pusat(supa, str(_rw["NO_PUSAT"]), _c, kelas_auto(_c)):
                                            _n_reset += 1
                                    except Exception:
                                        pass
                                try:
                                    st.cache_data.clear()
                                except Exception:
                                    pass
                                st.session_state[f"ver_selpusat_{kod_ppd}"] = _ver_sp + 1
                                flash("success", f"✅ KELAS dikira semula secara auto untuk {_n_reset} pusat.")
                                st.rerun()

                        with col_info:
                            st.caption(f"Total: {len(edited_df)} pusat | Boleh edit BIL CALON dan KELAS")

                        st.markdown("---")
                        st.markdown("#### ⚙️ Tetapan Maksimum Guru Sekolah Sama Setiap Pusat")
                        st.caption("Had bilangan guru dari SATU sekolah asal yang boleh bertugas di SATU pusat yang sama. "
                                   "Terpakai untuk Jana Keseluruhan, Jana Mengikut Jawatan, Penempatan Manual, Penempatan Zon, Hasil Janaan dan Semakan Lantikan.")
                        _mc1, _mc2, _mc3 = st.columns([1, 1, 2])
                        _max_baru = _mc1.number_input("Maksimum guru / sekolah / pusat", min_value=MAX_MIN, max_value=MAX_MAKS,
                                                      value=int(MAXS), step=1, key=f"max_sek_{kod_ppd}")
                        with _mc2:
                            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                            if st.button("💾 Simpan Tetapan", type="primary", use_container_width=True,
                                         key=f"simpan_max_{kod_ppd}", disabled=int(_max_baru) == int(MAXS)):
                                try:
                                    simpan_max(kod_ppd, int(_max_baru))
                                    try:
                                        st.cache_data.clear()
                                    except Exception:
                                        pass
                                    flash("success", f"✅ Maksimum guru sekolah sama setiap pusat ditetapkan: {int(_max_baru)}.")
                                except Exception as e:
                                    flash("error", "Gagal simpan tetapan (pastikan jadual landing_config wujud): " + str(e)[:80])
                                st.rerun()
                        _mc3.caption(f"Tetapan semasa PPD {kod_ppd}: **{MAXS}** guru. Lalai asal: 3. "
                                     "Jana semula / semak semula untuk pusat yang sudah melebihi had baharu.")

                    if fly_cur == "ringkasan":  # Paparan Warna digabung dengan Ringkasan
                        st.markdown("---")

                        # Also show colored HTML table for quick view
                        st.markdown("#### 📊 Paparan Status Berwarna")
                        # Create HTML table with colors
                        html_table = """
                    <style>
                    .ppd-table {width:100%; border-collapse:collapse; font-size:13px; background:white;}
                    .ppd-table th {background:#0d47a1; color:white; padding:0 8px; height:40px; text-align:left; font-weight:700; position:sticky; top:0; z-index:2; white-space:nowrap;}
                    .ppd-scroll {max-height:480px; overflow-y:auto; overflow-x:auto; border:2px solid #90caf9; border-radius:6px; background:white;}
                    .ppd-table td {padding:0 8px; height:44px; border-bottom:1px solid #e0e0e0; background:white; color:#0d47a1; white-space:nowrap;}
                    .ppd-table tr:hover td {background:#f5f5f5 !important;}
                    .badge-merah {background:#0d47a1 !important; color:#ffffff !important; padding:4px 8px; border-radius:12px; font-weight:700; border:2px solid #0d47a1;}
                    .badge-kuning {background:#bbdefb !important; color:#0d47a1 !important; padding:4px 8px; border-radius:12px; font-weight:700; border:2px solid #0d47a1;}
                    .badge-hijau {background:#ffffff !important; color:#0d47a1 !important; padding:4px 8px; border-radius:12px; font-weight:700; border:2px solid #0d47a1;}
                    .edit-hint {background:#e3f2fd; border-left:4px solid #1976d2; padding:6px 10px; margin:4px 0; font-size:11px;}
                    </style>
                    <div class="edit-hint">✏️ <b>PPD boleh edit:</b> BIL CALON, KELAS, PERLU (K+9) ikut keperluan sebenar - klik angka dalam table atas untuk edit &nbsp;|&nbsp; 📜 Papar 10 baris - skrol ke bawah untuk lihat selebihnya</div>
                    <div class="ppd-scroll"><table class="ppd-table">
                    <tr><th>BIL</th><th>NO PUSAT</th><th>NAMA PUSAT</th><th>KOD TUAN</th><th>BIL CALON ✏️</th><th>KELAS ✏️</th><th>PERLU (K+9) ✏️</th><th>DICADANG</th><th>STATUS</th></tr>
                    """

                        for _, r in (edited_df if 'edited_df' in locals() else df_editable).iterrows():
                            dic = r["DICADANGKAN"]
                            sep = r["PERLU_K9"]
                            if dic == 0:
                                badge_class = "badge-merah"
                                badge_text = f"🔴 {dic}"
                                status_badge = f'<span class="{badge_class}">🔴 Belum Ada</span>'
                            elif dic < sep:
                                badge_class = "badge-kuning"
                                badge_text = f"🟡 {dic}"
                                status_badge = f'<span class="{badge_class}">🟡 Belum Cukup</span>'
                            else:
                                badge_class = "badge-hijau"
                                badge_text = f"🟢 {dic}"
                                status_badge = f'<span class="{badge_class}">🟢 Cukup</span>'

                            html_table += f"<tr><td><b>{r['BIL']}</b></td><td><b>{r['NO_PUSAT']}</b></td><td>{r['NAMA_PUSAT']}</td><td>{r['KOD_TUAN']}</td><td style='text-align:center; background:#e3f2fd; font-weight:700; border:1px dashed #0d47a1;'>{r['BIL_CALON']}</td><td style='text-align:center; background:#e3f2fd; font-weight:700; border:1px dashed #1976d2;'>{r['KELAS']}</td><td style='text-align:center; background:#bbdefb; font-weight:700; border:1px dashed #0d47a1;'>{r['PERLU_K9']}</td><td style='text-align:center;'><span class='{badge_class}'>{badge_text}</span></td><td>{status_badge}</td></tr>"

                        html_table += "</table></div>"

                        st.markdown(html_table, unsafe_allow_html=True)

                    if fly_cur == "sekolah":
                        st.markdown("---")

                        # Export
                        with st.expander("📊 Export Data", expanded=False):
                            st.dataframe(df_pusat_ppd.sort_values("NO_PUSAT"), use_container_width=True, hide_index=True)
                            st.download_button(f"📥 Export Dashboard PPD {kod_ppd} (Excel)", to_excel(df_pusat_ppd), file_name=f"Dashboard_PPD_{kod_ppd}_{datetime.date.today()}.xlsx", use_container_width=True)

                        # Senarai sekolah dalam PPD
                        st.markdown("---")
                        st.markdown(f"### 🏫 Senarai Sekolah dalam PPD {kod_ppd} ({len(df_sekolah_list)} sekolah)")
                        if not df_sekolah_list.empty:
                            # Kira cadangan per sekolah
                            sekolah_cad_count = {}
                            if not df_cad_all.empty:
                                for _, c_row in df_cad_all.iterrows():
                                    k_sek = str(c_row.get("kod_sekolah") or c_row.get("kod_sekolah_asal") or "").upper().strip()
                                    if k_sek:
                                        sekolah_cad_count[k_sek] = sekolah_cad_count.get(k_sek, 0) + 1

                            # Kuota sekolah = jumlah (kelas+12) bagi pusat yang sekolah itu jadi tuan rumah (SAMA seperti Dashboard SUP)
                            perlu_sek, pusat_sek = {}, {}
                            for _, pp in df_pusat_ppd.iterrows():
                                ks_t = str(pp.get("KOD_TUAN_RUMAH") or "").upper().strip()
                                if not ks_t:
                                    continue
                                perlu_sek[ks_t] = perlu_sek.get(ks_t, 0) + kira_sekolah_perlu_calonkan(int(pp.get("KELAS") or 0))
                                pusat_sek.setdefault(ks_t, []).append(str(pp.get("NO_PUSAT") or ""))

                            sekolah_rows = []
                            for _, s in df_sekolah_list.iterrows():
                                k_sek = str(s.get("kod_sekolah") or s.get("KOD_SEKOLAH") or "").upper().strip()
                                n_sek = str(s.get("nama_sekolah") or s.get("NAMA_SEKOLAH") or "").upper().strip()
                                cad = sekolah_cad_count.get(k_sek, 0)
                                perlu = perlu_sek.get(k_sek, 0)
                                kurang = max(0, perlu - cad)

                                # Status ikut kuota yang perlu dihantar (sama seperti Ringkasan: KURANG n / CUKUP)
                                if perlu == 0:
                                    s_status = "⚪ Bukan Pusat" if cad == 0 else f"🟢 {cad} dicadang"
                                elif cad == 0:
                                    s_status = "🔴 Belum Cadang"
                                elif cad < perlu:
                                    s_status = f"🟡 Belum Lengkap (KURANG {kurang})"
                                else:
                                    s_status = "🟢 Lengkap (CUKUP)"

                                sekolah_rows.append({"Logo": "🏫", "KOD_SEKOLAH": k_sek, "NAMA_SEKOLAH": n_sek[:35],
                                                     "NO_PUSAT": ", ".join(pusat_sek.get(k_sek, [])),
                                                     "PERLU": perlu, "DICADANGKAN": cad, "KEKURANGAN": kurang, "STATUS": s_status})

                            df_sekolah_display = pd.DataFrame(sekolah_rows).sort_values("KOD_SEKOLAH")
                            _st = df_sekolah_display["STATUS"].astype(str)
                            m1, m2, m3, m4 = st.columns(4)
                            m1.metric("🟢 Lengkap", int(_st.str.startswith("🟢").sum()))
                            m2.metric("🟡 Belum Lengkap", int(_st.str.startswith("🟡").sum()))
                            m3.metric("🔴 Belum Cadang", int(_st.str.startswith("🔴").sum()))
                            m4.metric("📋 Kurang (orang)", int(df_sekolah_display["KEKURANGAN"].sum()))
                            st.caption("Status ikut kuota calon yang SUP perlu hantar (kelas + 12 bagi pusat di sekolah itu) - sama seperti Dashboard SUP & Ringkasan.")
                            st.dataframe(df_sekolah_display, use_container_width=True, hide_index=True)
                            st.download_button("📥 Export Senarai Sekolah + Status (Excel)", to_excel(df_sekolah_display),
                                               file_name=f"Sekolah_PPD_{kod_ppd}_{datetime.date.today()}.xlsx", key=f"dl_sek_status_{kod_ppd}")
                        else:
                            st.info(f"Tiada sekolah dijumpai untuk PPD {kod_ppd}")

            except Exception as e:
                st.error(f"Error dashboard PPD: {e}")
                # Fallback simple
                try:
                    cnt_sekolah = supa.table("sekolah_master").select("kod_sekolah", count="exact").eq("kod_ppd", kod_ppd).execute()
                    cnt_cadang = supa.table("cadangan_sup").select("id", count="exact").eq("kod_ppd", kod_ppd).execute()
                    c1, c2 = st.columns(2)
                    c1.metric("Sekolah", cnt_sekolah.count)
                    c2.metric("Cadangan", cnt_cadang.count)
                except Exception as e2:
                    st.error(f"Fallback error: {e2}")

        elif menu == "sekolah":
            st.header(f"Senarai Sekolah PPD {kod_ppd}")
            try:
                res = supa.table("sekolah_master").select("*").eq("kod_ppd", kod_ppd).limit(2000).execute()
                df = pd.DataFrame(res.data or [])
                st.dataframe(df, use_container_width=True)
                st.download_button("Export Sekolah", to_excel(df), file_name=f"sekolah_{kod_ppd}.xlsx")
            except Exception as e:
                st.error(f"Error baca sekolah: {e}")

        elif menu == "pusat":
            st.header(f"Pusat di PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')} - Total Calon & Poskod Pusat")
            st.caption("Filter BETUL ikut NO_PUSAT prefix BA=Klang sahaja | PPD boleh tambah/edit POSKOD PUSAT untuk jana ikut poskod terdekat")
            df_pusat_raw = get_pusat_df()
            if df_pusat_raw.empty:
                st.info("pusat_master kosong")
            else:
                rows = []
                for _, r in df_pusat_raw.iterrows():
                    d = r.get("data") if isinstance(r.get("data"), dict) else {}
                    if isinstance(d, str):
                        try: d = json.loads(d)
                        except: d = {}
                    no_pusat = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                    nama = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                    _q = kuota_pusat(r)
                    jc, jk = _q["calon"], _q["kelas"]
                    rows.append({"NO_PUSAT": no_pusat, "NAMA_PUSAT": nama, "JUMLAH_CALON": jc, "JUMLAH_KELAS": jk, "PETUGAS_K9": kira_petugas_dari_kelas(jk), "SEKOLAH_PERLU": kira_sekolah_perlu_calonkan(jk)})

                df_all = pd.DataFrame(rows)
                df_f = df_all[df_all["NO_PUSAT"].str.startswith(kod_ppd.upper())].copy() if not df_all.empty else df_all
                if df_f.empty:
                    st.warning(f"Tiada pusat dengan prefix {kod_ppd}")
                else:
                    if fly_cur == "senarai":
                        st.success(f"Jumpa {len(df_f)} pusat di PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')}")
                        st.dataframe(df_f.sort_values("NO_PUSAT"), use_container_width=True, hide_index=True)
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Jumlah Pusat", len(df_f))
                        c2.metric("Total Calon", int(df_f["JUMLAH_CALON"].sum()))
                        c3.metric("Total Kelas", int(df_f["JUMLAH_KELAS"].sum()))
                        c4.metric("Total Perlu", int(df_f["SEKOLAH_PERLU"].sum()))
                        st.download_button(f"Export Pusat {kod_ppd}", to_excel(df_f), file_name=f"pusat_{kod_ppd}.xlsx", use_container_width=True)

                    if fly_cur == "poskod":
                        st.markdown("---")
                        st.markdown("### 📮 Tambah/Edit Poskod Pusat (Untuk Jana Poskod Terdekat)")
                        st.info("💡 Poskod Pusat diperlukan untuk sistem kira jarak poskod rumah guru vs pusat. Kalau kosong, sistem akan guna poskod sekolah tuan rumah sebagai fallback.")
                        with st.expander("✏️ Edit Poskod Pusat - Klik untuk buka", expanded=False):
                            # Build editable table for poskod
                            poskod_rows = []
                            for _, r in df_f.iterrows():
                                no_p = r["NO_PUSAT"]
                                # Try get existing poskod
                                existing_poskod = ""
                                try:
                                    df_raw = df_pusat_raw
                                    for _, pr in df_raw.iterrows():
                                        d = pr.get("data") if isinstance(pr.get("data"), dict) else {}
                                        if isinstance(d, str):
                                            try: d = json.loads(d)
                                            except: d = {}
                                        no_check = str(pr.get("no_pusat") or pr.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                                        if no_check == no_p:
                                            existing_poskod = str(pr.get("poskod") or d.get("POSKOD") or d.get("POSKOD_PUSAT") or "").strip()
                                            break
                                except:
                                    pass
                                poskod_rows.append({"NO_PUSAT": no_p, "NAMA_PUSAT": r["NAMA_PUSAT"][:30], "POSKOD_SEKARANG": existing_poskod, "POSKOD_BARU": existing_poskod})
                            df_poskod_edit = pd.DataFrame(poskod_rows)
                            edited_poskod = st.data_editor(
                                df_poskod_edit,
                                column_config={
                                    "NO_PUSAT": st.column_config.TextColumn("NO_PUSAT", disabled=True),
                                    "NAMA_PUSAT": st.column_config.TextColumn("NAMA PUSAT", disabled=True),
                                    "POSKOD_SEKARANG": st.column_config.TextColumn("Sekarang", disabled=True),
                                    "POSKOD_BARU": st.column_config.TextColumn("Poskod Baru (5 digit)", help="Contoh: 41000 untuk Klang"),
                                },
                                use_container_width=True,
                                hide_index=True,
                                key="edit_poskod_pusat"
                            )
                            if st.button("💾 Simpan Poskod Pusat", type="primary", use_container_width=True, key="simpan_poskod_pusat"):
                                try:
                                    berjaya_poskod = 0
                                    for _, row_edit in edited_poskod.iterrows():
                                        no_p = row_edit["NO_PUSAT"]
                                        pk_baru = str(row_edit["POSKOD_BARU"]).strip()
                                        if not pk_baru or pk_baru == row_edit["POSKOD_SEKARANG"]:
                                            continue
                                        # Update pusat_master
                                        try:
                                            # Get existing record
                                            res = supa.table("pusat_master").select("*").eq("no_pusat", no_p).limit(1).execute()
                                            if not res.data:
                                                res = supa.table("pusat_master").select("*").eq("kod_pusat", no_p).limit(1).execute()
                                            if res.data:
                                                rec = res.data[0]
                                                rec_id = rec.get("id")
                                                d = rec.get("data") or {}
                                                if isinstance(d, str):
                                                    try: d = json.loads(d)
                                                    except: d = {}
                                                d["POSKOD"] = pk_baru
                                                d["POSKOD_PUSAT"] = pk_baru
                                                # Try update with poskod column if exists, else only data
                                                try:
                                                    supa.table("pusat_master").update({"poskod": pk_baru, "data": d}).eq("id", rec_id).execute()
                                                except:
                                                    supa.table("pusat_master").update({"data": d}).eq("id", rec_id).execute()
                                                berjaya_poskod += 1
                                        except Exception as e:
                                            st.warning(f"{no_p}: {e}")
                                    st.success(f"✅ Berjaya kemaskini {berjaya_poskod} poskod pusat!")
                                    st.balloons()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error simpan poskod: {e}")



        elif menu == "jana":
            st.markdown(f"""
            <div style="background: #0d47a1; padding:20px; border-radius:12px; color:white; border: 2px solid #002171; margin-bottom:20px;">
                <div style="display:flex; align-items:center; gap:15px;">
                    <div style="font-size:48px;">🚀</div>
                    <div>
                        <h2 style="margin:0; color:white; font-size:24px;">Jana Keseluruhan - PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')}</h2>
                        <p style="margin:5px 0 0 0; color:#bbdefb; font-size:13px;">Pilih: Jana Keseluruhan (Auto Poskod Terdekat) atau Jana Mengikut Jawatan - Kekal Max {MAXS}</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            df_pusat_raw = get_pusat_df()
            df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)
            df_cad_all = jana_pool_panel(kod_ppd, df_cad_all)   # hanya calon TERPILIH PPD (+ yang sudah diproses)

            if df_pusat_raw.empty:
                st.warning("⚠️ Tiada pusat_master")
                st.stop()
            if df_cad_all.empty:
                st.warning("⚠️ Belum ada calon untuk dijana. Lihat arahan di atas.")
                st.stop()

            # Parse pusat with poskod
            rows = []
            for _, r in df_pusat_raw.iterrows():
                d = r.get("data") if isinstance(r.get("data"), dict) else {}
                if isinstance(d, str):
                    try: d = json.loads(d)
                    except: d = {}
                no_pusat = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                if not no_pusat.startswith(kod_ppd.upper()): continue
                nama = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                kod_sek_tuan = str(r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or "").upper().strip()
                poskod_pusat = str(r.get("poskod") or d.get("POSKOD") or d.get("POSKOD_PUSAT") or "").strip()
                _q = kuota_pusat(r)
                jc, jk = _q["calon"], _q["kelas"]
                rows.append({"NO_PUSAT": no_pusat, "NAMA_PUSAT": nama, "KOD_SEKOLAH_TUAN_RUMAH": kod_sek_tuan, "JUMLAH_CALON": jc, "JUMLAH_KELAS": jk, "PETUGAS": kira_petugas_dari_kelas(jk), "POSKOD_PUSAT": poskod_pusat})
            df_pusat_ppd = pd.DataFrame(rows)

            if df_pusat_ppd.empty:
                st.warning(f"Tiada pusat dengan prefix {kod_ppd}")
                st.stop()

            def get_poskod_guru(row):
                return str(row.get("POSKOD_RUMAH") or row.get("poskod_rumah") or "").strip()
            def get_poskod_pusat_val(no_pusat):
                r = df_pusat_ppd[df_pusat_ppd["NO_PUSAT"]==no_pusat]
                if not r.empty:
                    pk = str(r.iloc[0].get("POSKOD_PUSAT") or "").strip()
                    if pk and pk.lower() not in ("none","nan",""):
                        return pk
                try:
                    kod_tuan = str(r.iloc[0].get("KOD_SEKOLAH_TUAN_RUMAH") or "").strip() if not r.empty else ""
                    if kod_tuan:
                        res_sek = supa.table("sekolah_master").select("*").eq("kod_sekolah", kod_tuan).limit(1).execute()
                        if res_sek.data:
                            d = res_sek.data[0].get("data") or {}
                            if isinstance(d, str):
                                try: d = json.loads(d)
                                except: d = {}
                            pk = str(res_sek.data[0].get("poskod") or d.get("POSKOD") or "").strip()
                            if pk: return pk
                except: pass
                return ""
            def poskod_distance(pk_guru, pk_pusat):
                try:
                    g = int(re.sub(r"\D","", pk_guru)[:5] or 0)
                    p = int(re.sub(r"\D","", pk_pusat)[:5] or 0)
                    if g==0 or p==0: return 99999
                    return abs(g-p)
                except: return 99999

            # ===== SUB MENU UTAMA =====
            sub_jana = "🌍 Jana Keseluruhan (Auto Poskod Terdekat)" if fly_cur == "auto" else "👑 Jana Mengikut Jawatan"

            # ===== TAB 1: JANA KESELURUHAN AUTO POSKOD =====
            if "Jana Keseluruhan" in sub_jana:
                st.markdown("### 🌍 Jana Keseluruhan - Auto Poskod Terdekat")
                st.info(f"Baca POSKOD RUMAH guru vs POSKOD PUSAT, pusat paling dekat dulu. Kalau penuh, auto ke pusat kedua terdekat. Kekal Max {MAXS} & elak sekolah sendiri. Penyelia Kawasan TIDAK termasuk di sini - lantik di Selenggara Bilik Kebal.")

                # FIX FINAL: Jana Keseluruhan Auto HANYA untuk 3 jawatan biasa sahaja - Khas langsung tak masuk
                # Hanya benarkan: Ketua Pengawas, Timbalan Ketua Pengawas, Pengawas Peperiksaan (exact)
                # Semua Khas (Juru Tulis, Juru Baca, Hospital, Pengiring, Pengemas, Penyelia) dikeluarkan terus - hanya di Penempatan Manual sahaja
                def is_auto_jawatan(r):
                    j = str(r.get("JAWATAN_CADANGAN") or r.get("jawatan_cadangan") or r.get("JAWATAN") or "").upper().strip()
                    # Hanya 3 ini sahaja yang boleh auto
                    if "KETUA PENGAWAS" in j and "TIMBALAN" not in j and "HOSPITAL" not in j:
                        return True
                    if "TIMBALAN KETUA PENGAWAS" in j or ("TIMBALAN" in j and "KETUA" in j and "HOSPITAL" not in j):
                        return True
                    if j == "PENGAWAS PEPERIKSAAN" or (j.startswith("PENGAWAS") and "HOSPITAL" not in j and "PENGIRING" not in j and "KHAS" not in j):
                        # Pengawas Peperiksaan biasa sahaja
                        if "HOSPITAL" in j or "PENGIRING" in j or "JURU" in j or "PENGEMAS" in j or "PENYELIA" in j or "SELENGGARA" in j or "MAKMAL" in j:
                            return False
                        return True
                    # Semua lain (Juru Tulis, Juru Baca, Hospital, Pengiring, Pengemas, Penyelia, Selenggara) = False - tak masuk auto
                    return False

                df_cad_all_auto = df_cad_all[df_cad_all.apply(is_auto_jawatan, axis=1)].copy() if not df_cad_all.empty else df_cad_all.copy()
                # Info
                try:
                    khas_count = len(df_cad_all) - len(df_cad_all_auto)
                    if khas_count > 0:
                        st.info(f"ℹ️ Jana Keseluruhan Auto: {len(df_cad_all_auto)} petugas biasa (KP/TKP/Pengawas) akan dijana auto. {khas_count} Pengawas Khas (JT/JB/Hospital/Pengiring/Pengemas/Penyelia) TIDAK termasuk auto - sila guna Jana Ikut Jawatan atau Penempatan Manual")
                except:
                    pass

                cad_per_sekolah = {}
                for _, c in df_cad_all_auto.iterrows():
                    k_sek = str(c.get("KOD_SEKOLAH") or c.get("KOD_SEKOLAH_ASAL") or "").upper().strip()
                    if k_sek: cad_per_sekolah[k_sek] = cad_per_sekolah.get(k_sek, 0) + 1
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("📚 Sekolah Mencadang", len(cad_per_sekolah))
                c2.metric("👨‍🏫 Guru Dicadang", len(df_cad_all))
                c3.metric("🏫 Pusat", len(df_pusat_ppd))
                c4.metric("📋 Perlu Petugas", int(df_pusat_ppd["PETUGAS"].sum()))

                with st.expander(f"📋 Lihat {len(df_cad_all)} Cadangan Dari SUP", expanded=False):
                    cols = [c for c in ["NAMA_GURU","IC_GURU","JANTINA","POSKOD_RUMAH","JAWATAN_CADANGAN","KOD_SEKOLAH_ASAL","STATUS"] if c in df_cad_all.columns]
                    st.dataframe(df_cad_all[cols] if cols else df_cad_all, use_container_width=True, hide_index=True)

                col_jana_all, col_clear = st.columns([3,1])
                with col_jana_all:
                    btn_jana_all = st.button("🌍 JANA KESELURUHAN - Auto Poskod Terdekat (1 KP + 1 TKP + Pengawas)", type="primary", use_container_width=True, key="btn_jana_all_poskod_v3")
                with col_clear:
                    if st.button("🗑️ Clear", use_container_width=True, key="clear_jana_all_v3"):
                        if "jana_all_result" in st.session_state: del st.session_state["jana_all_result"]
                        st.rerun()

                if btn_jana_all or "jana_all_result" in st.session_state:
                    if btn_jana_all:
                        import random
                        assignments = []
                        df_pool_all = df_cad_all.copy()
                        def is_belum(row):
                            kp = str(row.get("kod_pusat") or row.get("KOD_PUSAT") or "").strip()
                            return kp == "" or kp.lower() in ("none","null","nan","nat","-")
                        df_pool = df_pool_all[df_pool_all.apply(is_belum, axis=1)].copy()
                        if df_pool.empty:
                            st.warning("Semua guru telah dilantik!")
                            st.stop()
                        pusat_info_map = {}
                        for _, p in df_pusat_ppd.iterrows():
                            pusat_info_map[p["NO_PUSAT"]] = {"KOD_TUAN": str(p.get("KOD_SEKOLAH_TUAN_RUMAH","") or "").upper().strip(), "NAMA": p.get("NAMA_PUSAT",""), "PETUGAS": int(p.get("PETUGAS",0)), "POSKOD": str(p.get("POSKOD_PUSAT") or "").strip()}
                        df_pool["POSKOD_GURU_NORM"] = df_pool.apply(lambda r: get_poskod_guru(r), axis=1)
                        df_pool_shuffled = df_pool.sample(frac=1, random_state=random.randint(1,100000)).reset_index(drop=True)
                        pusat_sekolah_count = {}
                        pusat_total = {no:0 for no in pusat_info_map.keys()}
                        pusat_kp = {no:0 for no in pusat_info_map.keys()}
                        pusat_tkp = {no:0 for no in pusat_info_map.keys()}
                        used_ic = set()
                        def cari_pusat_terdekat(guru_row):
                            poskod_guru = str(guru_row.get("POSKOD_GURU_NORM") or "")
                            kod_sek_guru = str(guru_row.get("KOD_SEKOLAH_ASAL") or "").upper().strip()
                            jarak_list = []
                            for no_pusat, info in pusat_info_map.items():
                                if info["KOD_TUAN"] and kod_sek_guru and info["KOD_TUAN"] == kod_sek_guru: continue
                                if pusat_sekolah_count.get((no_pusat, kod_sek_guru),0) >= MAXS: continue
                                if pusat_total.get(no_pusat,0) >= info["PETUGAS"]: continue
                                jaw = str(guru_row.get("JAWATAN_CADANGAN") or "").upper()
                                if "KETUA PENGAWAS" in jaw and "TIMBALAN" not in jaw:
                                    if pusat_kp.get(no_pusat,0) >=1: continue
                                elif "TIMBALAN" in jaw:
                                    if pusat_tkp.get(no_pusat,0) >=1: continue
                                poskod_pusat_val = get_poskod_pusat_val(no_pusat) or info.get("POSKOD","")
                                jarak = poskod_distance(poskod_guru, poskod_pusat_val)
                                jarak_list.append((jarak, no_pusat))
                            jarak_list.sort(key=lambda x: x[0])
                            return [no for _, no in jarak_list]
                        # KP
                        for _, guru_row in df_pool_shuffled.iterrows():
                            ic = str(guru_row.get("IC_GURU") or "")
                            if ic in used_ic: continue
                            jaw = str(guru_row.get("JAWATAN_CADANGAN") or "").upper()
                            if "KETUA PENGAWAS" not in jaw or "TIMBALAN" in jaw: continue
                            cands = cari_pusat_terdekat(guru_row)
                            if not cands: continue
                            chosen = cands[0]
                            assignments.append({"IC_GURU": ic, "NAMA_GURU": guru_row.get("NAMA_GURU",""), "KOD_SEKOLAH_ASAL": str(guru_row.get("KOD_SEKOLAH_ASAL") or "").upper(), "JAWATAN_CADANGAN": guru_row.get("JAWATAN_CADANGAN",""), "POSKOD_RUMAH": guru_row.get("POSKOD_GURU_NORM",""), "NO_PUSAT_TUGAS": chosen, "NAMA_PUSAT_TUGAS": pusat_info_map[chosen]["NAMA"], "id": guru_row.get("id","")})
                            used_ic.add(ic)
                            pusat_sekolah_count[(chosen, str(guru_row.get("KOD_SEKOLAH_ASAL") or "").upper())] = pusat_sekolah_count.get((chosen, str(guru_row.get("KOD_SEKOLAH_ASAL") or "").upper()),0)+1
                            pusat_total[chosen] +=1
                            pusat_kp[chosen] +=1
                        # TKP
                        for _, guru_row in df_pool_shuffled.iterrows():
                            ic = str(guru_row.get("IC_GURU") or "")
                            if ic in used_ic: continue
                            if "TIMBALAN" not in str(guru_row.get("JAWATAN_CADANGAN") or "").upper(): continue
                            cands = cari_pusat_terdekat(guru_row)
                            if not cands: continue
                            chosen = cands[0]
                            assignments.append({"IC_GURU": ic, "NAMA_GURU": guru_row.get("NAMA_GURU",""), "KOD_SEKOLAH_ASAL": str(guru_row.get("KOD_SEKOLAH_ASAL") or "").upper(), "JAWATAN_CADANGAN": guru_row.get("JAWATAN_CADANGAN",""), "POSKOD_RUMAH": guru_row.get("POSKOD_GURU_NORM",""), "NO_PUSAT_TUGAS": chosen, "NAMA_PUSAT_TUGAS": pusat_info_map[chosen]["NAMA"], "id": guru_row.get("id","")})
                            used_ic.add(ic)
                            pusat_sekolah_count[(chosen, str(guru_row.get("KOD_SEKOLAH_ASAL") or "").upper())] = pusat_sekolah_count.get((chosen, str(guru_row.get("KOD_SEKOLAH_ASAL") or "").upper()),0)+1
                            pusat_total[chosen] +=1
                            pusat_tkp[chosen] +=1
                        # Pengawas - HANYA Pengawas Peperiksaan biasa sahaja - Khas (JT/JB/Hospital/Pengiring/Pengemas/Penyelia) langsung tak masuk auto, hanya Penempatan Manual
                        def is_pengawas_biasa_only(row):
                            j = str(row.get("JAWATAN_CADANGAN") or row.get("jawatan_cadangan") or "").upper().strip()
                            # Hanya Pengawas Peperiksaan exact sahaja
                            if "PENGAWAS PEPERIKSAAN" not in j:
                                return False
                            if any(k in j for k in ["PENYELIA", "JURU", "HOSPITAL", "PENGIRING", "PENGEMAS", "SELENGGARA", "BILIK KEBAL", "MAKMAL"]):
                                return False
                            return True
                        df_pool_biasa = [r for _, r in df_pool_shuffled.iterrows() if is_pengawas_biasa_only(r)]
                        for guru_row in df_pool_biasa:
                            ic = str(guru_row.get("IC_GURU") or "")
                            if ic in used_ic: continue
                            jaw = str(guru_row.get("JAWATAN_CADANGAN") or "").upper()
                            if "KETUA PENGAWAS" in jaw: continue
                            if "TIMBALAN" in jaw: continue
                            if "PENYELIA" in jaw: continue
                            cands = cari_pusat_terdekat(guru_row)
                            if not cands: continue
                            chosen = cands[0]
                            poskod_guru = str(guru_row.get("POSKOD_GURU_NORM") or "")
                            poskod_pusat_val = get_poskod_pusat_val(chosen) or pusat_info_map[chosen].get("POSKOD","")
                            jarak_val = poskod_distance(poskod_guru, poskod_pusat_val)
                            assignments.append({"IC_GURU": ic, "NAMA_GURU": guru_row.get("NAMA_GURU",""), "KOD_SEKOLAH_ASAL": str(guru_row.get("KOD_SEKOLAH_ASAL") or "").upper(), "JAWATAN_CADANGAN": guru_row.get("JAWATAN_CADANGAN",""), "POSKOD_RUMAH": poskod_guru, "POSKOD_PUSAT": poskod_pusat_val, "NO_PUSAT_TUGAS": chosen, "NAMA_PUSAT_TUGAS": pusat_info_map[chosen]["NAMA"], "JARAK": jarak_val, "id": guru_row.get("id","")})
                            used_ic.add(ic)
                            pusat_sekolah_count[(chosen, str(guru_row.get("KOD_SEKOLAH_ASAL") or "").upper())] = pusat_sekolah_count.get((chosen, str(guru_row.get("KOD_SEKOLAH_ASAL") or "").upper()),0)+1
                            pusat_total[chosen] +=1
                        st.session_state["jana_all_result"] = assignments
                        st.success(f"✅ Berjaya jana {len(assignments)} guru ikut poskod terdekat!")
                    else:
                        assignments = st.session_state.get("jana_all_result", [])

                    if st.session_state.get("jana_all_result"):
                        df_assign = pd.DataFrame(st.session_state["jana_all_result"])
                        st.dataframe(df_assign, use_container_width=True, hide_index=True)
                        if st.button("💾 Simpan Jana Keseluruhan ke DB", type="primary", use_container_width=True, key="simpan_jana_all_v3"):
                            try:
                                for a in assignments:
                                    if a.get("id"):
                                        supa.table("cadangan_sup").update({"kod_pusat": a.get("NO_PUSAT_TUGAS"), "status": "DILANTIK PPD"}).eq("id", a.get("id")).execute()
                                    else:
                                        supa.table("cadangan_sup").update({"kod_pusat": a.get("NO_PUSAT_TUGAS"), "status": "DILANTIK PPD"}).eq("ic_guru", a.get("IC_GURU")).execute()
                                st.success(f"✅ {len(assignments)} disimpan!")
                                st.balloons()
                            except Exception as e:
                                st.error(f"Gagal: {e}")
                        st.download_button("📥 Export", to_excel(df_assign), file_name=f"jana_poskod_{kod_ppd}.xlsx", use_container_width=True)

            # ===== TAB 2: JANA MENGIKUT JAWATAN - FIXED VISIBLE =====
            else:
                st.markdown("### 👑 Jana Mengikut Jawatan")
                st.info("Klik jawatan di bawah, sistem akan paparkan semua guru jawatan tersebut yang BELUM ditempatkan lagi. Kemudian pilih pusat & jana.")

                # Pilihan jawatan - BUTTON style - TANPA Penyelia Kawasan (sebab lantik di Selenggara Bilik Kebal)
                st.markdown("#### Pilih Jawatan (Klik untuk papar - Penyelia Kawasan tidak perlu di sini, lantik di Selenggara Bilik Kebal):")
                col_j1, col_j2, col_j3 = st.columns(3)
                with col_j1:
                    btn_kp = st.button("👑 Ketua Pengawas", use_container_width=True, key="btn_jawatan_kp_main", type="primary" if st.session_state.get("pilih_jawatan_jana_main")=="Ketua Pengawas" else "secondary")
                with col_j2:
                    btn_tkp = st.button("👑 Timbalan KP", use_container_width=True, key="btn_jawatan_tkp_main", type="primary" if st.session_state.get("pilih_jawatan_jana_main")=="Timbalan Ketua Pengawas" else "secondary")
                with col_j3:
                    btn_peng = st.button("👨‍🏫 Pengawas Peperiksaan", use_container_width=True, key="btn_jawatan_peng_main", type="primary" if st.session_state.get("pilih_jawatan_jana_main")=="Pengawas Peperiksaan" else "secondary")

                # Set session based on button click
                if btn_kp:
                    st.session_state["pilih_jawatan_jana_main"] = "Ketua Pengawas"
                if btn_tkp:
                    st.session_state["pilih_jawatan_jana_main"] = "Timbalan Ketua Pengawas"
                if btn_peng:
                    st.session_state["pilih_jawatan_jana_main"] = "Pengawas Peperiksaan"

                # Default
                if "pilih_jawatan_jana_main" not in st.session_state:
                    st.session_state["pilih_jawatan_jana_main"] = "Ketua Pengawas"

                pilih_jawatan_jana = st.session_state["pilih_jawatan_jana_main"]
                st.markdown(f"### 📋 {pilih_jawatan_jana} - Belum Ditempatkan")

                # Filter guru by jawatan & belum lantik
                def match_jawatan(row, target):
                    jaw = str(row.get("JAWATAN_CADANGAN") or row.get("jawatan_cadangan") or "").upper()
                    tgt = target.upper()
                    if "KETUA PENGAWAS" in tgt and "TIMBALAN" not in tgt:
                        return "KETUA PENGAWAS" in jaw and "TIMBALAN" not in jaw
                    elif "TIMBALAN" in tgt:
                        return "TIMBALAN" in jaw
                    elif "PENGAWAS PEPERIKSAAN" in tgt or tgt=="PENGAWAS PEPERIKSAAN":
                        return "PENGAWAS PEPERIKSAAN" in jaw or (jaw.strip()=="PENGAWAS")
                    elif "PENYELIA" in tgt:
                        return "PENYELIA" in jaw
                    else:
                        return tgt in jaw

                df_jawatan_all = df_cad_all[df_cad_all.apply(lambda r: match_jawatan(r, pilih_jawatan_jana), axis=1)].copy()
                df_belum_jawatan = df_jawatan_all[df_jawatan_all.apply(lambda r: str(r.get("kod_pusat") or r.get("KOD_PUSAT") or "").strip() in ("", "None", "none", "null", "nan", "nat"), axis=1)].copy()

                if df_belum_jawatan.empty:
                    st.warning(f"⚠️ Tiada {pilih_jawatan_jana} yang belum ditempatkan - semua sudah dilantik atau tiada cadangan jawatan ini.")
                    if not df_jawatan_all.empty:
                        st.info(f"Ada {len(df_jawatan_all)} {pilih_jawatan_jana} total, tapi semua sudah ada kod_pusat.")
                        st.dataframe(df_jawatan_all[["NAMA_GURU","IC_GURU","KOD_SEKOLAH_ASAL","kod_pusat","STATUS"]].head(20), use_container_width=True)
                else:
                    st.success(f"✅ Jumpa {len(df_belum_jawatan)} {pilih_jawatan_jana} yang BELUM ditempatkan lagi")

                    # Add poskod & jarak sorting - need to choose pusat first? Show without pusat first, then allow pilih pusat
                    # Show list of guru belum ditempatkan
                    display_belum = []
                    for _, r in df_belum_jawatan.iterrows():
                        display_belum.append({
                            "id": r.get("id",""),
                            "NAMA GURU": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                            "IC": r.get("IC_GURU","") or r.get("ic_guru",""),
                            "JAWATAN": r.get("JAWATAN_CADANGAN","") or r.get("jawatan_cadangan",""),
                            "SEKOLAH ASAL": r.get("KOD_SEKOLAH_ASAL","") or r.get("kod_sekolah_asal",""),
                            "POSKOD RUMAH": r.get("POSKOD_RUMAH","") or r.get("poskod_rumah",""),
                            "TELEFON": r.get("TELEFON_GURU","") or r.get("telefon_guru",""),
                            "STATUS": r.get("STATUS","") or r.get("status","")
                        })
                    df_display_belum = pd.DataFrame(display_belum)
                    st.dataframe(df_display_belum, use_container_width=True, hide_index=True)

                    st.markdown("---")
                    st.markdown(f"#### 🎯 Pilih Pusat Untuk {pilih_jawatan_jana} Ini")

                    # Pilih pusat dropdown
                    pilihan_pusat_jawatan = st.selectbox(
                        f"Pilih Pusat Peperiksaan untuk {pilih_jawatan_jana}",
                        df_pusat_ppd["NO_PUSAT"].tolist(),
                        format_func=lambda x: f"{x} - {df_pusat_ppd[df_pusat_ppd['NO_PUSAT']==x]['NAMA_PUSAT'].values[0][:35] if not df_pusat_ppd[df_pusat_ppd['NO_PUSAT']==x].empty else x} (Perlu {df_pusat_ppd[df_pusat_ppd['NO_PUSAT']==x]['PETUGAS'].values[0] if not df_pusat_ppd[df_pusat_ppd['NO_PUSAT']==x].empty else '?'})",
                        key=f"pilih_pusat_jawatan_v3_{pilih_jawatan_jana}"
                    )

                    info_pusat = df_pusat_ppd[df_pusat_ppd["NO_PUSAT"]==pilihan_pusat_jawatan]
                    kod_tuan = str(info_pusat["KOD_SEKOLAH_TUAN_RUMAH"].values[0] if not info_pusat.empty else "").upper().strip()
                    poskod_pusat_val = get_poskod_pusat_val(pilihan_pusat_jawatan)

                    st.caption(f"Pusat {pilihan_pusat_jawatan} | Tuan Rumah: {kod_tuan or 'Tiada'} | Poskod Pusat: {poskod_pusat_val or 'Fallback poskod sekolah'} | Max {MAXS} per sekolah | Elak sekolah sendiri")

                    # Count current in pusat
                    try:
                        res_curr = supa.table("cadangan_sup").select("*").eq("kod_pusat", pilihan_pusat_jawatan).limit(5000).execute()
                        df_curr = pd.DataFrame(res_curr.data or [])
                        sekolah_count_curr = {}
                        if not df_curr.empty:
                            for _, r in df_curr.iterrows():
                                ks = str(r.get("kod_sekolah_asal") or "").upper().strip()
                                sekolah_count_curr[ks] = sekolah_count_curr.get(ks, 0) + 1
                        st.info(f"ℹ️ Pusat {pilihan_pusat_jawatan} sudah ada {len(df_curr)} petugas ditempatkan. Sekolah count: {sekolah_count_curr}")
                    except:
                        df_curr = pd.DataFrame()
                        sekolah_count_curr = {}

                    # Filter eligible by max3 & sekolah sendiri & poskod terdekat
                    eligible_with_jarak = []
                    for _, r in df_belum_jawatan.iterrows():
                        ks = str(r.get("KOD_SEKOLAH_ASAL") or r.get("kod_sekolah_asal") or "").upper().strip()
                        if kod_tuan and ks == kod_tuan: continue
                        if sekolah_count_curr.get(ks,0) >= MAXS: continue
                        pk_guru = str(r.get("POSKOD_RUMAH") or r.get("poskod_rumah") or "")
                        jarak = poskod_distance(pk_guru, poskod_pusat_val)
                        eligible_with_jarak.append((jarak, r))

                    eligible_with_jarak.sort(key=lambda x: x[0])

                    if not eligible_with_jarak:
                        st.warning(f"Tiada calon layak untuk pusat ini (semua sekolah sama atau max {MAXS})")
                    else:
                        st.markdown(f"**{len(eligible_with_jarak)} calon {pilih_jawatan_jana} layak untuk {pilihan_pusat_jawatan} (disusun poskod terdekat):**")
                        display_eligible = []
                        for jarak, r in eligible_with_jarak:
                            display_eligible.append({
                                "JARAK": jarak if jarak!=99999 else "Tiada poskod",
                                "NAMA GURU": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                                "IC": r.get("IC_GURU","") or r.get("ic_guru",""),
                                "SEKOLAH ASAL": r.get("KOD_SEKOLAH_ASAL","") or r.get("kod_sekolah_asal",""),
                                "POSKOD RUMAH": r.get("POSKOD_RUMAH","") or r.get("poskod_rumah",""),
                                "POSKOD PUSAT": poskod_pusat_val,
                                "id": r.get("id","")
                            })
                        df_eligible_disp = pd.DataFrame(display_eligible)
                        st.dataframe(df_eligible_disp, use_container_width=True, hide_index=True)

                        pilih_guru_jawatan = st.multiselect(
                            f"Pilih {pilih_jawatan_jana} untuk lantik ke {pilihan_pusat_jawatan} (paling dekat di atas)",
                            df_eligible_disp["id"].tolist(),
                            format_func=lambda x: f"{df_eligible_disp[df_eligible_disp['id']==x]['NAMA GURU'].values[0]} - {df_eligible_disp[df_eligible_disp['id']==x]['SEKOLAH ASAL'].values[0]} - Poskod {df_eligible_disp[df_eligible_disp['id']==x]['POSKOD RUMAH'].values[0]} - Jarak {df_eligible_disp[df_eligible_disp['id']==x]['JARAK'].values[0]}" if not df_eligible_disp[df_eligible_disp['id']==x].empty else str(x),
                            key=f"multiselect_jawatan_v3_{pilih_jawatan_jana}_{pilihan_pusat_jawatan}"
                        )

                        col_lantik_j, col_export_j = st.columns([2,1])
                        with col_lantik_j:
                            if st.button(f"✅ Lantik {len(pilih_guru_jawatan)} {pilih_jawatan_jana} ke {pilihan_pusat_jawatan}", type="primary", use_container_width=True, key=f"btn_lantik_jawatan_v3_{pilih_jawatan_jana}_{pilihan_pusat_jawatan}", disabled=len(pilih_guru_jawatan)==0):
                                try:
                                    berjaya = 0
                                    for gid in pilih_guru_jawatan:
                                        supa.table("cadangan_sup").update({"kod_pusat": pilihan_pusat_jawatan, "status": "DILANTIK PPD"}).eq("id", gid).execute()
                                        berjaya+=1
                                    st.success(f"✅ {berjaya} {pilih_jawatan_jana} dilantik ke {pilihan_pusat_jawatan} (poskod terdekat)")
                                    st.balloons()
                                    st.rerun()
                                except Exception as e:
                                    st.error("Maaf, berlaku masalah semasa memproses. Sila cuba lagi.")
                        with col_export_j:
                            st.download_button(f"📥 Export {pilih_jawatan_jana}", to_excel(df_eligible_disp), file_name=f"{pilih_jawatan_jana.replace(' ','_')}_{pilihan_pusat_jawatan}.xlsx", use_container_width=True, key=f"exp_jawatan_v3_{pilih_jawatan_jana}")


        elif menu == "hasil" and fly_cur == "pk_bk":
            show_flash()
            _pp.render_pk_ikut_bk(kod_ppd, mod="hasil")

        elif menu == "hasil" and fly_cur == "jawatan_pusat":
            show_flash()
            _df_h = get_cadangan_df(kod_ppd=kod_ppd)
            _tugas_h, _ = bina_tugas(_df_h)
            _pp.render_ikut_pusat(kod_ppd, pd.DataFrame([baris_semakan(v) for v in _tugas_h.values()]), mod="hasil")

        elif menu == "semakan" and fly_cur == "pk":
            _pp.render_pk_ikut_bk(kod_ppd, mod="semak")

        elif menu == "sah":
            _pp.render_sah_lantik(kod_ppd, fly_cur)

        elif menu == "hasil":
            st.header(f"Hasil Janaan - PPD {kod_ppd}")
            _al.render_langkah_hasil(kod_ppd)   # peringkat 1: Setuju Hasil Janaan -> Semakan

            # ===== BUTANG BATAL JANAAN - RESET SEMUA JADI 0 =====
            col_batal1, col_batal2 = st.columns([3, 1])
            with col_batal1:
                st.caption(f"PPD {kod_ppd} - Jika ada pelanggaran max {MAXS} (contoh SAM NURUL IMAN 10 orang di BA021), batal dan jana semula")
            with col_batal2:
                if st.button("🗑️ Batal Janaan - Reset 0", type="primary", use_container_width=True, key="batal_janaan_all"):
                    st.session_state["confirm_batal"] = True

            if st.session_state.get("confirm_batal"):
                st.warning("⚠️ Anda pasti nak batal semua janaan? Semua penempatan akan jadi 0 dan perlu Jana Keseluruhan semula!")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("✅ YA, Batal Semua Janaan", type="primary", use_container_width=True, key="confirm_yes_batal"):
                        try:
                            # Clear DB - set kod_pusat = None untuk PPD ini
                            st.info("Membatalkan semua janaan...")
                            # Update semua cadangan PPD ini
                            _ids_reset = [int(float(str(x))) for x in _pp.tanpa_pk(get_cadangan_df(kod_ppd=kod_ppd))["id"].tolist() if str(x).strip() not in ("", "nan", "None")]
                            for _i in range(0, len(_ids_reset), 100):
                                supa.table("cadangan_sup").update({"kod_pusat": None, "status": "TERPILIH PPD"}).in_("id", _ids_reset[_i:_i + 100]).execute()
                            get_cadangan_df.clear()
                            # Clear session
                            if "jana_all_result" in st.session_state:
                                del st.session_state["jana_all_result"]
                            if "jana_pusat_result" in st.session_state:
                                del st.session_state["jana_pusat_result"]
                            if "jana_pusat_no" in st.session_state:
                                del st.session_state["jana_pusat_no"]
                            st.session_state["confirm_batal"] = False
                            st.success(f"✅ Berjaya batal semua janaan untuk PPD {kod_ppd}. Hasil janaan sekarang 0. Sila Jana Keseluruhan semula!")
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal batal: {e}")
                            st.session_state["confirm_batal"] = False
                with col_no:
                    if st.button("❌ Tidak", use_container_width=True, key="confirm_no_batal"):
                        st.session_state["confirm_batal"] = False
                        st.rerun()

            st.markdown("---")
            df_pusat_raw = get_pusat_df()
            df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)
            if df_pusat_raw.empty:
                st.warning("Tiada pusat_master")
                st.stop()
            pusat_list = []
            for _, r in df_pusat_raw.iterrows():
                d = r.get("data") if isinstance(r.get("data"), dict) else {}
                if isinstance(d, str):
                    try: d = json.loads(d)
                    except: d = {}
                no_pusat = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                if not no_pusat.startswith(kod_ppd.upper()): continue
                nama = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                # Kuota pusat: sama seperti Dashboard (kelas dari JUMLAH_KELAS, jika 0 dikira dari calon; perlu = kelas + 9)
                _q = kuota_pusat(r)
                _jc, _jk = _q["calon"], _q["kelas"]
                pusat_list.append({"NO_PUSAT": no_pusat, "NAMA_PUSAT": nama, "CALON": _jc, "KELAS": _jk, "PERLU": kira_petugas_dari_kelas(_jk) if _jk > 0 else 0})
            df_pusat_list = pd.DataFrame(pusat_list)
            if df_pusat_list.empty:
                st.warning(f"Tiada pusat untuk PPD {kod_ppd}")
                st.stop()
            show_flash()
            _bersih, _kunci, _ambil_pusat = _t_bersih, _t_kunci, _t_ambil_pusat
            tugas, pending_rows = bina_tugas(df_cad_all)

            # Build dropdown - only pusat ada hasil by default
            semua_pusat_db = df_pusat_list["NO_PUSAT"].tolist()
            pusat_ada_hasil = sorted(set([str(v.get("pusat","")).strip() for v in tugas.values() if v.get("pusat")]))
            def _nama_pusat(kod):
                try:
                    row = df_pusat_list[df_pusat_list["NO_PUSAT"]==kod]
                    if not row.empty:
                        return f"{kod} - {str(row.iloc[0]['NAMA_PUSAT'])[:40]}"
                    return kod
                except:
                    return kod
            tunjuk_semua = st.checkbox(f"Tunjuk semua pusat ({len(semua_pusat_db)} pusat) - ada hasil {len(pusat_ada_hasil)} pusat: {', '.join(pusat_ada_hasil[:10])}{'...' if len(pusat_ada_hasil)>10 else ''}", value=False, key="toggle_semua_pusat")
            if tunjuk_semua:
                pilihan_list = semua_pusat_db
            else:
                pilihan_list = pusat_ada_hasil if pusat_ada_hasil else semua_pusat_db
            def _format_pusat_hasil(x):
                base = _nama_pusat(x)
                if x in pusat_ada_hasil:
                    return f"✅ {base}"
                return f"❌ {base} (tiada)"
            if not pilihan_list:
                st.warning("Belum ada hasil janaan. Sila jana di menu Jana Keseluruhan.")
                st.stop()
            pilihan_pusat_hasil = st.selectbox("Pilih Pusat", pilihan_list, format_func=_format_pusat_hasil, key="pilih_pusat_hasil")

            hasil_pusat = []
            for v in tugas.values():
                if str(v.get("pusat","")).strip() == str(pilihan_pusat_hasil).strip():

                    hasil_pusat.append(v["row"].copy())
            df_hasil = pd.DataFrame(hasil_pusat)

            # Semakan pelanggaran max 3 untuk pusat yang dipilih
            if not df_hasil.empty:
                sekolah_count_check = {}
                for _, r in df_hasil.iterrows():
                    kod = str(r.get("KOD_SEKOLAH_ASAL") or r.get("kod_sekolah_asal") or "").upper().strip()
                    if kod:
                        sekolah_count_check[kod] = sekolah_count_check.get(kod, 0) + 1
                pelanggaran = [(k, v) for k, v in sekolah_count_check.items() if v > MAXS]
                if pelanggaran:
                    st.error(f"❌ PELANGGARAN MAX {MAXS} DI {pilihan_pusat_hasil}:")
                    for kod, cnt in pelanggaran:
                        st.error(f"   - {kod}: {cnt} orang (LANGGAR! Max {MAXS} sahaja) - Contoh: SAM NURUL IMAN 10 orang di BA021")
                    st.warning("⚠️ Sila klik Batal Janaan di atas dan Jana Keseluruhan semula untuk betulkan!")
                else:
                    st.success(f"✅ Semakan Max {MAXS} OK di {pilihan_pusat_hasil}: Tiada sekolah lebih {MAXS} orang")

            st.markdown("---")
            if df_hasil.empty:
                st.warning(f"Belum Ada Hasil Janaan Di Pusat Yang Dipilih: {pilihan_pusat_hasil}")
                st.info("Sila pergi ke Jana Keseluruhan untuk jana petugas.")
            else:
                pusat_nama_h = df_pusat_list[df_pusat_list["NO_PUSAT"] == pilihan_pusat_hasil]["NAMA_PUSAT"].values[0] if not df_pusat_list[df_pusat_list["NO_PUSAT"] == pilihan_pusat_hasil].empty else ""
                st.success(f"{pilihan_pusat_hasil} - {pusat_nama_h} | {len(df_hasil)} petugas: 1 Ketua, 1 Timbalan, {len(df_hasil)-2} Pengawas")
                jawatan_groups = {}
                for _, r in df_hasil.iterrows():
                    jaw = str(r.get("JAWATAN_CADANGAN") or r.get("jawatan_cadangan") or r.get("JAWATAN") or "Pengawas Peperiksaan").strip()
                    if jaw not in jawatan_groups:
                        jawatan_groups[jaw] = []
                    jawatan_groups[jaw].append(r)
                order = ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Pengawas Peperiksaan", "Juru Tulis", "Juru Baca", "Ketua Pengawas Hospital", "Pengawas Hospital", "Pengawas Pengiring", "Pengemas Bilik"]
                for jawatan in order:
                    if jawatan not in jawatan_groups: continue
                    guru_list = jawatan_groups[jawatan]
                    if "Ketua Pengawas" in jawatan and "Timbalan" not in jawatan:
                        label = "Ketua Pengawas - 1 orang"
                    elif "Timbalan" in jawatan:
                        label = "Timbalan Ketua Pengawas - 1 orang"
                    else:
                        label = f"Pengawas Peperiksaan - {len(guru_list)} orang"
                    st.subheader(label)
                    rows_j = []
                    for g in guru_list:
                        rows_j.append({"NAMA": g.get("NAMA_GURU", ""), "NO IC": g.get("IC_GURU", ""), "SEKOLAH ASAL": g.get("KOD_SEKOLAH_ASAL", ""), "NAMA SEKOLAH ASAL": str(g.get("NAMA_SEKOLAH_ASAL", ""))[:30], "JANTINA": g.get("JANTINA", "") or g.get("jantina", ""), "NO TELEFON": g.get("TELEFON_GURU", "") or g.get("telefon_guru", "")})
                    df_j = pd.DataFrame(rows_j)
                    st.dataframe(df_j, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("## 📊 Hasil Janaan Keseluruhan Untuk Setiap Sekolah")

            # [FLYOUT] st.tabs diganti sub menu flyout

            if fly_cur == "ringkasan":
                st.markdown("### 📋 Ringkasan Keseluruhan - Semua Pusat")
                st.caption("STATUS ikut kuota pusat: PERLU = kelas + 9. ✅ Cukup = jumlah sama dengan kuota | 🟡 Belum Cukup = kurang daripada kuota | 🔵 Lebih = melebihi kuota | ❌ Belum Ada = 0 petugas.")
                ringkas_all = []
                for _, pr in df_pusat_list.iterrows():
                    no_p = pr["NO_PUSAT"]
                    nama_p = pr["NAMA_PUSAT"]
                    guru_di_pusat = [v for v in tugas.values() if v["pusat"] == no_p]
                    kp = sum(1 for v in guru_di_pusat if "Ketua Pengawas" in str(v["row"].get("JAWATAN_CADANGAN") or v["row"].get("JAWATAN") or "") and "Timbalan" not in str(v["row"].get("JAWATAN_CADANGAN") or ""))
                    tkp = sum(1 for v in guru_di_pusat if "Timbalan" in str(v["row"].get("JAWATAN_CADANGAN") or v["row"].get("JAWATAN") or ""))
                    peng = len(guru_di_pusat) - kp - tkp
                    perlu_p = int(pr.get("PERLU", 0) or 0)
                    jum_p = len(guru_di_pusat)
                    baki_p = perlu_p - jum_p
                    if perlu_p <= 0:
                        status = "⚠️ Tiada kuota" if jum_p == 0 else "⚠️ Kuota belum ditetapkan"
                    elif jum_p == 0:
                        status = "❌ Belum Ada"
                    elif jum_p < perlu_p:
                        status = f"🟡 Belum Cukup (kurang {baki_p})"
                    elif jum_p == perlu_p:
                        status = "✅ Cukup"
                    else:
                        status = f"🔵 Lebih ({-baki_p})"
                    ringkas_all.append({"NO PUSAT": no_p, "NAMA PUSAT": str(nama_p)[:30], "KELAS": int(pr.get("KELAS", 0) or 0), "PERLU (K+9)": perlu_p, "JUMLAH": jum_p, "BAKI": baki_p, "KP": kp, "TKP": tkp, "PENGAWAS": peng, "STATUS": status})
                df_ringkas_all = pd.DataFrame(ringkas_all)
                if not df_ringkas_all.empty:
                    st.dataframe(df_ringkas_all, use_container_width=True, hide_index=True)
                    st.download_button("📥 Export Ringkasan Semua Pusat", to_excel(df_ringkas_all), file_name=f"ringkasan_semua_pusat_{kod_ppd}.xlsx", use_container_width=True)
                else:
                    st.info("Belum ada hasil janaan keseluruhan")

            if fly_cur == "sekolah":
                _hl = hasil_lookup(df_pusat_raw, kod_ppd)
                st.markdown("### 🏫 Hasil Janaan Mengikut Sekolah Asal")
                st.caption("Setiap sekolah - berapa guru ditempatkan dan ke pusat mana")
                sekolah_groups = {}
                for v in tugas.values():
                    r = v["row"]
                    kod_sek = str(r.get("KOD_SEKOLAH_ASAL") or r.get("kod_sekolah_asal") or "TIADA KOD").upper().strip()
                    nama_sek = str(r.get("NAMA_SEKOLAH_ASAL") or r.get("nama_sekolah_asal") or kod_sek)[:35]
                    key = f"{kod_sek} - {nama_sek}"
                    if key not in sekolah_groups:
                        sekolah_groups[key] = []
                    sekolah_groups[key].append({"row": r, "pusat": v["pusat"]})

                if not sekolah_groups:
                    st.info("Belum ada hasil janaan")
                else:
                    # Summary per sekolah
                    summary_sekolah = []
                    for key, guru_list in sorted(sekolah_groups.items()):
                        kod = key.split(" - ")[0]
                        pusat_list = list(set([g["pusat"] for g in guru_list]))
                        summary_sekolah.append({"KOD SEKOLAH": kod, "NAMA SEKOLAH": key.split(" - ", 1)[1] if " - " in key else key, "NO PUSAT ASAL": ", ".join(_hl["asal"].get(kod, [])) or "-", "BIL GURU": len(guru_list), "PUSAT DITEMPATKAN": ", ".join(sorted(pusat_list)), "NAMA PUSAT TUGAS": " | ".join(sorted({_hl["pusat"].get(_p, {}).get("nama", "") for _p in pusat_list} - {""}))})
                    df_sum_sek = pd.DataFrame(summary_sekolah)
                    st.dataframe(df_sum_sek, use_container_width=True, hide_index=True)
                    st.markdown("---")
                    st.markdown("#### 🔍 Detail Setiap Sekolah")
                    pilih_sekolah = st.selectbox("Pilih Sekolah Untuk Lihat Detail", sorted(sekolah_groups.keys()), key="pilih_sekolah_hasil")
                    if pilih_sekolah:
                        detail = sekolah_groups[pilih_sekolah]
                        st.markdown(f"**{pilih_sekolah} - {len(detail)} guru ditempatkan:**")
                        rows_detail = []
                        for g in detail:
                            r = g["row"]
                            rows_detail.append(hasil_row(r, g["pusat"], _hl))
                        df_detail = pd.DataFrame(rows_detail)
                        st.dataframe(df_detail, use_container_width=True, hide_index=True)
                        st.download_button(f"📥 Export {pilih_sekolah}", to_excel(df_detail), file_name=f"hasil_{pilih_sekolah.split(' - ')[0]}_{kod_ppd}.xlsx", use_container_width=True, key=f"export_{pilih_sekolah}")

            if fly_cur == "guru":
                _hl = hasil_lookup(df_pusat_raw, kod_ppd)
                st.markdown("### 👥 Semua Guru Ditempatkan - Keseluruhan")
                all_guru_rows = []
                for v in tugas.values():
                    r = v["row"]
                    all_guru_rows.append(hasil_row(r, v["pusat"], _hl))
                df_all_guru = pd.DataFrame(all_guru_rows)
                if df_all_guru.empty:
                    st.info("Belum ada guru ditempatkan")
                else:
                    st.dataframe(df_all_guru, use_container_width=True, hide_index=True)
                    st.download_button("📥 Export Semua Guru Ditempatkan", to_excel(df_all_guru), file_name=f"semua_guru_ditempatkan_{kod_ppd}.xlsx", use_container_width=True)

        elif menu == "manual":
            st.markdown(f'''
            <div style="background: linear-gradient(135deg, #0d47a1 0%, #0d47a1 100%); padding:20px; border-radius:12px; color:white; margin-bottom:20px;">
                <h2 style="margin:0; color:white;">📌 Penempatan Manual - PPD {kod_ppd}</h2>
                <p style="margin:5px 0 0 0; color:#e3f2fd;">Pilih pusat, klik kolum jawatan untuk pilih petugas secara manual - 1 Pusat = 1 KP + 1 TKP + Pengawas ikut keperluan</p>
            </div>
            ''', unsafe_allow_html=True)

            df_pusat_raw = get_pusat_df()
            df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)

            if df_pusat_raw.empty:
                st.warning("Tiada pusat_master")
                st.stop()
            if df_cad_all.empty:
                st.warning(f"Belum ada cadangan SUP untuk PPD {kod_ppd}")
                st.stop()

            # ✅ INFO: Berapa guru telah dilantik vs belum
            total_cad = len(df_cad_all)
            def is_belum_info(row):
                kp = str(row.get("kod_pusat") or row.get("KOD_PUSAT") or "").strip()
                return kp == "" or kp.lower() in ("none", "null", "nan", "nat")
            belum_info = df_cad_all[df_cad_all.apply(is_belum_info, axis=1)]
            sudah_info = total_cad - len(belum_info)
            if sudah_info > 0:
                st.info(f"📊 Status PPD {kod_ppd}: {total_cad} cadangan | {sudah_info} telah dilantik (tidak akan dipapar di sini) | {len(belum_info)} belum dilantik (akan dipapar)")
            else:
                st.info(f"📊 Status PPD {kod_ppd}: {total_cad} cadangan | Semua belum dilantik")

            # Parse pusat list
            pusat_list_m = []
            for _, r in df_pusat_raw.iterrows():
                d = r.get("data") if isinstance(r.get("data"), dict) else {}
                if isinstance(d, str):
                    try: d = json.loads(d)
                    except: d = {}
                no_pusat = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                if not no_pusat.startswith(kod_ppd.upper()): continue
                nama = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                _q = kuota_pusat(r)
                jc, jk = _q["calon"], _q["kelas"]
                petugas_perlu = _q["petugas"]
                kod_tuan = str(r.get("kod_sekolah_tuan_rumah") or d.get("KOD_SEKOLAH_TUAN_RUMAH") or "").upper().strip()
                pusat_list_m.append({"NO_PUSAT": no_pusat, "NAMA_PUSAT": nama, "CALON": jc, "KELAS": jk, "PERLU": petugas_perlu, "KOD_TUAN": kod_tuan})

            df_pusat_m = pd.DataFrame(pusat_list_m)
            if df_pusat_m.empty:
                st.warning(f"Tiada pusat untuk PPD {kod_ppd}")
                st.stop()

            # Pilih pusat
            st.markdown("### 📍 STEP 1: Pilih Pusat Daerah")
            col_pus1, col_pus2 = st.columns([2, 1])
            with col_pus1:
                pilih_pusat_manual = st.selectbox(
                    "Pilih Pusat",
                    df_pusat_m["NO_PUSAT"].tolist(),
                    format_func=lambda x: f"{x} - {df_pusat_m[df_pusat_m['NO_PUSAT']==x]['NAMA_PUSAT'].values[0][:30] if not df_pusat_m[df_pusat_m['NO_PUSAT']==x].empty else x}",
                    key="pilih_pusat_manual"
                )
            with col_pus2:
                info_pusat = df_pusat_m[df_pusat_m["NO_PUSAT"] == pilih_pusat_manual]
                if not info_pusat.empty:
                    perlu_m = int(info_pusat["PERLU"].values[0])
                    st.markdown(f'''
                    <div style="background:#e3f2fd; border:2px solid #1565c0; border-radius:8px; padding:10px; text-align:center;">
                        <div style="font-size:11px; color:#1565c0;">KEPERLUAN PUSAT</div>
                        <div style="font-size:20px; font-weight:800; color:#0d47a1;">{perlu_m} Petugas</div>
                        <div style="font-size:11px; color:#0d47a1;">1 KP + 1 TKP + {perlu_m-2} Pengawas</div>
                        <div style="font-size:10px; color:#1565c0; margin-top:4px;">{info_pusat['CALON'].values[0]} calon | {info_pusat['KELAS'].values[0]} kelas</div>
                    </div>
                    ''', unsafe_allow_html=True)

            st.markdown("---")

            # Load current placement for this pusat
            def _bersih_m(v):
                s = "" if v is None else str(v).strip()
                return "" if s.lower() in ("", "nan", "none", "null", "nat") else s.upper()

            def _kunci_m(r):
                i = _bersih_m(r.get("id"))
                return f"ID:{i}" if i else "IC:" + re.sub(r"\D", "", str(r.get("IC_GURU") or r.get("ic_guru") or ""))

            # Current tugas untuk pusat ini
            tugas_pusat_ini = {}
            if not df_cad_all.empty:
                for _, c in df_cad_all.iterrows():
                    p_db = _bersih_m(c.get("kod_pusat")) or _bersih_m(c.get("KOD_PUSAT"))
                    if p_db == pilih_pusat_manual:
                        tugas_pusat_ini[_kunci_m(c)] = c

            # Kira sekolah count untuk max 3 check
            sekolah_count_manual = {}
            for _, c in df_cad_all.iterrows():
                p_db = _bersih_m(c.get("kod_pusat")) or _bersih_m(c.get("KOD_PUSAT"))
                if p_db == pilih_pusat_manual:
                    kod = str(c.get("KOD_SEKOLAH_ASAL") or c.get("kod_sekolah_asal") or "").upper().strip()
                    if kod:
                        sekolah_count_manual[kod] = sekolah_count_manual.get(kod, 0) + 1

            # Paparan semasa
            st.markdown(f"### 🏫 Pusat {pilih_pusat_manual} - Penempatan Semasa")
            col_curr1, col_curr2, col_curr3, col_curr4, col_curr5, col_curr6 = st.columns(6)
            # FIX: 5 jawatan - Penyelia dari SUP, Selenggara dari PPD
            kp_curr_dict = {}
            tkp_curr_dict = {}
            penyelia_curr_dict = {}
            selenggara_curr_dict = {}
            peng_curr_dict = {}
            for k, c in tugas_pusat_ini.items():
                jaw = str(c.get("JAWATAN_CADANGAN") or c.get("jawatan_cadangan") or c.get("JAWATAN") or "").upper()
                if "KETUA PENGAWAS" in jaw and "TIMBALAN" not in jaw:
                    kp_curr_dict[k] = c
                elif "TIMBALAN" in jaw:
                    tkp_curr_dict[k] = c
                elif "PENYELIA KAWASAN" in jaw or ("PENYELIA" in jaw and "KAWASAN" in jaw):
                    penyelia_curr_dict[k] = c
                elif "SELENGGARA" in jaw or "BILIK KEBAL" in jaw:
                    selenggara_curr_dict[k] = c
                elif "JURU TULIS" in jaw or "JURU BACA" in jaw or "PENGEMAS" in jaw:
                    pass  # Pengawas Khas - dikira di panel jawatan masing-masing, bukan Pengawas biasa
                else:
                    peng_curr_dict[k] = c
            kp_curr = list(kp_curr_dict.values())
            tkp_curr = list(tkp_curr_dict.values())
            peng_curr = list(peng_curr_dict.values())

            with col_curr1:
                st.metric("Ketua Pengawas", f"{len(kp_curr)}/1", delta="OK" if len(kp_curr)==1 else "Perlu 1", delta_color="normal" if len(kp_curr)==1 else "inverse")
            with col_curr2:
                st.metric("Timbalan KP", f"{len(tkp_curr)}/1", delta="OK" if len(tkp_curr)==1 else "Perlu 1", delta_color="normal" if len(tkp_curr)==1 else "inverse")
            with col_curr3:
                st.metric("Penyelia Kawasan", f"{len(penyelia_curr_dict)}/1", delta="OK" if len(penyelia_curr_dict)>=1 else "Perlu 1", delta_color="normal" if len(penyelia_curr_dict)>=1 else "inverse")
            with col_curr4:
                st.metric("Selenggara BK", f"{len(selenggara_curr_dict)}/1", delta="OK" if len(selenggara_curr_dict)>=1 else "Perlu 1", delta_color="normal" if len(selenggara_curr_dict)>=1 else "inverse")
            with col_curr5:
                perlu_p = int(info_pusat["PERLU"].values[0]) if not info_pusat.empty else 0
                st.metric("Pengawas", f"{len(peng_curr)}/{max(perlu_p-4,0)}", delta=f"Perlu {max(perlu_p-4,0)}")
            with col_curr6:
                st.metric("Jumlah", f"{len(tugas_pusat_ini)}/{perlu_p}", delta="Cukup" if len(tugas_pusat_ini)>=perlu_p else f"Kurang {perlu_p-len(tugas_pusat_ini)}")

            # Check pelanggaran max 3
            pelanggaran_m = [(k, v) for k, v in sekolah_count_manual.items() if v > MAXS]
            if pelanggaran_m:
                st.error(f"❌ Pelanggaran Max {MAXS} di {pilih_pusat_manual}:")
                for kod, cnt in pelanggaran_m:
                    st.error(f"  - {kod}: {cnt} orang (Max {MAXS} sahaja!)")
            else:
                st.success(f"✅ Max {MAXS} OK di {pilih_pusat_manual} - Tiada sekolah lebih {MAXS} orang")

            st.markdown("---")

            # =====================================================================
            # STEP 2 (BARU): Klik kolum jawatan -> paparan besar -> senarai belum ditempatkan
            #   - Klik satu kolum jawatan (KP / TKP / Pengawas / JT / JB / PB) untuk buka panel besar
            #   - Semua calon BELUM ditempatkan dipapar (nama + sekolah asal) untuk dipilih
            #   - Pusat yang sudah ada pencalonan: PPD boleh BATAL seorang demi seorang & gantikan
            #   - Yang dibatalkan kembali ke ruang "belum dilantik" dan boleh dipilih untuk pusat lain
            #   - Butang "Selesai" menutup panel supaya PPD boleh pilih jawatan / pusat lain
            # =====================================================================
            import html as _html

            st.markdown("### 📌 STEP 2: Penempatan Manual - Klik Kolum Untuk Pilih")
            show_flash()

            # Tutup panel bila tukar pusat
            if st.session_state.get("_manual_pusat_prev") != pilih_pusat_manual:
                st.session_state["_manual_pusat_prev"] = pilih_pusat_manual
                st.session_state["manual_jaw"] = None
            st.session_state.setdefault("manual_ver", 0)
            _ver = st.session_state["manual_ver"]

            kod_tuan_m = info_pusat["KOD_TUAN"].values[0] if not info_pusat.empty else ""
            perlu_p = int(info_pusat["PERLU"].values[0]) if not info_pusat.empty else 10
            perlu_pengawas = max(0, perlu_p - 2)

            def _jenis_jaw(jaw):
                j = str(jaw or "").upper()
                if "JURU TULIS" in j: return "jt"
                if "JURU BACA" in j: return "jb"
                if "PENGEMAS" in j: return "pb"
                if "TIMBALAN" in j: return "tkp"
                if "KETUA PENGAWAS" in j: return "kp"
                if "PENYELIA" in j or "SELENGGARA" in j or "BILIK KEBAL" in j: return "lain"
                return "peng"

            def _belum_m(r):
                """Belum ditempatkan = tiada kod pusat & belum disahkan dengan no surat."""
                kp = _bersih_m(r.get("kod_pusat")) or _bersih_m(r.get("KOD_PUSAT"))
                if kp not in ("", "-"):
                    return False
                stt = str(r.get("status") or r.get("STATUS") or "").upper()
                ns = str(r.get("no_surat") or "").strip()
                if ("LULUS" in stt or "DILANTIK" in stt or "SURAT" in stt) and ns and ns.lower() not in ("none", "null", "nan"):
                    return False
                return True

            # Tetapan jawatan: kunci -> (ikon, nama, kuota (None = khas, tiada kuota tetap), 1 sahaja?)
            _JAW = {
                "kp":   ("👑", "Ketua Pengawas", 1, True),
                "tkp":  ("🎖️", "Timbalan KP", 1, True),
                "peng": ("👨‍🏫", "Pengawas", perlu_pengawas, False),
                "jt":   ("✍️", "Juru Tulis", None, False),
                "jb":   ("📖", "Juru Baca", None, False),
                "pb":   ("🧹", "Pengemas Bilik", None, False),
            }

            # Penempatan semasa di pusat ini ikut jawatan
            semasa_ikut = {k: [] for k in _JAW}
            for _c in tugas_pusat_ini.values():
                _jn = _jenis_jaw(_c.get("JAWATAN_CADANGAN"))
                if _jn in semasa_ikut:
                    semasa_ikut[_jn].append(_c)

            # Pool BELUM ditempatkan (seluruh daerah) - kemas kini serta-merta selepas batal/lantik
            _mask_belum = df_cad_all.apply(_belum_m, axis=1)
            df_belum_all = df_cad_all[_mask_belum].copy()
            df_belum_all["_JENIS"] = df_belum_all["JAWATAN_CADANGAN"].apply(_jenis_jaw)

            def _set_jaw(k):
                st.session_state["manual_jaw"] = k

            # ----- Baris kolum jawatan (klik untuk pilih) -----
            _cols_jaw = st.columns(6)
            for _col, (_k, (_ik, _nm, _kuota, _satu)) in zip(_cols_jaw, _JAW.items()):
                _n_sem = len(semasa_ikut[_k])
                _n_belum = int((df_belum_all["_JENIS"] == _k).sum())
                _teks_kuota = f"{_n_sem}/{_kuota}" if _kuota is not None else f"{_n_sem}"
                with _col:
                    st.button(
                        f"{_ik} {_nm} ({_teks_kuota})",
                        key=f"btn_jaw_{_k}",
                        type="primary" if st.session_state.get("manual_jaw") == _k else "secondary",
                        use_container_width=True,
                        on_click=_set_jaw, args=(_k,),
                    )
                    st.caption(f"{_n_belum} belum ditempatkan")

            jaw_pilih = st.session_state.get("manual_jaw")

            if jaw_pilih not in _JAW:
                st.info("👆 Klik salah satu kolum jawatan di atas untuk membuka paparan pemilihan. "
                        "Contoh: klik **Ketua Pengawas** untuk melihat semua KP yang belum ditempatkan.")
            else:
                _ik, _nm, _kuota, _satu = _JAW[jaw_pilih]
                _semasa = semasa_ikut[jaw_pilih]

                # ----- Tajuk panel besar + butang Selesai -----
                _h1, _h2 = st.columns([4, 1])
                with _h1:
                    _kuota_txt = f"Kuota pusat: {_kuota}" if _kuota is not None else "Jawatan khas (tiada kuota tetap)"
                    st.markdown(
                        f'<div style="background:linear-gradient(135deg,#0d47a1,#1976d2); color:white; border-radius:12px; padding:18px 22px;">'
                        f'<div style="font-size:30px; font-weight:800;">{_ik} {_nm.upper()}</div>'
                        f'<div style="font-size:15px; opacity:.9;">Pusat {_html.escape(str(pilih_pusat_manual))} &nbsp;|&nbsp; '
                        f'Semasa: {len(_semasa)} &nbsp;|&nbsp; {_kuota_txt}</div></div>',
                        unsafe_allow_html=True)
                with _h2:
                    st.write("")
                    st.button("✅ Selesai - Tutup", key="manual_tutup", type="primary", use_container_width=True,
                              on_click=_set_jaw, args=(None,))

                st.write("")

                # ----- A. SEMASA di pusat ini: batal seorang demi seorang -----
                st.markdown(f"#### 📍 A. Semasa di Pusat {pilih_pusat_manual} ({len(_semasa)})")
                if not _semasa:
                    st.warning(f"Belum ada {_nm} di pusat ini.")
                else:
                    st.caption("Jika pencalonan hasil jana tidak sesuai, tekan **❌ Batal** pada orang berkenaan. "
                               "Beliau kembali ke senarai *belum ditempatkan* dan boleh dipilih semula untuk pusat lain.")
                    for _c in _semasa:
                        _cid = _c.get("id")
                        _stt = str(_c.get("status") or _c.get("STATUS") or "")
                        _dihantar = "LULUS" in _stt.upper()
                        _r1, _r2 = st.columns([5, 1.3])
                        with _r1:
                            st.markdown(
                                f'<div style="background:#e3f2fd; border:2px solid #0d47a1; border-radius:10px; padding:12px 16px; margin:4px 0;">'
                                f'<div style="font-size:20px; font-weight:800; color:#0d47a1;">{_html.escape(str(_c.get("NAMA_GURU", "")))}</div>'
                                f'<div style="font-size:14px;">🏫 <b>{_html.escape(str(_c.get("KOD_SEKOLAH_ASAL", "")))}</b> - '
                                f'{_html.escape(str(_c.get("NAMA_SEKOLAH_ASAL", "")))}</div>'
                                f'<div style="font-size:12px; color:#455a64;">IC: {_html.escape(str(_c.get("IC_GURU", "")))} &nbsp;|&nbsp; Status: {_html.escape(_stt)}</div>'
                                f'</div>', unsafe_allow_html=True)
                        with _r2:
                            st.write("")
                            if _dihantar:
                                st.caption("🔒 Surat telah dihantar - tidak boleh dibatal di sini")
                            elif st.button("❌ Batal", key=f"batal_{jaw_pilih}_{_cid}_{_ver}", use_container_width=True):
                                try:
                                    supa.table("cadangan_sup").update({"kod_pusat": None, "status": "DICADANGKAN"}).eq("id", _core._id_py(_cid)).execute()
                                    flash("success", f"✅ {_c.get('NAMA_GURU', '')} dibatalkan daripada {pilih_pusat_manual} - kembali ke senarai belum ditempatkan.")
                                    st.session_state["manual_ver"] = _ver + 1
                                    st.rerun()
                                except Exception as e:
                                    st.error(str(e))

                st.markdown("---")

                # ----- B. SENARAI BELUM DITEMPATKAN (seluruh daerah) -----
                st.markdown(f"#### 📋 B. Senarai {_nm} Belum Ditempatkan - Pilih Untuk Pusat {pilih_pusat_manual}")

                pindah_on = st.checkbox(
                    "🔀 Papar juga guru yang sudah ditempatkan di pusat lain (untuk dipindahkan ke pusat ini)",
                    key=f"pindah_{pilih_pusat_manual}_{jaw_pilih}_{_ver}")

                df_pool = df_belum_all[df_belum_all["_JENIS"] == jaw_pilih].copy()
                df_pool["_PUSAT_LAMA"] = ""
                if pindah_on:
                    def _di_pusat_lain(r):
                        kp = _bersih_m(r.get("kod_pusat")) or _bersih_m(r.get("KOD_PUSAT"))
                        if kp in ("", "-") or kp == pilih_pusat_manual:
                            return False
                        # Surat sudah dihantar ke sekolah = dikunci
                        if "LULUS" in str(r.get("status") or "").upper():
                            return False
                        ns = str(r.get("no_surat") or "").strip()
                        return not (ns and ns.lower() not in ("none", "null", "nan"))
                    df_lain = df_cad_all[df_cad_all.apply(_di_pusat_lain, axis=1)].copy()
                    df_lain["_JENIS"] = df_lain["JAWATAN_CADANGAN"].apply(_jenis_jaw)
                    df_lain = df_lain[df_lain["_JENIS"] == jaw_pilih]
                    df_lain["_PUSAT_LAMA"] = df_lain.apply(
                        lambda r: _bersih_m(r.get("kod_pusat")) or _bersih_m(r.get("KOD_PUSAT")), axis=1)
                    df_pool = pd.concat([df_pool, df_lain], ignore_index=True)

                # Kiraan sekolah asal di pusat ini. Jika slot tunggal akan diganti, pengganti ambil tempat penghuni lama.
                _kira = dict(sekolah_count_manual)
                if _satu:
                    for _c in _semasa:
                        _ks = str(_c.get("KOD_SEKOLAH_ASAL") or "").upper().strip()
                        if _ks:
                            _kira[_ks] = max(_kira.get(_ks, 0) - 1, 0)

                def _sebab_m(r):
                    kod = str(r.get("KOD_SEKOLAH_ASAL") or "").upper().strip()
                    if kod_tuan_m and kod == kod_tuan_m:
                        return "Sekolah tuan rumah pusat ini"
                    if kod and _kira.get(kod, 0) >= MAXS:
                        return f"Sekolah asal sudah {MAXS} orang di pusat ini (had maksimum)"
                    return ""

                if df_pool.empty:
                    st.warning(f"Tiada {_nm} yang belum ditempatkan dalam PPD {kod_ppd}. "
                               f"Batalkan seseorang di bahagian A untuk melepaskannya ke senarai ini.")
                else:
                    df_pool["_SEBAB"] = df_pool.apply(_sebab_m, axis=1)

                    cari = st.text_input("🔍 Cari nama / kod sekolah / nama sekolah", key=f"cari_{jaw_pilih}_{_ver}").strip().upper()
                    if cari:
                        df_pool = df_pool[
                            df_pool["NAMA_GURU"].astype(str).str.upper().str.contains(cari, na=False, regex=False)
                            | df_pool["KOD_SEKOLAH_ASAL"].astype(str).str.upper().str.contains(cari, na=False, regex=False)
                            | df_pool["NAMA_SEKOLAH_ASAL"].astype(str).str.upper().str.contains(cari, na=False, regex=False)
                        ]
                    df_pool = df_pool.sort_values(["KOD_SEKOLAH_ASAL", "NAMA_GURU"])
                    df_layak_p = df_pool[df_pool["_SEBAB"] == ""].copy()
                    df_tak_p = df_pool[df_pool["_SEBAB"] != ""].copy()

                    st.caption(f"{len(df_layak_p)} boleh dipilih | {len(df_tak_p)} tidak layak untuk pusat ini | "
                               f"Had setiap sekolah asal: {MAXS} orang/pusat")

                    if df_layak_p.empty:
                        st.warning("Tiada calon yang boleh dipilih untuk pusat ini (lihat senarai tidak layak di bawah).")
                    else:
                        df_edit = pd.DataFrame({
                            "PILIH": False,
                            "NAMA GURU": df_layak_p["NAMA_GURU"].values,
                            "KOD SEKOLAH ASAL": df_layak_p["KOD_SEKOLAH_ASAL"].values,
                            "NAMA SEKOLAH ASAL": df_layak_p["NAMA_SEKOLAH_ASAL"].values,
                            "IC": df_layak_p["IC_GURU"].astype(str).values,
                            "PUSAT SEMASA": df_layak_p["_PUSAT_LAMA"].replace("", "- (belum)").values,
                            "_id": df_layak_p["id"].values,
                        })
                        edited = st.data_editor(
                            df_edit,
                            hide_index=True,
                            use_container_width=True,
                            height=min(520, 60 + 36 * len(df_edit)),
                            column_config={
                                "PILIH": st.column_config.CheckboxColumn("Pilih", help="Tandakan untuk memilih", width="small"),
                                "NAMA GURU": st.column_config.TextColumn("Nama Guru", disabled=True, width="large"),
                                "KOD SEKOLAH ASAL": st.column_config.TextColumn("Kod Sekolah Asal", disabled=True),
                                "NAMA SEKOLAH ASAL": st.column_config.TextColumn("Sekolah Asal", disabled=True, width="large"),
                                "IC": st.column_config.TextColumn("No. IC", disabled=True),
                                "PUSAT SEMASA": st.column_config.TextColumn("Pusat Semasa", disabled=True),
                                "_id": None,
                            },
                            key=f"editor_{pilih_pusat_manual}_{jaw_pilih}_{_ver}_{cari}_{int(bool(pindah_on))}",
                        )
                        dipilih = edited[edited["PILIH"] == True]
                        n_pilih = len(dipilih)

                        # Semakan sebelum lantik
                        sah = n_pilih > 0
                        if _satu and n_pilih > 1:
                            st.error(f"❌ {_nm} hanya 1 orang. Anda menanda {n_pilih} - sila tinggalkan 1 sahaja.")
                            sah = False
                        if not _satu and n_pilih > 0:
                            _temp = dict(sekolah_count_manual)
                            for _, _dr in dipilih.iterrows():
                                _ks = str(_dr["KOD SEKOLAH ASAL"]).upper().strip()
                                if _ks and _temp.get(_ks, 0) >= MAXS:
                                    st.error(f"❌ {_ks} sudah {MAXS} orang di {pilih_pusat_manual} - tidak boleh tambah lagi!")
                                    sah = False
                                _temp[_ks] = _temp.get(_ks, 0) + 1
                            if _kuota is not None:
                                _sisa = max(_kuota - len(_semasa), 0)
                                if n_pilih > _sisa:
                                    st.warning(f"⚠️ Anda pilih {n_pilih} tetapi baki keperluan pusat hanya {_sisa}.")

                        if _satu and _semasa:
                            _label = f"🔄 Gantikan {_nm} Semasa dengan Yang Dipilih"
                        else:
                            _label = f"✅ Lantik {n_pilih if n_pilih else ''} {_nm}".replace("  ", " ")
                        if st.button(_label, type="primary", use_container_width=True, key=f"lantik_{jaw_pilih}_{_ver}", disabled=not sah):
                            try:
                                if _satu:
                                    for _c in _semasa:
                                        if "LULUS" in str(_c.get("status") or "").upper():
                                            raise ValueError("Penghuni semasa sudah dihantar suratnya - tidak boleh diganti di sini.")
                                    for _c in _semasa:
                                        supa.table("cadangan_sup").update({"kod_pusat": None, "status": "DICADANGKAN"}).eq("id", _core._id_py(_c.get("id"))).execute()
                                for _, _dr in dipilih.iterrows():
                                    supa.table("cadangan_sup").update({"kod_pusat": pilih_pusat_manual, "status": "DILANTIK PPD"}).eq("id", _core._id_py(_dr["_id"])).execute()
                                _n_pindah = int((dipilih["PUSAT SEMASA"] != "- (belum)").sum())
                                _msg_p = f" ({_n_pindah} dipindahkan dari pusat lain)" if _n_pindah else ""
                                flash("success", f"✅ {n_pilih} {_nm} dilantik ke {pilih_pusat_manual}.{_msg_p}")
                                st.session_state["manual_ver"] = _ver + 1
                                st.rerun()
                            except ValueError as e:
                                st.error(str(e))
                            except Exception as e:
                                st.error(str(e))

                    if not df_tak_p.empty:
                        with st.expander(f"⛔ {len(df_tak_p)} calon tidak layak untuk pusat ini (klik untuk lihat sebab)"):
                            st.dataframe(
                                pd.DataFrame({
                                    "NAMA GURU": df_tak_p["NAMA_GURU"].values,
                                    "SEKOLAH ASAL": df_tak_p["KOD_SEKOLAH_ASAL"].values,
                                    "NAMA SEKOLAH ASAL": df_tak_p["NAMA_SEKOLAH_ASAL"].values,
                                    "SEBAB": df_tak_p["_SEBAB"].values,
                                }),
                                use_container_width=True, hide_index=True)

                st.write("")
                st.button("✅ Selesai - Tutup & Pilih Jawatan / Pusat Lain", key="manual_tutup_bawah",
                          use_container_width=True, on_click=_set_jaw, args=(None,))


            st.markdown("---")
            st.markdown("### 📊 Ringkasan Penempatan Manual - Kumulatif (Tidak Hilang Bila Pilih Sekolah Kedua)")
            st.info("💡 Ringkasan ini kumulatif - bila PPD lantik Sekolah Kedua, lantikan Pertama masih kekal di bawah. Column ikut jawatan: KP, TKP, Pengawas.")

            # ===== RINGKASAN KUMULATIF - SEMUA PUSAT YANG TELAH DILANTIK MANUAL =====
            try:
                # Ambil semua yang sudah ada kod_pusat dan status DILANTIK PPD untuk PPD ini
                res_all_lantik = supa.table("cadangan_sup").select("*").eq("kod_ppd", kod_ppd).not_.is_("kod_pusat", "null").limit(5000).execute()
                df_all_lantik = __import__("pandas").DataFrame(res_all_lantik.data or [])
                # Filter hanya yang status DILANTIK / LULUS
                if not df_all_lantik.empty:
                    df_all_lantik = df_all_lantik[df_all_lantik.apply(lambda r: str(r.get("status") or "").upper() not in ("", "DICADANGKAN", "HANTAR KE PPD"), axis=1)]
            except:
                df_all_lantik = __import__("pandas").DataFrame()

            # Tambah juga yang baru di session ini (kalau belum save DB pun, tunjuk)
            # Gabungkan
            if not df_all_lantik.empty:
                # Build rows dengan column ikut jawatan
                all_rows_kum = []
                for _, c in df_all_lantik.iterrows():
                    jaw = str(c.get("jawatan_cadangan") or c.get("JAWATAN_CADANGAN") or "")
                    # Tentukan column jawatan
                    if "Ketua Pengawas" in jaw and "Timbalan" not in jaw:
                        jaw_col = "KETUA PENGAWAS"
                    elif "Timbalan" in jaw:
                        jaw_col = "TIMBALAN KP"
                    elif "Pengawas" in jaw:
                        jaw_col = "PENGAWAS PEPERIKSAAN"
                    elif "Penyelia" in jaw:
                        jaw_col = "PENYELIA KAWASAN"
                    else:
                        jaw_col = jaw.upper()

                    all_rows_kum.append({
                        "BIL": len(all_rows_kum)+1,
                        "NAMA GURU": c.get("nama_guru","") or c.get("NAMA_GURU",""),
                        "IC": c.get("ic_guru","") or c.get("IC_GURU",""),
                        "JAWATAN": jaw,
                        "KOLUM JAWATAN": jaw_col,
                        "SEKOLAH ASAL": c.get("kod_sekolah_asal","") or c.get("KOD_SEKOLAH_ASAL",""),
                        "NAMA SEKOLAH ASAL": str(c.get("nama_sekolah_asal","") or c.get("NAMA_SEKOLAH_ASAL",""))[:25],
                        "PUSAT TUGAS": c.get("kod_pusat","") or c.get("KOD_PUSAT",""),
                        "STATUS": c.get("status","")
                    })

                df_summary_kum = __import__("pandas").DataFrame(all_rows_kum)

                if df_summary_kum.empty:
                    st.info("Belum ada penempatan manual - Sila lantik di atas")
                else:
                    # Papar ikut tab jawatan
                    tab_kp, tab_tkp, tab_peng, tab_semua = st.tabs(["👑 Ketua Pengawas", "🎖️ Timbalan KP", "👨‍🏫 Pengawas", "📋 Semua (Kumulatif)"])

                    with tab_kp:
                        df_kp = df_summary_kum[df_summary_kum["KOLUM JAWATAN"]=="KETUA PENGAWAS"].copy()
                        st.markdown(f"**{len(df_kp)} Ketua Pengawas telah dilantik (kumulatif, tidak hilang bila pilih sekolah kedua):**")
                        if df_kp.empty:
                            st.info("Belum ada Ketua Pengawas dilantik")
                        else:
                            st.dataframe(df_kp[["BIL","NAMA GURU","IC","SEKOLAH ASAL","NAMA SEKOLAH ASAL","PUSAT TUGAS"]], use_container_width=True, hide_index=True)

                    with tab_tkp:
                        df_tkp = df_summary_kum[df_summary_kum["KOLUM JAWATAN"]=="TIMBALAN KP"].copy()
                        st.markdown(f"**{len(df_tkp)} Timbalan KP telah dilantik (kumulatif):**")
                        if df_tkp.empty:
                            st.info("Belum ada Timbalan KP")
                        else:
                            st.dataframe(df_tkp[["BIL","NAMA GURU","IC","SEKOLAH ASAL","NAMA SEKOLAH ASAL","PUSAT TUGAS"]], use_container_width=True, hide_index=True)

                    with tab_peng:
                        df_peng = df_summary_kum[df_summary_kum["KOLUM JAWATAN"]=="PENGAWAS PEPERIKSAAN"].copy()
                        st.markdown(f"**{len(df_peng)} Pengawas telah dilantik (kumulatif):**")
                        if df_peng.empty:
                            st.info("Belum ada Pengawas")
                        else:
                            st.dataframe(df_peng[["BIL","NAMA GURU","IC","SEKOLAH ASAL","NAMA SEKOLAH ASAL","PUSAT TUGAS"]], use_container_width=True, hide_index=True)

                    with tab_semua:
                        st.markdown(f"**📋 Ringkasan Kumulatif Keseluruhan: {len(df_summary_kum)} guru telah dilantik manual - Lantikan pertama kekal bila tambah lantikan kedua:**")
                        st.dataframe(df_summary_kum, use_container_width=True, hide_index=True)
                        # Export kumulatif
                        try:
                            import io
                            output = io.BytesIO()
                            with __import__("pandas").ExcelWriter(output, engine='openpyxl') as writer:
                                df_summary_kum.to_excel(writer, index=False, sheet_name='Kumulatif Semua')
                                if not df_kp.empty:
                                    df_kp.to_excel(writer, index=False, sheet_name='Ketua Pengawas')
                                if not df_tkp.empty:
                                    df_tkp.to_excel(writer, index=False, sheet_name='Timbalan KP')
                                if not df_peng.empty:
                                    df_peng.to_excel(writer, index=False, sheet_name='Pengawas')
                            st.download_button("📥 Export Excel Kumulatif (4 Sheet Ikut Jawatan)", data=output.getvalue(), file_name=f"ringkasan_manual_kumulatif_{kod_ppd}_{__import__('datetime').date.today()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="export_kum_manual_excel")
                        except Exception as e:
                            st.caption(f"Export error: {e}")
                            st.download_button("📥 Export CSV Kumulatif", df_summary_kum.to_csv(index=False).encode('utf-8'), file_name=f"ringkasan_manual_kumulatif_{kod_ppd}.csv", mime="text/csv", use_container_width=True, key="export_kum_csv")

                    # Info tambahan: papar lantikan untuk pusat semasa juga (supaya nampak konteks)
                    st.markdown("---")
                    st.markdown(f"#### 📍 Lantikan Untuk Pusat Semasa: {pilih_pusat_manual}")
                    if tugas_pusat_ini:
                        all_rows_curr = []
                        for c in tugas_pusat_ini.values():
                            all_rows_curr.append({"NAMA": c.get("NAMA_GURU", ""), "IC": c.get("IC_GURU", ""), "JAWATAN": c.get("JAWATAN_CADANGAN", ""), "SEKOLAH ASAL": c.get("KOD_SEKOLAH_ASAL", ""), "PUSAT": pilih_pusat_manual})
                        df_curr_sum = __import__("pandas").DataFrame(all_rows_curr)
                        st.dataframe(df_curr_sum, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"Belum ada penempatan di {pilih_pusat_manual} - ini paparan pusat semasa sahaja, ringkasan kumulatif di atas kekal")
            else:
                st.info(f"Belum ada penempatan manual di PPD {kod_ppd} - Sila lantik KP, TKP, Pengawas di atas. Ringkasan kumulatif akan muncul di sini dan tidak hilang bila pilih sekolah kedua.")

        elif menu == "zon":
            render_penempatan_zon(kod_ppd, fly_cur)

        elif menu == "cadangan" and fly_cur == "nama":
            render_senarai_nama(kod_ppd)

        elif menu == "cadangan" and fly_cur == "simpanan":
            render_senarai_simpanan(kod_ppd)

        elif menu == "cadangan":
            st.markdown(f'''
            <div style="background: linear-gradient(135deg, #1565c0 0%, #1e88e5 100%); padding:20px; border-radius:12px; color:white; margin-bottom:20px;">
                <h2 style="margin:0; color:white;">📋 Cadangan SUP - PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')}</h2>
                <p style="margin:5px 0 0 0; color:#bbdefb;">Pilih sekolah dalam daerah untuk lihat senarai cadangan dari sekolah berkenaan</p>
            </div>
            ''', unsafe_allow_html=True)

            df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)
            if df_cad_all.empty:
                st.warning(f"Belum ada cadangan SUP untuk PPD {kod_ppd}")
                st.stop()

            # ===== FILTER IKUT JAWATAN (MESTI AWAL) + CLEAN NAN =====
            # Clean NAN rows from df_cad_all - remove rows where KOD_SEKOLAH_ASAL is NAN/nan/None/empty
            def is_valid_sekolah(row):
                kod = str(row.get("KOD_SEKOLAH_ASAL") or row.get("kod_sekolah_asal") or row.get("KOD_SEKOLAH") or row.get("kod_sekolah") or "").strip()
                if kod.lower() in ("", "nan", "none", "null", "nat", "-"):
                    return False
                return True

            # Filter out NAN sekolah for display, but keep count for info
            df_cad_all = _pp.tanpa_pk(df_cad_all)          # PK dipaparkan di Lantik Penyelia Kawasan > Cadangan SUP sahaja
            if df_cad_all.empty:
                st.info("Tiada cadangan petugas (cadangan Penyelia Kawasan ada di menu Lantik Penyelia Kawasan).")
                st.stop()
            df_cad_valid = df_cad_all[df_cad_all.apply(is_valid_sekolah, axis=1)].copy()
            df_cad_invalid = df_cad_all[~df_cad_all.apply(is_valid_sekolah, axis=1)].copy()
            if not df_cad_invalid.empty:
                st.warning(f"⚠️ Ada {len(df_cad_invalid)} cadangan dengan KOD SEKOLAH kosong/NAN - akan disembunyikan dari senarai sekolah. Sila betulkan di SUP.")

            jawatan_list_all = []
            for _, r in df_cad_valid.iterrows():
                j = str(r.get("JAWATAN_CADANGAN") or r.get("jawatan_cadangan") or r.get("JAWATAN") or "").strip()
                if j and j.lower() not in ("", "nan", "none") and j not in jawatan_list_all:
                    jawatan_list_all.append(j)
            order_jawatan = ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Penyelia Kawasan", "Pengawas Peperiksaan", "Selenggara Bilik Kebal", "Juru Tulis", "Juru Baca", "Ketua Pengawas Hospital", "Pengawas Hospital", "Pengawas Pengiring", "Pengemas Bilik"]
            jawatan_sorted = sorted(jawatan_list_all, key=lambda x: (order_jawatan.index(x) if x in order_jawatan else 99, x))

            # Default filter from session
            filter_jawatan = st.session_state.get("filter_jawatan_cad", [])
            if filter_jawatan is None:
                filter_jawatan = []

            # Init df_cad_filtered as valid first
            df_cad_filtered = df_cad_valid.copy()
            if filter_jawatan:
                df_cad_filtered = df_cad_valid[df_cad_valid.apply(lambda r: str(r.get("JAWATAN_CADANGAN") or r.get("jawatan_cadangan") or r.get("JAWATAN") or "").strip() in filter_jawatan, axis=1)].copy()

            # Get sekolah list in PPD
            try:
                res_sek = supa.table("sekolah_master").select("*").eq("kod_ppd", kod_ppd).limit(2000).execute()
                df_sek_list = pd.DataFrame(res_sek.data or [])
            except:
                df_sek_list = pd.DataFrame()

            # Build sekolah groups dari cadangan (ikut filter) - SKIP NAN + STRICT PPD CHECK
            # Safety: get sekolah list for this PPD again to ensure no cross-PPD leak
            kod_list_ppd_check = []
            try:
                res_sek_check = supa.table("sekolah_master").select("kod_sekolah").eq("kod_ppd", kod_ppd.upper()).limit(2000).execute()
                kod_list_ppd_check = [str(s.get('kod_sekolah','')).upper().strip() for s in (res_sek_check.data or [])]
            except:
                kod_list_ppd_check = []

            sekolah_groups = {}
            for _, r in df_cad_filtered.iterrows():
                # Extra strict check: if sekolah code not in PPD list and KOD_PPD != requested PPD, skip
                kppd_row = str(r.get("KOD_PPD") or "").upper().strip()
                ksek_row = str(r.get("KOD_SEKOLAH_ASAL") or "").upper().strip()
                if kod_list_ppd_check:
                    if ksek_row not in kod_list_ppd_check and kppd_row != kod_ppd.upper():
                        continue
                else:
                    # If no list, check KOD_PPD exact
                    if kppd_row and kppd_row != kod_ppd.upper():
                        continue
                kod_sek_raw = r.get("KOD_SEKOLAH_ASAL") or r.get("kod_sekolah_asal") or r.get("KOD_SEKOLAH") or r.get("kod_sekolah") or ""
                kod_sek = str(kod_sek_raw).strip().upper()
                if kod_sek.lower() in ("", "nan", "none", "null", "nat", "-", "tiada kod"):
                    continue
                nama_sek_raw = r.get("NAMA_SEKOLAH_ASAL") or r.get("nama_sekolah_asal") or r.get("NAMA_SEKOLAH") or kod_sek
                nama_sek = str(nama_sek_raw).strip()
                if nama_sek.lower() in ("", "nan", "none", "null"):
                    nama_sek = kod_sek
                nama_sek = nama_sek[:50]
                key = f"{kod_sek} - {nama_sek}"
                if key not in sekolah_groups:
                    sekolah_groups[key] = []
                sekolah_groups[key].append(r)

            # Summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🏫 Sekolah Mencadang", len(sekolah_groups))
            with col2:
                st.metric("👥 Jumlah Cadangan", len(df_cad_all))
            with col3:
                # Belum vs sudah lantik
                def is_belum(row):
                    kp = str(row.get("kod_pusat") or row.get("KOD_PUSAT") or "").strip()
                    return kp == "" or kp.lower() in ("none", "null", "nan", "nat")
                belum = df_cad_all[df_cad_all.apply(is_belum, axis=1)]
                st.metric("✅ Belum Dilantik", len(belum), delta=f"{len(df_cad_all)-len(belum)} telah dilantik")

            st.markdown("### 🔍 Filter Ikut Jawatan")
            st.caption("Filter untuk tengok siapa Penyelia Kawasan, Ketua Pengawas, Timbalan, Pengawas Peperiksaan - senang PPD semak")

            # V20: SIMPLE - no widget key manipulation at all, use direct variable
            if "filter_jawatan_cad" not in st.session_state:
                st.session_state["filter_jawatan_cad"] = []

            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            with col_f1:
                # V21 FIX DefaultNotInOptionsError: pastikan default ada dalam options
                # Jika Penyelia Kawasan tidak ada dalam jawatan_sorted (data kosong), tambah manual
                safe_default = [x for x in st.session_state["filter_jawatan_cad"] if x in jawatan_sorted]
                # Jika user pilih Penyelia Kawasan tapi jawatan_sorted kosong, tetap tunjuk semua option yang mungkin
                if not jawatan_sorted:
                    jawatan_sorted = ["Ketua Pengawas", "Timbalan Ketua Pengawas", "Penyelia Kawasan", "Pengawas Peperiksaan", "Juru Tulis", "Juru Baca", "Ketua Pengawas Hospital", "Pengawas Hospital", "Pengawas Pengiring", "Pengemas Bilik"]
                    safe_default = st.session_state["filter_jawatan_cad"]
                # Jika safe_default kosong tapi session ada value yang bukan dalam options, guna empty supaya tak error
                # Tapi untuk kes Penyelia Kawasan, kita benarkan jika memang dalam senarai tetap
                if st.session_state["filter_jawatan_cad"] and not safe_default:
                    # Kalau filter ada tapi takde dalam options, jangan error - guna filter tu sebagai options tambahan
                    for v in st.session_state["filter_jawatan_cad"]:
                        if v not in jawatan_sorted:
                            jawatan_sorted.append(v)
                    safe_default = st.session_state["filter_jawatan_cad"]

                filter_jawatan_ui = st.multiselect("Filter Jawatan", jawatan_sorted, default=safe_default, placeholder="Pilih jawatan - kosong = semua")
            with col_f2:
                if filter_jawatan_ui:
                    st.metric(f"Filter: {len(filter_jawatan_ui)} jawatan", f"{len(df_cad_valid[df_cad_valid.apply(lambda r: str(r.get('JAWATAN_CADANGAN') or r.get('jawatan_cadangan') or r.get('JAWATAN') or '').strip() in filter_jawatan_ui, axis=1)]) if filter_jawatan_ui else len(df_cad_all)} guru")
                else:
                    st.metric("Semua Jawatan", f"{len(df_cad_all)} guru")
            with col_f3:
                if st.button("🔐 Hanya Penyelia Kawasan", use_container_width=True, key="btn_filter_pk"):
                    st.session_state["filter_jawatan_cad"] = ["Penyelia Kawasan"]
                    st.rerun()
            with col_f4:
                if st.button("🔄 Clear Filter", use_container_width=True, key="btn_clear_filter"):
                    st.session_state["filter_jawatan_cad"] = []
                    st.rerun()

            # V22 ROBUST: filter using normalized lowercase contains
            def match_jawatan(row_jawatan, filter_list):
                if not filter_list:
                    return True
                rj = str(row_jawatan).strip().lower()
                rj = ' '.join(rj.split())
                for f in filter_list:
                    f_low = str(f).strip().lower()
                    f_low = ' '.join(f_low.split())
                    # Exact or contains
                    if f_low == rj or f_low in rj or rj in f_low:
                        return True
                    # Special for Penyelia Kawasan - check both words
                    if 'penyelia' in f_low and 'penyelia' in rj:
                        return True
                return False

            # Determine active filter list
            active_filter = filter_jawatan_ui if filter_jawatan_ui else st.session_state.get("filter_jawatan_cad", [])

            if active_filter:
                df_cad_filtered = df_cad_valid[df_cad_valid['JAWATAN_CADANGAN'].apply(lambda x: match_jawatan(x, active_filter))].copy()
                # Save for next run default
                if active_filter != st.session_state["filter_jawatan_cad"]:
                    st.session_state["filter_jawatan_cad"] = active_filter
                filter_jawatan_ui = active_filter
            else:
                df_cad_filtered = df_cad_valid.copy()

            if active_filter and len(df_cad_filtered) == 0:
                st.info("Tiada guru yang sepadan dengan penapis jawatan yang dipilih.")

            if st.session_state.get("filter_jawatan_cad"):
                st.success(f"✅ Filter aktif: {', '.join(st.session_state.get('filter_jawatan_cad', []))} - Jumpa {len(df_cad_filtered)} guru")

            # Show breakdown by jawatan
            st.markdown("#### 📊 Pecahan Ikut Jawatan")
            jawatan_counts = {}
            for _, r in df_cad_filtered.iterrows():
                j = str(r.get("JAWATAN_CADANGAN") or r.get("jawatan_cadangan") or "TIADA").strip()
                jawatan_counts[j] = jawatan_counts.get(j, 0) + 1

            if jawatan_counts:
                cols_j = st.columns(len(jawatan_counts))
                for idx, (j, cnt) in enumerate(sorted(jawatan_counts.items(), key=lambda x: (order_jawatan.index(x[0]) if x[0] in order_jawatan else 99, x[0]))):
                    with cols_j[idx % len(cols_j)]:
                        icon = "👑" if "Ketua Pengawas" in j and "Timbalan" not in j else "🎖️" if "Timbalan" in j else "🔐" if "Penyelia" in j else "👨‍🏫" if "Pengawas" in j else "🔧"
                        st.metric(f"{icon} {j}", cnt)

            st.markdown("---")

            # Ringkasan ikut sekolah
            st.markdown("### 📋 Ringkasan Cadangan Mengikut Sekolah (Ikut Filter Jawatan)")
            summary_rows = []
            for key, guru_list in sorted(sekolah_groups.items()):
                kod = key.split(" - ")[0]
                nama = key.split(" - ", 1)[1] if " - " in key else key
                # Kira belum vs sudah
                def _is_sudah_lantik(g):
                    kp = str(g.get("kod_pusat") or g.get("KOD_PUSAT") or g.get("kod_pusat_tugas") or "").strip()
                    status = str(g.get("status") or g.get("STATUS") or "").upper().strip()
                    if kp == "" or kp.lower() in ("none","null","nan","nat",""):
                        return False
                    # Jika kod_pusat == no_pusat_asal dan status HANTAR KE PPD, itu BUKAN sudah lantik (bug lama)
                    no_asal = str(g.get("no_pusat_asal") or g.get("NO_PUSAT_ASAL") or "").upper().strip()
                    if kp.upper() == no_asal and "HANTAR KE PPD" in status:
                        return False
                    # Sudah lantik jika ada kod_pusat dan status LULUS/DILANTIK/SURAT
                    if any(x in status for x in ["LULUS","DILANTIK","DITEMPATKAN","SURAT","SAH"]):
                        return True
                    # Jika kod_pusat ada tapi status masih HANTAR/DICADANGKAN, masih belum lantik
                    if "HANTAR KE PPD" in status or "DICADANGKAN" in status:
                        return False
                    # Default: kalau ada kod_pusat dan bukan HANTAR/DICADANGKAN, anggap sudah
                    return kp != ""
                belum_cnt = sum(1 for g in guru_list if not _is_sudah_lantik(g))
                sudah_cnt = len(guru_list) - belum_cnt
                summary_rows.append({
                    "KOD SEKOLAH": kod,
                    "NAMA SEKOLAH": nama[:35],
                    "JUMLAH CADANGAN": len(guru_list),
                    "BELUM LANTIK": belum_cnt,
                    "SUDAH LANTIK": sudah_cnt,
                    "status": "✅ Lengkap" if belum_cnt == 0 else f"⏳ {belum_cnt} belum"
                })
            df_summary = pd.DataFrame(summary_rows)
            st.dataframe(df_summary, use_container_width=True, hide_index=True)
            st.download_button("📥 Export Ringkasan Cadangan Ikut Sekolah", to_excel(df_summary), file_name=f"ringkasan_cadangan_{kod_ppd}.xlsx", use_container_width=True)

            st.markdown("---")
            st.markdown("### 🔍 Detail Cadangan Ikut Sekolah - Pilih Sekolah (Ikut Filter Jawatan)")
            if filter_jawatan:
                st.info(f"📋 Menunjukkan guru dengan jawatan: {', '.join(filter_jawatan)} sahaja. Clear filter untuk lihat semua.")

            # Pilih sekolah dropdown
            pilih_sek_cad = st.selectbox(
                "Pilih Sekolah Dalam Daerah Untuk Lihat Senarai Cadangan",
                sorted(sekolah_groups.keys()),
                format_func=lambda x: f"{x} ({len(sekolah_groups[x])} cadangan)",
                key="pilih_sekolah_cadangan"
            )

            if pilih_sek_cad:
                guru_list = sekolah_groups[pilih_sek_cad]
                st.markdown(f"#### 🏫 {pilih_sek_cad} - {len(guru_list)} cadangan")

                # Filter tabs: Semua, Belum Lantik, Sudah Lantik
                tab_all, tab_belum, tab_sudah = st.tabs(["📋 Semua", "⏳ Belum Dilantik", "✅ Sudah Dilantik"])

                def make_df_from_list(g_list):
                    rows = []
                    for g in g_list:
                        rows.append({
                            "NAMA GURU": g.get("NAMA_GURU", "") or g.get("nama_guru", ""),
                            "NO IC": g.get("IC_GURU", "") or g.get("ic_guru", ""),
                            "JAWATAN": g.get("JAWATAN_CADANGAN", "") or g.get("jawatan_cadangan", ""),
                            "JANTINA": g.get("JANTINA", "") or g.get("jantina", ""),
                            "TELEFON": g.get("TELEFON_GURU", "") or g.get("telefon_guru", ""),
                            "KOD PUSAT": g.get("kod_pusat", "") or g.get("KOD_PUSAT", "") or "- Belum -",
                            "STATUS": g.get("status", "") or g.get("STATUS", ""),
                            "SEKOLAH": g.get("KOD_SEKOLAH_ASAL", "") or g.get("kod_sekolah_asal", "")
                        })
                    return pd.DataFrame(rows)

                with tab_all:
                    # Additional filter inside school view by jawatan
                    if filter_jawatan:
                        guru_list_filtered_j = [g for g in guru_list if str(g.get("JAWATAN_CADANGAN") or g.get("jawatan_cadangan") or "").strip() in filter_jawatan]
                    else:
                        guru_list_filtered_j = guru_list

                    df_all_guru = make_df_from_list(guru_list_filtered_j)
                    if filter_jawatan:
                        st.caption(f"Filter aktif: {', '.join(filter_jawatan)} - {len(guru_list_filtered_j)} guru dalam sekolah ini")
                    st.dataframe(df_all_guru, use_container_width=True, hide_index=True)
                    st.download_button(f"📥 Export {pilih_sek_cad.split(' - ')[0]} - Semua", to_excel(df_all_guru), file_name=f"cadangan_{pilih_sek_cad.split(' - ')[0]}_semua.xlsx", use_container_width=True, key="exp_all")

                    # Show jawatan breakdown for this school
                    if guru_list_filtered_j:
                        j_count_school = {}
                        for g in guru_list_filtered_j:
                            jj = str(g.get("JAWATAN_CADANGAN") or g.get("jawatan_cadangan") or "TIADA").strip()
                            j_count_school[jj] = j_count_school.get(jj, 0) + 1
                        cols_js = st.columns(len(j_count_school))
                        for idx, (jj, cnt) in enumerate(j_count_school.items()):
                            with cols_js[idx]:
                                st.metric(jj, cnt)

                with tab_belum:
                    def _check_sudah(g):
                        kp = str(g.get("kod_pusat") or g.get("KOD_PUSAT") or "").strip()
                        stt = str(g.get("status") or g.get("STATUS") or "").upper()
                        no_asal = str(g.get("no_pusat_asal") or g.get("NO_PUSAT_ASAL") or "").upper().strip()
                        if kp == "" or kp.lower() in ("none","null","nan","nat",""):
                            return False
                        if kp.upper() == no_asal and "HANTAR KE PPD" in stt:
                            return False
                        if "HANTAR KE PPD" in stt or "DICADANGKAN" in stt:
                            return False
                        if any(x in stt for x in ["LULUS","DILANTIK","DITEMPATKAN","SURAT"]):
                            return True
                        return kp != ""
                    belum_list = [g for g in guru_list if not _check_sudah(g)]
                    st.markdown(f"**{len(belum_list)} guru belum dilantik dari {pilih_sek_cad}**")
                    if belum_list:
                        df_belum_guru = make_df_from_list(belum_list)
                        st.dataframe(df_belum_guru, use_container_width=True, hide_index=True)
                        st.download_button(f"📥 Export Belum Lantik", to_excel(df_belum_guru), file_name=f"cadangan_{pilih_sek_cad.split(' - ')[0]}_belum.xlsx", use_container_width=True, key="exp_belum")
                    else:
                        st.success("✅ Semua guru dari sekolah ini telah dilantik!")

                with tab_sudah:
                    sudah_list = [g for g in guru_list if _check_sudah(g)]
                    st.markdown(f"**{len(sudah_list)} guru sudah dilantik dari {pilih_sek_cad}**")
                    if sudah_list:
                        df_sudah_guru = make_df_from_list(sudah_list)
                        st.dataframe(df_sudah_guru, use_container_width=True, hide_index=True)
                        st.download_button(f"📥 Export Sudah Lantik", to_excel(df_sudah_guru), file_name=f"cadangan_{pilih_sek_cad.split(' - ')[0]}_sudah.xlsx", use_container_width=True, key="exp_sudah")
                    else:
                        st.info("Belum ada guru dilantik dari sekolah ini")


        elif menu == "semakan":
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #0d47a1 0%, #0d47a1 100%); padding:20px; border-radius:12px; color:white; margin-bottom:20px;">
                <h2 style="margin:0; color:white;">🔍 Semakan Lantikan Ikut Pusat - PPD {kod_ppd}</h2>
                <p style="margin:5px 0 0 0; color:#e3f2fd;">Pilih pusat, akan keluar 4 table ikut jawatan: Penyelia Kawasan, Ketua Pengawas, Timbalan, Pengawas. PPD boleh batalkan lantikan & guru masuk semula ke cadangan untuk pilih pusat lain. Boleh isi kekosongan dengan guru lain.</p>
            </div>
            """, unsafe_allow_html=True)

            df_pusat_raw = get_pusat_df()
            try:  # bacaan terus (segar) supaya sentiasa sepadan selepas batal/isi
                df_cad_all = pd.DataFrame(supa.table("cadangan_sup").select("*").eq("kod_ppd", kod_ppd).limit(5000).execute().data or [])
            except Exception:
                df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)
            tugas_semak, _pending_semak = bina_tugas(df_cad_all)
            # ===== ALIRAN: Semakan hanya untuk petugas yang telah DISETUJUI di Hasil Janaan =====
            _al_raw, _al_rows = _al.muat(kod_ppd)
            _al.bar(_al_rows, 1)
            if not _al.gate(_al_rows, 1, "Semakan Lantikan", "Hasil Janaan (Setuju & Hantar ke Semakan)"):
                st.stop()
            _al_ok = {_al.idk(r["id"]) for r in _al_rows if r["rank"] >= 1}
            tugas_semak = {k: v for k, v in tugas_semak.items() if _al.idk(v["row"].get("id", "")) in _al_ok}
            _al.render_langkah_semakan(kod_ppd, _al_rows)   # peringkat 2: Setuju Semakan -> Kelulusan

            if df_pusat_raw.empty:
                st.warning("Tiada pusat_master")
                st.stop()
            if df_cad_all.empty and not tugas_semak:
                st.warning("Belum ada cadangan")
                st.stop()

            # Parse pusat list
            pusat_list = []
            for _, r in df_pusat_raw.iterrows():
                d = r.get("data") if isinstance(r.get("data"), dict) else {}
                if isinstance(d, str):
                    try: d = json.loads(d)
                    except: d = {}
                no_pusat = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                if not no_pusat.startswith(kod_ppd.upper()): continue
                nama = r.get("nama_pusat") or d.get("NAMA_PUSAT") or ""
                pusat_list.append({"NO_PUSAT": no_pusat, "NAMA_PUSAT": nama})
            df_pusat_list = __import__("pandas").DataFrame(pusat_list)

            if df_pusat_list.empty:
                st.warning(f"Tiada pusat untuk PPD {kod_ppd}")
                st.stop()

            # Pilih pusat
            pilihan_pusat_semak = st.selectbox(
                "📍 Pilih Pusat Untuk Semakan Lantikan",
                df_pusat_list["NO_PUSAT"].tolist(),
                format_func=lambda x: f"{x} - {df_pusat_list[df_pusat_list['NO_PUSAT']==x]['NAMA_PUSAT'].values[0][:35] if not df_pusat_list[df_pusat_list['NO_PUSAT']==x].empty else x}",
                key="pilih_pusat_semakan"
            )

            st.markdown(f"### 🔍 Semakan Lantikan - Pusat {pilihan_pusat_semak}")

            # Get lantikan for this pusat
            # SAMA seperti Hasil Janaan: semua guru yang pusatnya = pusat dipilih (DB + janaan belum simpan)
            _rec_pusat = [v for v in tugas_semak.values() if str(v.get("pusat", "")).strip() == str(pilihan_pusat_semak).strip()]
            df_lantik_pusat = pd.DataFrame([baris_semakan(v) for v in _rec_pusat])
            _n_pending = sum(1 for v in _rec_pusat if v.get("pending"))
            if _n_pending:
                st.warning(f"⚠️ {_n_pending} petugas hasil janaan di pusat ini BELUM DISIMPAN ke pangkalan data. "
                           "Simpan janaan di menu Jana Keseluruhan supaya lantikan kekal.")

            if fly_cur == "semak":
                if df_lantik_pusat.empty:
                    st.warning(f"Belum ada lantikan di pusat {pilihan_pusat_semak}")
                    # Still allow to add guru
                    df_lantik_pusat = __import__("pandas").DataFrame()
                else:
                    st.success(f"Ada {len(df_lantik_pusat)} lantikan di {pilihan_pusat_semak}")

                # Helper to get jawatan groups
                def get_jawatan_group(df, keyword, exclude_keywords=[]):
                    if df.empty:
                        return __import__("pandas").DataFrame()
                    def match(row):
                        jaw = str(row.get("jawatan_cadangan") or row.get("JAWATAN_CADANGAN") or "").upper()
                        if keyword.upper() not in jaw:
                            return False
                        for ex in exclude_keywords:
                            if ex.upper() in jaw:
                                # Special handling for Ketua vs Timbalan
                                if keyword.upper()=="KETUA PENGAWAS" and "TIMBALAN" in jaw:
                                    return False
                                if keyword.upper()=="PENYELIA" and ex.upper() not in jaw:
                                    continue
                        # For Ketua Pengawas, exclude Timbalan
                        if keyword.upper()=="KETUA PENGAWAS" and "TIMBALAN" in jaw:
                            return False
                        # For Pengawas Peperiksaan, exclude Ketua, Timbalan, Penyelia
                        if keyword.upper()=="PENGAWAS" and any(k in jaw for k in ["KETUA","TIMBALAN","PENYELIA","SELENGGARA"]):
                            return False
                        return True
                    return df[df.apply(match, axis=1)].copy()

                # Split into 4 groups
                # Penyelia Kawasan
                df_penyelia = df_lantik_pusat[df_lantik_pusat.apply(lambda r: "PENYELIA" in str(r.get("jawatan_cadangan") or "").upper(), axis=1)].copy() if not df_lantik_pusat.empty else __import__("pandas").DataFrame()
                # Ketua Pengawas
                df_kp = df_lantik_pusat[df_lantik_pusat.apply(lambda r: "KETUA PENGAWAS" in str(r.get("jawatan_cadangan") or "").upper() and "TIMBALAN" not in str(r.get("jawatan_cadangan") or "").upper(), axis=1)].copy() if not df_lantik_pusat.empty else __import__("pandas").DataFrame()
                # Timbalan
                df_tkp = df_lantik_pusat[df_lantik_pusat.apply(lambda r: "TIMBALAN" in str(r.get("jawatan_cadangan") or "").upper(), axis=1)].copy() if not df_lantik_pusat.empty else __import__("pandas").DataFrame()
                # Pengawas
                df_peng = df_lantik_pusat[df_lantik_pusat.apply(lambda r: "PENGAWAS" in str(r.get("jawatan_cadangan") or "").upper() and "KETUA" not in str(r.get("jawatan_cadangan") or "").upper() and "TIMBALAN" not in str(r.get("jawatan_cadangan") or "").upper() and "PENYELIA" not in str(r.get("jawatan_cadangan") or "").upper(), axis=1)].copy() if not df_lantik_pusat.empty else __import__("pandas").DataFrame()

                # Function to display table with batal action
                def display_jawatan_table(df_jawatan, tajuk, icon, color, jawatan_name):
                    st.markdown(f"""
                <div style="background: {color}; padding:12px; border-radius:8px; color:white; margin:15px 0 10px 0;">
                    <h3 style="margin:0; color:white;">{icon} {tajuk} - {len(df_jawatan)} orang di {pilihan_pusat_semak}</h3>
                </div>
                """, unsafe_allow_html=True)

                    if df_jawatan.empty:
                        st.info(f"Belum ada {tajuk} di pusat ini")
                        return

                    # Build display rows
                    rows = []
                    for _, r in df_jawatan.iterrows():
                        rows.append({
                            "id": r.get("id",""),
                            "NAMA GURU": r.get("nama_guru","") or r.get("NAMA_GURU",""),
                            "IC": r.get("ic_guru","") or r.get("IC_GURU",""),
                            "JAWATAN": r.get("jawatan_cadangan","") or r.get("JAWATAN_CADANGAN",""),
                            "SEKOLAH ASAL": r.get("kod_sekolah_asal","") or r.get("KOD_SEKOLAH_ASAL",""),
                            "NAMA SEKOLAH ASAL": str(r.get("nama_sekolah_asal","") or r.get("NAMA_SEKOLAH_ASAL","")),
                            "POSKOD RUMAH": r.get("poskod_rumah","") or r.get("POSKOD_RUMAH",""),
                            "TELEFON": r.get("telefon_guru","") or r.get("TELEFON_GURU",""),
                            "STATUS": r.get("status","") or r.get("STATUS","")
                        })
                    df_disp = __import__("pandas").DataFrame(rows)
                    st.dataframe(df_disp, use_container_width=True, hide_index=True)

                    # Batalkan lantikan section
                    with st.expander(f"❌ Batalkan Lantikan {tajuk} di {pilihan_pusat_semak}", expanded=False):
                        st.warning(f"Jika PPD rasa guru ini tidak sesuai di {pilihan_pusat_semak}, boleh batalkan. Guru akan masuk semula ke bahagian cadangan SUP untuk dipilih di pusat lain.")
                        batal_ids = st.multiselect(
                            f"Pilih {tajuk} untuk batalkan lantikan di {pilihan_pusat_semak}",
                            df_disp["id"].tolist(),
                            format_func=lambda x: f"{df_disp[df_disp['id']==x]['NAMA GURU'].values[0]} - {df_disp[df_disp['id']==x]['SEKOLAH ASAL'].values[0]} - {df_disp[df_disp['id']==x]['IC'].values[0]}" if not df_disp[df_disp['id']==x].empty else str(x),
                            key=f"batal_{jawatan_name}_{pilihan_pusat_semak}"
                        )
                        if batal_ids:
                            st.error(f"Anda akan batalkan {len(batal_ids)} {tajuk} dari {pilihan_pusat_semak}. Guru akan kembali ke cadangan SUP (kod_pusat = NULL, status = HANTAR KE PPD).")
                            if st.button(f"❌ Confirm Batalkan {len(batal_ids)} {tajuk} dari {pilihan_pusat_semak}", type="primary", use_container_width=True, key=f"btn_batal_{jawatan_name}_{pilihan_pusat_semak}"):
                                try:
                                    berjaya = 0
                                    for gid in batal_ids:
                                        if str(gid).startswith("PENDING:"):
                                            continue  # belum disimpan - guna Batal Janaan
                                        # Batalkan: set kod_pusat None, status HANTAR KE PPD supaya masuk semula ke cadangan
                                        supa.table("cadangan_sup").update({"kod_pusat": None, "status": "HANTAR KE PPD", "status": "HANTAR KE PPD"}).eq("id", gid).execute()
                                        berjaya+=1
                                    st.cache_data.clear()
                                    if berjaya < len(batal_ids):
                                        st.warning("Sebahagian guru belum disimpan ke DB - gunakan Hasil Janaan > Batal Janaan untuk janaan yang belum disimpan.")
                                    st.success(f"✅ Berjaya batalkan {berjaya} {tajuk} dari {pilihan_pusat_semak}. Guru masuk semula ke cadangan SUP untuk dipilih di pusat lain.")
                                    st.balloons()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Gagal batal: {e}")

                # Display 4 tables
                st.caption("🔐 Penyelia Kawasan disemak mengikut bilik kebal di sub menu **Semakan PK (Bilik Kebal)**.")
                display_jawatan_table(df_kp, "Ketua Pengawas", "👑", "linear-gradient(135deg, #0d47a1 0%, #0d47a1 100%)", "kp")
                display_jawatan_table(df_tkp, "Timbalan Ketua Pengawas", "🎖️", "linear-gradient(135deg, #0d47a1 0%, #0d47a1 100%)", "tkp")
                display_jawatan_table(df_peng, "Pengawas Peperiksaan", "👨‍🏫", "linear-gradient(135deg, #0d47a1 0%, #0d47a1 100%)", "pengawas")

            if fly_cur == "kosong":
                st.markdown("---")
                st.markdown(f"### ➕ Isi Kekosongan di {pilihan_pusat_semak} - Pilih Guru Lain")
                st.info(f"Selepas batalkan lantikan di atas, PPD boleh pilih guru lain dari cadangan SUP untuk isi kekosongan di {pilihan_pusat_semak}. Guru yang dibatalkan tadi sudah masuk semula ke pool cadangan.")

                # Get guru yang belum dilantik (pool untuk isi kekosongan)
                try:
                    df_belum_pool = df_cad_all[df_cad_all.apply(lambda r: str(r.get("kod_pusat") or r.get("KOD_PUSAT") or "").strip() in ("", "None", "none", "null", "nan", "nat"), axis=1)].copy()
                except:
                    df_belum_pool = __import__("pandas").DataFrame()

                if df_belum_pool.empty:
                    st.warning("Tiada guru dalam pool cadangan yang belum dilantik - semua sudah dilantik. Batalkan dulu lantikan di atas untuk kembalikan guru ke pool.")
                else:
                    st.markdown(f"**{len(df_belum_pool)} guru dalam pool belum dilantik - boleh pilih untuk isi kekosongan di {pilihan_pusat_semak}:**")

                    # Filter by jawatan for easier selection
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        filter_jawatan_semak = st.selectbox(
                            "Filter Ikut Jawatan Untuk Isi Kekosongan",
                            ["Semua Jawatan", "Ketua Pengawas", "Timbalan Ketua Pengawas", "Pengawas Peperiksaan", "Penyelia Kawasan", "Juru Tulis", "Juru Baca", "Ketua Pengawas Hospital", "Pengawas Hospital", "Pengawas Pengiring", "Pengemas Bilik"],
                            key=f"filter_jawatan_semak_{pilihan_pusat_semak}"
                        )
                    with col_f2:
                        # Info pusat tuan rumah for max3 check
                        info_pusat_semak = df_pusat_list[df_pusat_list["NO_PUSAT"]==pilihan_pusat_semak]
                        # Get current count per sekolah in this pusat
                        sekolah_count_semak = {}
                        if not df_lantik_pusat.empty:
                            for _, r in df_lantik_pusat.iterrows():
                                ks = str(r.get("kod_sekolah_asal") or "").upper().strip()
                                sekolah_count_semak[ks] = sekolah_count_semak.get(ks, 0) + 1
                        st.caption(f"Pusat {pilihan_pusat_semak} sudah ada {len(df_lantik_pusat)} petugas. Max {MAXS} per sekolah. Count: {sekolah_count_semak}")

                    df_pool_filtered = df_belum_pool.copy()
                    if filter_jawatan_semak != "Semua Jawatan":
                        def match_filter(r, target):
                            jaw = str(r.get("JAWATAN_CADANGAN") or r.get("jawatan_cadangan") or "").upper()
                            tgt = target.upper()
                            if "KETUA PENGAWAS" in tgt and "TIMBALAN" not in tgt:
                                return "KETUA PENGAWAS" in jaw and "TIMBALAN" not in jaw
                            elif "TIMBALAN" in tgt:
                                return "TIMBALAN" in jaw
                            elif "PENGAWAS PEPERIKSAAN" in tgt:
                                return "PENGAWAS PEPERIKSAAN" in jaw or jaw.strip()=="PENGAWAS"
                            elif "PENYELIA" in tgt:
                                return "PENYELIA" in jaw
                            else:
                                return tgt in jaw
                        df_pool_filtered = df_pool_filtered[df_pool_filtered.apply(lambda r: match_filter(r, filter_jawatan_semak), axis=1)].copy()

                    # Filter out sekolah tuan rumah and max3
                    # Get kod tuan rumah
                    kod_tuan_semak = ""
                    try:
                        df_pusat_raw_all = get_pusat_df()
                        for _, pr in df_pusat_raw_all.iterrows():
                            d = pr.get("data") if isinstance(pr.get("data"), dict) else {}
                            if isinstance(d, str):
                                try: d = json.loads(d)
                                except: d = {}
                            no_p = str(pr.get("no_pusat") or pr.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
                            if no_p == pilihan_pusat_semak:
                                kod_tuan_semak = str(pr.get("kod_sekolah_tuan_rumah") or pr.get("kod_sekolah") or d.get("KOD_SEKOLAH") or "").upper().strip()
                                break
                    except:
                        kod_tuan_semak = ""

                    df_pool_layak = df_pool_filtered.copy()
                    if kod_tuan_semak:
                        df_pool_layak = df_pool_layak[~df_pool_layak.apply(lambda r: str(r.get("KOD_SEKOLAH_ASAL") or r.get("kod_sekolah_asal") or "").upper().strip() == kod_tuan_semak, axis=1)]

                    # Check max3
                    def check_max3_semak(row):
                        kod = str(row.get("KOD_SEKOLAH_ASAL") or row.get("kod_sekolah_asal") or "").upper().strip()
                        return sekolah_count_semak.get(kod, 0) < MAXS if kod else True
                    df_pool_layak = df_pool_layak[df_pool_layak.apply(check_max3_semak, axis=1)].copy()

                    st.markdown(f"**{len(df_pool_layak)} calon layak untuk isi kekosongan di {pilihan_pusat_semak} (selepas filter {filter_jawatan_semak}, elak sekolah sendiri & max3):**")

                    if df_pool_layak.empty:
                        st.warning("Tiada calon layak untuk pusat ini")
                    else:
                        display_pool = []
                        for _, r in df_pool_layak.iterrows():
                            display_pool.append({
                                "id": r.get("id",""),
                                "NAMA GURU": r.get("NAMA_GURU","") or r.get("nama_guru",""),
                                "IC": r.get("IC_GURU","") or r.get("ic_guru",""),
                                "JAWATAN": r.get("JAWATAN_CADANGAN","") or r.get("jawatan_cadangan",""),
                                "SEKOLAH ASAL": r.get("KOD_SEKOLAH_ASAL","") or r.get("kod_sekolah_asal",""),
                                "NAMA SEKOLAH ASAL": str(r.get("NAMA_SEKOLAH_ASAL","") or r.get("nama_sekolah_asal",""))[:35],
                                "POSKOD": r.get("POSKOD_RUMAH","") or r.get("poskod_rumah",""),
                                "STATUS": r.get("STATUS","") or r.get("status","")
                            })
                        df_pool_disp = __import__("pandas").DataFrame(display_pool)
                        st.dataframe(df_pool_disp, use_container_width=True, hide_index=True)

                        pilih_guru_isi = st.multiselect(
                            f"Pilih guru untuk isi kekosongan di {pilihan_pusat_semak}",
                            df_pool_disp["id"].tolist(),
                            format_func=lambda x: f"{df_pool_disp[df_pool_disp['id']==x]['NAMA GURU'].values[0]} - {df_pool_disp[df_pool_disp['id']==x]['SEKOLAH ASAL'].values[0]} - {df_pool_disp[df_pool_disp['id']==x]['JAWATAN'].values[0]}" if not df_pool_disp[df_pool_disp['id']==x].empty else str(x),
                            key=f"pilih_guru_isi_{pilihan_pusat_semak}"
                        )

                        if pilih_guru_isi:
                            if st.button(f"✅ Lantik {len(pilih_guru_isi)} Guru Terpilih ke {pilihan_pusat_semak} Untuk Isi Kekosongan", type="primary", use_container_width=True, key=f"btn_lantik_isi_{pilihan_pusat_semak}"):
                                try:
                                    berjaya = 0
                                    for gid in pilih_guru_isi:
                                        supa.table("cadangan_sup").update({"kod_pusat": pilihan_pusat_semak, "status": _al.ST_HASIL}).eq("id", gid).execute()
                                        berjaya+=1
                                    st.success(f"✅ Berjaya lantik {berjaya} guru untuk isi kekosongan di {pilihan_pusat_semak}")
                                    st.balloons()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Gagal lantik: {e}")




        elif menu == "kelulusan":
            _al.render_kelulusan(kod_ppd, fly_cur)

        elif menu == "selenggara":
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #0d47a1 0%, #1565c0 100%); padding:20px; border-radius:12px; color:white; margin-bottom:20px; border:2px solid #002171;">
                <h2 style="margin:0; color:white;">🔐 Selenggara Bilik Kebal - PPD {kod_ppd} - {PPD_MAP.get(kod_ppd,'')}</h2>
                <p style="margin:5px 0 0 0; color:#bbdefb;">Tapak Bilik Kebal Master - PPD isi data bilik kebal ikut daerah. Penyelia Kawasan akan ditempatkan ke bilik kebal ini. SUP tidak nampak menu ini.</p>
            </div>
            """, unsafe_allow_html=True)

            def get_bilik_kebal_df(kod_ppd_filter=None):
                try:
                    q = supa.table("bilik_kebal_master").select("*").limit(10000)
                    if kod_ppd_filter:
                        q = q.eq("kod_ppd", kod_ppd_filter)
                    res = q.execute()
                    return pd.DataFrame(res.data or [])
                except Exception as e:
                    st.error(f"Error load bilik_kebal_master: {e}")
                    return pd.DataFrame()

            df_bk = get_bilik_kebal_df(kod_ppd)

            c1,c2,c3 = st.columns(3)
            c1.metric("Bilik Kebal di PPD", len(df_bk))
            c2.metric("Daerah", PPD_MAP.get(kod_ppd,''))
            try:
                res_cad = supa.table("cadangan_sup").select("*", count="exact").eq("kod_ppd", kod_ppd.lower()).limit(1).execute()
                total_guru_ppd = res_cad.count if hasattr(res_cad,'count') else 0
            except:
                total_guru_ppd = 0
            c3.metric("Guru PPD", total_guru_ppd)

            # [FLYOUT] st.tabs diganti sub menu flyout

            if fly_cur == "form":
                st.markdown("### Borang Daftar Bilik Kebal Baru")
                st.caption("PPD isi form ini, data terus masuk Supabase table bilik_kebal_master")
                with st.form("form_bilik_kebal"):
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        kod_bk = st.text_input("KOD_BILIK_KEBAL *", placeholder="Contoh: BK-BA001 atau BA-BK01")
                        nama_bk = st.text_input("NAMA_BILIK_KEBAL *", placeholder="Contoh: Bilik Kebal PPD Klang")
                        kod_ppd_form = st.text_input("KOD_PPD", value=kod_ppd, disabled=True)
                    with col_f2:
                        alamat_bk = st.text_area("ALAMAT *", placeholder="Alamat penuh bilik kebal", height=100)
                        catatan = st.text_area("Catatan / DATA JSON (optional)", placeholder='Contoh: {"kapasiti": 50}', height=100)
                    submit_bk = st.form_submit_button("Simpan Bilik Kebal ke Supabase", type="primary", use_container_width=True)
                    if submit_bk:
                        if not kod_bk or not nama_bk or not alamat_bk:
                            st.error("Sila isi KOD, NAMA dan ALAMAT wajib!")
                        else:
                            try:
                                data_json = {}
                                if catatan:
                                    try:
                                        data_json = json.loads(catatan)
                                    except:
                                        data_json = {"catatan": catatan}
                                existing = supa.table("bilik_kebal_master").select("*").eq("kod_bilik_kebal", kod_bk.upper().strip()).limit(1).execute()
                                if existing.data:
                                    st.error(f"KOD {kod_bk} sudah wujud!")
                                else:
                                    payload = {
                                        "kod_bilik_kebal": kod_bk.upper().strip(),
                                        "nama_bilik_kebal": nama_bk.upper().strip(),
                                        "alamat": alamat_bk.strip(),
                                        "kod_ppd": kod_ppd.upper().strip(),
                                        "data": data_json
                                    }
                                    supa.table("bilik_kebal_master").insert(payload).execute()
                                    st.success(f"Berjaya simpan {kod_bk} - {nama_bk}")
                                    st.balloons()
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error simpan: {e}")

            if fly_cur == "senarai":
                st.markdown(f"### Senarai Bilik Kebal PPD {kod_ppd}")
                if df_bk.empty:
                    st.info("Belum ada bilik kebal didaftarkan untuk PPD ini.")
                else:
                    cari_bk = st.text_input("Cari bilik kebal (kod / nama / alamat)", key="cari_bk")
                    if cari_bk:
                        mask = df_bk.apply(lambda r: cari_bk.lower() in str(r.get("kod_bilik_kebal","")).lower() or cari_bk.lower() in str(r.get("nama_bilik_kebal","")).lower() or cari_bk.lower() in str(r.get("alamat","")).lower(), axis=1)
                        df_show = df_bk[mask]
                    else:
                        df_show = df_bk
                    st.dataframe(df_show, use_container_width=True, hide_index=True)
                    col_exp1, col_exp2 = st.columns(2)
                    with col_exp1:
                        st.download_button("Download Senarai Bilik Kebal (Excel)", to_excel(df_show), file_name=f"bilik_kebal_{kod_ppd}_{datetime.date.today()}.xlsx", use_container_width=True)
                    with col_exp2:
                        if st.button("Refresh", use_container_width=True):
                            st.rerun()
                    st.markdown("---")
                    st.markdown("### Buang Bilik Kebal")
                    if not df_show.empty:
                        pilih_buang = st.selectbox("Pilih Bilik Kebal untuk buang", df_show["kod_bilik_kebal"].tolist() if "kod_bilik_kebal" in df_show.columns else [], key="buang_bk")
                        if st.button(f"Buang {pilih_buang}", type="secondary", use_container_width=True):
                            try:
                                supa.table("bilik_kebal_master").delete().eq("kod_bilik_kebal", pilih_buang).execute()
                                st.success(f"Berjaya buang {pilih_buang}")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

            if fly_cur == "import":
                st.markdown("### Import Pukal Bilik Kebal dari Excel")
                st.info("Format Excel mesti ada column: KOD_BILIK_KEBAL, NAMA_BILIK_KEBAL, ALAMAT, KOD_PPD")
                df_template = pd.DataFrame([
                    {"KOD_BILIK_KEBAL": f"BK-{kod_ppd}01", "NAMA_BILIK_KEBAL": f"BILIK KEBAL PPD {PPD_MAP.get(kod_ppd,'')} 1", "ALAMAT": "SMK CONTOH 1, KLANG", "KOD_PPD": kod_ppd},
                    {"KOD_BILIK_KEBAL": f"BK-{kod_ppd}02", "NAMA_BILIK_KEBAL": f"BILIK KEBAL PPD {PPD_MAP.get(kod_ppd,'')} 2", "ALAMAT": "SMK CONTOH 2, KLANG", "KOD_PPD": kod_ppd},
                ])
                st.download_button("Download Template Excel Bilik Kebal", to_excel(df_template), file_name=f"template_bilik_kebal_{kod_ppd}.xlsx", use_container_width=True)
                st.markdown("---")
                up_bk = st.file_uploader("Upload Excel Bilik Kebal", type=["xlsx","xls"], key="up_bk_excel")
                if up_bk:
                    try:
                        df_up = pd.read_excel(up_bk, sheet_name=0)
                        st.write(f"Ada {len(df_up)} baris.")
                        st.dataframe(df_up.head(10), use_container_width=True)
                        if st.button(f"Import {len(df_up)} Bilik Kebal ke Supabase", type="primary", use_container_width=True):
                            bar = st.progress(0)
                            ok = 0
                            err = 0
                            for idx, row in df_up.iterrows():
                                try:
                                    kod = str(row.get("KOD_BILIK_KEBAL") or row.get("kod_bilik_kebal") or "").upper().strip()
                                    nama = str(row.get("NAMA_BILIK_KEBAL") or row.get("nama_bilik_kebal") or "").upper().strip()
                                    alamat = str(row.get("ALAMAT") or row.get("alamat") or "").strip()
                                    kppd = str(row.get("KOD_PPD") or row.get("kod_ppd") or kod_ppd).upper().strip()
                                    if not kod or not nama:
                                        err += 1
                                        continue
                                    dup = supa.table("bilik_kebal_master").select("*").eq("kod_bilik_kebal", kod).limit(1).execute()
                                    if dup.data:
                                        err += 1
                                        continue
                                    supa.table("bilik_kebal_master").insert({"kod_bilik_kebal": kod, "nama_bilik_kebal": nama, "alamat": alamat, "kod_ppd": kppd, "data": {}}).execute()
                                    ok += 1
                                except:
                                    err += 1
                                bar.progress((idx+1)/len(df_up))
                            st.success(f"Selesai: {ok} berjaya, {err} gagal/duplicate")
                            st.balloons()
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error baca Excel: {e}")


        elif menu == "penyelia":
            _pp.render_penyelia(kod_ppd, fly_cur)

        elif menu == "amali":
            _amali.render_menu(kod_ppd, fly_cur)

        elif menu == "um":
            _um.render_menu(kod_ppd, fly_cur)

        elif menu == "jana_surat":
            surat_panel("PPD", kod_ppd=kod_ppd)
            _al.render_jana_surat(kod_ppd, fly_cur)

        elif menu == "batal":
            st.header(f"🗑️ Batal - PPD {kod_ppd} - Batal Semua Penempatan / Cadangan")
            st.warning("⚠️ Tindakan ini hanya untuk PPD anda sahaja. Daerah lain tidak terjejas kerana sistem guna scoped_db.")
            
            from ppd_cadangan import batal_semua_penempatan_ppd, batal_semua_cadangan_ppd
            
            tab1, tab2, tab3 = st.tabs(["1️⃣ Batal Semua Penempatan", "2️⃣ Batal Semua Cadangan", "3️⃣ Batal Ikut Pusat"])
            
            with tab1:
                st.subheader("Batal Semua Penempatan")
                st.caption("Fungsi: Clear kod_pusat + reset status jadi TERPILIH PPD. Cadangan SUP kekal, cuma penempatan PPD direset.")
                try:
                    df_c = get_cadangan_df(kod_ppd=kod_ppd)
                    cnt_penempatan = len(df_c[df_c.get("kod_pusat","").astype(str).str.strip()!=""]) if not df_c.empty else 0
                except:
                    cnt_penempatan = 0
                st.metric("Jumlah ada penempatan sekarang", cnt_penempatan)
                
                c1, c2 = st.columns(2)
                confirm_penempatan = c1.text_input("Taip BATAL PENEMPATAN untuk sahkan", key="confirm_batal_penempatan", placeholder="BATAL PENEMPATAN")
                if c2.button("🔴 Batal Semua Penempatan", key="btn_batal_penempatan", type="primary", disabled=confirm_penempatan!="BATAL PENEMPATAN", use_container_width=True):
                    with st.spinner("Membatalkan penempatan..."):
                        ok, msg = batal_semua_penempatan_ppd(kod_ppd)
                    if msg and ok==0:
                        st.error(f"Gagal: {msg}")
                    else:
                        st.success(f"✅ {ok} penempatan berjaya dibatalkan. Status reset ke TERPILIH PPD.")
                        st.cache_data.clear()
                        st.rerun()
            
            with tab2:
                st.subheader("Batal Semua Cadangan")
                st.caption("Fungsi: Padam / reset semua cadangan SUP dalam PPD anda. Guna bila nak mula semula.")
                st.error("⛔ Berbahaya: Semua cadangan SUP untuk PPD anda akan hilang!")
                try:
                    df_all = get_cadangan_df(kod_ppd=kod_ppd)
                    cnt_all = len(df_all) if df_all is not None and not df_all.empty else 0
                except:
                    cnt_all = 0
                st.metric("Jumlah cadangan sekarang", cnt_all)
                
                pilihan_batal = st.radio("Pilih tindakan", ["Reset status ke HANTAR KE PPD (selamat, masih ada data)", "Padam terus dari database (DELETE)"], key="pilihan_batal_cadangan")
                mode = "reset" if "Reset" in pilihan_batal else "delete"
                
                c1, c2 = st.columns(2)
                confirm_cadangan = c1.text_input("Taip BATAL CADANGAN untuk sahkan", key="confirm_batal_cadangan", placeholder="BATAL CADANGAN")
                if c2.button("🔴 Batal Semua Cadangan", key="btn_batal_cadangan", type="primary", disabled=confirm_cadangan!="BATAL CADANGAN", use_container_width=True):
                    with st.spinner("Membatalkan cadangan..."):
                        ok, msg = batal_semua_cadangan_ppd(kod_ppd, mode=mode)
                    if msg and ok==0:
                        st.error(f"Gagal: {msg}")
                    else:
                        if mode=="delete":
                            st.success(f"✅ {ok} cadangan berjaya DIPADAM terus dari database.")
                        else:
                            st.success(f"✅ {ok} cadangan berjaya direset ke HANTAR KE PPD.")
                        st.cache_data.clear()
                        st.rerun()

            with tab3:
                from ppd_cadangan import batal_penempatan_pusat, batal_cadangan_pusat, kira_di_pusat
                st.subheader("Batal Ikut Pusat")
                st.caption("Pilih satu pusat sahaja. Petugas di pusat lain tidak terjejas. Penyelia Kawasan tidak terlibat (batal PK di Lantik Penyelia Kawasan > Tempatkan PK).")
                _peta_b = _pp._peta_pusat(kod_ppd)
                if not _peta_b:
                    st.info("Tiada pusat.")
                else:
                    _pb = st.selectbox("📍 Pilih Pusat", sorted(_peta_b.keys()),
                                       format_func=lambda x: f"{x} - {(_peta_b.get(x) or {}).get('nama', '')[:35]}", key="batal_pusat_pilih")
                    _n = kira_di_pusat(kod_ppd, _pb)
                    st.metric(f"Petugas di {_pb}", _n)
                    st.markdown("##### 🗑️ Batal Semua Penempatan di Pusat Ini")
                    st.caption("Kosongkan pusat & no surat. Petugas kembali ke status TERPILIH PPD (cadangan kekal).")
                    _c1, _c2 = st.columns(2)
                    _k1 = _c1.text_input(f"Taip BATAL PENEMPATAN {_pb} untuk sahkan", key="confirm_batal_pen_pusat")
                    if _c2.button(f"🔴 Batal Penempatan {_pb}", key="btn_batal_pen_pusat", type="primary", use_container_width=True,
                                  disabled=(_k1.strip().upper() != f"BATAL PENEMPATAN {_pb}") or _n == 0):
                        with st.spinner("Membatalkan penempatan..."):
                            _ok, _msg = batal_penempatan_pusat(kod_ppd, _pb)
                        if _msg and _ok == 0:
                            st.error(f"Gagal: {_msg}")
                        else:
                            st.success(f"✅ {_ok} penempatan di {_pb} dibatalkan.")
                            st.cache_data.clear()
                            st.rerun()
                    st.markdown("---")
                    st.markdown("##### 🗑️ Batal Semua Cadangan di Pusat Ini")
                    _mode_txt = st.radio("Tindakan", ["Reset ke HANTAR KE PPD (selamat - kembali ke Cadangan SUP)", "Padam terus dari database (DELETE)"], key="mode_batal_cad_pusat")
                    _mode_b = "reset" if _mode_txt.startswith("Reset") else "delete"
                    if _mode_b == "delete":
                        st.error("⛔ Cadangan di pusat ini akan dipadam terus.")
                    _d1, _d2 = st.columns(2)
                    _k2 = _d1.text_input(f"Taip BATAL CADANGAN {_pb} untuk sahkan", key="confirm_batal_cad_pusat")
                    if _d2.button(f"🔴 Batal Cadangan {_pb}", key="btn_batal_cad_pusat", type="primary", use_container_width=True,
                                  disabled=(_k2.strip().upper() != f"BATAL CADANGAN {_pb}") or _n == 0):
                        with st.spinner("Membatalkan cadangan..."):
                            _ok, _msg = batal_cadangan_pusat(kod_ppd, _pb, mode=_mode_b)
                        if _msg and _ok == 0:
                            st.error(f"Gagal: {_msg}")
                        else:
                            st.success(f"✅ {_ok} cadangan di {_pb} " + ("dipadam." if _mode_b == "delete" else "direset ke HANTAR KE PPD."))
                            st.cache_data.clear()
                            st.rerun()


        elif menu == "export":
            st.header(f"Export Data PPD {kod_ppd}")

            st.header(f"Export Data PPD {kod_ppd}")


            df_cad = get_cadangan_df(kod_ppd=kod_ppd)
            if not df_cad.empty:
                st.download_button("📥 Export Cadangan PPD (Excel)", to_excel(df_cad), file_name=f"laporan_PPD_{kod_ppd}_{datetime.date.today()}.xlsx", use_container_width=True)
            try:
                res = supa.table("guru_master").select("*").eq("kod_ppd", kod_ppd.lower()).limit(5000).execute()
                df_guru = pd.DataFrame(res.data or [])
                if not df_guru.empty:
                    st.download_button("📥 Export Guru PPD (Excel)", to_excel(df_guru), file_name=f"guru_PPD_{kod_ppd}.xlsx", use_container_width=True)
            except Exception as e:
                st.error(str(e))

# ================= ROLE: JPN =================
