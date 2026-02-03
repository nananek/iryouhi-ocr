"""Step3: 各様式のOCR対象領域を矩形で指定"""
import streamlit as st
import cv2
from streamlit_drawable_canvas import st_canvas
from PIL import Image

def show():
    target_labels = ["領収金額", "自費金額", "日付", "受診者名", "医療機関名"]
    unique_styles = sorted(list(set(p["style_id"] for p in st.session_state.pages)))
    
    if st.session_state.wiz_style_idx >= len(unique_styles):
        st.success("すべてのグループの設定が完了しました！")
        if st.button("OCR実行へ進む", use_container_width=True, type="primary"):
            st.session_state.step_idx = 3
            st.rerun()
        st.stop()

    current_sid = unique_styles[st.session_state.wiz_style_idx]
    current_label = target_labels[st.session_state.wiz_field_idx]
    
    st.header(f"3. 読取位置の指定")
    st.info(f"グループ {current_sid} の代表画像です。各項目の位置を矩形で囲んでください。")
    rep = next(p for p in st.session_state.pages if p["style_id"] == current_sid)
    pil_img = Image.fromarray(cv2.cvtColor(rep["img"], cv2.COLOR_BGR2RGB))
    
    canvas_w = 800
    scale = pil_img.size[0] / canvas_w
    canvas_h = int(pil_img.size[1] / scale)

    st.subheader(f"📍 「{current_label}」の位置を囲んでください")
    canvas_res = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)", stroke_width=1, stroke_color="#e00",
        background_image=pil_img, width=canvas_w, height=canvas_h,
        drawing_mode="rect", key=f"wiz_{current_sid}_{st.session_state.wiz_field_idx}"
    )

    col1, col2 = st.columns(2)
    
    def advance_to_next():
        if st.session_state.wiz_field_idx < len(target_labels) - 1:
            st.session_state.wiz_field_idx += 1
        else:
            st.session_state.wiz_field_idx = 0
            st.session_state.wiz_style_idx += 1

    with col1:
        if st.button("この位置で確定", use_container_width=True, type="primary"):
            if canvas_res.json_data and canvas_res.json_data["objects"]:
                obj = canvas_res.json_data["objects"][-1]
                if current_sid not in st.session_state.templates:
                    st.session_state.templates[current_sid] = {}
                st.session_state.templates[current_sid][current_label] = {
                    "x": int(obj["left"] * scale), "y": int(obj["top"] * scale),
                    "w": int(obj["width"] * scale), "h": int(obj["height"] * scale)
                }
                advance_to_next()
                st.rerun()
    
    with col2:
        if st.button("この項目をスキップ", use_container_width=True):
            advance_to_next()
            st.rerun()