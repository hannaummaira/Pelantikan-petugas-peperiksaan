# -*- coding: utf-8 -*-
"""PPD Hulu Selangor (BE) - SUP + PPD. Hanya membaca data daerah Hulu Selangor dari Supabase."""
import streamlit as st
st.set_page_config(page_title="SPM 2026 - PPD Hulu Selangor", layout="wide", page_icon="📚", initial_sidebar_state="collapsed")
from daerah_app import run_daerah
run_daerah("BE")
