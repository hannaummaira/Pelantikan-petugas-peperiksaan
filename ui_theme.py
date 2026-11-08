# -*- coding: utf-8 -*-
"""
ui_theme.py - Susun atur & gaya seragam
"""
from tahun_sistem import tahun_semasa
import datetime
import html as _html
import json
try:
    import streamlit as st
except ModuleNotFoundError:
    class _Dummy:
        def __getattr__(self, name):
            return lambda *a, **k: None
    st = _Dummy()

try:
    import spm_core as core
    from spm_core import PPD_MAP, SCOPE, get_pusat_df
except Exception:
    try:
        import spm_core_1 as core
        from spm_core_1 import PPD_MAP, SCOPE, get_pusat_df
    except Exception:
        core = None
        PPD_MAP = {}
        SCOPE = {}
        def get_pusat_df():
            return None

MY_TZ = datetime.timezone(datetime.timedelta(hours=8))
def now_my():
    return datetime.datetime.now(MY_TZ).strftime("%d/%m %H:%M:%S")
def esc(x):
    return _html.escape(str(x if x is not None else ""))
def kc(key):
    try:
        return st.container(key=key)
    except TypeError:
        return st.container()

THEME_CSS = """
<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {display:none!important}
.stApp {background:#e3f2fd!important}
.block-container {max-width:1600px!important;padding-top:.6rem!important;padding-bottom:1rem!important}
.sup-box {background:#fff;border:1px solid #c5d6e8;border-radius:4px;box-shadow:0 1px 3px rgba(0,0,0,.06);overflow:hidden;margin-bottom:8px}
.sup-id {font-size:11px;font-weight:700;line-height:1.35;letter-spacing:.03em;color:#0d47a1;text-transform:uppercase}
.sup-pusat {margin-top:8px;background:#e8f0fe;border:1px solid #90caf9;border-radius:4px;padding:8px}
.sup-pusat .l {font-size:10px;font-weight:600;letter-spacing:.1em;color:#0d47a1}
.sup-pusat .v {font-size:13px;font-weight:800;color:#0d47a1;margin-top:2px}
.sup-last {font-size:10px;color:#5f6f85;margin-top:6px}
.sup-red {font-size:9px;line-height:11px;color:#d32f2f;font-weight:500;margin:2px 0 8px}
.sup-banner {background:#0d47a1;color:#fff;padding:10px 16px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px}
.sup-banner .t {font-size:13px;font-weight:700;letter-spacing:.03em}
.sup-pill {display:inline-flex;align-items:center;gap:6px;background:#42a5f5;color:#fff;font-size:10px;font-weight:700;padding:4px 10px;border-radius:999px;letter-spacing:.1em;margin-left:12px}
.sup-pill i {width:6px;height:6px;background:#fff;border-radius:50%;display:inline-block}
.sup-right {font-size:11px;opacity:.8}
.sup-info {background:#fff;padding:8px 16px;display:flex;flex-wrap:wrap;gap:4px 16px;font-size:11px;border-bottom:1px solid #c5d6e8;align-items:center}
.sup-info b {color:#5f6f85;font-weight:700}
.sup-info .sep {color:#90a4b8}
.sup-online {margin-left:auto;display:inline-flex;align-items:center;gap:6px;font-size:10px;font-weight:500;color:#2e7d32;background:#e8f5e9;border:1px solid #a5d6a7;padding:2px 8px;border-radius:999px}
.sup-online i {width:8px;height:8px;background:#43a047;border-radius:50%;display:inline-block}
.sup-note {background:#fff;border:1px solid #c5d6e8;border-radius:4px;padding:10px;font-size:10px;line-height:1.4;margin-top:12px}
.sup-note b {color:#0d47a1;display:block;margin-bottom:4px}
.sup-note span {color:#5f6f85}
.sup-sub-h {background:#0d47a1;color:#fff;font-size:11px;font-weight:700;letter-spacing:.1em;padding:6px 8px;border-radius:4px 4px 0 0}
.sup-card-h {background:#e3f2fd;border-bottom:1px solid #c5d6e8;padding:8px 12px;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px}
.sup-card-h .t {font-size:12px;font-weight:800;letter-spacing:.03em;color:#0d47a1}
.sup-chip {font-size:10px;background:#fff;border:1px solid #90caf9;padding:4px 8px;border-radius:4px;font-weight:700;color:#0d47a1}
.sup-tiles {padding:12px;display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.sup-tile {background:#fff;border:1px solid #c5d6e8;border-radius:4px;padding:12px;text-align:center}
.sup-tile.hl {background:#e3f2fd;border-color:#90caf9}
.sup-tile .l {font-size:11px;font-weight:700;letter-spacing:.1em;color:#5f6f85}
.sup-tile.hl .l {color:#0d47a1}
.sup-tile .n {font-size:28px;font-weight:800;color:#0d47a1;line-height:1;margin-top:4px}
.sup-tile .s {font-size:10px;color:#5f6f85;margin-top:4px}
.sup-tile.hl .s {color:#1565c0;font-weight:500}
[data-testid="stMetric"] {background:#fff;border:1px solid #c5d6e8;border-radius:4px;padding:10px 12px!important}
[data-testid="stMetricLabel"] p {font-size:11px!important;font-weight:700!important;color:#5f6f85!important;text-transform:none}
[data-testid="stMetricValue"] {font-size:22px!important;font-weight:800!important;color:#0d47a1!important}
.st-key-shellmenu, .st-key-shellsub {gap:4px!important}
.st-key-shellmenu [class*="st-key-flymenu_"] button {width:100%;justify-content:flex-start!important;text-align:left!important;background:#0d47a1!important;color:#fff!important;border:none!important;border-left:3px solid transparent!important;border-radius:0 4px 4px 0!important;padding:8px 12px!important;min-height:0!important;box-shadow:none!important;transform:none!important}
.st-key-shellmenu [class*="st-key-flymenu_"] button * {color:#fff!important;font-size:12px!important;font-weight:600!important;text-align:left!important}
.st-key-shellmenu [class*="st-key-flymenu_"] button:hover {background:#0a367e!important}
.st-key-shellmenu [class*="st-key-flymenu_"] button[kind="primary"],
.st-key-shellmenu [class*="st-key-flymenu_"] [data-testid="stBaseButton-primary"] {border-left:3px solid #ffca28!important;box-shadow:0 2px 8px rgba(13,71,161,.3)!important;background:#0d47a1!important}
.st-key-shellsub {background:#fff;border:1px solid #c5d6e8;border-top:0;border-radius:0 0 4px 4px}
.st-key-shellsub [class*="st-key-flysub_"] button {width:100%;justify-content:flex-start!important;text-align:left!important;background:#1565c0!important;border:none!important;border-radius:0!important;border-bottom:1px solid #0d47a1!important;border-left:3px solid transparent!important;padding:9px 12px!important;min-height:0!important;box-shadow:none!important;transform:none!important}
.st-key-shellsub [class*="st-key-flysub_"] button * {color:#ffffff!important;-webkit-text-fill-color:#ffffff!important;font-size:12px!important;font-weight:600!important;text-align:left!important}
.st-key-shellsub [class*="st-key-flysub_"] button:hover {background:#0d47a1!important}
.st-key-shellsub [class*="st-key-flysub_"] button[kind="primary"],
.st-key-shellsub [class*="st-key-flysub_"] [data-testid="stBaseButton-primary"] {background:#0a2a66!important;border-left:3px solid #ffca28!important;box-shadow:none!important}
.st-key-shellsub [class*="st-key-flysub_"] button[kind="primary"] *,
.st-key-shellsub [class*="st-key-flysub_"] [data-testid="stBaseButton-primary"] * {color:#ffffff!important;-webkit-text-fill-color:#ffffff!important;font-weight:800!important}
.st-key-suprefresh .stButton>button {width:100%;background:#0d47a1!important;border:none!important;border-radius:4px!important;box-shadow:0 2px 0 #082c62!important;padding:10px 0!important;min-height:0!important}
.st-key-suprefresh .stButton>button * {color:#fff!important;font-size:12px!important;font-weight:800!important;letter-spacing:.03em}
.land-top {background:#0d47a1;color:#fff;border-radius:6px;padding:10px 18px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}
.land-top .logo {width:34px;height:34px;background:#fff;border-radius:8px;display:inline-flex;align-items:center;justify-content:center;color:#0d47a1;font-weight:800;font-size:13px;margin-right:10px}
.land-top .n {font-weight:700;font-size:13px;letter-spacing:.02em}
.land-top .s {font-size:10px;opacity:.8;letter-spacing:.05em}
.land-top .r {font-size:11px;opacity:.9}
.land-head {background:#fff;border:1px solid #dbe3f0;border-radius:14px;padding:22px 24px;margin:12px 0;display:flex;flex-wrap:wrap;gap:18px;justify-content:space-between;align-items:flex-end}
.land-chip {display:inline-flex;align-items:center;gap:8px;padding:4px 12px;border-radius:999px;background:#e3eefe;border:1px solid #b7cdef;font-size:11px;font-weight:600;color:#0d47a1;letter-spacing:.04em;text-transform:uppercase}
.land-chip i {width:6px;height:6px;background:#0d47a1;border-radius:50%;display:inline-block}
.land-h1 {font-size:32px;font-weight:800;letter-spacing:-.02em;line-height:1.05;color:#0d47a1;margin:10px 0 4px}
.land-h1 span {color:#13233f}
.land-p {font-size:14px;color:#5f708c;font-weight:500}
.land-stats {display:grid;grid-template-columns:repeat(3,110px);gap:10px}
.land-stat {border-radius:14px;padding:12px;border:1px solid #dbe3f0;background:#f5f7fb}
.land-stat .l {font-size:10px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:#5f708c}
.land-stat .v {font-size:22px;font-weight:800;color:#13233f;line-height:1;margin-top:4px}
.land-stat .s {font-size:10px;color:#5f708c;margin-top:3px}
.sch-card {padding:2px 2px 0}
.sch-row {display:flex;justify-content:space-between;align-items:flex-start;gap:8px}
.sch-ico {width:38px;height:38px;border-radius:10px;background:#e3eefe;display:inline-flex;align-items:center;justify-content:center;font-size:18px;margin-right:10px}
.sch-code {font-size:11px;font-weight:800;color:#0d47a1;letter-spacing:.04em}
.sch-sub {font-size:10px;color:#5f708c}
.sch-name {font-size:15px;font-weight:700;color:#13233f;margin:10px 0 6px;line-height:1.25;min-height:38px}
.sch-meta {font-size:11px;color:#5f708c;margin-bottom:6px}
.badge {display:inline-flex;align-items:center;gap:6px;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700;border:1px solid}
.badge.ok {background:#dcfce7;border-color:#bbf7d0;color:#166534}
.badge.warn {background:#fef3c7;border-color:#fde68a;color:#92400e}
.badge i {width:6px;height:6px;border-radius:50%;display:inline-block}
.badge.ok i {background:#16a34a}.badge.warn i {background:#d97706}
@media (max-width:900px) {.sup-tiles {grid-template-columns:repeat(2,1fr)} .sup-right {display:none} .land-stats{grid-template-columns:repeat(3,1fr);width:100%}}
</style>
"""

KONTRAS_CSS = """
<style>
html, body, .stApp, [data-testid="stAppViewContainer"] {color:#0b1b33!important}
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {color:#0b1b33;font-size:15px;line-height:1.5}
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label, label {color:#0b1b33!important;font-weight:700!important;font-size:14px!important}
[data-testid="stCaptionContainer"] p, .stCaption, small {color:#1e293b!important;font-size:13px!important;font-weight:500!important;opacity:1!important}
[data-testid="stMetricLabel"] p {color:#1e293b!important;font-size:12px!important;font-weight:700!important}
[data-testid="stMetricValue"] {color:#0a2a66!important}
[data-baseweb="tab"] {font-weight:700!important;color:#0a2a66!important}
[data-testid="stExpander"] summary p {font-weight:700!important;color:#0a2a66!important}
input, textarea, [data-baseweb="select"] > div, [data-baseweb="input"] {color:#0b1b33!important;background:#ffffff!important;border-color:#475569!important}
[data-baseweb="select"] *, [data-baseweb="input"] * {color:#0b1b33!important}
.stButton > button,
.stDownloadButton > button,
[data-testid="stFormSubmitButton"] > button,
button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-secondary"] {background:#0d47a1!important;border:2px solid #0a367e!important;color:#ffffff!important;font-weight:700!important}
.stButton > button *,
.stDownloadButton > button *,
button[data-testid="stBaseButton-primary"] *,
button[data-testid="stBaseButton-secondary"] * {color:#ffffff!important;-webkit-text-fill-color:#ffffff!important}
[data-testid="stMarkdownContainer"] th, [data-testid="stTable"] th {background:#0d47a1!important;color:#ffffff!important}
[data-testid="stMarkdownContainer"] td, [data-testid="stTable"] td {color:#0b1b33!important}
.cn-head {color:#ffffff!important;background:#0d47a1!important}
</style>
"""

FIX_CSS = """
<style>
/* PPD PUTIH - yang kau kata ok */
html body [data-testid="stMarkdownContainer"] .sup-banner,
html body [data-testid="stMarkdownContainer"] .sup-banner span,
html body [data-testid="stMarkdownContainer"] .land-top,
html body [data-testid="stMarkdownContainer"] .land-top span,
html body [data-testid="stMarkdownContainer"] .sup-sub-h,
html body [data-testid="stMarkdownContainer"] .sup-card-h,
html body [data-testid="stMarkdownContainer"] .cn-head,
.sup-banner, .sup-banner span, .sup-banner div, .sup-banner p,
.land-top, .land-top span, .land-top div, .land-top p,
.sup-sub-h, .sup-sub-h span,
.sup-card-h, .sup-card-h span,
.cn-head, .cn-head span,
.ppd-table th {
  color:#ffffff!important;
  -webkit-text-fill-color:#ffffff!important;
}
.sup-banner, .land-top, .sup-sub-h, .sup-card-h, .cn-head {background:#0d47a1!important}
div[style*="0d47a1"] h2, div[style*="0d47a1"] p {color:#ffffff!important; -webkit-text-fill-color:#ffffff!important}
div[style*="0d47a1"] p {color:#e3f2fd!important; -webkit-text-fill-color:#e3f2fd!important}
</style>
"""


MODERN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, .stApp, [data-testid="stAppViewContainer"], button, input, textarea, select {font-family:'Inter','Segoe UI',system-ui,-apple-system,Roboto,Arial,sans-serif!important}
.stApp {background:linear-gradient(180deg,#dcecfb 0%,#eaf3fd 38%,#f4f9ff 100%)!important}
footer, [data-testid="stFooter"] {visibility:hidden!important;height:0!important}
.block-container {padding-left:1.2rem!important;padding-right:1.2rem!important}
/* kad & pengepala */
.sup-box {border-radius:14px!important;border:1px solid #c9daee!important;box-shadow:0 6px 18px rgba(13,71,161,.08)!important}
.sup-banner {background:linear-gradient(100deg,#0a3a8a 0%,#0d47a1 45%,#1976d2 100%)!important;padding:13px 18px!important}
.sup-banner .t {font-size:14px!important;letter-spacing:.02em!important}
.sup-pill {background:rgba(255,255,255,.18)!important;border:1px solid rgba(255,255,255,.35)!important}
.sup-info {background:#f7fbff!important}
.sup-note {border-radius:12px!important;box-shadow:0 2px 8px rgba(13,71,161,.06)}
.sup-sub-h {border-radius:10px 10px 0 0!important;background:linear-gradient(100deg,#0a3a8a,#1565c0)!important}
.st-key-shellsub {border-radius:0 0 10px 10px!important;overflow:hidden}
.st-key-shellmenu [class*="st-key-flymenu_"] button {border-radius:0 10px 10px 0!important;transition:background .15s ease,box-shadow .15s ease,padding-left .15s ease!important}
.st-key-shellmenu [class*="st-key-flymenu_"] button:hover {padding-left:16px!important}
.st-key-shellmenu [class*="st-key-flymenu_"] button[kind="primary"],
.st-key-shellmenu [class*="st-key-flymenu_"] [data-testid="stBaseButton-primary"] {background:linear-gradient(100deg,#0a2a66,#1258b8)!important}
/* tajuk */
h1, h2, h3 {color:#0a2a66!important;letter-spacing:-.01em!important;font-weight:800!important}
h2 {border-bottom:3px solid #90caf9;padding-bottom:6px!important;margin-bottom:12px!important}
/* metrik */
[data-testid="stMetric"] {border-radius:12px!important;border:1px solid #c9daee!important;border-left:5px solid #1e88e5!important;box-shadow:0 3px 10px rgba(13,71,161,.07);transition:transform .15s ease,box-shadow .15s ease}
[data-testid="stMetric"]:hover {transform:translateY(-1px);box-shadow:0 6px 16px rgba(13,71,161,.12)}
/* butang */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {border-radius:10px!important;transition:filter .15s ease,transform .1s ease,box-shadow .15s ease!important;box-shadow:0 2px 6px rgba(13,71,161,.18)!important}
.stButton > button:hover, .stDownloadButton > button:hover {filter:brightness(1.12);box-shadow:0 5px 12px rgba(13,71,161,.28)!important}
.stButton > button:active, .stDownloadButton > button:active {transform:translateY(1px)}
.stButton > button:disabled, .stDownloadButton > button:disabled {filter:grayscale(.6) opacity(.6)}
/* tab */
[data-baseweb="tab-list"] {gap:4px;border-bottom:2px solid #c9daee}
[data-baseweb="tab"] {border-radius:10px 10px 0 0!important;padding:8px 16px!important}
[data-baseweb="tab"][aria-selected="true"] {background:#ffffff!important;box-shadow:0 -2px 8px rgba(13,71,161,.08)}
[data-baseweb="tab-highlight"] {background:#0d47a1!important;height:3px!important}
/* jadual / pengembang / amaran / input */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {border-radius:12px;overflow:hidden;border:1px solid #c9daee;box-shadow:0 3px 10px rgba(13,71,161,.06)}
[data-testid="stExpander"] {background:#ffffff;border:1px solid #c9daee!important;border-radius:12px!important;box-shadow:0 2px 8px rgba(13,71,161,.05)}
[data-testid="stAlert"] {border-radius:12px!important}
[data-baseweb="select"] > div, [data-baseweb="input"], textarea {border-radius:10px!important}
[data-testid="stProgress"] > div > div > div > div {background:linear-gradient(90deg,#1565c0,#42a5f5)!important}
::-webkit-scrollbar {width:9px;height:9px} ::-webkit-scrollbar-thumb {background:#90a4c8;border-radius:8px} ::-webkit-scrollbar-track {background:#e3eefb}
/* komponen kemajuan */
.kmj-grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:6px 0 14px}
.kmj-tile {background:#fff;border:1px solid #c9daee;border-radius:14px;padding:12px 14px;box-shadow:0 3px 10px rgba(13,71,161,.07);position:relative;overflow:hidden}
.kmj-tile:before {content:"";position:absolute;left:0;top:0;bottom:0;width:5px;background:#1e88e5}
.kmj-tile.ok:before {background:#2e9d57} .kmj-tile.warn:before {background:#f59e0b} .kmj-tile.bad:before {background:#d32f2f}
.kmj-tile .l {font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#46556d}
.kmj-tile .n {font-size:26px;font-weight:800;color:#0a2a66;line-height:1.1;margin-top:4px}
.kmj-tile .s {font-size:11px;color:#46556d;margin-top:3px;font-weight:500}
.kmj-sec {display:flex;align-items:center;gap:10px;margin:18px 0 8px;font-size:15px;font-weight:800;color:#0a2a66}
.kmj-sec:after {content:"";flex:1;height:2px;background:linear-gradient(90deg,#90caf9,transparent)}
.kmj-bar {margin:7px 0}
.kmj-bar .h {display:flex;justify-content:space-between;font-size:12px;font-weight:700;color:#0b1b33;margin-bottom:3px}
.kmj-bar .h span:last-child {color:#46556d;font-weight:600}
.kmj-bar .t {height:11px;background:#dbe7f6;border-radius:999px;overflow:hidden}
.kmj-bar .f {height:100%;border-radius:999px;background:linear-gradient(90deg,#1565c0,#42a5f5);transition:width .4s ease}
.kmj-bar.ok .f {background:linear-gradient(90deg,#2e9d57,#6fd39a)} .kmj-bar.warn .f {background:linear-gradient(90deg,#e08a00,#fbbf24)} .kmj-bar.bad .f {background:linear-gradient(90deg,#c62828,#ef6c6c)}
.kmj-pill {display:inline-block;font-size:11px;font-weight:700;padding:2px 10px;border-radius:999px;border:1px solid #90caf9;background:#e8f1fd;color:#0a2a66}
.kmj-pill.ok {background:#dcfce7;border-color:#bbf7d0;color:#166534} .kmj-pill.warn {background:#fef3c7;border-color:#fde68a;color:#92400e} .kmj-pill.bad {background:#fee2e2;border-color:#fecaca;color:#991b1b}
@media (max-width:900px) {.block-container {padding-left:.6rem!important;padding-right:.6rem!important} .kmj-grid {grid-template-columns:repeat(2,1fr)}}
</style>
"""


def kmj_tile(label, nilai, sub="", tone=""):
    return f'<div class="kmj-tile {esc(tone)}"><div class="l">{esc(label)}</div><div class="n">{esc(nilai)}</div><div class="s">{esc(sub)}</div></div>'


def kmj_grid(tiles):
    """tiles: senarai (label, nilai, sub, tone)."""
    st.markdown('<div class="kmj-grid">' + "".join(kmj_tile(*t) for t in tiles) + '</div>', unsafe_allow_html=True)


def kmj_sec(teks):
    st.markdown(f'<div class="kmj-sec">{esc(teks)}</div>', unsafe_allow_html=True)


def kmj_bar(label, nilai, jumlah, tone=""):
    pct = 0 if not jumlah else max(0, min(100, round(100 * nilai / jumlah)))
    if not tone:
        tone = "ok" if pct >= 100 else ("warn" if pct >= 50 else ("bad" if jumlah and pct < 25 else ""))
    st.markdown(f'<div class="kmj-bar {esc(tone)}"><div class="h"><span>{esc(label)}</span><span>{esc(nilai)} / {esc(jumlah)} &nbsp;·&nbsp; {pct}%</span></div><div class="t"><div class="f" style="width:{pct}%"></div></div></div>', unsafe_allow_html=True)

def apply_theme():
    st.markdown(THEME_CSS, unsafe_allow_html=True)
    st.markdown(KONTRAS_CSS, unsafe_allow_html=True)
    st.markdown(FIX_CSS, unsafe_allow_html=True)
    st.markdown(MODERN_CSS, unsafe_allow_html=True)

def _refresh_block(role):
    with kc("suprefresh"):
        if st.button("REFRESH - Baca Data Baru", key=f"refresh_{role}", use_container_width=True):
            st.cache_data.clear()
            st.session_state["last_refresh"] = now_my()
            st.rerun()
    st.markdown('<div class="sup-red">Tekan selepas SUP buat pertukaran / cadangan</div>', unsafe_allow_html=True)

def shell_header(role, id_html, banner_title, pill, right_text, info_html):
    last = st.session_state.get("last_refresh") or now_my()
    st.session_state["last_refresh"] = last
    hl, hr = st.columns([1.25, 6.4], gap="small")
    with hl:
        st.markdown(f'<div class="sup-box" style="padding:12px">{id_html}<div class="sup-last">Last: {esc(last)}</div></div>', unsafe_allow_html=True)
        _refresh_block(role)
    with hr:
        st.markdown(f"""<div class="sup-box"><div class="sup-banner"><div style="display:flex;align-items:center;flex-wrap:wrap"><span class="t">{esc(banner_title)}</span><span class="sup-pill"><i></i>{esc(pill)}</span></div><div class="sup-right">{esc(right_text)}</div></div><div class="sup-info">{info_html}<span class="sup-online"><i></i> Online</span></div></div>""", unsafe_allow_html=True)

def _kv(k, v):
    return f'<span><b>{esc(k)}:</b> <b style="color:#1a2332">{esc(v)}</b></span>'

def sup_no_pusat_list(kod):
    out = []
    try:
        df = get_pusat_df()
        kod = kod.upper().strip()
        for _, r in df.iterrows():
            d = r.get("data") if isinstance(r.get("data"), dict) else {}
            if isinstance(d, str):
                try:
                    d = json.loads(d)
                except Exception:
                    d = {}
            ks_tuan = str(r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or r.get("KOD_SEKOLAH") or d.get("KOD_SEKOLAH") or d.get("KOD SEKOLAH") or "").upper().strip()
            ks_biasa = str(r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or "").upper().strip()
            if ks_tuan == kod or ks_biasa == kod:
                no_p = str(r.get("no_pusat") or r.get("kod_pusat") or r.get("NO_PUSAT") or d.get("NO_PUSAT") or d.get("NO PUSAT") or "").upper().strip()
                if no_p and no_p not in out:
                    out.append(no_p)
    except Exception:
        pass
    return out

def shell_header_sup(kod, info, no_pusat_list):
    nama = info.get("nama_sekolah", "")
    kppd = str(info.get("kod_ppd", "")).upper()
    nppd = PPD_MAP.get(kppd, "")
    pusat = ", ".join(no_pusat_list) if no_pusat_list else "-"
    id_html = (f'<div class="sup-id">SUP {esc(kod)}<br>{esc(nama)}<br>{esc(kppd)} - {esc(nppd)}</div>'
               f'<div class="sup-pusat"><div class="l">NO PUSAT SEKOLAH:</div><div class="v">{esc(pusat)}</div></div>')
    info_html = _kv("Kod Sekolah", kod) + '<span class="sep">|</span>' + _kv("PPD", f"{kppd} - {nppd}") + '<span class="sep">|</span>' + _kv("Nama", nama)
    shell_header("sup", id_html, f"Dashboard SUP - {kod} {nama}", "App Ringan - 1 Sekolah Sahaja", f"Sistem Pengurusan Pengawas Peperiksaan | JPN Selangor {tahun_semasa()}", info_html)

def shell_header_ppd(kod_ppd):
    nppd = PPD_MAP.get(kod_ppd, "")
    id_html = f'<div class="sup-id">PPD {esc(kod_ppd)}<br>{esc(nppd)}<br>Pejabat Pendidikan Daerah</div>'
    info_html = _kv("Kod PPD", kod_ppd) + '<span class="sep">|</span>' + _kv("Daerah", nppd) + '<span class="sep">|</span>' + _kv("Sumber data", "cadangan_sup (daerah ini sahaja)")
    shell_header("ppd", id_html, f"Dashboard PPD - {kod_ppd} {nppd}", f"App Daerah - {nppd} Sahaja", f"Sistem Pengurusan Pengawas Peperiksaan | JPN Selangor {tahun_semasa()}", info_html)

def shell_header_jpn():
    id_html = '<div class="sup-id">JPN SELANGOR<br>Pentadbir Sistem<br>Semua Daerah</div>'
    info_html = _kv("Peranan", "JPN") + '<span class="sep">|</span>' + _kv("Skop", "10 daerah PPD")
    shell_header("jpn", id_html, f"Dashboard JPN Selangor - Pelantikan SPM {tahun_semasa()}", "Pentadbir Negeri", f"Sistem Pengurusan Pengawas Peperiksaan | JPN Selangor {tahun_semasa()}", info_html)

def shell_layout(skey, items, fly_map, dash_key, prefix):
    keys = [k for k, _ in items]
    if st.session_state.get(skey) not in keys:
        st.session_state[skey] = keys[0]
    cur = st.session_state[skey]
    subs = fly_map.get(cur)
    cols = st.columns([1.25, 1.0, 5.4] if subs else [1.25, 6.4], gap="small")
    with cols[0]:
        with kc("shellmenu"):
            for k, label in items:
                if st.button(label, key=f"flymenu_{skey}_{k}", use_container_width=True, type="primary" if k == cur else "secondary"):
                    if k != cur:
                        st.session_state[skey] = k
                        st.rerun()
        st.markdown('<div class="sup-note"><b>NOTA SISTEM</b><span>Paparan ini hanya membaca data skop anda sahaja, jadi lebih ringan dan laju.</span></div>', unsafe_allow_html=True)
    fly_cur = None
    if subs:
        sk = dash_key if (dash_key and cur == "dashboard") else f"{prefix}_{cur}"
        sk_keys = [k for k, _ in subs]
        if st.session_state.get(sk) not in sk_keys:
            st.session_state[sk] = sk_keys[0]
        fly_cur = st.session_state[sk]
        with cols[1]:
            st.markdown('<div class="sup-sub-h">SUB MENU</div>', unsafe_allow_html=True)
            with kc("shellsub"):
                for k, label in subs:
                    if st.button(label, key=f"flysub_{sk}_{k}", use_container_width=True, type="primary" if k == fly_cur else "secondary"):
                        if k != fly_cur:
                            st.session_state[sk] = k
                            st.rerun()
    return cur, fly_cur, cols[-1]
