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
3. **読取位置の指定**: 各グループで領収金額・日付などの位置を矩形で囲む
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
