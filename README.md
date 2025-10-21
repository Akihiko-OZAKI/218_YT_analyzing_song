# YouTube音声分析アプリ

YouTube動画のURLを入力すると、動画内の会話・歌詞をテキスト化して表示するWebアプリケーションです。

## 機能

- YouTube動画のURL入力
- 音声の自動抽出・ダウンロード
- OpenAI Whisperによる高精度文字起こし
- 結果の表示・コピー・ダウンロード機能

## 技術スタック

- **バックエンド**: Flask (Python)
- **音声処理**: OpenAI Whisper, librosa, yt-dlp
- **フロントエンド**: HTML, CSS, Bootstrap
- **デプロイ**: Render

## デプロイ方法

### Renderでのデプロイ

1. GitHubリポジトリにコードをプッシュ
2. Renderで新しいWebサービスを作成
3. 以下の設定を使用：
   - **Build Command**: `pip install -r requirements.txt && apt-get update && apt-get install -y ffmpeg`
   - **Start Command**: `python app.py`
   - **Python Version**: 3.11

### 環境変数

- `SECRET_KEY`: Flaskの秘密鍵（省略可能）
- `PORT`: ポート番号（Renderが自動設定）

## ローカル開発

```bash
# 依存関係をインストール
pip install -r requirements.txt

# ffmpegをインストール（必要に応じて）
# Windows: https://ffmpeg.org/download.html
# macOS: brew install ffmpeg
# Ubuntu: sudo apt install ffmpeg

# アプリケーションを起動
python app.py
```

## ファイル構成

```
├── app.py              # メインアプリケーション
├── requirements.txt    # Python依存関係
├── Procfile           # Render用設定
├── runtime.txt        # Pythonバージョン指定
├── aptfile           # システム依存関係（ffmpeg）
├── templates/
│   ├── index.html    # メインページ
│   └── result.html   # 結果表示ページ
└── static/
    └── style.css     # スタイルシート
```

## ライセンス

MIT License
