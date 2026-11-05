# -*- coding: utf-8 -*-
"""penyelia_surat.py - Surat Lantikan Penyelia Kawasan dijana daripada TEMPLAT JPN (jawatan "PENYELIA KAWASAN").

Placeholder tambahan (selain {{NAMA}} {{IC}} {{SEKOLAH_ASAL}} {{NAMA_SEKOLAH_ASAL}} {{NO_SURAT}} {{TARIKH}} {{TAHUN}} dll):
  {{KOD_BILIK_KEBAL}} {{NAMA_BILIK_KEBAL}} {{ALAMAT_BILIK_KEBAL}} {{BILIK_KEBAL_PENUH}}
  {{TELEFON}}
  {{BIL_PUSAT}}                 bilangan pusat di bawah jagaan penyelia ini
  {{SENARAI_PUSAT}}             pusat jagaan penyelia (satu baris teks: BA021 - SMK X; BA053 - SK Y)
  {{SENARAI_PUSAT_JADUAL}}      jadual HTML Bil | No Pusat | Nama Pusat
  {{SENARAI_PUSAT_BK}}          semua pusat di bawah kawalan bilik kebal (ikut zon), satu baris teks
  {{SENARAI_PUSAT_BK_JADUAL}}   jadual HTML semua pusat bilik kebal
  {{BIL_SEKOLAH_BK}}            bilangan sekolah dalam zon bilik kebal (jadual zon_bilik_kebal)
  {{SENARAI_SEKOLAH_BK}}        senarai sekolah zon (nama dibaca dari sekolah_master), satu baris teks
  {{SENARAI_SEKOLAH_BK_JADUAL}} jadual HTML Bil | Kod | Nama Sekolah
Jika templat PENYELIA KAWASAN belum disimpan oleh JPN, surat lama (berasaskan kod) digunakan sebagai sandaran.
"""
import html as _html
import streamlit as st

JAWATAN_TEMPLAT = "PENYELIA KAWASAN"


def _e(x):
    return _html.escape(str(x if x is not None else ""))


def _jadual(baris, tajuk_lajur):
    if not baris:
        return "<p>-</p>"
    th = "".join(f"<th style='border:1px solid #000;padding:3px 6px;text-align:left'>{_e(t)}</th>" for t in tajuk_lajur)
    tr = "".join("<tr>" + "".join(f"<td style='border:1px solid #000;padding:3px 6px'>{_e(c)}</td>" for c in r) + "</tr>" for r in baris)
    return f"<table style='border-collapse:collapse;width:100%;font-size:10pt'><tr>{th}</tr>{tr}</table>"


@st.cache_data(ttl=300, show_spinner=False)
def _peta_sekolah(kod_ppd):
    import spm_core as core
    out = {}
    try:
        for r in core.supa.table("sekolah_master").select("kod_sekolah,nama_sekolah").limit(5000).execute().data or []:
            k = str(r.get("kod_sekolah") or "").upper().strip()
            if k:
                out[k] = str(r.get("nama_sekolah") or "").strip().upper()
    except Exception:
        pass
    return out


def _peta_pusat(kod_ppd):
    """{no_pusat: {nama, tuan}} untuk daerah ini."""
    import ppd_zon
    try:
        return {no: {"nama": v.get("NAMA", ""), "tuan": v.get("KOD_TUAN", "")} for no, v in ppd_zon.load_pusat(kod_ppd).items()}
    except Exception:
        return {}


def zon_sekolah(kod_ppd, kod_bk):
    """Senarai (kod, nama) sekolah dalam zon bilik kebal; nama dibaca dari sekolah_master."""
    import ppd_zon
    try:
        zon = ppd_zon.zon_load(ppd_zon.zon_db_ok())
    except Exception:
        zon = {}
    sek = _peta_sekolah(kod_ppd)
    return [(k, sek.get(k, "")) for k in sorted(set(zon.get(str(kod_bk).upper().strip(), [])))]


def pusat_zon(kod_ppd, kod_bk):
    """No pusat yang bertapak di sekolah dalam zon bilik kebal."""
    sek = {k for k, _ in zon_sekolah(kod_ppd, kod_bk)}
    return sorted(no for no, v in _peta_pusat(kod_ppd).items() if v["tuan"] in sek)


def nama_bk_cari(kod_ppd, kod_bk, nama_asal=""):
    """Nama bilik kebal: nama sedia ada -> sekolah_master (cache) -> bilik_kebal_master -> sekolah_master (terus). '' jika tiada."""
    import spm_core as core
    kod = str(kod_bk or "").upper().strip()
    nama = str(nama_asal or "").strip()
    if nama and nama.upper() != kod:
        return nama
    n = _peta_sekolah(kod_ppd).get(kod, "")
    if n:
        return n
    try:
        for r in core.supa.table("bilik_kebal_master").select("*").eq("kod_bilik_kebal", kod).limit(1).execute().data or []:
            d = r.get("data") if isinstance(r.get("data"), dict) else {}
            for k in ("nama_bilik_kebal", "NAMA_BILIK_KEBAL", "nama", "NAMA", "nama_sekolah", "NAMA_SEKOLAH"):
                v = str(r.get(k) or d.get(k) or "").strip()
                if v and v.upper() != kod:
                    return v
    except Exception:
        pass
    try:
        for r in core.supa.table("sekolah_master").select("nama_sekolah").ilike("kod_sekolah", kod).limit(1).execute().data or []:
            v = str(r.get("nama_sekolah") or "").strip().upper()
            if v:
                return v
    except Exception:
        pass
    return ""


def bina_extra(kod_ppd, kod_bk, nama_bk, alamat_bk, telefon, pusat_jagaan):
    """Kamus placeholder tambahan untuk templat Penyelia Kawasan."""
    pp = _peta_pusat(kod_ppd)
    jag = [str(p).strip().upper() for p in (pusat_jagaan or []) if str(p).strip()]
    baris_j = [(i, p, pp.get(p, {}).get("nama", "")) for i, p in enumerate(jag, 1)]
    zp = pusat_zon(kod_ppd, kod_bk)
    baris_z = [(i, p, pp.get(p, {}).get("nama", "")) for i, p in enumerate(zp, 1)]
    zs = zon_sekolah(kod_ppd, kod_bk)
    nama_bk = nama_bk_cari(kod_ppd, kod_bk, nama_bk)
    teks = lambda b: "; ".join(f"{p} - {n}" if n else p for _, p, n in b) or "-"
    return {
        "KOD_BILIK_KEBAL": kod_bk, "NAMA_BILIK_KEBAL": nama_bk, "ALAMAT_BILIK_KEBAL": alamat_bk or "",
        "BILIK_KEBAL_PENUH": f"{kod_bk} - {nama_bk}" if nama_bk and nama_bk.upper() != str(kod_bk).upper() else kod_bk,
        "TELEFON": telefon or "",
        "BIL_PUSAT": len(jag),
        "SENARAI_PUSAT": teks(baris_j),
        "SENARAI_PUSAT_MERAH": "<br>".join(f"{p} - {n}" if n else p for _, p, n in baris_j) or "-",
        "TAHUN": str(__import__("spm_core").tahun_semasa()),
        "SENARAI_PUSAT_JADUAL": _jadual(baris_j, ["Bil", "No Pusat", "Nama Pusat"]),
        "SENARAI_PUSAT_BK": teks(baris_z),
        "SENARAI_PUSAT_BK_JADUAL": _jadual(baris_z, ["Bil", "No Pusat", "Nama Pusat"]),
        "BIL_SEKOLAH_BK": len(zs),
        "SENARAI_SEKOLAH_BK": "; ".join(f"{k} - {n}" if n else k for k, n in zs) or "-",
        "SENARAI_SEKOLAH_BK_JADUAL": _jadual([(i, k, n) for i, (k, n) in enumerate(zs, 1)], ["Bil", "Kod Sekolah", "Nama Sekolah"]),
    }


def ada_templat():
    import spm_core as core
    return bool(core.get_jpn_template_for_jawatan(JAWATAN_TEMPLAT))


def jana_html(core, *, nama, ic, sek_asal, nama_sek_asal, telefon, kod_bk, nama_bk, alamat_bk, pusat_jagaan,
              no_surat, kod_ppd, ppd_name, tarikh):
    """HTML surat dari templat JPN, atau None jika templat tiada. Pulang (html, extra)."""
    extra = bina_extra(kod_ppd, kod_bk, nama_bk, alamat_bk, telefon, pusat_jagaan)
    pusat_kod = ", ".join(pusat_jagaan or [])
    html = core.render_jpn_template_html(JAWATAN_TEMPLAT, nama, ic, sek_asal, nama_sek_asal, pusat_kod, extra["SENARAI_PUSAT"],
                                         no_surat, kod_ppd, ppd_name, tarikh, kod_bk, extra=extra)
    return html, extra


# ---------------------------------------------------------------- templat cadangan (untuk JPN)
TEMPLAT_CADANGAN = """<div style="font-family:Arial,Helvetica,sans-serif;font-size:11pt;line-height:1.5">
<table style="width:100%;border:none"><tr>
<td style="width:80px;border:none"><img src="{{LOGO}}" style="width:70px"></td>
<td style="border:none"><b>KEMENTERIAN PENDIDIKAN MALAYSIA</b><br>JABATAN PENDIDIKAN NEGERI SELANGOR<br>PEJABAT PENDIDIKAN DAERAH {{NAMA_PPD}}</td>
</tr></table>
<hr>
<p>Ruj. Kami : {{NO_SURAT}}<br>Tarikh : {{TARIKH}}</p>
<p><b>{{NAMA}}</b><br>No. KP : {{IC}}<br>No. Tel : {{TELEFON}}</p>
<p>Melalui:<br>Pengetua/Guru Besar,<br><b>{{SEKOLAH_ASAL_PENUH}}</b></p>
<p>Tuan/Puan,</p>
<p><b>SIJIL PELAJARAN MALAYSIA (SPM) TAHUN {{TAHUN}}:<br>PELANTIKAN SEBAGAI PENYELIA KAWASAN</b></p>
<p>Dengan hormatnya perkara di atas adalah dirujuk.</p>
<p>2. Sukacita dimaklumkan bahawa tuan/puan telah dilantik sebagai <b>Penyelia Kawasan</b> bagi Bilik Kebal
<b>{{BILIK_KEBAL_PENUH}}</b> ({{ALAMAT_BILIK_KEBAL}}) bagi peperiksaan SPM Tahun {{TAHUN}}.</p>
<p>3. Tuan/puan bertanggungjawab ke atas <b>{{BIL_PUSAT}}</b> pusat peperiksaan berikut di bawah kawalan Bilik Kebal tersebut:</p>
{{SENARAI_PUSAT_JADUAL}}
<p>4. Sekolah-sekolah di bawah kawalan Bilik Kebal {{KOD_BILIK_KEBAL}} ({{BIL_SEKOLAH_BK}} sekolah):</p>
{{SENARAI_SEKOLAH_BK_JADUAL}}
<p>5. Tuan/puan dikehendaki hadir taklimat Penyelia Kawasan dan bertugas mengikut jadual yang dimaklumkan oleh PPD.</p>
<p>Sekian, terima kasih.</p>
<p><b>"MALAYSIA MADANI"<br>"BERKHIDMAT UNTUK NEGARA"</b></p>
<p>Saya yang menjalankan amanah,<br><img src="{{TANDATANGAN}}" style="width:140px"><br>Pegawai Pendidikan Daerah<br>PPD {{NAMA_PPD}}</p>
</div>"""
