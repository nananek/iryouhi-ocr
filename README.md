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

- Python 3.10+
- CUDA対応GPU（推奨）

## インストール

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 使い方

```bash
streamlit run app.py
```

1. **PDF読込**: 医療費領収書をスキャンしたPDFをアップロード
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
