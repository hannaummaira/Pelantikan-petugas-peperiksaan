# -*- coding: utf-8 -*-
"""Peranan PPD - pentadbir daerah (SUP baca guru_master, PPD baca cadangan_sup) - FIXED dengan Clear Surat"""
import spm_core as _core
import ui_theme as _ui
from surat_clear import render_clear_surat_ui, clear_surat_lantikan, get_surat_count
globals().update({k: v for k, v in vars(_core).items() if not k.startswith("__")})
globals().update({k: v for k, v in vars(_ui).items() if not k.startswith("__")})

def render_ppd():
    kod_ppd = st.session_state.get("kod") or st.session_state.get("portal") or SCOPE.get("ppd") or ""
    kod_ppd = str(kod_ppd).upper()
    
    if SCOPE["ppd"] and kod_ppd != SCOPE["ppd"]:
        st.session_state.clear()
        st.rerun()
    
    # Menu PPD + Clear Surat
    MENU_PPD = [
        ('dashboard', '📊 Dashboard PPD'),
        ('cadangan', '📋 Cadangan SUP'),
        ('jana', '⚙️ Jana Penempatan'),
        ('hasil', '📊 Hasil Janaan'),
        ('semakan', '🔍 Semakan Lantikan'),
        ('kelulusan', '✅ Kelulusan'),
        ('jana_surat', '📄 Jana Surat Lantikan'),
        ('clear_surat', '🗑️ Clear Surat'),  # <-- BARU
        ('selenggara', '🔧 Selenggara'),
        ('keluar', '🚪 Log Keluar')
    ]
    
    shell_header_ppd(kod_ppd)
    menu, fly_cur, col_main = shell_layout("ppd_menu_sel", MENU_PPD, FLY_PPD, None, "fly_ppd")
    
    with col_main:
        if menu == "keluar":
            st.session_state.clear()
            st.rerun()
        
        # ===== CLEAR SURAT LANTIKAN - PPD =====
        elif menu == "clear_surat":
            st.header(f"🗑️ Clear Surat Lantikan - PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')}")
            st.markdown("""
            <div style='background:#FFF3E0; border:1px solid #FFB74D; border-radius:8px; padding:12px; margin-bottom:16px;'>
            <b>⚠️ Fungsi Penting:</b> Clear surat akan reset status <code>SURAT_SAMPAI_SEKOLAH_ASAL</code> kembali ke <code>DILANTIK PPD</code>.
            Surat boleh dijana semula selepas clear. Gunakan dengan berhati-hati.
            </div>
            """, unsafe_allow_html=True)
            
            # Guna function dari surat_clear.py
            render_clear_surat_ui(kod_ppd=kod_ppd, role="PPD", kod_sekolah=None)
        
        elif menu == "dashboard":
            # Dashboard PPD asal - copy dari code lama anda
            st.header(f"Dashboard PPD {kod_ppd} - {PPD_MAP.get(kod_ppd, '')}")
            try:
                # Ringkasan
                res_sek = supa.table("sekolah_master").select("kod_sekolah", count="exact").limit(1).execute()
                res_cad = supa.table("cadangan_sup").select("id", count="exact").eq("kod_ppd", kod_ppd).limit(1).execute()
                res_surat = supa.table("cadangan_sup").select("id", count="exact").eq("kod_ppd", kod_ppd).eq("status", "SURAT_SAMPAI_SEKOLAH_ASAL").limit(1).execute()
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Sekolah", res_sek.count if hasattr(res_sek, 'count') else 0)
                c2.metric("Cadangan PPD", res_cad.count if hasattr(res_cad, 'count') else 0)
                c3.metric("Surat Dijana", res_surat.count if hasattr(res_surat, 'count') else 0)
                c4.metric("Kod PPD", kod_ppd)
            except Exception as e:
                st.error(f"Error dashboard: {e}")
        
        else:
            # Untuk menu lain, panggil fungsi asal dari spm_core atau role_ppd lama
            # Jika anda ada code asal untuk cadangan, jana, dll, letak di sini
            # Contoh fallback:
            st.info(f"Menu {menu} - {fly_cur} - Sila tambah code asal PPD anda di sini jika perlu.")
            st.caption("File ini adalah template dengan Clear Surat. Copy code asal menu PPD anda dari backup lama ke dalam blok elif ini.")
            
            # Contoh untuk menu cadangan - anda boleh ganti dengan import ppd_cadangan
            if menu == "cadangan":
                try:
                    import ppd_cadangan as pc
                    # Panggil fungsi cadangan asal jika ada
                    if hasattr(pc, 'render_cadangan'):
                        pc.render_cadangan(kod_ppd)
                except Exception as e:
                    st.warning(f"Module ppd_cadangan belum ada: {e}")
