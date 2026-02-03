"""AI Vision モデルによる OCR 領域自動検出クライアント"""
import os
import json
import base64
import logging
from abc import ABC, abstractmethod
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# 環境変数から設定を読み込み
AI_DETECTOR_PROVIDER = os.environ.get("AI_DETECTOR_PROVIDER", "disabled")  # "ollama", "openai", "disabled"
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llava:7b-v1.6-mistral-q4_K_M")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

# フィールド検出用のプロンプト（日本語・相対位置で返答）
DETECTION_PROMPT = """あなたは日本の医療費領収書の画像を分析するアシスタントです。

以下の5つの項目について、画像内での位置を特定してください：

1. **領収金額**: 合計金額（通常、最も大きく目立つ数字。「領収金額」「合計」などのラベル付近）
2. **自費金額**: 保険外診療等で患者が負担した金額（「保険外」「負担額」などのラベル付近）
3. **日付**: 領収書の発行日または受診日（「発行日」「領収日」付近、または上部に記載）
4. **受診者名**: 患者の氏名（「患者名」「氏名」「様」付近）
5. **医療機関名**: 病院・クリニック・薬局などの名前（通常、領収書の上部または下部に大きく記載）

## 回答形式

各項目の位置を **画像全体に対するパーセンテージ（0〜100）** で指定してください。
- `x`: 左端からの位置（%）
- `y`: 上端からの位置（%）
- `w`: 幅（%）
- `h`: 高さ（%）

例: 画像の左上1/4の領域なら x=0, y=0, w=25, h=25

## 重要な注意点

- 位置は **おおよそ** で構いません。少し広めに指定してください。
- 該当する項目が見つからない場合は、その項目を省略してください。
- **JSONのみ** を返してください。説明文やマークダウンは不要です。

## 回答例

```json
{{
  "領収金額": {{"x": 60, "y": 30, "w": 35, "h": 8}},
  "自費金額": {{"x": 60, "y": 45, "w": 30, "h": 6}},
  "日付": {{"x": 10, "y": 5, "w": 25, "h": 5}},
  "受診者名": {{"x": 10, "y": 15, "w": 30, "h": 5}},
  "医療機関名": {{"x": 30, "y": 85, "w": 40, "h": 8}}
}}
```

それでは、添付の医療費領収書画像を分析し、JSONのみで回答してください。"""


class AIDetectorClient(ABC):
    """AI Vision 検出クライアントの抽象基底クラス"""

    def __init__(self):
        # 最後のレスポンステキストやエラーを保持（デバッグ用）
        self.last_response_text: Optional[str] = None
        self.last_error: Optional[str] = None

    @abstractmethod
    def detect_fields(
        self, image_base64: str, width: int, height: int
    ) -> dict[str, dict]:
        """
        画像から各フィールドの矩形座標を検出する

        Args:
            image_base64: Base64エンコードされた画像データ
            width: 画像の幅 (px)
            height: 画像の高さ (px)

        Returns:
            {フィールド名: {"x", "y", "w", "h"}} の辞書
            検出失敗時は空の辞書
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """サーバーへの接続確認"""
        pass

    def _parse_response(self, text: str, width: int, height: int) -> dict[str, dict]:
        """レスポンステキストからJSONを抽出してパース（パーセンテージ→ピクセル変換）"""
        # デバッグ用に生レスポンスを格納
        try:
            self.last_response_text = text
            # マークダウンのコードブロックを除去
            text = text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                # 最初と最後の```行を除去
                lines = [l for l in lines if not l.strip().startswith("```")]
                text = "\n".join(lines)

            data = json.loads(text)

            # 結果を検証・正規化（パーセンテージからピクセルに変換）
            result = {}
            target_labels = ["領収金額", "自費金額", "日付", "受診者名", "医療機関名"]
            for label in target_labels:
                if label in data and isinstance(data[label], dict):
                    rect = data[label]
                    # 必要なキーがすべて存在し、数値であることを確認
                    if all(
                        k in rect and isinstance(rect[k], (int, float))
                        for k in ["x", "y", "w", "h"]
                    ):
                        # パーセンテージ（0〜100）からピクセルに変換
                        result[label] = {
                            "x": int(rect["x"] * width / 100),
                            "y": int(rect["y"] * height / 100),
                            "w": int(rect["w"] * width / 100),
                            "h": int(rect["h"] * height / 100),
                        }
            return result
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # パース失敗は last_error に保存
            self.last_error = str(e)
            logger.warning(f"Failed to parse AI response: {e}\nResponse: {text[:500]}")
            return {}

    def get_debug(self) -> dict:
        """デバッグ用情報を返す: last_response_text, last_error"""
        return {"response": self.last_response_text, "error": self.last_error}


class OllamaDetector(AIDetectorClient):
    """Ollama Vision モデル用クライアント"""

    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or OLLAMA_BASE_URL
        self.model = model or OLLAMA_MODEL
        self.timeout = 120.0  # Vision モデルは時間がかかる
        self.last_response_text = None
        self.last_error = None

    def health_check(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    def detect_fields(
        self, image_base64: str, width: int, height: int
    ) -> dict[str, dict]:
        payload = {
            "model": self.model,
            "prompt": DETECTION_PROMPT,
            "images": [image_base64],
            "stream": False,
            "options": {
                "temperature": 0.1,  # 低めで一貫した出力を期待
            },
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(f"{self.base_url}/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                response_text = data.get("response", "")
                # デバッグ情報を保持
                self.last_response_text = response_text
                self.last_error = None
                logger.info(f"Ollama response: {response_text[:500]}")
                return self._parse_response(response_text, width, height)
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Ollama detection failed: {e}")
            return {}


class OpenAIDetector(AIDetectorClient):
    """OpenAI Vision API 用クライアント"""

    def __init__(self, api_key: str = None, model: str = None, base_url: str = None):
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model or OPENAI_MODEL
        self.base_url = base_url or OPENAI_BASE_URL
        self.timeout = 60.0
        self.last_response_text = None
        self.last_error = None

    def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return resp.status_code == 200
        except Exception as e:
            logger.warning(f"OpenAI health check failed: {e}")
            return False

    def detect_fields(
        self, image_base64: str, width: int, height: int
    ) -> dict[str, dict]:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": DETECTION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.1,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                response_text = data["choices"][0]["message"]["content"]
                self.last_response_text = response_text
                self.last_error = None
                logger.info(f"OpenAI response: {response_text[:500]}")
                return self._parse_response(response_text, width, height)
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"OpenAI detection failed: {e}")
            return {}


# シングルトンインスタンス
_detector_instance: Optional[AIDetectorClient] = None
_detector_checked: bool = False


def get_detector() -> Optional[AIDetectorClient]:
    """
    設定に基づいて適切な AI Detector を返す
    接続できない場合や無効化されている場合は None を返す
    """
    global _detector_instance, _detector_checked

    if _detector_checked:
        return _detector_instance

    _detector_checked = True

    if AI_DETECTOR_PROVIDER == "disabled":
        logger.info("AI Detector is disabled")
        return None

    if AI_DETECTOR_PROVIDER == "ollama":
        detector = OllamaDetector()
        if detector.health_check():
            _detector_instance = detector
            logger.info(f"Ollama detector initialized: {OLLAMA_BASE_URL}")
        else:
            logger.warning("Ollama server not available, falling back to manual mode")

    elif AI_DETECTOR_PROVIDER == "openai":
        detector = OpenAIDetector()
        if detector.health_check():
            _detector_instance = detector
            logger.info("OpenAI detector initialized")
        else:
            logger.warning("OpenAI API not available, falling back to manual mode")

    else:
        logger.warning(f"Unknown AI_DETECTOR_PROVIDER: {AI_DETECTOR_PROVIDER}")

    return _detector_instance


def reset_detector():
    """Detector のキャッシュをリセット（設定変更時に使用）"""
    global _detector_instance, _detector_checked
    _detector_instance = None
    _detector_checked = False
