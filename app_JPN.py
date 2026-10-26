# -*- coding: utf-8 -*-
"""JPN Selangor - pentadbir negeri (semua daerah)."""
import streamlit as st
st.set_page_config(page_title="SPM 2026 - JPN Selangor", layout="wide", page_icon="🏛️", initial_sidebar_state="collapsed")
from jpn_app import run_jpn
run_jpn()
