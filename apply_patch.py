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
    ("pool Jana Keseluruhan", "jana_pool_panel(kod_ppd, df_cad_all)",
     '            df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)\n\n            if df_pusat_raw.empty:\n                st.warning("⚠️ Tiada pusat_master")\n                st.stop()\n            if df_cad_all.empty:\n                st.warning(f"⚠️ Belum ada cadangan SUP untuk PPD {kod_ppd}")\n                st.stop()\n',
     '            df_cad_all = get_cadangan_df(kod_ppd=kod_ppd)\n            df_cad_all = jana_pool_panel(kod_ppd, df_cad_all)   # hanya calon TERPILIH PPD (+ yang sudah diproses)\n\n            if df_pusat_raw.empty:\n                st.warning("⚠️ Tiada pusat_master")\n                st.stop()\n            if df_cad_all.empty:\n                st.warning("⚠️ Belum ada calon untuk dijana. Lihat arahan di atas.")\n                st.stop()\n'),
])
print("SIAP")
