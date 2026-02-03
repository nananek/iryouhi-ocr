"""医療費領収書OCRアプリケーション - メインエントリーポイント"""
import streamlit as st
import step1_upload, step2_classify, step3_wizard, step4_ocr

if "pages" not in st.session_state:
    st.session_state.update({
        "pages": [], "templates": {}, "ocr_results": [], "step_idx": 0,
        "wiz_style_idx": 0, "wiz_field_idx": 0
    })

st.set_page_config(layout="wide", page_title="医療費OCR集計")

st.sidebar.title("🩺 医療費OCR集計")
steps = ["1. PDF読込", "2. 様式の確認", "3. 読取位置の指定", "4. OCR実行・出力"]
selected = st.sidebar.radio("ステップ", steps, index=st.session_state.step_idx)

if selected == "1. PDF読込":
    step1_upload.show()
elif selected == "2. 様式の確認":
    step2_classify.show()
elif selected == "3. 読取位置の指定":
    step3_wizard.show()
elif selected == "4. OCR実行・出力":
    step4_ocr.show()