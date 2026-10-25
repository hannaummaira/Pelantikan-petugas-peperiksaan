
import streamlit as st
st.set_page_config(page_title="PPD - SPM", layout="wide", page_icon="📄")
from common.config import TAHUN_PILIHAN, tahun_aktif
from modules.ppd_module import render_ppd
def bar():
    t=tahun_aktif()
    st.radio("📅 Tahun", TAHUN_PILIHAN, index=TAHUN_PILIHAN.index(t), horizontal=True, key="tahun_ppd", on_change=lambda: st.session_state.update({"_tahun": int(st.session_state["tahun_ppd"])}))
st.title(f"PPD - Tahun {tahun_aktif()}")
bar()
render_ppd()
