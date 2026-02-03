"""Step2: 様式グループの確認・手動修正"""
import streamlit as st
import cv2

def show():
    st.header("2. 様式グループの確認")
    st.info("レイアウトが似ている領収書を自動でグループ分けしました。間違いがあれば番号を変更してください。")
    
    if not st.session_state.pages:
        st.warning("まずステップ1でPDFを読み込んでください。")
        return

    unique_styles = sorted(list(set(p["style_id"] for p in st.session_state.pages)))
    
    for sid in unique_styles:
        with st.container():
            st.subheader(f"📂 グループ {sid}")
            pages_in_style = [p for p in st.session_state.pages if p["style_id"] == sid]
            
            cols = st.columns(5)
            for idx, p in enumerate(pages_in_style):
                with cols[idx % 5]:
                    img_display = cv2.cvtColor(p["img"], cv2.COLOR_BGR2RGB)
                    st.image(img_display, caption=f"{p['page_num']}ページ目", use_column_width=True)
                    
                    new_id = st.number_input(
                        f"グループ番号", 
                        0, 20, sid, 
                        key=f"classify_{p['page_num']}"
                    )
                    if new_id != sid:
                        p["style_id"] = new_id
                        st.rerun()
    
    st.divider()
    if st.button("確定して次へ", use_container_width=True, type="primary"):
        st.session_state.step_idx = 2
        st.rerun()
