
import streamlit as st
st.set_page_config(page_title="SUP - SPM", layout="wide", page_icon="🏫")
from common.config import TAHUN_PILIHAN, tahun_aktif
from modules.sup_module import render_sup
def bar():
    t=tahun_aktif()
    st.radio("📅 Tahun", TAHUN_PILIHAN, index=TAHUN_PILIHAN.index(t), horizontal=True, key="tahun_sup", on_change=lambda: st.session_state.update({"_tahun": int(st.session_state["tahun_sup"])}))
st.title(f"SUP - Tahun {tahun_aktif()}")
bar()
render_sup()
