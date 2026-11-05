# -*- coding: utf-8 -*-
"""tahun_sistem.py - Tahun peperiksaan semasa (dipaparkan di semua halaman, surat dan tajuk).

Disimpan dalam jadual `landing_config` (baris id=2, config={"tahun": 2027}) - TIADA jadual baharu diperlukan
selain `landing_config` yang sudah dibuat untuk Landing Page.
Jika jadual / baris tiada, tahun lalai digunakan (TAHUN_LALAI).
"""
import time

TAHUN_LALAI = 2026
_ID = 2
_TTL = 120
_C = {"t": 0.0, "v": None}


def _raw():
    from spm_core import _RAW  # import lewat supaya tiada kitaran import
    return _RAW


TEMPOH_LALAI = "14 Julai hingga 16 Julai"


def _baca():
    """Pulang dict tetapan {tahun, tempoh_penyelia}; lalai jika tiada."""
    out = {"tahun": TAHUN_LALAI, "tempoh_penyelia": TEMPOH_LALAI}
    try:
        res = _raw().table("landing_config").select("config").eq("id", _ID).limit(1).execute()
        rows = res.data or []
        if rows:
            cfg = rows[0].get("config")
            if isinstance(cfg, str):
                import json
                cfg = json.loads(cfg)
            cfg = cfg or {}
            t = int(cfg.get("tahun"))
            if 2000 <= t <= 2100:
                out["tahun"] = t
            if str(cfg.get("tempoh_penyelia") or "").strip():
                out["tempoh_penyelia"] = str(cfg["tempoh_penyelia"]).strip()
    except Exception:
        pass
    return out


def tetapan():
    now = time.time()
    if _C["v"] is None or now - _C["t"] > _TTL:
        _C["v"] = _baca()
        _C["t"] = now
    return _C["v"]


def tahun_semasa():
    """Tahun semasa (int). Di-cache 2 minit dalam proses; dikosongkan serta-merta apabila disimpan."""
    return tetapan()["tahun"]


def tempoh_penyelia():
    """Teks tempoh bertugas dalam surat penyelia kawasan, cth '14 Julai hingga 16 Julai'."""
    return tetapan()["tempoh_penyelia"]


def simpan_tetapan(tahun, tempoh=None):
    """Simpan tahun (dan tempoh penyelia). Naikkan ralat jika jadual belum ada."""
    t = int(tahun)
    if not (2000 <= t <= 2100):
        raise ValueError("Tahun tidak sah")
    cfg = {"tahun": t, "tempoh_penyelia": (tempoh or "").strip() or tempoh_penyelia()}
    _raw().table("landing_config").upsert({"id": _ID, "config": cfg}).execute()
    _C["v"] = cfg
    _C["t"] = time.time()
    return cfg


def simpan_tahun(tahun):
    return simpan_tetapan(tahun)["tahun"]
