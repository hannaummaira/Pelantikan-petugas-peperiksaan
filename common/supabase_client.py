
import streamlit as st
from supabase import create_client
from .config import SUPABASE_URL, SUPABASE_KEY, TAHUN_TABLES

@st.cache_resource
def get_supabase_raw():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data(ttl=300, show_spinner=False)
def lajur_tahun_sedia(nama_jadual: str) -> bool:
    try:
        get_supabase_raw().table(nama_jadual).select("tahun").limit(1).execute()
        return True
    except Exception:
        return False

def _tambah_tahun_payload(data, tahun):
    if isinstance(data, list):
        return [dict(d, tahun=d.get("tahun", tahun)) if isinstance(d, dict) else d for d in data]
    if isinstance(data, dict):
        return dict(data, tahun=data.get("tahun", tahun))
    return data

class _JadualTahun:
    def __init__(self, jadual, tahun):
        self._t = jadual
        self._y = tahun
    def select(self, *a, **k):
        return self._t.select(*a, **k).eq("tahun", self._y)
    def update(self, *a, **k):
        return self._t.update(*a, **k).eq("tahun", self._y)
    def delete(self, *a, **k):
        return self._t.delete(*a, **k).eq("tahun", self._y)
    def insert(self, data, *a, **k):
        return self._t.insert(_tambah_tahun_payload(data, self._y), *a, **k)
    def upsert(self, data, *a, **k):
        return self._t.upsert(_tambah_tahun_payload(data, self._y), *a, **k)
    def __getattr__(self, n):
        return getattr(self._t, n)

class TahunClient:
    def __init__(self, raw, tahun):
        self._raw = raw
        self._tahun = tahun
    def table(self, nama):
        t = self._raw.table(nama)
        if nama in TAHUN_TABLES and lajur_tahun_sedia(nama):
            return _JadualTahun(t, self._tahun)
        return t
    def __getattr__(self, n):
        return getattr(self._raw, n)

def get_supa():
    from .config import tahun_aktif
    raw = get_supabase_raw()
    return TahunClient(raw, tahun_aktif())

@st.cache_data(ttl=60, show_spinner=False)
def status_migrasi_tahun():
    return {t: lajur_tahun_sedia(t) for t in sorted(TAHUN_TABLES)}

SQL_MIGRASI_TAHUN = """-- JALANKAN SEKALI di Supabase > SQL Editor
""" + "\n".join(
    f"DO $$ BEGIN IF to_regclass('public.{t}') IS NOT NULL THEN\n"
    f"  EXECUTE 'ALTER TABLE public.{t} ADD COLUMN IF NOT EXISTS tahun integer NOT NULL DEFAULT 2026';\n"
    f"  EXECUTE 'CREATE INDEX IF NOT EXISTS idx_{t}_tahun ON public.{t}(tahun)';\n"
    f"END IF; END $$;"
    for t in sorted(TAHUN_TABLES)
) + """
DO $$ DECLARE r record; BEGIN
  FOR r IN SELECT con.conname, rel.relname FROM pg_constraint con
  JOIN pg_class rel ON rel.oid = con.conrelid JOIN pg_namespace n ON n.oid = rel.relnamespace
  WHERE n.nspname='public' AND con.contype='u' AND rel.relname IN ('bilik_kebal_master','cadangan_sup','guru_master','pusat_master','surat_hantar_sekolah_asal') LOOP
    EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', r.relname, r.conname);
  END LOOP;
  FOR r IN SELECT ic.relname AS idxname FROM pg_index ix JOIN pg_class ic ON ic.oid=ix.indexrelid JOIN pg_class t ON t.oid=ix.indrelid JOIN pg_namespace n ON n.oid=t.relnamespace
  WHERE n.nspname='public' AND ix.indisunique AND NOT ix.indisprimary AND t.relname IN ('bilik_kebal_master','cadangan_sup','guru_master','pusat_master','surat_hantar_sekolah_asal')
  AND NOT EXISTS (SELECT 1 FROM pg_constraint c WHERE c.conindid=ix.indexrelid) LOOP
    EXECUTE format('DROP INDEX public.%I', r.idxname); END LOOP;
END $$;
"""
