# -*- coding: utf-8 -*-
"""tetapan_ppd.py - Tetapan PPD: maksimum guru dari SATU sekolah asal yang boleh bertugas di SATU pusat yang sama.

Disimpan dalam jadual `landing_config` (baris id=3, config={"max_per_sekolah": {"BA": 3, ...}}) - tiada jadual baharu.
Lalai = 3 (peraturan asal). Setiap PPD ada nilai sendiri.
"""
import json
import time

MAX_LALAI = 3
MAX_MIN, MAX_MAKS = 1, 20
_ID = 3
_TTL = 60
_C = {"t": 0.0, "v": None}


def _raw():
    from spm_core import _RAW  # import lewat supaya tiada kitaran import
    return _RAW


def _baca_semua():
    try:
        rows = _raw().table("landing_config").select("config").eq("id", _ID).limit(1).execute().data or []
        if rows:
            cfg = rows[0].get("config")
            if isinstance(cfg, str):
                cfg = json.loads(cfg)
            m = (cfg or {}).get("max_per_sekolah") or {}
            return {str(k).upper(): int(v) for k, v in m.items() if MAX_MIN <= int(v) <= MAX_MAKS}
    except Exception:
        pass
    return {}


def _semua():
    now = time.time()
    if _C["v"] is None or now - _C["t"] > _TTL:
        _C["v"] = _baca_semua()
        _C["t"] = now
    return _C["v"]


def max_per_sekolah(kod_ppd):
    """Maksimum guru sekolah yang sama di satu pusat bagi PPD ini (lalai 3)."""
    return _semua().get(str(kod_ppd or "").upper().strip(), MAX_LALAI)


def simpan_max(kod_ppd, n):
    """Simpan nilai untuk satu PPD. Naikkan ralat jika jadual landing_config belum ada."""
    n = int(n)
    if not (MAX_MIN <= n <= MAX_MAKS):
        raise ValueError(f"Nilai mesti antara {MAX_MIN} dan {MAX_MAKS}")
    kod = str(kod_ppd).upper().strip()
    semasa = dict(_baca_semua())
    semasa[kod] = n
    _raw().table("landing_config").upsert({"id": _ID, "config": {"max_per_sekolah": semasa}}).execute()
    _C["v"] = semasa
    _C["t"] = time.time()
    return n
