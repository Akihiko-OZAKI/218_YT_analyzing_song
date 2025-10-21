import os
import subprocess
from flask import Flask, render_template, request, flash, redirect, url_for

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# 設定
AUDIO_DIR = "temp_audio"
OUTPUT_DIR = "temp_output"

# フォルダ作成
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_video():
    url = request.form.get('url')
    
    if not url:
        flash('YouTube URLを入力してください')
        return redirect(url_for('index'))
    
    try:
        # YouTube音声ダウンロード
        print(f"YouTube音声をダウンロード中: {url}")
        
        # ユニークなファイル名を生成
        import uuid
        task_id = str(uuid.uuid4())
        output_filename = f"{task_id}.%(ext)s"
        
        # YouTube側のボット検出を回避するための複数のアプローチ
        download_success = False
        attempts = [
            # アプローチ1: 標準的な音声抽出
            {
                "name": "標準音声抽出",
                "cmd": [
                    "yt-dlp",
                    "-f", "bestaudio",
                    "--extract-audio",
                    "--audio-format", "mp3",
                    "--no-playlist",
                    "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "-o", f"{AUDIO_DIR}/{output_filename}",
                    url
                ]
            },
            # アプローチ2: 異なるUser-Agent
            {
                "name": "異なるUser-Agent",
                "cmd": [
                    "yt-dlp",
                    "-f", "bestaudio/best",
                    "--extract-audio",
                    "--audio-format", "mp3",
                    "--no-playlist",
                    "--user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "-o", f"{AUDIO_DIR}/{output_filename}",
                    url
                ]
            },
            # アプローチ3: 動画から抽出
            {
                "name": "動画から音声抽出",
                "cmd": [
                    "yt-dlp",
                    "-f", "best[height<=480]",
                    "--extract-audio",
                    "--audio-format", "mp3",
                    "--no-playlist",
                    "--user-agent", "Mozilla/5.0 (compatible; Googlebot/2.1)",
                    "-o", f"{AUDIO_DIR}/{output_filename}",
                    url
                ]
            }
        ]
        
        last_error = ""
        try:
            for attempt in attempts:
                print(f"ダウンロード試行: {attempt['name']}")
                result = subprocess.run(
                    attempt["cmd"],
                    capture_output=True, 
                    text=True, 
                    timeout=180
                )
                
                if result.returncode == 0:
                    download_success = True
                    print(f"成功: {attempt['name']}")
                    break
                else:
                    print(f"失敗: {attempt['name']} - {result.stderr}")
                    last_error = result.stderr
            
            if not download_success:
                # より具体的なエラーメッセージ
                if "Sign in to confirm you're not a bot" in last_error:
                    error_msg = """YouTube側のセキュリティ制限により、この動画の処理ができない可能性があります。

対処方法：
1. 別のYoutube動画URLを試してください
2. しばらく時間をおいてから再試行してください
3. 動画がプライベートまたは年齢制限されている場合は処理できません"""
                else:
                    error_msg = f"YouTube動画のダウンロードに失敗しました: {last_error[:300]}"
                
                flash(error_msg)
                return redirect(url_for('index'))
                
        except subprocess.TimeoutExpired:
            flash('YouTube動画のダウンロードがタイムアウトしました')
            return redirect(url_for('index'))
        
        # ダウンロードされたファイルを探す
        audio_files = []
        try:
            for f in os.listdir(AUDIO_DIR):
                if f.startswith(task_id) and any(f.endswith(ext) for ext in ['.mp3', '.m4a', '.webm', '.wav']):
                    audio_files.append(f)
        except Exception as e:
            print(f"ディレクトリ読み込みエラー: {e}")
            
        if not audio_files:
            flash('音声ファイルが見つかりませんでした')
            return redirect(url_for('index'))
        
        audio_file = audio_files[0]
        audio_path = os.path.join(AUDIO_DIR, audio_file)
        file_size = os.path.getsize(audio_path) / (1024 * 1024)  # MB
        
        # Whisperで文字起こし
        text = ""
        try:
            import whisper
            
            print("Whisperで文字起こし開始...")
            model = whisper.load_model("base")
            result_whisper = model.transcribe(audio_path)
            text = result_whisper["text"].strip()
            
            # 結果保存
            txt_filename = audio_file.replace(".mp3", ".txt").replace(".m4a", ".txt").replace(".webm", ".txt")
            txt_path = os.path.join(OUTPUT_DIR, txt_filename)
            
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)
                
            print(f"文字起こし完了: {len(text)}文字")
            
        except ImportError:
            text = f"""音声ファイルのダウンロードは成功しました！
ファイル名: {audio_file}
ファイルサイズ: {file_size:.2f} MB

Whisperがまだインストール中です。
文字起こし機能を使用するには、Whisperのインストール完了をお待ちください。

YouTube URL: {url}"""

        except Exception as e:
            print(f"Whisper処理エラー: {e}")
            text = f"""音声ファイルのダウンロードは成功しましたが、文字起こしでエラーが発生しました。

ファイル名: {audio_file}
ファイルサイズ: {file_size:.2f} MB
エラー: {str(e)}

YouTube URL: {url}"""
        
        # 一時ファイルを削除（成功した場合のみ）
        if text and len(text) > 50 and not ("エラーが発生しました" in text):
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                    print("一時ファイル削除完了")
            except Exception as e:
                print(f"ファイル削除エラー: {e}")
        
        return render_template('result.html', text=text, url=url)
        
    except subprocess.CalledProcessError as e:
        flash(f'YouTube URLが無効またはアクセスできません: {str(e)}')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'処理中にエラーが発生しました: {str(e)}')
        return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)