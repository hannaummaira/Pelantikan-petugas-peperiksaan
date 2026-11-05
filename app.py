# -*- coding: utf-8 -*-
"""Sistem Pelantikan Petugas SPM Selangor 2026 - SATU URL (JPN + 10 PPD). Main file: app.py"""
import streamlit as st
from tahun_sistem import tahun_semasa
st.set_page_config(page_title=f"SPM {tahun_semasa()} - Selangor", layout="wide", page_icon="📚", initial_sidebar_state="collapsed")
from main_app import run_app
run_app()
