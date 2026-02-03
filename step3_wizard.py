"""Step3: 各様式のOCR対象領域を矩形で指定"""
import streamlit as st
import cv2
from PIL import Image
import base64
import io
import sys
import os

# コンポーネントのパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'components'))
from rect_selector import rect_selector


def image_to_base64(pil_img: Image.Image) -> str:
    """PIL画像をBase64文字列に変換"""
    buffer = io.BytesIO()
    pil_img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def show():
    target_labels = ["領収金額", "自費金額", "日付", "受診者名", "医療機関名"]
    unique_styles = sorted(list(set(p["style_id"] for p in st.session_state.pages)))
    
    if st.session_state.wiz_style_idx >= len(unique_styles):
        st.success("すべてのグループの設定が完了しました！")
        if st.button("OCR実行へ進む", type="primary"):
            st.session_state.step_idx = 3
            st.rerun()
        st.stop()

    current_sid = unique_styles[st.session_state.wiz_style_idx]
    current_label = target_labels[st.session_state.wiz_field_idx]
    
    st.header(f"3. 読取位置の指定")
    
    # 進捗表示（静的なプログレスバー）
    total_fields = len(target_labels)
    current_field = st.session_state.wiz_field_idx + 1
    total_styles = len(unique_styles)
    current_style_num = st.session_state.wiz_style_idx + 1
    progress_pct = ((st.session_state.wiz_style_idx * total_fields) + current_field) / (total_styles * total_fields) * 100
    
    st.markdown(f"""
    <div style="margin-bottom: 1rem;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 14px; color: #555;">
            <span>グループ {current_style_num}/{total_styles} - 項目 {current_field}/{total_fields}</span>
            <span>{progress_pct:.0f}%</span>
        </div>
        <div style="background: #e0e0e0; border-radius: 4px; height: 8px; overflow: hidden;">
            <div style="background: #4CAF50; height: 100%; width: {progress_pct}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.info(f"グループ {current_sid} の代表画像です。「**{current_label}**」の位置を矩形で囲んでください。")
    rep = next(p for p in st.session_state.pages if p["style_id"] == current_sid)
    pil_img = Image.fromarray(cv2.cvtColor(rep["img"], cv2.COLOR_BGR2RGB))
    
    canvas_w = 800
    scale = pil_img.size[0] / canvas_w
    canvas_h = int(pil_img.size[1] / scale)
    
    # 画像をBase64に変換
    img_b64 = image_to_base64(pil_img.resize((canvas_w, canvas_h), Image.LANCZOS))

    # 戻るボタンの有効/無効
    can_go_back = st.session_state.wiz_field_idx > 0 or st.session_state.wiz_style_idx > 0
    
    # ヘルパー関数
    def go_back():
        if st.session_state.wiz_field_idx > 0:
            st.session_state.wiz_field_idx -= 1
        elif st.session_state.wiz_style_idx > 0:
            st.session_state.wiz_style_idx -= 1
            st.session_state.wiz_field_idx = len(target_labels) - 1
    
    def advance_to_next():
        if st.session_state.wiz_field_idx < len(target_labels) - 1:
            st.session_state.wiz_field_idx += 1
        else:
            st.session_state.wiz_field_idx = 0
            st.session_state.wiz_style_idx += 1
    
    st.subheader(f"📍 「{current_label}」")
    
    # 既存の矩形データを取得（戻った時に表示するため）
    initial_rect = None
    if current_sid in st.session_state.templates:
        if current_label in st.session_state.templates[current_sid]:
            initial_rect = st.session_state.templates[current_sid][current_label]
    
    # 矩形選択コンポーネント
    result = rect_selector(
        image_base64=img_b64,
        width=canvas_w,
        height=canvas_h,
        scale=scale,
        can_go_back=can_go_back,
        initial_rect=initial_rect,
        key=f"rect_{current_sid}_{st.session_state.wiz_field_idx}"
    )
    
    # コンポーネントからの結果を処理
    if result:
        action = result.get("action")
        if action == "confirm":
            rect_data = result.get("rect")
            if rect_data:
                if current_sid not in st.session_state.templates:
                    st.session_state.templates[current_sid] = {}
                st.session_state.templates[current_sid][current_label] = rect_data
                advance_to_next()
                st.rerun()
        elif action == "skip":
            advance_to_next()
            st.rerun()
        elif action == "back" and can_go_back:
            go_back()
            st.rerun()
    
    # 現在設定済みの項目を表示
    if current_sid in st.session_state.templates and st.session_state.templates[current_sid]:
        st.markdown("---")
        st.markdown("**設定済みの項目:**")
        for label, r in st.session_state.templates[current_sid].items():
            st.caption(f"• {label}: ({r['x']}, {r['y']}) - {r['w']}x{r['h']}px")
