# -*- coding: utf-8 -*-
"""Pintu masuk utama: landing page daerah + JPN Selangor (pentadbir negeri)."""
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="SPM 2026 - Selangor", layout="wide",
                   page_icon="🏛️", initial_sidebar_state="collapsed")

if st.session_state.get("masuk_jpn"):
    from jpn_app import run_jpn   # data Supabase hanya dimuat selepas ini
    run_jpn()
else:
    with open("landing.html", encoding="utf-8") as f:
        components.html(f.read(), height=720, scrolling=True)
    _, mid, _ = st.columns([1, 2, 1])
    if mid.button("Masuk JPN", use_container_width=True):
        st.session_state["masuk_jpn"] = True
        st.rerun()
