-- JALANKAN SEKALI di Supabase > SQL Editor (data sedia ada automatik jadi tahun 2026)
DO $$ BEGIN IF to_regclass('public.bilik_kebal_master') IS NOT NULL THEN
  EXECUTE 'ALTER TABLE public.bilik_kebal_master ADD COLUMN IF NOT EXISTS tahun integer NOT NULL DEFAULT 2026';
  EXECUTE 'CREATE INDEX IF NOT EXISTS idx_bilik_kebal_master_tahun ON public.bilik_kebal_master(tahun)';
END IF; END $$;
DO $$ BEGIN IF to_regclass('public.cadangan_sup') IS NOT NULL THEN
  EXECUTE 'ALTER TABLE public.cadangan_sup ADD COLUMN IF NOT EXISTS tahun integer NOT NULL DEFAULT 2026';
  EXECUTE 'CREATE INDEX IF NOT EXISTS idx_cadangan_sup_tahun ON public.cadangan_sup(tahun)';
END IF; END $$;
DO $$ BEGIN IF to_regclass('public.guru_master') IS NOT NULL THEN
  EXECUTE 'ALTER TABLE public.guru_master ADD COLUMN IF NOT EXISTS tahun integer NOT NULL DEFAULT 2026';
  EXECUTE 'CREATE INDEX IF NOT EXISTS idx_guru_master_tahun ON public.guru_master(tahun)';
END IF; END $$;
DO $$ BEGIN IF to_regclass('public.pusat_master') IS NOT NULL THEN
  EXECUTE 'ALTER TABLE public.pusat_master ADD COLUMN IF NOT EXISTS tahun integer NOT NULL DEFAULT 2026';
  EXECUTE 'CREATE INDEX IF NOT EXISTS idx_pusat_master_tahun ON public.pusat_master(tahun)';
END IF; END $$;
DO $$ BEGIN IF to_regclass('public.surat_hantar_sekolah_asal') IS NOT NULL THEN
  EXECUTE 'ALTER TABLE public.surat_hantar_sekolah_asal ADD COLUMN IF NOT EXISTS tahun integer NOT NULL DEFAULT 2026';
  EXECUTE 'CREATE INDEX IF NOT EXISTS idx_surat_hantar_sekolah_asal_tahun ON public.surat_hantar_sekolah_asal(tahun)';
END IF; END $$;

-- Buang syarat UNIQUE lama (cth. unik pada IC / kod sahaja) supaya data yang sama boleh wujud pada tahun berbeza
DO $$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT con.conname, rel.relname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    JOIN pg_namespace n ON n.oid = rel.relnamespace
    WHERE n.nspname = 'public' AND con.contype = 'u'
      AND rel.relname IN ('bilik_kebal_master', 'cadangan_sup', 'guru_master', 'pusat_master', 'surat_hantar_sekolah_asal')
  LOOP
    EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', r.relname, r.conname);
  END LOOP;
  FOR r IN
    SELECT ic.relname AS idxname
    FROM pg_index ix
    JOIN pg_class ic ON ic.oid = ix.indexrelid
    JOIN pg_class t ON t.oid = ix.indrelid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE n.nspname = 'public' AND ix.indisunique AND NOT ix.indisprimary
      AND t.relname IN ('bilik_kebal_master', 'cadangan_sup', 'guru_master', 'pusat_master', 'surat_hantar_sekolah_asal')
      AND NOT EXISTS (SELECT 1 FROM pg_constraint c WHERE c.conindid = ix.indexrelid)
  LOOP
    EXECUTE format('DROP INDEX public.%I', r.idxname);
  END LOOP;
END $$;
