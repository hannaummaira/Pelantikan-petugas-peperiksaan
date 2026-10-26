# Sistem Pelantikan Petugas SPM Selangor 2026 - versi diasingkan

11 aplikasi Streamlit berasingan, satu kod asas:

| Fail utama (Main file path) | Fungsi | Data Supabase yang dibaca |
|---|---|---|
| `app_BA.py` ... `app_BK.py` (10 fail) | SUP + PPD satu daerah | daerah itu sahaja |
| `app_JPN.py` | JPN (pentadbir negeri) | semua daerah |

Kod daerah: BA Klang, BB Kuala Langat, BC Kuala Selangor, BD Hulu Langat, BE Hulu Selangor,
BF Sabak Bernam, BG Gombak, BH Petaling Perdana, BJ Sepang, BK Petaling Utama.

## Cara deploy (Streamlit Community Cloud)
1. Letak semua fail dalam satu repo (akar repo).
2. Cipta 11 app, setiap satu pilih "Main file path" yang berbeza (cth `app_BG.py` untuk Gombak).
3. Dalam Secrets setiap app:
   ```
   SUPABASE_URL = "https://xxxx.supabase.co"
   SUPABASE_KEY = "kunci-anda"
   ```
   (Jika tiada, kod guna nilai lama yang masih ada dalam `spm_core.py` - sila buang selepas secrets diset.)

## Struktur
- `spm_core.py`   fungsi kongsi (surat, loader, PDF/ZIP) - dari app.py asal
- `scoped_db.py`  penapis daerah automatik untuk SEMUA bacaan Supabase + paginasi > 1000 baris
- `ui_theme.py`   susun atur ikut contoh (header, menu kiri, sub menu, kad)
- `daerah_app.py` halaman pilih sekolah + log masuk SUP/PPD satu daerah
- `role_sup.py`   SUP (membaca `guru_master`, menulis `cadangan_sup`)
- `role_ppd.py`   PPD (membaca `cadangan_sup` daerah sendiri)
- `role_jpn.py`, `jpn_app.py`  JPN
