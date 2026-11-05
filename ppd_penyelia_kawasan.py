# -*- coding: utf-8 -*-
"""
ppd_penyelia_kawasan.py - Menu PPD baru: Lantik Penyelia Kawasan

Flow baru:
 1. Selenggara Bilik Kebal (ppd_zon.py) hanya tetapkan zon: kod_ppd, kod_bilik_kebal, kod_sekolah
 2. Menu baru ini: Pilih Penyelia Kawasan -> Tempatkan ikut Bilik Kebal -> Kelulusan -> Jana Surat (guna Template JPN)

Table:
  zon_bilik_kebal(kod_ppd, kod_bilik_kebal, kod_sekolah)
  Join nama sekolah dari sekolah_master.kod_sekolah

Surat:
  Guna core.get_jpn_template_for_jawatan('PENYELIA KAWASAN') / render_jpn_template_html()
  Placeholders yang disokong (JPN template):
    {{NAMA}}, {{IC}}, {{JAWATAN}}, {{SEKOLAH_ASAL}}, {{NAMA_SEKOLAH_ASAL}},
    {{BILIK_KEBAL}}, {{NAMA_BILIK_KEBAL}}, {{PUSAT_JAGAAN}}, {{SENARAI_PUSAT}},
    {{NO_SURAT}}, {{PPD}}, {{PPD_NAME}}, {{TARIKH}}, {{TAHUN}}
"""

import json
import pandas as pd
import streamlit as st
import spm_core as core
from spm_core import supa, get_cadangan_df, get_pusat_df, PPD_MAP
from tahun_sistem import tahun_semasa, tempoh_penyelia
from ui_theme import esc

TABLE_ZON = "zon_bilik_kebal"

@st.cache_data(ttl=300, show_spinner=False)
def _sekolah_map(kod_ppd):
    """{kod_sekolah: nama_sekolah} untuk daerah ini"""
    out = {}
    try:
        res = supa.table("sekolah_master").select("kod_sekolah,nama_sekolah,data").eq("kod_ppd", kod_ppd).limit(5000).execute()
        for r in res.data or []:
            k = str(r.get("kod_sekolah") or "").upper().strip()
            nama = str(r.get("nama_sekolah") or "").strip()
            if k:
                out[k] = nama
    except Exception:
        pass
    return out

@st.cache_data(ttl=300, show_spinner=False)
def _bilik_kebal_list(kod_ppd):
    out=[]
    try:
        res = supa.table("bilik_kebal_master").select("*").limit(2000).execute()
        for r in res.data or []:
            # tapis ikut kod_ppd jika ada lajur, jika tiada tapis ikut prefix
            k = str(r.get("kod_bilik_kebal") or r.get("KOD_BILIK_KEBAL") or "").upper().strip()
            if not k: continue
            # simpan semua dulu
            out.append({
                "kod": k,
                "nama": str(r.get("nama_bilik_kebal") or r.get("NAMA_BILIK_KEBAL") or "").strip(),
                "alamat": str(r.get("alamat") or r.get("ALAMAT") or "").strip(),
                "kod_ppd": str(r.get("kod_ppd") or "").upper()
            })
    except Exception:
        pass
    # filter ikut kod_ppd jika ada
    filtered = [b for b in out if not b["kod_ppd"] or b["kod_ppd"]==kod_ppd or k.startswith(kod_ppd)]
    return filtered if filtered else out

def _zon_map(kod_ppd):
    """{kod_bilik_kebal: [kod_sekolah]}"""
    out={}
    try:
        res = supa.table(TABLE_ZON).select("kod_bilik_kebal,kod_sekolah").eq("kod_ppd", kod_ppd).limit(5000).execute()
        for r in res.data or []:
            bk = str(r.get("kod_bilik_kebal") or "").upper().strip()
            ks = str(r.get("kod_sekolah") or "").upper().strip()
            if bk and ks:
                out.setdefault(bk, []).append(ks)
    except Exception:
        pass
    return out

def _pusat_under_zon(kod_ppd):
    """{kod_bilik_kebal: [pusat_dict]} - pusat yang tuan rumahnya ada dalam zon"""
    zon = _zon_map(kod_ppd)
    if not zon:
        return {}
    # load semua pusat daerah
    pusat_all = {}
    df = get_pusat_df()
    if df is not None:
        for _, r in df.iterrows():
            d = r.get("data") if isinstance(r.get("data"), dict) else {}
            if isinstance(d,str):
                try: d=json.loads(d)
                except: d={}
            no = str(r.get("no_pusat") or r.get("kod_pusat") or d.get("NO_PUSAT") or "").upper().strip()
            if not no.startswith(kod_ppd): continue
            tuan = str(r.get("kod_sekolah_tuan_rumah") or r.get("kod_sekolah") or d.get("KOD_SEKOLAH") or "").upper().strip()
            pusat_all[no] = {"NO": no, "NAMA": str(r.get("nama_pusat") or d.get("NAMA_PUSAT") or "").strip(), "TUAN": tuan}
    # map
    out={bk: [] for bk in zon}
    for bk, sek_list in zon.items():
        sek_set=set([s.upper() for s in sek_list])
        for no,p in pusat_all.items():
            if p["TUAN"] in sek_set:
                out[bk].append(p)
    return out

def _calon_penyelia(kod_ppd):
    """Load calon PENYELIA KAWASAN dari cadangan_sup"""
    import ppd_cadangan as pc
    df = pc.normalize(get_cadangan_df(kod_ppd=kod_ppd))
    if df.empty:
        return pd.DataFrame()
    # tapis jawatan penyel ia
    mask = df["JAWATAN"].astype(str).str.upper().str.contains("PENYELIA")
    df = df[mask]
    return df

def _render_template_penyelia(row, bilik_kebal_code, nama_bilik, pusat_list, no_surat, kod_ppd):
    """Jana HTML surat guna template JPN jika ada, fallback ke kod lama"""
    nama = row.get("NAMA") or row.get("nama") or ""
    ic = row.get("IC") or ""
    sek_asal = row.get("KOD_SEK") or ""
    nama_sek_asal = row.get("NAMA_SEK") or ""
    ppd_name = PPD_MAP.get(kod_ppd, kod_ppd)
    tarikh = pd.Timestamp.now().strftime("%d %B %Y")
    pusat_jagaan_str = ", ".join([f"{p['NO']} - {p['NAMA']}" for p in pusat_list]) if pusat_list else "-"
    
    # Cuba guna template JPN dulu
    try:
        html = core.render_jpn_template_html(
            "PENYELIA KAWASAN",
            nama, ic, sek_asal, nama_sek_asal,
            bilik_kebal_code,  # pusat param kita guna sebagai bilik kebal untuk template lama
            f"{nama_bilik} | Pusat jagaan: {pusat_jagaan_str}",
            no_surat, kod_ppd, ppd_name, tarikh,
            bilik_kebal=bilik_kebal_code
        )
        if html and len(html)>200:
            # tambah placeholder tambahan manual jika template JPN pakai {{BILIK_KEBAL}} etc
            html = html.replace("{{BILIK_KEBAL}}", esc(bilik_kebal_code))
            html = html.replace("{{NAMA_BILIK_KEBAL}}", esc(nama_bilik))
            html = html.replace("{{SENARAI_PUSAT}}", esc(pusat_jagaan_str))
            html = html.replace("{{PUSAT_JAGAAN}}", esc(pusat_jagaan_str))
            html = html.replace("{{SEKOLAH_ASAL}}", esc(sek_asal))
            html = html.replace("{{NAMA_SEKOLAH_ASAL}}", esc(nama_sek_asal))
            html = html.replace("{{KOD_BILIK_KEBAL}}", esc(bilik_kebal_code))
            return html
    except Exception as e:
        pass

    # Tiada fallback hardcode - wajib guna Template JPN
    return None

def render_penyelia_kawasan(kod_ppd, fly_cur=None):
    st.markdown(f"<div class='sup-sub-h'>LANTIK PENYELIA KAWASAN - PPD {esc(kod_ppd)} {esc(PPD_MAP.get(kod_ppd,''))}</div>", unsafe_allow_html=True)
    zon = _zon_map(kod_ppd)
    sekolah_map = _sekolah_map(kod_ppd)
    pusat_map = _pusat_under_zon(kod_ppd)
    bilik_list = _bilik_kebal_list(kod_ppd)

    if not zon:
        st.warning("⚠️ Belum ada zon bilik kebal. Sila tetapkan di **Selenggara Bilik Kebal > Tetapan Zon** dahulu.")
        st.info(f"Table `{TABLE_ZON}` (kod_ppd, kod_bilik_kebal, kod_sekolah) perlu ada data. Kod sekolah akan dibaca nama dari `sekolah_master`.")
        return

    # papar info zon
    with st.expander(f"📍 Maklumat Zon Semasa ({len(zon)} Bilik Kebal)", expanded=False):
        for bk, sek in zon.items():
            nama_bk = next((b["nama"] for b in bilik_list if b["kod"]==bk), "")
            pusat = pusat_map.get(bk, [])
            st.markdown(f"**{bk} - {nama_bk}** : {len(sek)} sekolah, {len(pusat)} pusat")
            for ks in sek[:10]:
                st.caption(f"- {ks} - {sekolah_map.get(ks, 'Nama tidak ditemui di sekolah_master')}")
            if len(sek)>10: st.caption(f"... +{len(sek)-10} lagi")

    fly_cur = fly_cur or "calon"

    if fly_cur=="calon":
        st.subheader("👥 Calon Penyelia Kawasan (TERPILIH PPD)")
        df = _calon_penyelia(kod_ppd)
        if df.empty:
            st.info("Tiada calon Penyelia Kawasan dalam cadangan_sup untuk daerah ini.")
            return
        st.dataframe(df[["NAMA","IC","KOD_SEK","NAMA_SEK","JAWATAN","STATUS","KOD_PUSAT"]], use_container_width=True)
        st.caption("Calon ini akan ditempatkan ke Bilik Kebal di tab 'Tempatkan'")

    elif fly_cur=="tempat":
        st.subheader("🔐 Tempatkan Penyelia Kawasan Mengikut Bilik Kebal")
        df = _calon_penyelia(kod_ppd)
        if df.empty:
            st.info("Tiada calon.")
            return
        
        # filter yang belum ditempatkan atau sudah ditempatkan
        for idx, bk in enumerate(zon.keys()):
            nama_bk = next((b["nama"] for b in bilik_list if b["kod"]==bk), "")
            pusat = pusat_map.get(bk, [])
            with st.container(border=True):
                st.markdown(f"### 🔐 {bk} - {nama_bk}")
                st.caption(f"{len(pusat)} pusat di bawah: " + ", ".join([f"{p['NO']}" for p in pusat[:5]]) + (" ..." if len(pusat)>5 else ""))
                # calon untuk bilik ini
                # pilih calon
                calon_options = df.to_dict('records')
                labels = [f"{c['NAMA']} ({c['KOD_SEK']} - {sekolah_map.get(c['KOD_SEK'],'')}) - {c['STATUS']}" for c in calon_options]
                pilih = st.multiselect(f"Pilih Penyelia untuk {bk}", options=list(range(len(calon_options))), format_func=lambda i: labels[i], key=f"pilih_{bk}")
                if st.button(f"Simpan Penempatan {bk}", key=f"simpan_{bk}"):
                    ids = [calon_options[i]["id"] for i in pilih]
                    if not ids:
                        st.warning("Pilih sekurang-kurangnya seorang")
                    else:
                        try:
                            # simpan kod_bilik_kebal dalam kod_pusat
                            supa.table("cadangan_sup").update({"kod_pusat": bk, "status": "DILANTIK PPD"}).in_("id", ids).execute()
                            st.success(f"{len(ids)} penyel ia ditempatkan ke {bk}")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal simpan: {e}")

    elif fly_cur=="lulus":
        st.subheader("✅ Kelulusan Penyelia Kawasan")
        df = _calon_penyelia(kod_ppd)
        df_lantik = df[df["KOD_PUSAT"].astype(str).str.upper().isin(list(zon.keys()))]
        if df_lantik.empty:
            st.info("Belum ada penyel ia ditempatkan.")
            return
        st.dataframe(df_lantik, use_container_width=True)
        if st.button("Luluskan Semua (Status LULUS PPD)", type="primary"):
            try:
                ids = df_lantik["id"].tolist()
                supa.table("cadangan_sup").update({"status": "LULUS PPD"}).in_("id", ids).execute()
                st.success("Diluluskan")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(str(e))

    elif fly_cur=="surat":
        st.subheader("📄 Jana Surat Penyelia Kawasan (Guna Template JPN)")
        # semak template
        try:
            tmpl = core.get_jpn_template_for_jawatan("PENYELIA KAWASAN")
            if tmpl:
                st.success(f"✅ Template JPN Penyelia Kawasan ditemui ({len(tmpl)} chars) - akan guna template ini")
            else:
                st.warning("⚠️ Template JPN Penyelia Kawasan belum ada di surat_templates_jpn. JPN perlu cipta di menu Template Surat JPN (11 Jawatan) dahulu. Surat tidak akan dijana tanpa template.")
        except Exception as e:
            st.warning(f"Semak template gagal: {e}")

        df = _calon_penyelia(kod_ppd)
        df_lulus = df[df["STATUS"].astype(str).str.upper().str.contains("LULUS|DILANTIK")]
        if df_lulus.empty:
            df_lulus = df[df["KOD_PUSAT"].astype(str).str.upper().isin(list(zon.keys()))]
        if df_lulus.empty:
            st.info("Tiada penyel ia untuk dijana surat.")
            return
        
        for _, r in df_lulus.iterrows():
            bk = str(r["KOD_PUSAT"]).upper().strip()
            nama_bk = next((b["nama"] for b in bilik_list if b["kod"]==bk), bk)
            pusat = pusat_map.get(bk, [])
            no_surat = f"JPNS.SPP 600-7/17/5 Jld.2 ({r['IC'][-4:] if len(str(r['IC']))>=4 else ''})"
            with st.container(border=True):
                st.markdown(f"**{r['NAMA']}** - {bk} - {r['NAMA_SEK']}")
                st.caption(f"Pusat jagaan: {', '.join([p['NO'] for p in pusat]) or '-'}")
                if st.button(f"Jana Surat {r['NAMA']}", key=f"surat_{r['id']}"):
                    html = _render_template_penyelia(r, bk, nama_bk, pusat, no_surat, kod_ppd)
                    if html:
                        pdf = core.html_to_pdf_bytes(html)
                        if pdf:
                            st.download_button(f"Download PDF {r['NAMA']}", data=pdf, file_name=f"Surat_Penyelia_{r['NAMA']}_{bk}.pdf", mime="application/pdf")
                            st.components.v1.html(html, height=600, scrolling=True)
                        else:
                            st.error("Gagal convert HTML ke PDF (xhtml2pdf tiada?)")
                            st.components.v1.html(html, height=600, scrolling=True)
                    else:
                        st.error("Gagal jana surat")
        
        # kolektif
        if len(df_lulus)>1 and st.button("Jana Semua Surat (Kolektif PDF)", type="primary"):
            surat_list=[]
            for _, r in df_lulus.iterrows():
                bk = str(r["KOD_PUSAT"]).upper().strip()
                nama_bk = next((b["nama"] for b in bilik_list if b["kod"]==bk), bk)
                pusat = pusat_map.get(bk, [])
                no_surat = f"JPNS.SPP 600-7/17/5 Jld.2"
                html = _render_template_penyelia(r, bk, nama_bk, pusat, no_surat, kod_ppd)
                if html:
                    surat_list.append({"nama": r["NAMA"], "ic": r["IC"], "jawatan": "PENYELIA KAWASAN", "sekolah_asal": r["KOD_SEK"], "nama_sekolah_asal": r["NAMA_SEK"], "pusat": bk, "nama_pusat": nama_bk, "no_surat": no_surat, "html": html})
            if surat_list:
                try:
                    pdf = core.generate_surat_kolektif_pdf_bytes_JPN(surat_list, kod_ppd, PPD_MAP.get(kod_ppd,""), title_prefix="SURAT PENYELIA KAWASAN")
                    if pdf:
                        st.download_button("Download PDF Kolektif", data=pdf, file_name=f"KOLEKTIF_Penyelia_{kod_ppd}.pdf", mime="application/pdf")
                except Exception as e:
                    st.error(f"Gagal jana kolektif: {e}")
