"""
no_surat.py - Format no rujukan surat berjilid.

    JPNS.SPP 600-7/1/1 (1) ... (100)
    JPNS.SPP 600-7/1/1 JLD 2 (1) ... (100)
    JPNS.SPP 600-7/1/1 JLD 3 (1) ...

Setiap siri = (PPD, no rujukan fail). Turutan global n (1,2,3...) -> jilid = (n-1)//100+1, kurungan = (n-1)%100+1.
Siri dikesan daripada no surat sedia ada PPD itu sendiri, jadi setiap PPD (dan setiap no rujukan fail) ada turutan berasingan.
"""
import json
import re

RUJ_LALAI = "JPNS.SPP 600-7/1/1"
SAIZ_JILID = 100


def format_no(ruj, n):
    """n = turutan global bermula 1. Jilid 1 tanpa 'JLD'."""
    ruj = " ".join(str(ruj or RUJ_LALAI).split())
    n = max(1, int(n))
    jilid, kur = (n - 1) // SAIZ_JILID + 1, (n - 1) % SAIZ_JILID + 1
    return f"{ruj} ({kur})" if jilid == 1 else f"{ruj} JLD {jilid} ({kur})"


def parse_no(no, ruj):
    """Pulang turutan global jika no surat tergolong dalam siri `ruj`, jika tidak None."""
    ruj = " ".join(str(ruj or RUJ_LALAI).split())
    m = re.match(r"^\s*" + re.escape(ruj) + r"(?:\s+JLD\s+(\d+))?\s*\(\s*(\d+)\s*\)\s*$", " ".join(str(no or "").split()), re.I)
    if not m:
        return None
    jilid = int(m.group(1)) if m.group(1) else 1
    return (jilid - 1) * SAIZ_JILID + int(m.group(2))


def ruj_dari_no(no):
    """Ekstrak no rujukan fail daripada no surat berjilid, atau None."""
    m = re.match(r"^\s*(.*?)(?:\s+JLD\s+\d+)?\s*\(\s*\d+\s*\)\s*$", " ".join(str(no or "").split()), re.I)
    return m.group(1).strip() if m and m.group(1).strip() else None


def _senarai_no(df):
    """Semua no surat (kolum no_surat + data.SURAT_NO_JANA + data.surat_no) dalam DataFrame cadangan."""
    out = []
    if df is None or getattr(df, "empty", True):
        return out
    for _, r in df.iterrows():
        d = r.get("data")
        if isinstance(d, str):
            try:
                d = json.loads(d)
            except Exception:
                d = {}
        if not isinstance(d, dict):
            d = {}
        for v in (r.get("no_surat"), r.get("NO_SURAT"), d.get("SURAT_NO_JANA"), d.get("no_surat")):
            if v and str(v).strip() not in ("", "None", "nan"):
                out.append(str(v).strip())
    return out


def max_no(df, ruj):
    """Turutan global tertinggi yang sudah digunakan dalam siri `ruj` (0 jika belum ada). df = rekod PPD itu sahaja."""
    mx = 0
    for no in _senarai_no(df):
        n = parse_no(no, ruj)
        if n:
            mx = max(mx, n)
    return mx


def ruj_terkini(df):
    """No rujukan fail daripada no surat berjilid terakhir PPD ini, atau lalai."""
    for no in reversed(_senarai_no(df)):
        r = ruj_dari_no(no)
        if r and parse_no(no, r):
            return r
    return RUJ_LALAI
