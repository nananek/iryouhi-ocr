"""ユーティリティ関数: 日付パース、レイアウトクラスタリング、OCRテキスト抽出"""
import cv2
import numpy as np
import re
from datetime import date
from sklearn.cluster import AgglomerativeClustering

ZEN2HAN = str.maketrans('０１２３４５６７８９', '0123456789')

WAREKI_MAP = {
    '令和': 2019, 'r': 2019, 'R': 2019,
    '平成': 1989, 'h': 1989, 'H': 1989,
    '昭和': 1926, 's': 1926, 'S': 1926,
}

def parse_date(text: str, output_format: str = '%Y-%m-%d') -> str:
    """
    日本語日付形式を統一フォーマットに変換
    
    対応: 令和7年1月2日, R7.1.2, 2025/01/02, 2025年1月2日, 2025-01-02
    """
    if not text:
        return text
    
    text = text.translate(ZEN2HAN).strip()
    text = re.sub(r'\s+', '', text)
    
    year, month, day = None, None, None
    
    m = re.search(r'(令和|平成|昭和)(\d{1,2})年(\d{1,2})月(\d{1,2})日?', text)
    if m:
        era, y, month, day = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
        year = WAREKI_MAP[era] + y - 1
    
    if year is None:
        m = re.search(r'([RHSrhs])(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{1,2})', text)
        if m:
            era, y, month, day = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
            year = WAREKI_MAP[era] + y - 1
    
    if year is None:
        m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日?', text)
        if m:
            year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    
    if year is None:
        m = re.search(r'(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})', text)
        if m:
            year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    
    if year and month and day:
        try:
            return date(year, month, day).strftime(output_format)
        except ValueError:
            pass
    
    return text


def get_layout_fingerprint(img):
    """画像からレイアウト特徴量（フィンガープリント）を生成"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (300, 400))
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 11, 2)
    return cv2.GaussianBlur(binary, (21, 21), 0)

def perform_clustering(images):
    """画像群をレイアウト類似度でクラスタリング"""
    num = len(images)
    if num < 2: return [0]
    fps = [get_layout_fingerprint(m) for m in images]
    dist_matrix = np.zeros((num, num))
    for i in range(num):
        for j in range(i, num):
            res = cv2.matchTemplate(fps[i], fps[j], cv2.TM_CCOEFF_NORMED)
            _, score, _, _ = cv2.minMaxLoc(res)
            dist_matrix[i, j] = dist_matrix[j, i] = 1 - score
    return AgglomerativeClustering(n_clusters=None, distance_threshold=0.4, 
                                   metric='precomputed', linkage='complete').fit(dist_matrix).labels_

def extract_text_from_roi(words_data, roi):
    """
    OCR結果からROI内のテキストを文字単位で抽出（横書き1行想定）
    
    各文字の中心座標がROI内にあるかで判定。wordの幅を文字数で等分して推定。
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