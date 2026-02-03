"""OCR Server: FastAPI + GPU Semaphore for concurrent access control"""
import asyncio
import base64
import io
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# GPU同時実行数の上限 (環境変数で設定可能)
MAX_CONCURRENT_OCR = int(os.environ.get("MAX_CONCURRENT_OCR", "1"))

# グローバル変数
ocr_engine = None
gpu_semaphore = None


class OCRRequest(BaseModel):
    """OCRリクエスト"""
    image_base64: str
    options: Optional[dict] = None


class ROI(BaseModel):
    """領域指定"""
    label: str
    x: int
    y: int
    w: int
    h: int


class ExtractROIRequest(BaseModel):
    """ROI抽出リクエスト"""
    words_data: list
    rois: list[ROI]


class OCRResponse(BaseModel):
    """OCRレスポンス"""
    status: str
    words: list
    processing_time_ms: float


class ExtractROIResponse(BaseModel):
    """ROI抽出レスポンス"""
    extractions: dict[str, str]


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""
    status: str
    gpu_available: bool
    queue_size: int
    max_concurrent: int


def load_ocr_engine():
    """OCRエンジンをロード（シングルトン）"""
    global ocr_engine
    if ocr_engine is None:
        from yomitoku import OCR
        device = os.environ.get("OCR_DEVICE", "cuda")
        print(f"Loading YomiToku OCR engine on {device}...")
        ocr_engine = OCR(visualize=False, device=device)
        print("OCR engine loaded successfully!")
    return ocr_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションライフサイクル管理"""
    global gpu_semaphore
    gpu_semaphore = asyncio.Semaphore(MAX_CONCURRENT_OCR)
    
    # 起動時にOCRエンジンをプリロード
    load_ocr_engine()
    
    yield
    
    # シャットダウン時のクリーンアップ
    print("Shutting down OCR server...")


app = FastAPI(
    title="YomiToku OCR Server",
    description="GPU-accelerated OCR server with concurrent access control",
    version="1.0.0",
    lifespan=lifespan
)


def decode_image(image_base64: str) -> np.ndarray:
    """Base64エンコードされた画像をデコード"""
    image_data = base64.b64decode(image_base64)
    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode image")
    return img


def extract_text_from_roi(words_data: list, roi: dict) -> str:
    """
    OCR結果からROI内のテキストを文字単位で抽出（横書き1行想定）
    """
    matched_chars = []
    rx, ry, rw, rh = roi['x'], roi['y'], roi['w'], roi['h']
    roi_x2, roi_y2 = rx + rw, ry + rh
    
    for word in words_data:
        points = word.get('points', [])
        content = word.get('content', '')
        if len(points) < 4 or not content:
            continue
            
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        wx1, wy1 = min(xs), min(ys)
        wx2, wy2 = max(xs), max(ys)
        
        cy = (wy1 + wy2) / 2
        if not (ry <= cy <= roi_y2):
            continue
        
        char_count = len(content)
        word_width = wx2 - wx1
        char_width = word_width / char_count if char_count > 0 else 0
        
        for i, char in enumerate(content):
            char_cx = wx1 + char_width * (i + 0.5)
            if rx <= char_cx <= roi_x2:
                matched_chars.append({"char": char, "x": char_cx})

    matched_chars.sort(key=lambda k: k['x'])
    return "".join([m['char'] for m in matched_chars])


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """ヘルスチェック"""
    import torch
    return HealthResponse(
        status="healthy",
        gpu_available=torch.cuda.is_available(),
        queue_size=MAX_CONCURRENT_OCR - gpu_semaphore._value,
        max_concurrent=MAX_CONCURRENT_OCR
    )


@app.post("/ocr", response_model=OCRResponse)
async def run_ocr(request: OCRRequest):
    """
    画像に対してOCRを実行
    
    GPU Semaphoreにより同時実行数を制限
    """
    start_time = time.time()
    
    try:
        img = decode_image(request.image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")
    
    # GPU Semaphoreを取得してOCR実行
    async with gpu_semaphore:
        loop = asyncio.get_event_loop()
        
        def do_ocr():
            engine = load_ocr_engine()
            results, _ = engine(img)
            try:
                res_dict = results.model_dump()
            except AttributeError:
                res_dict = results.dict()
            return res_dict.get('words', [])
        
        words = await loop.run_in_executor(None, do_ocr)
    
    processing_time = (time.time() - start_time) * 1000
    
    return OCRResponse(
        status="completed",
        words=words,
        processing_time_ms=round(processing_time, 2)
    )


@app.post("/extract-roi", response_model=ExtractROIResponse)
async def extract_roi(request: ExtractROIRequest):
    """
    OCR結果から指定されたROI領域のテキストを抽出
    """
    extractions = {}
    for roi in request.rois:
        roi_dict = {"x": roi.x, "y": roi.y, "w": roi.w, "h": roi.h}
        text = extract_text_from_roi(request.words_data, roi_dict)
        extractions[roi.label] = text.strip()
    
    return ExtractROIResponse(extractions=extractions)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
