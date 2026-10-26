# -*- coding: utf-8 -*-
"""jpn_app.py - Aplikasi JPN (pentadbir negeri, semua daerah). Tiada SUP/PPD di sini."""
import streamlit as st
import spm_core as core
import ui_theme as ui


def render_login():
    core.show_hero_header()
    st.markdown("""
    <div class="land-top"><div style="display:flex;align-items:center"><span class="logo">JPN</span>
      <div><div class="n">JABATAN PENDIDIKAN NEGERI SELANGOR</div><div class="s">KEMENTERIAN PENDIDIKAN MALAYSIA</div></div></div>
      <div class="r">Pelantikan Petugas SPM Selangor 2026</div></div>
    <div class="land-head"><div><span class="land-chip"><i></i>Pentadbir Negeri</span>
      <div class="land-h1">Log Masuk <span>JPN</span></div>
      <div class="land-p">Akses semua daerah PPD • Template surat • Pusat Master • Guru Master</div></div></div>
    """, unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        with st.container(border=True):
            jpn_id = st.text_input("ID JPN", value="1", key="jpn_id_in")
            pwd = st.text_input("Kata laluan JPN", type="password", key="jpn_pwd_in")
            if st.button("Masuk JPN", type="primary", use_container_width=True, key="jpn_masuk"):
                if jpn_id.strip() == "1" and pwd.strip().lower() in ["a", "1", "123451", "12345"]:
                    st.session_state["role"] = "JPN"
                    st.rerun()
                else:
                    st.error("ID atau kata laluan JPN salah.")


def run_jpn():
    core.set_scope(None)                    # JPN: semua daerah
    core.apply_global_ui()
    ui.apply_theme()
    if st.session_state.get("role") == "JPN":
        import role_jpn
        role_jpn.render_jpn()
    else:
        if st.session_state.get("role"):
            st.session_state.clear()
        render_login()
    core.render_footer()
