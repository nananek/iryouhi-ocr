"""Step1: PDF読込・画像展開・様式クラスタリング"""
import streamlit as st
import fitz
import cv2
import numpy as np
from utils import perform_clustering

def show():
    st.header("1. 領収書PDFの読み込み")
    st.info("医療費の領収書をスキャンしたPDFファイルを選択してください。複数ページ対応。")
    uploaded_file = st.file_uploader("PDFファイルを選択", type="pdf")
    
    if uploaded_file and st.button("読み込んで次へ", use_container_width=True):
        with st.spinner("PDFを画像に変換しています..."):
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            temp_imgs = []
            for p in doc:
                pix = p.get_pixmap(dpi=300)
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                if pix.n == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                else:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                temp_imgs.append(img)
            
            labels = perform_clustering(temp_imgs)
            st.session_state.pages = [
                {"img": img, "style_id": int(l), "page_num": i+1} 
                for i, (img, l) in enumerate(zip(temp_imgs, labels))
            ]
            st.session_state.step_idx = 1
            st.rerun()