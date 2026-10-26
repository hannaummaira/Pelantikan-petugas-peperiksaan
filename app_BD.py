# -*- coding: utf-8 -*-
"""PPD Hulu Langat (BD) - SUP + PPD. Hanya membaca data daerah Hulu Langat dari Supabase."""
import streamlit as st
st.set_page_config(page_title="SPM 2026 - PPD Hulu Langat", layout="wide", page_icon="📚", initial_sidebar_state="collapsed")
from daerah_app import run_daerah
run_daerah("BD")
