"""OCRサーバークライアント: HTTP API経由でOCRを実行"""
import base64
import os
import cv2
import numpy as np
import requests

OCR_SERVER_URL = os.environ.get("OCR_SERVER_URL", "http://localhost:8000")


class OCRClient:
    """OCRサーバーへのHTTPクライアント"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or OCR_SERVER_URL
    
    def health_check(self) -> dict:
        """サーバーの稼働状態を確認"""
        response = requests.get(f"{self.base_url}/health", timeout=5)
        response.raise_for_status()
        return response.json()
    
    def run_ocr(self, img_bgr: np.ndarray) -> list:
        """
        画像に対してOCRを実行
        
        Args:
            img_bgr: OpenCV BGR形式の画像 (numpy array)
            
        Returns:
            words_data: OCR結果のwordsリスト
        """
        # 画像をBase64エンコード
        _, buffer = cv2.imencode('.png', img_bgr)
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # OCRサーバーにリクエスト
        response = requests.post(
            f"{self.base_url}/ocr",
            json={"image_base64": image_base64},
            timeout=120  # OCRは時間がかかる場合がある
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get("words", [])
    
    def extract_roi(self, words_data: list, rois: list[dict]) -> dict:
        """
        OCR結果から指定領域のテキストを抽出
        
        Args:
            words_data: OCR結果のwordsリスト
            rois: ROI情報のリスト [{"label": "日付", "x": 100, "y": 200, "w": 150, "h": 30}, ...]
            
        Returns:
            extractions: {"label": "extracted_text", ...}
        """
        response = requests.post(
            f"{self.base_url}/extract-roi",
            json={"words_data": words_data, "rois": rois},
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get("extractions", {})


# デフォルトクライアントインスタンス
_default_client = None


def get_client() -> OCRClient:
    """デフォルトクライアントを取得（遅延初期化）"""
    global _default_client
    if _default_client is None:
        _default_client = OCRClient()
    return _default_client
