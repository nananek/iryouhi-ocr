"""Step4: YomiToku OCRによる文字認識・結果検証・CSV出力"""
import streamlit as st
import pandas as pd
import cv2
from yomitoku import OCR 
from utils import extract_text_from_roi, parse_date

def show():
    st.header("4. OCR実行・結果確認")
    
    st.markdown("""
        <style>
        [data-testid="stImage"] img {
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    if st.button("🚀 OCRを実行する", type="primary"):
        if not st.session_state.pages:
            st.error("読み込まれたページがありません。ステップ1からやり直してください。")
            return
        if not st.session_state.templates:
            st.error("読取位置が設定されていません。ステップ3で設定してください。")
            return
            
        ocr_engine = OCR(visualize=False, device="cuda")
        all_results = []
        
        with st.status("OCR処理中...", expanded=True) as status:
            for p in st.session_state.pages:
                img_bgr = p["img"]
                results, _ = ocr_engine(img_bgr)
                
                try:
                    res_dict = results.model_dump()
                except:
                    res_dict = results.dict()

                words_data = res_dict.get('words', [])

                template = st.session_state.templates.get(p["style_id"], {})
                row = {"ページ": p["page_num"], "グループ": p["style_id"]}
                
                if isinstance(template, dict):
                    st.subheader(f"ページ {p['page_num']}")
                    for label, coords in template.items():
                        text = extract_text_from_roi(words_data, coords)
                        text = text.strip()
                        if "金額" in label:
                            text = "".join(filter(str.isdigit, text))
                        elif "日付" in label or "日" in label:
                            text = parse_date(text)
                        row[label] = text
                        
                        x, y, w, h = coords['x'], coords['y'], coords['w'], coords['h']
                        cropped = img_bgr[y:y+h, x:x+w]
                        cropped_rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
                        
                        col1, col2 = st.columns([2, 3])
                        with col1:
                            st.image(cropped_rgb, width=200)
                        with col2:
                            st.text_input(label, value=text, key=f"p{p['page_num']}_{label}", disabled=True)
                
                all_results.append(row)
            status.update(label="OCR完了！", state="complete")
        st.session_state.ocr_results = all_results

    if st.session_state.ocr_results:
        st.subheader("📊 集計結果")
        df = pd.DataFrame(st.session_state.ocr_results)
        st.dataframe(df, width="stretch")
        st.download_button("📥 CSVファイルをダウンロード", df.to_csv(index=False).encode('utf-8-sig'), "医療費集計.csv")