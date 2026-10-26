# -*- coding: utf-8 -*-
"""PPD Petaling Perdana (BH) - SUP + PPD. Hanya membaca data daerah Petaling Perdana dari Supabase."""
import streamlit as st
st.set_page_config(page_title="SPM 2026 - PPD Petaling Perdana", layout="wide", page_icon="📚", initial_sidebar_state="collapsed")
from daerah_app import run_daerah
run_daerah("BH")
