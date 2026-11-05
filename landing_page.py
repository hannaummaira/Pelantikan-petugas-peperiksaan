# -*- coding: utf-8 -*-
"""landing_page.py - Halaman sambutan sebelum pilih portal JPN/PPD + selenggara oleh JPN.

Simpan: jadual Supabase `landing_config` (1 baris id=1, lajur config jsonb).
Gambar pegawai disaiz semula (PIL) dan disimpan sebagai base64 dalam JSON.
"""
import base64, copy, html as _html, io, json
import streamlit as st
import streamlit.components.v1 as components
import spm_core as core
from tahun_sistem import tahun_semasa


def _thn(s):
    """Ganti tahun lama (2026) dalam teks dengan tahun semasa sistem (Selenggara Tahun)."""
    try:
        return str(s).replace("2026", str(tahun_semasa()))
    except Exception:
        return str(s)

N_PEGAWAI = 12
SQL_LANDING = """create table if not exists landing_config (
  id int primary key,
  config jsonb,
  updated_at timestamptz default now()
);
alter table landing_config disable row level security;"""

DEFAULT = {
    "tajuk": "Selamat Datang ke Sistem Pelantikan Petugas Negeri Selangor",
    "subtajuk": "Jabatan Pendidikan Negeri Selangor • Peperiksaan SPM 2026",
    "butang": "Klik Masuk ke Sistem →",
    "info": [
        {"ikon": "📢", "tajuk": "Pengumuman", "teks": "Semua PPD dan sekolah dimohon melengkapkan cadangan petugas mengikut tarikh yang ditetapkan."},
        {"ikon": "📅", "tajuk": "Tarikh Penting", "teks": "Kemas kini tarikh tutup cadangan SUP, kelulusan PPD dan pengeluaran surat lantikan di sini."},
        {"ikon": "📞", "tajuk": "Bantuan", "teks": "Sebarang masalah sila hubungi Sektor Pengurusan Akademik JPN Selangor."},
        {"ikon": "📘", "tajuk": "Panduan", "teks": "Rujuk manual pengguna untuk panduan SUP, PPD dan JPN."},
    ],
    "pegawai": [{"nama": "", "jawatan": "", "gambar": ""} for _ in range(N_PEGAWAI)],
}
DEFAULT["pegawai"][0] = {"nama": "DATIN WAN NOR ASHIKIN BINTI ABU KASSIM",
                         "jawatan": "Pengarah Pendidikan JPN Selangor", "gambar": ""}


def _esc(x):
    return _html.escape(str(x if x is not None else ""))


def _normalize(cfg):
    out = copy.deepcopy(DEFAULT)
    if isinstance(cfg, str):
        try: cfg = json.loads(cfg)
        except Exception: cfg = {}
    if not isinstance(cfg, dict):
        return out
    for k in ("tajuk", "subtajuk", "butang"):
        if str(cfg.get(k) or "").strip():
            out[k] = str(cfg[k])
    if isinstance(cfg.get("info"), list):
        info = []
        for b in cfg["info"][:8]:
            if isinstance(b, dict):
                info.append({"ikon": str(b.get("ikon") or ""), "tajuk": str(b.get("tajuk") or ""), "teks": str(b.get("teks") or "")})
        out["info"] = info
    if isinstance(cfg.get("pegawai"), list):
        peg = []
        for p in cfg["pegawai"][:N_PEGAWAI]:
            p = p if isinstance(p, dict) else {}
            peg.append({"nama": str(p.get("nama") or ""), "jawatan": str(p.get("jawatan") or ""), "gambar": str(p.get("gambar") or "")})
        while len(peg) < N_PEGAWAI:
            peg.append({"nama": "", "jawatan": "", "gambar": ""})
        out["pegawai"] = peg
    return out


@st.cache_data(ttl=300, show_spinner=False)
def load_config():
    """(config, ralat). Jika jadual belum ada -> lalai + mesej ralat."""
    try:
        res = core._RAW.table("landing_config").select("config").eq("id", 1).limit(1).execute()
        rows = res.data or []
        if rows:
            return _normalize(rows[0].get("config")), ""
        return _normalize(None), ""
    except Exception as e:
        return _normalize(None), str(e)


def save_config(cfg):
    """Simpan, kemudian baca semula terus dari DB (tanpa cache) untuk sahkan benar-benar tersimpan."""
    payload = {"id": 1, "config": cfg}
    core._RAW.table("landing_config").upsert(payload).execute()
    load_config.clear()
    res = core._RAW.table("landing_config").select("config").eq("id", 1).limit(1).execute()
    rows = res.data or []
    if not rows:
        raise RuntimeError("Simpan tidak berjaya: baris tidak ditemui selepas simpan (semak RLS / jadual landing_config).")
    cfg2 = _normalize(rows[0].get("config"))
    n_asal = sum(1 for p in cfg.get("pegawai", []) if p.get("gambar"))
    n_db = sum(1 for p in cfg2["pegawai"] if p.get("gambar"))
    if n_db < n_asal:
        raise RuntimeError(f"Hanya {n_db} daripada {n_asal} gambar tersimpan dalam pangkalan data.")


def proses_gambar(data: bytes, lebar=360, tinggi=450):
    """Potong ke nisbah 4:5 (tengah) & kecilkan -> data URI JPEG."""
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    nisbah = lebar / tinggi
    w, h = im.size
    if w / h > nisbah:
        nw = int(h * nisbah); x0 = (w - nw) // 2
        im = im.crop((x0, 0, x0 + nw, h))
    else:
        nh = int(w / nisbah); y0 = max(0, int((h - nh) * 0.15))  # condong ke atas (muka)
        im = im.crop((0, y0, w, y0 + nh))
    im = im.resize((lebar, tinggi))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


# ------------------------------------------------------------------ hero (korporat)
def _logo_html(h=44):
    """Jata Negara (daripada spm_core.JATA_B64); jika tiada, kotak 'JPN' lama."""
    b64 = getattr(core, "JATA_B64", "") or ""
    if b64:
        return (f'<img src="data:image/png;base64,{b64}" style="height:{h}px;width:auto;margin-right:12px;'
                f'background:#fff;border-radius:8px;padding:3px">')
    return '<span class="logo">JPN</span>'


def hero_html(cfg, solid=False):
    """Hero sebagai HTML+CSS biasa (tanpa iframe/JS) supaya saiznya ikut skrin & tidak bertindih dengan elemen lain."""
    import math
    items = [p for p in cfg["pegawai"] if (p.get("nama") or p.get("jawatan") or p.get("gambar"))]
    n = len(items)
    cards = []
    for k, p in enumerate(items):
        if p.get("gambar"):
            img = f'<img src="{_esc(p["gambar"])}" alt="">'
        else:
            ini = "".join(w[0] for w in (p.get("nama") or "?").split()[:2]).upper()
            img = f'<div class="lph-ph">{_esc(ini)}</div>'
        tf = f"rotateY({k*360/n:.3f}deg) translateZ(var(--R))" if n > 1 else "none"
        cards.append(f'<div class="lph-card" style="transform:{tf}">{img}<div class="lph-cap">'
                     f'<div class="lph-nm">{_esc(p.get("nama"))}</div><div class="lph-jw">{_esc(p.get("jawatan"))}</div></div></div>')
    # jejari R = W*A + B  (A,B bergantung pada bilangan kad)
    if n > 2:
        t = math.tan(math.pi / n)
        A = 0.5 / t
        B = 12 / t
    else:
        A, B = 0.62, 14
    if solid:
        W = "150px"
        H = "560px"
    else:
        W = f"clamp(96px,min(calc((100vh - 380px)*0.5),calc((100vw - 60px - {2*B:.1f}px)/{2*A+1:.3f})),230px)"
        H = "max(430px,calc(100vh - 272px))"
    spin = "animation:lphspin 48s linear infinite;" if n > 1 else ""
    ring = (f'<div class="lph-stage"><div class="lph-pivot"><div class="lph-ring">{"".join(cards)}</div></div></div>' if n else "")
    logo = _logo_html(38)
    solid_css = "border-radius:18px;border:1px solid rgba(201,162,39,.45);background:linear-gradient(160deg,#0b2d63,#06193a 70%);" if solid else ""
    html = f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;500;600;700&display=swap');
.lph{{--gold:#c9a227;--gold2:#e9d28a;--w:{W};--R:calc(var(--w)*{A:.4f} + {B:.1f}px);
 position:relative;height:{H};display:flex;flex-direction:column;overflow:hidden;color:#fff;font-family:Inter,Arial,sans-serif;{solid_css}}}
.lph:before{{content:"";position:absolute;inset:0;opacity:.07;background-image:repeating-linear-gradient(45deg,#fff 0 1px,transparent 1px 22px);pointer-events:none}}
.lph-top{{position:relative;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;padding:8px clamp(16px,3vw,56px);
 border-bottom:1px solid rgba(201,162,39,.35);background:rgba(3,12,30,.35)}}
.lph-org{{display:flex;align-items:center}}
.lph-n{{font-weight:700;font-size:clamp(12px,1vw,17px);letter-spacing:.08em;color:#fff}}
.lph-s{{font-size:clamp(9.5px,.75vw,13px);letter-spacing:.14em;color:var(--gold2);margin-top:2px}}
.lph-r{{font-size:clamp(10.5px,.8vw,14px);letter-spacing:.1em;color:var(--gold2);text-transform:uppercase}}
.lph-hd{{position:relative;text-align:center;padding:clamp(8px,1.6vh,20px) 16px 0}}
.lph-chip{{display:inline-block;font-size:clamp(10px,.8vw,13px);font-weight:600;letter-spacing:.28em;color:var(--gold2);text-transform:uppercase;padding:3px 14px;border:1px solid rgba(201,162,39,.6);border-radius:999px}}
.lph-h1{{font-family:'Playfair Display',Georgia,serif;font-weight:700;font-size:clamp(21px,2.9vw,52px);line-height:1.15;margin:clamp(4px,1vh,12px) auto 0;max-width:94%;color:#f3e3a8}}
.lph-rule{{width:90px;height:2px;margin:clamp(5px,1vh,12px) auto clamp(3px,.7vh,8px);background:linear-gradient(90deg,transparent,var(--gold),transparent)}}
.lph-sub{{font-size:clamp(11.5px,1vw,18px);letter-spacing:.06em;color:#c9d6ee}}
.lph-stage{{position:relative;flex:1;min-height:0;perspective:calc(var(--w)*7.3);display:flex;align-items:center;justify-content:center;padding-top:2vh}}
.lph-pivot{{position:relative;width:var(--w);height:calc(var(--w)*1.667);transform-style:preserve-3d;transform:translateZ(calc(var(--R)*-1))}}
.lph-ring{{position:relative;width:100%;height:100%;transform-style:preserve-3d;{spin}}}
.lph-stage:hover .lph-ring{{animation-play-state:paused}}
@keyframes lphspin{{from{{transform:rotateY(0)}}to{{transform:rotateY(-360deg)}}}}
.lph-card{{position:absolute;left:0;top:0;width:100%;height:100%;border-radius:calc(var(--w)*.08);overflow:hidden;text-align:center;display:flex;flex-direction:column;
 background:linear-gradient(180deg,#0f2a57,#071a3a);border:1px solid var(--gold);box-shadow:0 10px 28px rgba(0,0,0,.45),0 0 0 3px rgba(201,162,39,.12);backface-visibility:hidden}}
.lph-card img,.lph-ph{{width:100%;flex:0 0 73%;min-height:0;object-fit:cover;display:block;margin:0;border-bottom:2px solid var(--gold)}}
.lph-ph{{background:linear-gradient(135deg,#123a7a,#0a2250);color:var(--gold2);font-family:'Playfair Display',serif;font-weight:700;font-size:calc(var(--w)*.27);display:flex;align-items:center;justify-content:center}}
.lph-cap{{padding:calc(var(--w)*.035) calc(var(--w)*.04);flex:1;display:flex;flex-direction:column;justify-content:center}}
.lph-nm{{font-size:calc(var(--w)*.066);font-weight:700;color:#fff;line-height:1.25;letter-spacing:.02em}}
.lph-jw{{font-size:calc(var(--w)*.058);color:var(--gold2);margin-top:3px;line-height:1.25;letter-spacing:.03em}}
</style>
<div class="lph"><div class="lph-top"><div class="lph-org">{logo}<div><div class="lph-n">JABATAN PENDIDIKAN NEGERI SELANGOR</div>
<div class="lph-s">KEMENTERIAN PENDIDIKAN MALAYSIA</div></div></div><div class="lph-r">Peperiksaan SPM {_thn("2026")}</div></div>
<div class="lph-hd"><span class="lph-chip">Portal Rasmi</span><div class="lph-h1">{_esc(_thn(cfg['tajuk']))}</div><div class="lph-rule"></div>
<div class="lph-sub">{_esc(_thn(cfg['subtajuk']))}</div></div>{ring}</div>"""
    # elak Markdown menganggap baris berjarak/berinden sebagai blok kod
    return "\n".join(l.strip() for l in html.splitlines() if l.strip())


def render_hero(cfg, solid=False):
    st.markdown(hero_html(cfg, solid), unsafe_allow_html=True)


LANDING_CSS = """<style>
.lp-info{background:#fff;border:1px solid #dfe5f1;border-top:3px solid #c9a227;border-radius:10px;padding:16px 16px 14px;
 min-height:132px;box-shadow:0 4px 14px rgba(6,25,58,.07);margin-bottom:12px}
.lp-info .t{font-weight:700;color:#06193a;font-size:14px;letter-spacing:.02em}
.lp-info .x{color:#4a5873;font-size:12.5px;margin-top:7px;line-height:1.5}
.st-key-land_cta button{background:linear-gradient(180deg,#e0bd4a,#b8901c)!important;color:#06193a!important;border:1px solid #8a6b10!important;
 font-weight:800!important;letter-spacing:.06em;padding:.85rem 1rem!important;border-radius:10px!important;box-shadow:0 6px 18px rgba(184,144,28,.35)}
.st-key-land_cta button:hover{filter:brightness(1.06);transform:translateY(-1px)}
</style>"""

LANDING_FULL_CSS = """<style>
[data-testid="stAppViewContainer"],.stApp{background:radial-gradient(1400px 600px at 50% -5%,#1b4a9a 0%,rgba(27,74,154,0) 60%),
 linear-gradient(160deg,#0b2d63 0%,#06193a 65%,#041229 100%) fixed!important;color:#c9d6ee}
header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
[data-testid="stMainBlockContainer"],.block-container{max-width:100%!important;padding:0 0 1rem 0!important}
[data-testid="stMain"] [data-testid="stVerticalBlock"]{gap:.5rem}
.st-key-land_body{padding:0 clamp(16px,3vw,56px);margin:0 auto}
.st-key-land_body .lp-info{background:rgba(255,255,255,.07);border:1px solid rgba(201,162,39,.4);border-top:3px solid #c9a227;
 min-height:clamp(84px,11vh,140px);padding:12px 16px 10px;margin-bottom:4px;box-shadow:0 8px 24px rgba(0,0,0,.25)}
.st-key-land_body .lp-info .t{color:#fff;font-size:clamp(15px,1.25vw,22px)}
.st-key-land_body .lp-info .x{color:#d3def2;font-size:clamp(13px,1.05vw,18px);margin-top:5px;line-height:1.45}
.st-key-land_cta button{padding:.6rem 1rem!important;font-size:clamp(14px,1.1vw,18px)}
.stApp p,.stApp span,.stApp label{color:#c9d6ee}
.st-key-land_cta button p,.st-key-land_cta button span{color:#06193a!important}
</style>"""


def info_cards(cfg):
    if not cfg["info"]:
        return
    cols = st.columns(min(4, len(cfg["info"])), gap="small")
    for i, b in enumerate(cfg["info"]):
        with cols[i % len(cols)]:
            st.markdown(f'<div class="lp-info"><div class="t">{_esc(b["ikon"])} {_esc(_thn(b["tajuk"]))}</div>'
                        f'<div class="x">{_esc(_thn(b["teks"]))}</div></div>', unsafe_allow_html=True)


# ------------------------------------------------------------------ halaman awam
def render_landing():
    cfg, err = load_config()
    st.markdown(LANDING_CSS + LANDING_FULL_CSS, unsafe_allow_html=True)
    render_hero(cfg)
    with st.container(key="land_body"):
        info_cards(cfg)
        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            with st.container(key="land_cta"):
                if st.button(cfg["butang"], key="btn_masuk_sistem", use_container_width=True):
                    st.session_state["masuk_sistem"] = True
                    st.rerun()


# ------------------------------------------------------------------ admin JPN
def render_admin_landing():
    st.header("🏠 Selenggara Landing Page")
    st.caption("Halaman sambutan yang dipaparkan sebelum pilihan JPN / PPD.")
    cfg, err = load_config()
    if err:
        st.error("Jadual `landing_config` belum sedia / tidak boleh dibaca. Jalankan SQL ini di Supabase (SQL Editor), kemudian muat semula:")
        st.code(SQL_LANDING, language="sql")
        st.caption(f"Butiran: {err[:200]}")

    n_img = sum(1 for p in cfg["pegawai"] if p.get("gambar"))
    st.info(f"Status semasa dalam pangkalan data: {n_img} gambar pegawai tersimpan.")

    t1, t2, t3 = st.tabs(["📝 Kandungan & Kotak Info", "🧑‍💼 12 Pegawai (Gambar)", "👁 Pratonton"])

    with t1:
        with st.form("frm_landing_kandungan"):
            tajuk = st.text_input("Tajuk utama", cfg["tajuk"])
            sub = st.text_input("Sub-tajuk", cfg["subtajuk"])
            butang = st.text_input("Teks butang masuk", cfg["butang"])
            st.markdown("**Kotak maklumat** (kosongkan tajuk & teks untuk membuang kotak)")
            info = []
            for i in range(4):
                b = cfg["info"][i] if i < len(cfg["info"]) else {"ikon": "", "tajuk": "", "teks": ""}
                c1, c2 = st.columns([1, 5])
                ik = c1.text_input("Ikon", b["ikon"], key=f"li_ik{i}")
                tj = c2.text_input(f"Tajuk kotak {i+1}", b["tajuk"], key=f"li_tj{i}")
                tx = st.text_area(f"Teks kotak {i+1}", b["teks"], height=70, key=f"li_tx{i}")
                if tj.strip() or tx.strip():
                    info.append({"ikon": ik, "tajuk": tj, "teks": tx})
            if st.form_submit_button("💾 Simpan Kandungan", type="primary"):
                new = copy.deepcopy(cfg)
                new.update({"tajuk": tajuk.strip() or DEFAULT["tajuk"], "subtajuk": sub, "butang": butang.strip() or DEFAULT["butang"], "info": info})
                try:
                    save_config(new)
                    st.success("✅ Kandungan disimpan.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal simpan: {e}")
                    st.code(SQL_LANDING, language="sql")

    with t2:
        st.caption("Muat naik gambar (JPG/PNG, disaran potret). Gambar dipotong 4:5 dan dikecilkan automatik. "
                   "Slot kosong tidak dipaparkan. Carousel berpusing automatik dan berhenti bila tetikus di atasnya.")
        with st.form("frm_landing_pegawai"):
            hasil = []
            for i in range(N_PEGAWAI):
                p = cfg["pegawai"][i]
                with st.container(border=True):
                    c0, c1, c2 = st.columns([1, 3, 3])
                    if p["gambar"]:
                        c0.markdown(f'<img src="{_esc(p["gambar"])}" style="width:70px;border-radius:6px">', unsafe_allow_html=True)
                    else:
                        c0.markdown(f"**#{i+1}**")
                    nama = c1.text_input(f"Nama #{i+1}", p["nama"], key=f"lp_n{i}")
                    jaw = c2.text_input(f"Jawatan #{i+1}", p["jawatan"], key=f"lp_j{i}")
                    f = st.file_uploader(f"Gambar #{i+1}", type=["jpg", "jpeg", "png", "webp"], key=f"lp_f{i}")
                    buang = st.checkbox("Buang gambar sedia ada", key=f"lp_b{i}") if p["gambar"] else False
                hasil.append((nama, jaw, f, buang, p["gambar"]))
            if st.form_submit_button("💾 Simpan Pegawai", type="primary"):
                peg, ralat = [], []
                for i, (nama, jaw, f, buang, lama) in enumerate(hasil):
                    g = "" if buang else lama
                    if f is not None:
                        try:
                            g = proses_gambar(f.getvalue())
                        except Exception as e:
                            ralat.append(f"#{i+1}: {e}")
                    peg.append({"nama": nama.strip(), "jawatan": jaw.strip(), "gambar": g})
                new = copy.deepcopy(cfg); new["pegawai"] = peg
                try:
                    save_config(new)
                    for m in ralat:
                        st.warning(f"Gambar gagal diproses - {m}")
                    st.success(f"✅ Pegawai disimpan ({sum(1 for p in peg if p['gambar'])} gambar). Muat semula halaman untuk melihat status terkini.")
                except Exception as e:
                    st.error(f"Gagal simpan: {e}")
                    st.code(SQL_LANDING, language="sql")

    with t3:
        st.markdown(LANDING_CSS, unsafe_allow_html=True)
        render_hero(cfg, solid=True)
        info_cards(cfg)
        st.button(cfg["butang"], disabled=True, key="prev_btn")
