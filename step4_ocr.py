"""Step4: YomiToku OCRによる文字認識・結果検証・CSV出力"""
import streamlit as st
import pandas as pd
import cv2
from ocr_client import get_client
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
    
    # OCRサーバーの状態確認
    ocr_client = get_client()
    try:
        health = ocr_client.health_check()
        if health.get("queue_size", 0) > 0:
            st.warning(f"⏳ OCRサーバーは現在 {health['queue_size']}/{health['max_concurrent']} 件処理中です。順番待ちになる場合があります。")
    except Exception as e:
        st.error(f"❌ OCRサーバーに接続できません: {e}")
        return
    
    if st.button("🚀 OCRを実行する", type="primary"):
        if not st.session_state.pages:
            st.error("読み込まれたページがありません。ステップ1からやり直してください。")
            return
        if not st.session_state.templates:
            st.error("読取位置が設定されていません。ステップ3で設定してください。")
            return
            
        all_results = []
        # 切り抜き画像を保存するリスト
        cropped_images = []
        
        with st.status("OCR処理中...", expanded=True) as status:
            for p in st.session_state.pages:
                img_bgr = p["img"]
                
                # OCRサーバーにリクエスト
                try:
                    words_data = ocr_client.run_ocr(img_bgr)
                except Exception as e:
                    st.error(f"OCRエラー (ページ {p['page_num']}): {e}")
                    continue

                template = st.session_state.templates.get(p["style_id"], {})
                row = {"ページ": p["page_num"], "グループ": p["style_id"]}
                page_crops = {"ページ": p["page_num"]}
                
                if isinstance(template, dict):
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
                        page_crops[label] = cropped_rgb
                
                all_results.append(row)
                cropped_images.append(page_crops)
            status.update(label="OCR完了！", state="complete")
        st.session_state.ocr_results = all_results
        st.session_state.cropped_images = cropped_images

    # OCR結果の編集UI
    if st.session_state.ocr_results:
        st.subheader("📝 読み取り結果の確認・編集")
        st.info("読み取り結果に誤りがある場合は、下記のテキストボックスで修正してください。")
        
        cropped_images = st.session_state.get("cropped_images", [])
        
        for idx, row in enumerate(st.session_state.ocr_results):
            page_num = row.get("ページ", idx + 1)
            st.subheader(f"ページ {page_num}")
            
            # 対応する切り抜き画像を取得
            page_crops = cropped_images[idx] if idx < len(cropped_images) else {}
            
            for label in row.keys():
                if label in ["ページ", "グループ"]:
                    continue
                
                input_key = f"edit_p{page_num}_{label}"
                
                col1, col2 = st.columns([2, 3])
                with col1:
                    if label in page_crops:
                        st.image(page_crops[label], width=200)
                    else:
                        st.empty()
                with col2:
                    new_value = st.text_input(
                        label, 
                        value=row[label], 
                        key=input_key
                    )
                    # 編集された値を反映
                    st.session_state.ocr_results[idx][label] = new_value
            
            st.divider()

        st.subheader("📊 集計結果")
        df = pd.DataFrame(st.session_state.ocr_results)
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 CSVファイルをダウンロード", df.to_csv(index=False).encode('utf-8-sig'), "医療費集計.csv")