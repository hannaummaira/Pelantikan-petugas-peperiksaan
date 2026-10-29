# -*- coding: utf-8 -*-
"""
surat_clear.py - Function Clear Surat Lantikan untuk SUP & PPD
Untuk Sistem SPM 2026 Selangor

Fungsi: Reset status surat yang sudah sampai ke sekolah asal
- Clear status SURAT_SAMPAI_SEKOLAH_ASAL -> DILANTIK PPD
- Clear no_surat, tarikh_jana_surat, sekolah_asal_hantar
- Clear log table surat_hantar_sekolah_asal (jika ada)
- Support scope SUP (satu sekolah sahaja) dan PPD (satu daerah / semua sekolah / ikut IC)

Cara guna:
  from surat_clear import render_clear_surat_ui
  # dalam role_sup.py:
  render_clear_surat_ui(kod_ppd=kod_ppd, role="SUP", kod_sekolah=kod_sekolah)
  # dalam role_ppd.py:
  render_clear_surat_ui(kod_ppd=kod_ppd, role="PPD")

Atau guna function low-level:
  from surat_clear import clear_surat_lantikan
  clear_surat_lantikan(kod_ppd="BG", kod_sekolah="BBA0001", role="SUP")
  clear_surat_lantikan(kod_ppd="BG", role="PPD")  # clear satu daerah
"""

import streamlit as st
import datetime
from spm_core import supa, get_cadangan_df


# ================= CORE CLEAR FUNCTION =================
def clear_surat_lantikan(kod_ppd=None, kod_sekolah=None, role="PPD", ic_list=None, status_target="DILANTIK PPD"):
    """
    Clear surat lantikan.
    
    Args:
        kod_ppd: Kod daerah (BG, BT, GP, etc) - wajib untuk PPD & SUP
        kod_sekolah: Kod sekolah (untuk SUP - wajib, untuk PPD - optional filter)
        role: "SUP" atau "PPD"
        ic_list: List IC guru untuk clear specific sahaja (optional)
        status_target: Status selepas clear (default: DILANTIK PPD)
    
    Returns:
        (ok_count, err_list, details)
    """
    ok = 0
    err = []
    details = {"diclear": 0, "log_cleared": 0}
    
    try:
        # 1. Build query untuk cari rekod yang ada surat
        query = supa.table("cadangan_sup").select("id,ic_guru,kod_ppd,kod_sekolah_asal,status,no_surat")
        
        # Filter ikut status surat
        query = query.eq("status", "SURAT_SAMPAI_SEKOLAH_ASAL")
        
        # Filter ikut PPD
        if kod_ppd:
            # cuba filter ikut kod_ppd (lowercase dalam DB ada yang lower)
            # kita akan filter manual selepas fetch untuk selamat
            pass
        
        # Fetch dulu (limit 10000 untuk satu daerah ok)
        res = query.limit(10000).execute()
        rows = res.data or []
        
        # Filter manual ikut kod_ppd, kod_sekolah, ic_list
        filtered = []
        for r in rows:
            # Filter PPD
            if kod_ppd:
                r_ppd = str(r.get("kod_ppd") or "").upper().strip()
                if r_ppd and r_ppd != kod_ppd.upper():
                    # check juga lowercase
                    if r_ppd.lower() != kod_ppd.lower():
                        continue
            
            # Filter sekolah (SUP wajib filter sekolah dia sahaja)
            if kod_sekolah:
                r_sek = str(r.get("kod_sekolah_asal") or r.get("kod_sekolah") or "").upper().strip()
                # untuk SUP, dia hanya boleh clear sekolah dia sahaja
                if r_sek != kod_sekolah.upper():
                    continue
            
            # Filter IC jika ada list
            if ic_list:
                ic_norm = str(r.get("ic_guru") or "").strip()
                if ic_norm not in [str(x).strip() for x in ic_list]:
                    continue
            
            # Role check: SUP hanya boleh clear sekolah sendiri
            if role == "SUP" and not kod_sekolah:
                err.append("SUP mesti ada kod_sekolah")
                return 0, err, details
            
            filtered.append(r)
        
        if not filtered:
            return 0, [], {"diclear": 0, "msg": "Tiada surat untuk di-clear"}
        
        # 2. Clear dalam cadangan_sup - update balik
        ids = [r.get("id") for r in filtered if r.get("id")]
        
        # Payload clear - reset field surat
        payload = {
            "status": status_target,
            "no_surat": None,
            "tarikh_jana_surat": None,
            "sekolah_asal_hantar": None
        }
        
        # Batch update 100 IDs sekali
        for i in range(0, len(ids), 100):
            batch = ids[i:i+100]
            try:
                supa.table("cadangan_sup").update(payload).in_("id", batch).execute()
                ok += len(batch)
            except Exception as e:
                err.append(f"Batch {i}: {str(e)[:100]}")
        
        details["diclear"] = ok
        
        # 3. Clear log table surat_hantar_sekolah_asal jika ada
        try:
            # Delete log ikut kod_ppd dan ic
            if kod_ppd:
                # cuba delete ikut kod_ppd
                try:
                    # filter ikut kod_ppd
                    log_res = supa.table("surat_hantar_sekolah_asal").select("id,ic_guru,kod_ppd").eq("kod_ppd", kod_ppd).limit(10000).execute()
                    log_ids = [l.get("id") for l in (log_res.data or []) if l.get("id")]
                    # further filter ikut sekolah jika SUP
                    if kod_sekolah and log_res.data:
                        # need to fetch kod_sekolah_asal juga
                        log_res2 = supa.table("surat_hantar_sekolah_asal").select("id,kod_sekolah_asal").eq("kod_ppd", kod_ppd).limit(10000).execute()
                        log_ids = []
                        for l in (log_res2.data or []):
                            if kod_sekolah:
                                if str(l.get("kod_sekolah_asal") or "").upper() == kod_sekolah.upper():
                                    if l.get("id"):
                                        log_ids.append(l.get("id"))
                            else:
                                if l.get("id"):
                                    log_ids.append(l.get("id"))
                    
                    if ic_list:
                        # filter ikut IC
                        log_res3 = supa.table("surat_hantar_sekolah_asal").select("id,ic_guru").eq("kod_ppd", kod_ppd).limit(10000).execute()
                        log_ids = [l.get("id") for l in (log_res3.data or []) if str(l.get("ic_guru") or "").strip() in [str(x).strip() for x in ic_list]]
                    
                    # delete batch
                    for j in range(0, len(log_ids), 100):
                        b = log_ids[j:j+100]
                        try:
                            supa.table("surat_hantar_sekolah_asal").delete().in_("id", b).execute()
                            details["log_cleared"] += len(b)
                        except:
                            pass
                except Exception:
                    # table tak wujud atau tiada permission - ignore
                    pass
        except Exception:
            pass
        
        # Clear cache
        try:
            get_cadangan_df.clear()
        except:
            pass
        
        return ok, err, details
        
    except Exception as e:
        err.append(str(e)[:200])
        return ok, err, details


def get_surat_count(kod_ppd=None, kod_sekolah=None):
    """Dapatkan bilangan surat yang sudah sampai (untuk display)"""
    try:
        q = supa.table("cadangan_sup").select("id,kod_ppd,kod_sekolah_asal", count="exact").eq("status", "SURAT_SAMPAI_SEKOLAH_ASAL").limit(1).execute()
        # count sahaja - tapi perlu filter manual untuk tepat
        # fetch semua untuk count tepat
        res = supa.table("cadangan_sup").select("id,kod_ppd,kod_sekolah_asal,ic_guru,nama_guru").eq("status", "SURAT_SAMPAI_SEKOLAH_ASAL").limit(10000).execute()
        rows = res.data or []
        if kod_ppd:
            rows = [r for r in rows if str(r.get("kod_ppd") or "").upper() == kod_ppd.upper() or str(r.get("kod_ppd") or "").lower() == kod_ppd.lower()]
        if kod_sekolah:
            rows = [r for r in rows if str(r.get("kod_sekolah_asal") or "").upper() == kod_sekolah.upper()]
        return len(rows), rows
    except Exception as e:
        return 0, []


# ================= UI UNTUK SUP & PPD =================
def render_clear_surat_ui(kod_ppd, role="PPD", kod_sekolah=None):
    """
    UI untuk clear surat - boleh panggil dari role_sup.py dan role_ppd.py
    
    Args:
        kod_ppd: Kod daerah (BG, etc)
        role: "SUP" atau "PPD"
        kod_sekolah: Kod sekolah (wajib jika role=SUP)
    """
    st.markdown("---")
    if role == "SUP":
        st.subheader(f"🗑️ Clear Surat Lantikan - Sekolah {kod_sekolah}")
        st.caption("Fungsi ini akan reset surat yang sudah sampai ke sekolah asal, kembali ke status DILANTIK PPD. Hanya untuk sekolah anda sahaja.")
    else:
        st.subheader(f"🗑️ Clear Surat Lantikan - PPD {kod_ppd}")
        st.caption("PPD boleh clear surat untuk satu daerah, satu sekolah, atau semua. Surat akan kembali ke status DILANTIK PPD untuk dijana semula.")
    
    # Papar bilangan surat sedia ada
    count, rows = get_surat_count(kod_ppd=kod_ppd, kod_sekolah=kod_sekolah if role=="SUP" else None)
    
    if count == 0:
        st.info(f"✅ Tiada surat yang perlu di-clear. Tiada rekod dengan status SURAT_SAMPAI_SEKOLAH_ASAL untuk {kod_sekolah or kod_ppd}.")
        return
    
    st.warning(f"⚠️ Terdapat **{count} surat** dengan status SURAT_SAMPAI_SEKOLAH_ASAL yang akan di-clear.")
    
    # Untuk PPD - bagi option filter
    filter_sekolah = None
    filter_ic = None
    
    if role == "PPD":
        with st.expander(f"📋 Lihat {count} surat yang akan di-clear", expanded=False):
            import pandas as pd
            df = pd.DataFrame([{
                "IC": r.get("ic_guru") or r.get("IC_GURU") or "",
                "NAMA": r.get("nama_guru") or r.get("NAMA_GURU") or "",
                "SEKOLAH ASAL": r.get("kod_sekolah_asal") or "",
                "NO SURAT": r.get("no_surat") or ""
            } for r in rows[:100]])
            st.dataframe(df, use_container_width=True, hide_index=True)
            if count > 100:
                st.caption(f"Menunjukkan 100 dari {count} rekod.")
        
        c1, c2 = st.columns(2)
        with c1:
            mode = st.radio("Mode Clear:", ["Satu Daerah (Semua)", "Satu Sekolah Sahaja", "Pilih IC Tertentu"], key=f"clear_mode_{kod_ppd}_{role}")
        
        with c2:
            if mode == "Satu Sekolah Sahaja":
                # List sekolah yang ada surat
                sek_list = sorted(set([str(r.get("kod_sekolah_asal") or "").upper() for r in rows if r.get("kod_sekolah_asal")]))
                filter_sekolah = st.selectbox("Pilih Sekolah:", sek_list, key=f"clear_sek_{kod_ppd}")
                st.caption(f"{len([r for r in rows if str(r.get('kod_sekolah_asal') or '').upper() == filter_sekolah])} surat untuk sekolah ini")
            elif mode == "Pilih IC Tertentu":
                ic_input = st.text_area("Masukkan IC (satu per baris):", key=f"clear_ic_{kod_ppd}", placeholder="990101015555\n880202026666")
                if ic_input:
                    filter_ic = [x.strip() for x in ic_input.split("\n") if x.strip()]
                    st.caption(f"{len(filter_ic)} IC dimasukkan")
    
    else:  # SUP
        with st.expander(f"📋 Lihat {count} surat sekolah anda", expanded=False):
            import pandas as pd
            df = pd.DataFrame([{
                "IC": r.get("ic_guru") or "",
                "NAMA": r.get("nama_guru") or "",
                "NO SURAT": r.get("no_surat") or ""
            } for r in rows])
            st.dataframe(df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    # Confirmation
    col1, col2 = st.columns([2,1])
    with col1:
        confirm_text = st.text_input(f"Taip **CLEAR {kod_sekolah or kod_ppd}** untuk sahkan:", key=f"clear_confirm_{kod_ppd}_{role}_{kod_sekolah or ''}")
        expected = f"CLEAR {kod_sekolah or kod_ppd}"
        is_confirmed = confirm_text.strip().upper() == expected.upper()
    
    with col2:
        st.write("")
        st.write("")
        if role == "SUP":
            target_kod_sekolah = kod_sekolah
            target_kod_ppd = kod_ppd
        else:
            if mode == "Satu Sekolah Sahaja":
                target_kod_sekolah = filter_sekolah
                target_kod_ppd = kod_ppd
            elif mode == "Pilih IC Tertentu":
                target_kod_sekolah = None
                target_kod_ppd = kod_ppd
            else:
                target_kod_sekolah = None
                target_kod_ppd = kod_ppd
        
        if st.button(f"🗑️ CLEAR SURAT SEKARANG", type="primary", disabled=not is_confirmed, key=f"btn_clear_{kod_ppd}_{role}", use_container_width=True):
            with st.spinner(f"Clearing {count} surat..."):
                if role == "PPD" and mode == "Pilih IC Tertentu" and filter_ic:
                    ok, err, details = clear_surat_lantikan(kod_ppd=target_kod_ppd, kod_sekolah=None, role=role, ic_list=filter_ic)
                elif role == "PPD" and mode == "Satu Sekolah Sahaja":
                    ok, err, details = clear_surat_lantikan(kod_ppd=target_kod_ppd, kod_sekolah=target_kod_sekolah, role=role)
                else:
                    ok, err, details = clear_surat_lantikan(kod_ppd=target_kod_ppd, kod_sekolah=target_kod_sekolah if role=="SUP" or mode=="Satu Sekolah Sahaja" else None, role=role)
                
                if err:
                    st.error(f"Ralat: {' | '.join(err[:3])}")
                if ok > 0:
                    st.success(f"✅ Berjaya clear {ok} surat! Status kembali ke DILANTIK PPD. Boleh jana semula.")
                    st.json(details)
                    st.balloons()
                    # Clear cache
                    try:
                        get_cadangan_df.clear()
                    except:
                        pass
                    st.rerun()
                else:
                    if not err:
                        st.info("Tiada surat yang di-clear.")
    
    if not is_confirmed and confirm_text:
        st.error(f"Sila taip tepat: {expected}")


# ================= QUICK CLEAR UNTUK JPN (OPTIONAL) =================
def render_clear_surat_jpn(kod_ppd=None):
    """Untuk JPN - boleh clear satu daerah atau semua daerah"""
    st.subheader("🗑️ Clear Surat Lantikan - JPN (Semua Daerah)")
    st.caption("JPN boleh clear surat untuk mana-mana daerah atau semua daerah sekaligus.")
    
    from spm_core import KOD_DAERAH, PPD_MAP
    
    c1, c2 = st.columns(2)
    with c1:
        pilihan = st.selectbox("Pilih Daerah:", ["SEMUA DAERAH"] + [f"{k} - {PPD_MAP.get(k,k)}" for k in KOD_DAERAH], key="jpn_clear_ppd")
    with c2:
        if pilihan == "SEMUA DAERAH":
            kod_target = None
        else:
            kod_target = pilihan.split(" - ")[0]
    
    count, _ = get_surat_count(kod_ppd=kod_target)
    st.metric("Surat akan di-clear", f"{count} rekod" if kod_target else f"{count} rekod (semua daerah)" if count else "0")
    
    confirm = st.text_input(f"Taip CLEAR {kod_target or 'SEMUA'} untuk sahkan:", key="jpn_clear_confirm")
    if st.button("🗑️ CLEAR", type="primary", disabled=confirm.strip().upper() != f"CLEAR {kod_target or 'SEMUA'}".upper(), key="jpn_clear_btn"):
        with st.spinner("Clearing..."):
            if kod_target:
                ok, err, _ = clear_surat_lantikan(kod_ppd=kod_target, role="PPD")
            else:
                # Clear semua daerah satu-satu
                total_ok = 0
                total_err = []
                for k in KOD_DAERAH:
                    o, e, _ = clear_surat_lantikan(kod_ppd=k, role="PPD")
                    total_ok += o
                    total_err.extend(e)
                ok, err = total_ok, total_err
            
            if ok:
                st.success(f"✅ {ok} surat cleared!")
                st.rerun()
            else:
                st.error(f"Gagal: {err}")
