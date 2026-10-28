# -*- coding: utf-8 -*-
"""
apply_patch.py - Tambah aliran "Senarai Nama Cadangan / Senarai Simpanan / tapis Jana" ke projek sedia ada.
Jalankan dari folder projek:   python apply_patch.py
Selamat dijalankan berulang kali (tidak akan menggandakan perubahan).
"""
import sys, os

root = sys.argv[1] if len(sys.argv) > 1 else "."

def patch(path, steps):
    p = os.path.join(root, path)
    s = open(p, encoding="utf-8").read()
    changed = False
    for name, done_marker, old, new in steps:
        if done_marker in s:
            print(f"  - {path}: {name} (sudah ada, dilangkau)")
            continue
        if s.count(old) != 1:
            sys.exit(f"RALAT {path}: tidak jumpa tepat 1 padanan untuk '{name}' (jumpa {s.count(old)}). Fail mungkin sudah diubah - semak manual.")
        s = s.replace(old, new, 1)
        changed = True
        print(f"  + {path}: {name}")
    if changed:
        open(p, "w", encoding="utf-8").write(s)

patch("spm_core.py", [
    ("sub menu FLY_PPD['cadangan']", "('nama', '📝 Senarai Nama Cadangan')",
     "    'jana':       [('auto',",
     "    'cadangan':   [('sekolah', '🏫 Ikut Sekolah'), ('nama', '📝 Senarai Nama Cadangan'), ('simpanan', '📦 Senarai Simpanan')],\n    'jana':       [('auto',"),
    ("fungsi cari imej logo/tandatangan + amaran", "def surat_aset_amaran",
     "def render_footer():",
     '''import os as _os
_ASSET_DIR = _os.path.dirname(_os.path.abspath(__file__))
LOGO_NAMES = ["jata_cropped.png", "jata_negara_hd.png", "jata_negara.png"]
SIGN_NAMES = ["tandatangan_pengarah_hd.png", "tandatangan_pengarah.png", "tandatangan_pengarah.jpg", "tandatangan.png"]

def find_asset(names):
    """Cari fail imej di folder projek, ./, /mnt/data dan assets/."""
    for n in names:
        for d in (_ASSET_DIR, ".", "/mnt/data", _os.path.join(_ASSET_DIR, "assets"), "assets"):
            p = _os.path.join(d, n)
            if _os.path.exists(p):
                return p
    return None

def surat_aset_amaran():
    """Papar amaran jika logo / tandatangan surat tiada dalam repo (surat akan keluar tanpa logo/sign)."""
    miss = []
    if not find_asset(LOGO_NAMES):
        miss.append("logo Jata Negara (jata_negara_hd.png)")
    if not find_asset(SIGN_NAMES):
        miss.append("tandatangan Pengarah (tandatangan_pengarah_hd.png)")
    if miss:
        st.warning("⚠️ Fail imej surat tidak dijumpai dalam repo: " + " dan ".join(miss) +
                   ". Letakkan fail ini di folder yang sama dengan spm_core.py (atau dalam folder assets/), kemudian deploy semula. "
                   "Tanpa fail ini, surat PDF keluar tanpa logo dan tandatangan.")

def render_footer():'''),
    ("logo: cari juga dalam assets/", "logo_path = find_asset(LOGO_NAMES)",
     "        logo_path = None\n",
     "        logo_path = find_asset(LOGO_NAMES)\n"),
    ("keutamaan status baru", "'TERPILIH' in s or 'SIMPANAN' in s",
     "                if 'HANTAR' in s:\n                    return 3",
     "                if 'HANTAR' in s or 'TERPILIH' in s or 'SIMPANAN' in s:\n                    return 3"),
])

patch("role_ppd.py", [
    ("import modul baru", "from ppd_cadangan import",
     'globals().update({k: v for k, v in vars(_ui).items() if not k.startswith("__")})\n',
     'globals().update({k: v for k, v in vars(_ui).items() if not k.startswith("__")})\nfrom ppd_cadangan import render_senarai_nama, render_senarai_simpanan, jana_pool_panel\n'),
    ("cabang menu Senarai Nama / Simpanan", 'menu == "cadangan" and fly_cur == "nama"',
     '        elif menu == "cadangan":\n',
     '        elif menu == "cadangan" and fly_cur == "nama":\n            render_senarai_nama(kod_ppd)\n\n'
     '        elif menu == "cadangan" and fly_cur == "simpanan":\n            render_senarai_simpanan(kod_ppd)\n\n'
     '        elif menu == "cadangan":\n'),
    ("amaran imej surat (menu Jana Surat)", "surat_aset_amaran()",
     '        elif menu == "jana_surat":\n',
     '        elif menu == "jana_surat":\n            surat_aset_amaran()\n'),
    ("pool Jana Keseluruhan", "jana_pool_panel(kod_ppd, df_cad_all)",
     '            df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)\n\n            if df_pusat_raw.empty:\n                st.warning("⚠️ Tiada pusat_master")\n                st.stop()\n            if df_cad_all.empty:\n                st.warning(f"⚠️ Belum ada cadangan SUP untuk PPD {kod_ppd}")\n                st.stop()\n',
     '            df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)\n            df_cad_all = jana_pool_panel(kod_ppd, df_cad_all)   # hanya calon TERPILIH PPD (+ yang sudah diproses)\n\n            if df_pusat_raw.empty:\n                st.warning("⚠️ Tiada pusat_master")\n                st.stop()\n            if df_cad_all.empty:\n                st.warning("⚠️ Belum ada calon untuk dijana. Lihat arahan di atas.")\n                st.stop()\n'),
    ("import hasil_lookup/hasil_row", "hasil_lookup, hasil_row",
     'from ppd_cadangan import render_senarai_nama, render_senarai_simpanan, jana_pool_panel\n',
     'from ppd_cadangan import render_senarai_nama, render_senarai_simpanan, jana_pool_panel, hasil_lookup, hasil_row\n'),
    ("Hasil Janaan: peta pusat (Ikut Sekolah Asal)", 'hasil_lookup(df_pusat_raw, kod_ppd)\n                st.markdown("### 🏫',
     '            if fly_cur == "sekolah":\n                st.markdown("### 🏫 Hasil Janaan Mengikut Sekolah Asal")\n',
     '            if fly_cur == "sekolah":\n                _hl = hasil_lookup(df_pusat_raw, kod_ppd)\n                st.markdown("### 🏫 Hasil Janaan Mengikut Sekolah Asal")\n'),
    ("Hasil Janaan: ringkasan sekolah (no pusat asal, nama pusat tugas)", '"NO PUSAT ASAL": ", ".join(_hl["asal"]',
     '"BIL GURU": len(guru_list), "PUSAT DITEMPATKAN": ", ".join(sorted(pusat_list))})',
     '"NO PUSAT ASAL": ", ".join(_hl["asal"].get(kod, [])) or "-", "BIL GURU": len(guru_list), "PUSAT DITEMPATKAN": ", ".join(sorted(pusat_list)), "NAMA PUSAT TUGAS": " | ".join(sorted({_hl["pusat"].get(_p, {}).get("nama", "") for _p in pusat_list} - {""}))})'),
    ("Hasil Janaan: detail sekolah", 'hasil_row(r, g["pusat"], _hl)',
     'rows_detail.append({"NAMA": r.get("NAMA_GURU", ""), "NO IC": r.get("IC_GURU", ""), "JAWATAN": r.get("JAWATAN_CADANGAN") or r.get("JAWATAN") or "", "PUSAT TUGAS": g["pusat"], "JANTINA": r.get("JANTINA", "") or r.get("jantina", ""), "TELEFON": r.get("TELEFON_GURU", "") or r.get("telefon_guru", "")})',
     'rows_detail.append(hasil_row(r, g["pusat"], _hl))'),
    ("Hasil Janaan: peta pusat (Semua Guru)", 'hasil_lookup(df_pusat_raw, kod_ppd)\n                st.markdown("### 👥',
     '            if fly_cur == "guru":\n                st.markdown("### 👥 Semua Guru Ditempatkan - Keseluruhan")\n',
     '            if fly_cur == "guru":\n                _hl = hasil_lookup(df_pusat_raw, kod_ppd)\n                st.markdown("### 👥 Semua Guru Ditempatkan - Keseluruhan")\n'),
    ("Hasil Janaan: semua guru", 'hasil_row(r, v["pusat"], _hl)',
     'all_guru_rows.append({"NAMA": r.get("NAMA_GURU", ""), "NO IC": r.get("IC_GURU", ""), "JAWATAN": r.get("JAWATAN_CADANGAN") or r.get("JAWATAN") or "", "SEKOLAH ASAL": r.get("KOD_SEKOLAH_ASAL", ""), "NAMA SEKOLAH ASAL": str(r.get("NAMA_SEKOLAH_ASAL", ""))[:25], "PUSAT TUGAS": v["pusat"], "JANTINA": r.get("JANTINA", "") or r.get("jantina", ""), "TELEFON": r.get("TELEFON_GURU", "") or r.get("telefon_guru", "")})',
     'all_guru_rows.append(hasil_row(r, v["pusat"], _hl))'),
])
print("SIAP")
