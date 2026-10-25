
# SPM 2026 - 1 PROJEK STREAMLIT FINAL DEPLOY

## Cara Deploy - TETAP 1 PROJEK

1. Push folder ini ke GitHub (1 repo)
2. Pergi Streamlit Cloud -> New App
3. Pilih repo ini
4. **Main file path: app.py** <- SET INI JE
5. Deploy

Streamlit akan baca app.py sebagai landing 4 muka depan (SUP/PPD/JPN/INFO).
Bila klik, dia akan masuk ke pages/ - masih dalam 1 projek, 1 URL.

## Supabase
- Tetap 1 project Supabase sahaja
- Set SUPABASE_URL dan SUPABASE_KEY di Streamlit Secrets
- Semua role (SUP/PPD/JPN) share DB yang sama, RLS yang tapis

## Kod 8800 Baris
- Semua 57 fungsi masih kekal di setiap file dalam pages/
- Tak ada fungsi dibuang
- File asal fix4_surat.py ada dalam setiap page untuk pastikan tak hilang
- Bila dah stabil, baru buang menu yang tak perlu secara perlahan

## Struktur
- app.py = Landing 4 muka depan (ini je yang Streamlit baca first)
- pages/1_SUP_Sekolah.py = Portal SUP
- pages/2_PPD_Daerah.py = Portal PPD
- pages/3_JPN_Negeri.py = Portal JPN
- pages/4_Info_Panduan.py = Info
- packages/ = library kongsi
