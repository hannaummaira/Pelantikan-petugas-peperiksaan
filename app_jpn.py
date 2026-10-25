
import streamlit as st
st.set_page_config(page_title="JPN - SPM", layout="wide", page_icon="🏛️")
from common.config import TAHUN_PILIHAN, tahun_aktif
from modules.jpn_module import render_jpn
def bar():
    t=tahun_aktif()
    st.radio("📅 Tahun", TAHUN_PILIHAN, index=TAHUN_PILIHAN.index(t), horizontal=True, key="tahun_jpn", on_change=lambda: st.session_state.update({"_tahun": int(st.session_state["tahun_jpn"])}))
st.title(f"JPN - Tahun {tahun_aktif()}")
bar()
render_jpn()
