"""Step3: 各様式のOCR対象領域を矩形で指定"""
import streamlit as st
import cv2
from PIL import Image
import base64
import io
import sys
import os
import logging

# コンポーネントのパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'components'))
from rect_selector import rect_selector
from ai_detector_client import get_detector

logger = logging.getLogger(__name__)


def image_to_base64(pil_img: Image.Image) -> str:
    """PIL画像をBase64文字列に変換"""
    buffer = io.BytesIO()
    pil_img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def run_auto_detection(style_id: str, pil_img: Image.Image, target_labels: list[str]) -> bool:
    """
    AI Vision モデルで自動検出を実行し、結果を session_state.templates に保存する
    
    Returns:
        True: 検出成功（1つ以上のフィールドを検出）
        False: 検出失敗または AI 未接続
    """
    detector = get_detector()
    if detector is None:
        return False
    
    # 画像をBase64に変換（オリジナルサイズで送信）
    img_b64 = image_to_base64(pil_img)
    width, height = pil_img.size
    
    try:
        with st.spinner("🤖 AI が読取位置を検出中..."):
            detected = detector.detect_fields(img_b64, width, height)
        
        if detected:
            if style_id not in st.session_state.templates:
                st.session_state.templates[style_id] = {}
            
            # 検出結果をマージ（既存の手動設定は上書きしない場合はここで制御可能）
            for label, rect in detected.items():
                if label in target_labels:
                    st.session_state.templates[style_id][label] = rect
            
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"Auto detection failed: {e}")
        return False


def show():
    target_labels = ["領収金額", "自費金額", "日付", "受診者名", "医療機関名"]
    unique_styles = sorted(list(set(p["style_id"] for p in st.session_state.pages)))
    
    # 自動検出の状態を初期化
    if "auto_detect_attempted" not in st.session_state:
        st.session_state.auto_detect_attempted = {}  # {style_id: True/False}
    if "auto_detect_failed" not in st.session_state:
        st.session_state.auto_detect_failed = {}  # {style_id: True/False}
    
    if st.session_state.wiz_style_idx >= len(unique_styles):
        st.success("すべてのグループの設定が完了しました！")
        if st.button("OCR実行へ進む", type="primary"):
            st.session_state.step_idx = 3
            st.rerun()
        st.stop()

    current_sid = unique_styles[st.session_state.wiz_style_idx]
    current_label = target_labels[st.session_state.wiz_field_idx]
    
    st.header(f"3. 読取位置の指定")
    
    # 代表画像を取得
    rep = next(p for p in st.session_state.pages if p["style_id"] == current_sid)
    pil_img = Image.fromarray(cv2.cvtColor(rep["img"], cv2.COLOR_BGR2RGB))
    
    # ========================================
    # 自動検出フェーズ（各グループの最初のみ）
    # ========================================
    detector = get_detector()
    is_first_field = st.session_state.wiz_field_idx == 0
    not_yet_attempted = current_sid not in st.session_state.auto_detect_attempted
    
    if detector is not None and is_first_field and not_yet_attempted:
        # 自動検出を試行
        st.info("🤖 AI による読取位置の自動検出を試みます...")
        
        success = run_auto_detection(current_sid, pil_img, target_labels)
        st.session_state.auto_detect_attempted[current_sid] = True
        
        if success:
            detected_count = len(st.session_state.templates.get(current_sid, {}))
            st.success(f"✅ {detected_count} 個の項目を自動検出しました！確認・修正してください。")
            st.session_state.auto_detect_failed[current_sid] = False
        else:
            st.warning("⚠️ 自動検出に失敗しました。手動で位置を指定してください。")
            st.session_state.auto_detect_failed[current_sid] = True
        
        st.rerun()
    
    # 自動検出失敗時のメッセージ（1回だけ表示）
    if current_sid in st.session_state.auto_detect_failed:
        if st.session_state.auto_detect_failed[current_sid] and is_first_field:
            st.warning("⚠️ このグループは自動検出に失敗したため、手動で位置を指定してください。")
    
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
    
    # 自動検出成功時は確認モードのメッセージ
    if current_sid in st.session_state.templates and st.session_state.templates[current_sid]:
        if not st.session_state.auto_detect_failed.get(current_sid, True):
            st.info(f"グループ {current_sid} の代表画像です。「**{current_label}**」の位置を確認・修正してください。")
        else:
            st.info(f"グループ {current_sid} の代表画像です。「**{current_label}**」の位置を矩形で囲んでください。")
    else:
        st.info(f"グループ {current_sid} の代表画像です。「**{current_label}**」の位置を矩形で囲んでください。")
    
    canvas_w = 800
    scale = pil_img.size[0] / canvas_w
    canvas_h = int(pil_img.size[1] / scale)
    
    # 画像をBase64に変換（キャンバス用にリサイズ）
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
    
    # 既存の矩形データを取得（自動検出結果または戻った時に表示するため）
    initial_rect = None
    if current_sid in st.session_state.templates:
        if current_label in st.session_state.templates[current_sid]:
            # 自動検出の座標はオリジナルサイズなので、キャンバス用にスケール変換
            orig_rect = st.session_state.templates[current_sid][current_label]
            initial_rect = {
                "x": int(orig_rect["x"] / scale),
                "y": int(orig_rect["y"] / scale),
                "w": int(orig_rect["w"] / scale),
                "h": int(orig_rect["h"] / scale),
            }
    
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
    
    # 再検出ボタン（AI利用可能時のみ）
    if detector is not None:
        st.markdown("---")
        if st.button("🔄 このグループを再度自動検出", type="secondary"):
            # 現在のグループのテンプレートと状態をリセット
            if current_sid in st.session_state.templates:
                del st.session_state.templates[current_sid]
            if current_sid in st.session_state.auto_detect_attempted:
                del st.session_state.auto_detect_attempted[current_sid]
            if current_sid in st.session_state.auto_detect_failed:
                del st.session_state.auto_detect_failed[current_sid]
            st.session_state.wiz_field_idx = 0
            st.rerun()

