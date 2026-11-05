# -*- coding: utf-8 -*-
"""kuota_pusat.py - SATU sumber kebenaran untuk calon / kelas / kuota petugas setiap pusat.

Peraturan:
  KELAS            = (suntingan PPD) jika ada, jika tidak CEIL(CALON / 20)
  PETUGAS PERLU    = KELAS + 9                  (kuota pusat - dipaparkan di Dashboard PPD)
  SEKOLAH WAJIB    = KELAS + 12                 (kuota calon yang SUP perlu hantar = petugas + 1 KP + 1 TKP + 1 Penyelia)
Suntingan PPD (menu Pusat di PPD > Selenggara Pusat) disimpan dalam pusat_master.data:
  PPD_CALON, PPD_KELAS (PPD_KELAS hanya disimpan jika berbeza daripada CEIL(CALON/20)).
Semua halaman (Dashboard PPD, SUP, Hasil, Zon, halaman pilih sekolah) mesti guna fungsi di sini.
"""
import json
import math


def _int(v, lalai=0):
    try:
        s = str(v if v is not None else "").replace(",", "").strip()
        if s.lower() in ("", "nan", "none", "null"):
            return lalai
        return int(float(s))
    except Exception:
        return lalai


def _data(r):
    d = r.get("data") if hasattr(r, "get") else None
    if isinstance(d, dict):
        return d
    if isinstance(d, str) and d.strip().startswith("{"):
        try:
            return json.loads(d)
        except Exception:
            return {}
    return {}


def kelas_auto(calon):
    c = _int(calon)
    return math.ceil(c / 20) if c > 0 else 0


def petugas_perlu(kelas):
    return _int(kelas) + 9


def sekolah_perlu(kelas):
    return _int(kelas) + 12


def kuota_pusat(r):
    """r = satu baris pusat_master (dict / Series). Pulang {calon, kelas, petugas, sekolah_perlu, ubah_ppd}."""
    d = _data(r)
    calon = None
    if d.get("PPD_CALON") not in (None, ""):
        calon = _int(d.get("PPD_CALON"))
    if calon is None:
        for src, keys in ((r, ("jumlah_calon", "calon")), (d, ("JUMLAH_CALON", "CALON"))):
            for k in keys:
                v = src.get(k) if hasattr(src, "get") else None
                if _int(v) > 0:
                    calon = _int(v)
                    break
            if calon is not None:
                break
    calon = calon or 0
    if d.get("PPD_KELAS") not in (None, ""):
        kelas = _int(d.get("PPD_KELAS"))
        ubah = True
    else:
        kelas = kelas_auto(calon)
        ubah = d.get("PPD_CALON") not in (None, "")
    return {"calon": calon, "kelas": kelas, "petugas": petugas_perlu(kelas),
            "sekolah_perlu": sekolah_perlu(kelas), "ubah_ppd": ubah}


def kod_tuan_rumah(r):
    """Set kod sekolah yang dikira tuan rumah pusat (sama seperti padanan Dashboard SUP)."""
    d = _data(r)
    a = str(r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or r.get("KOD_SEKOLAH") or d.get("KOD_SEKOLAH")
            or d.get("KOD SEKOLAH") or d.get("KOD_SEKOLAH_TUAN_RUMAH") or "").upper().strip()
    b = str(r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or "").upper().strip()
    return {x for x in (a, b) if x}


def no_pusat(r):
    d = _data(r)
    return str(r.get("no_pusat") or r.get("kod_pusat") or r.get("NO_PUSAT") or d.get("NO_PUSAT") or d.get("NO PUSAT")
               or d.get("KOD_PUSAT") or "").upper().strip()


def kuota_ikut_sekolah(df_pusat):
    """{kod_sekolah: {"perlu": jumlah (kelas+12) semua pusat sekolah itu, "pusat": [no_pusat]}}"""
    out = {}
    if df_pusat is None or len(df_pusat) == 0:
        return out
    for _, r in df_pusat.iterrows():
        q = kuota_pusat(r)
        np_ = no_pusat(r)
        for ks in kod_tuan_rumah(r):
            e = out.setdefault(ks, {"perlu": 0, "pusat": []})
            if np_ in e["pusat"]:
                continue
            e["perlu"] += q["sekolah_perlu"]
            e["pusat"].append(np_)
    return out


# ------------------------------------------------------------------ suntingan PPD
def selaras_edit_pusat(asal, edit):
    """asal/edit: DataFrame dengan NO_PUSAT, BIL_CALON, KELAS. Pulang senarai perubahan sahaja:
    [{no, calon, kelas, perlu, calon_lama, kelas_lama, perlu_lama}]
    Peraturan: calon berubah -> kelas = CEIL(calon/20) (kecuali kelas turut diubah serentak); perlu = kelas + 9."""
    asal_map = {str(r["NO_PUSAT"]): r for _, r in asal.iterrows()}
    out = []
    for _, e in edit.iterrows():
        no = str(e["NO_PUSAT"])
        a = asal_map.get(no)
        if a is None:
            continue
        c0, k0 = _int(a["BIL_CALON"]), _int(a["KELAS"])
        c1, k1 = max(0, _int(e["BIL_CALON"], c0)), max(0, _int(e["KELAS"], k0))
        if c1 == c0 and k1 == k0:
            continue
        if c1 != c0 and k1 == k0:
            k1 = kelas_auto(c1)
        out.append({"no": no, "calon": c1, "kelas": k1, "perlu": petugas_perlu(k1),
                    "calon_lama": c0, "kelas_lama": k0, "perlu_lama": petugas_perlu(k0)})
    return out


def simpan_pusat(supa, no, calon, kelas):
    """Simpan suntingan PPD. Pulang True jika pusat dijumpai & dikemas kini."""
    calon, kelas = max(0, _int(calon)), max(0, _int(kelas))
    for col in ("no_pusat", "kod_pusat"):
        try:
            rows = supa.table("pusat_master").select("*").eq(col, no).limit(1).execute().data or []
        except Exception:
            continue
        if not rows:
            continue
        row = rows[0]
        d = dict(_data(row))
        d["PPD_CALON"] = calon
        if kelas == kelas_auto(calon):
            d.pop("PPD_KELAS", None)
        else:
            d["PPD_KELAS"] = kelas
        d["JUMLAH_CALON"] = calon
        d["CALON"] = calon
        d["JUMLAH_KELAS"] = kelas
        d["KELAS"] = kelas
        payload = {"data": json.dumps(d, ensure_ascii=False) if isinstance(row.get("data"), str) else d}
        for k in ("jumlah_calon", "calon"):
            if k in row:
                payload[k] = calon
        for k in ("jumlah_kelas", "bilik"):
            if k in row:
                payload[k] = kelas
        supa.table("pusat_master").update(payload).eq(col, no).execute()
        return True
    return False
