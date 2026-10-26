# -*- coding: utf-8 -*-
"""PPD Sepang (BJ) - SUP + PPD. Hanya membaca data daerah Sepang dari Supabase."""
import streamlit as st
st.set_page_config(page_title="SPM 2026 - PPD Sepang", layout="wide", page_icon="📚", initial_sidebar_state="collapsed")
from daerah_app import run_daerah
run_daerah("BJ")
