# -*- coding: utf-8 -*-
"""PPD Sabak Bernam (BF) - SUP + PPD. Hanya membaca data daerah Sabak Bernam dari Supabase."""
import streamlit as st
st.set_page_config(page_title="SPM 2026 - PPD Sabak Bernam", layout="wide", page_icon="📚", initial_sidebar_state="collapsed")
from daerah_app import run_daerah
run_daerah("BF")
