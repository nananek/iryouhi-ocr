# 医療費OCR集計

確定申告用の医療費領収書をOCRで読み取り、CSVに集計するStreamlitアプリケーションです。

## 機能

- PDFからの画像展開（300DPI）
- レイアウト類似度による領収書の自動グループ分け
- グループごとに読取位置を矩形で指定
- YomiToku OCRによる文字認識
- 日付の自動正規化（和暦・西暦対応）
- CSV出力

## 必要環境

- Docker & Docker Compose（推奨）
- または Python 3.10+ & CUDA対応GPU

## セットアップ

### Docker（推奨）

```bash
docker compose up --build
```

ブラウザで http://localhost:8501 にアクセス

### ローカル実行

OCRサーバーとフロントエンドを別々に起動する必要があります。

ターミナル1（OCRサーバー / GPU必要）:
```bash
cd server
pip install -r requirements.txt
uvicorn ocr_server:app --host 0.0.0.0 --port 8000
```

ターミナル2（フロントエンド）:
```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

OCRサーバーが別ホストにある場合は、環境変数で接続先を指定できます:
```bash
export OCR_SERVER_URL=http://192.168.1.100:8000
streamlit run app.py
```

## プロジェクト構成

```
├── frontend/          # Streamlitフロントエンド
│   ├── app.py
│   ├── step1_upload.py
│   ├── step2_classify.py
│   ├── step3_wizard.py
│   ├── step4_ocr.py
│   ├── utils.py
│   ├── ocr_client.py
│   ├── components/
│   ├── requirements.txt
│   └── Dockerfile
├── server/            # OCRサーバー
│   ├── ocr_server.py
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## 使い方
2. **様式の確認**: 自動グループ分けを確認・修正
3. **読取位置の指定（手動 or LLM自動検出）**: 各グループで領収金額・日付などの位置を矩形で囲むか、LLM（Vision対応モデル）に自動検出させることができます。自動検出は代表画像をモデルに送信し、各フィールドのバウンディングボックス（x,y,w,h）をJSONで受け取ってテンプレートに反映します。自動検出が失敗した場合は手動入力にフォールバックします。

	 - 有効化方法（環境変数）:

		 - `AI_DETECTOR_PROVIDER` = `ollama` | `openai` | `disabled`（デフォルト）
		 - Ollama の場合:
			 - `OLLAMA_BASE_URL` = `http://<ollama-host>:11434`
			 - `OLLAMA_MODEL` = `llava:7b-v1.6-mistral-q4_K_M`（RTX 3050 6GB に推奨の量子化モデル）
			 - 初回はモデルを pull する必要があります（Ollama コンテナ内または Ollama サーバ上で実行）:

				 ```bash
				 ollama pull llava:7b-v1.6-mistral-q4_K_M
				 ```

		 - OpenAI の場合:
			 - `OPENAI_API_KEY` を設定し、`OPENAI_MODEL` に対応モデルを指定します（例: `gpt-4o` 等）。

	 - 動作の流れ:
		 1. 各グループの代表画像に対して一度自動検出を試行します。
		 2. 検出結果がある場合はテンプレートにプリセットされ、ユーザーは確認・微調整できます。
		 3. 検出が失敗した場合は警告を表示し、従来通り手動で矩形を指定します。

4. **OCR実行・出力**: 結果を確認してCSVダウンロード

## 対応日付形式

- `令和7年1月2日`
- `R7.1.2`
- `2025/01/02`
- `2025年1月2日`
- `2025-01-02`

## ライセンス

MIT License

## 注意事項

- YomiTokuは非商用利用のみ無償です。商用利用には別途ライセンスが必要です。
- OCR精度は画像品質に依存します。300DPI以上でのスキャンを推奨します。
