import os
import subprocess
from flask import Flask, render_template, request, flash, redirect, url_for

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

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
        
        # ffmpeg問題を回避するため、確実に処理できるフォーマットを優先取得
        # フォーマット優先順位: m4a > mp3 > bestaudio
        download_success = False
        
        # 1. m4aフォーマット（ffmpeg不要）を最優先
        try:
            print("m4aフォーマットでダウンロード試行...")
            result = subprocess.run([
                "yt-dlp",
                "-f", "140/m4a/bestaudio",  # m4aまたはbestaudio
                "--no-playlist",
                "-o", f"{AUDIO_DIR}/{output_filename}",
                url
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                download_success = True
                print("m4aフォーマットでダウンロード成功")
            else:
                print(f"m4a失敗: {result.stderr}")
        except Exception as e:
            print(f"m4aダウンロードエラー: {e}")
        
        # 2. mp3フォーマットを試行（ffmpeg必要だが試してみる）
        if not download_success:
            try:
                print("mp3フォーマットでダウンロード試行...")
                result = subprocess.run([
                    "yt-dlp",
                    "-f", "bestaudio[ext=mp3]",  # mp3フォーマット優先
                    "--no-playlist",
                    "-o", f"{AUDIO_DIR}/{output_filename}",
                    url
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    download_success = True
                    print("mp3フォーマットでダウンロード成功")
                else:
                    print(f"mp3失敗: {result.stderr}")
            except Exception as e:
                print(f"mp3ダウンロードエラー: {e}")
        
        # 3. 最後の手段としてbestaudio
        if not download_success:
            try:
                print("bestaudioフォーマットでダウンロード試行...")
                result = subprocess.run([
                    "yt-dlp",
                    "-f", "bestaudio",
                    "--no-playlist",
                    "-o", f"{AUDIO_DIR}/{output_filename}",
                    url
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    download_success = True
                    print("bestaudioフォーマットでダウンロード成功")
            except subprocess.TimeoutExpired:
                flash('YouTube動画のダウンロードがタイムアウトしました')
                return redirect(url_for('index'))
            except Exception as e:
                print(f"bestaudioダウンロードエラー: {e}")
        
        if not download_success:
            flash(f'YouTube動画のダウンロードに失敗しました: {result.stderr if "result" in locals() else "すべてのフォーマットで失敗"}')
            return redirect(url_for('index'))
        
        # ダウンロードされたファイルを探す（ffmpeg不要なフォーマットを優先）
        audio_files = []
        try:
            for f in os.listdir(AUDIO_DIR):
                if f.startswith(task_id) and any(f.endswith(ext) for ext in ['.m4a', '.mp3', '.wav']):  # webmを除外
                    audio_files.append(f)
        except Exception as e:
            print(f"ディレクトリ読み込みエラー: {e}")
            
        # ffmpeg不要なフォーマットが見つからない場合、webmも含めて検索
        if not audio_files:
            try:
                for f in os.listdir(AUDIO_DIR):
                    if f.startswith(task_id) and any(f.endswith(ext) for ext in ['.mp3', '.m4a', '.webm', '.mp4']):
                        audio_files.append(f)
            except Exception as e:
                print(f"再検索エラー: {e}")
            
        if not audio_files:
            # エラー情報をより詳しく表示
            error_info = f"音声ファイルが見つかりませんでした。\n\nデバッグ情報:\n- 検索ディレクトリ: {AUDIO_DIR}\n- タスクID: {task_id}\n- yt-dlp出力: {result.stdout if 'result' in locals() else 'N/A'}\n- yt-dlpエラー: {result.stderr if 'result' in locals() else 'N/A'}"
            flash(error_info)
            return redirect(url_for('index'))
        
        # 最適なファイルを選択（m4a > mp3 > その他）
        preferred_extensions = ['.m4a', '.mp3', '.wav', '.webm', '.mp4']
        audio_file = None
        
        for ext in preferred_extensions:
            for f in audio_files:
                if f.endswith(ext):
                    audio_file = f
                    break
            if audio_file:
                break
                
        if not audio_file:
            audio_file = audio_files[0]  # フォールバック
        audio_path = os.path.join(AUDIO_DIR, audio_file)
        
        # ファイルサイズを取得
        file_size = os.path.getsize(audio_path) / (1024 * 1024)  # MB
        
        # Whisperで文字起こし
        text = ""
        try:
            import whisper
            import numpy as np
            
            # ファイルパスを絶対パスに変換
            absolute_audio_path = os.path.abspath(audio_path)
            print(f"Whisperで文字起こし中... ファイル: {absolute_audio_path}")
            print(f"ファイル存在確認: {os.path.exists(absolute_audio_path)}")
            
            # ffmpeg問題を根本的に解決
            import whisper
            import whisper.audio as whisper_audio
            
            # Whisperのload_audio関数をモンキーパッチ
            def load_audio_safe(path, sr=16000):
                """ffmpegを使わずに音声を読み込む"""
                try:
                    import librosa
                    print(f"librosaで音声読み込み試行: {path}")
                    audio, sr_orig = librosa.load(path, sr=sr)
                    return audio
                except Exception as e:
                    print(f"librosa失敗: {e}")
                    # 警告メッセージを表示
                    print("注意: ffmpegが見つからないため、一部の音声ファイルが処理できない可能性があります")
                    raise e
            
            try:
                model = whisper.load_model("base")
                
                # 一時的にload_audio関数を置き換え
                original_load_audio = whisper_audio.load_audio
                whisper_audio.load_audio = load_audio_safe
                
                try:
                    print("Whisperで文字起こし開始...")
                    result_whisper = model.transcribe(absolute_audio_path)
                    text = result_whisper["text"].strip()
                    print(f"文字起こし成功: {len(text)}文字")
                finally:
                    # 元の関数を復元
                    whisper_audio.load_audio = original_load_audio
                    
            except Exception as whisper_error:
                print(f"Whisper処理エラー: {whisper_error}")
                raise whisper_error
            
            # 結果保存
            txt_filename = audio_file.replace(".mp3", ".txt").replace(".m4a", ".txt")
            txt_path = os.path.join(OUTPUT_DIR, txt_filename)
            
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)
                
            print(f"文字起こし完了: {len(text)}文字")
            
        except ImportError:
            # Whisperがまだインストールされていない場合
            text = f"""音声ファイルのダウンロードは成功しました！
ファイル名: {audio_file}
ファイルサイズ: {file_size:.2f} MB

Whisperがまだインストール中です。
文字起こし機能を使用するには、Whisperのインストール完了をお待ちください。

YouTube URL: {url}
ダウンロードされた音声: {audio_path}"""

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"Whisper処理エラー: {e}")
            print(f"詳細エラー: {error_detail}")
            
            # 絶対パスも確認
            absolute_path = os.path.abspath(audio_path) if 'audio_path' in locals() else "不明"
            text = f"""音声ファイルのダウンロードは成功しましたが、文字起こしでエラーが発生しました。

ファイル名: {audio_file}
ファイルサイズ: {file_size:.2f} MB
エラー: {str(e)}

YouTube URL: {url}

音声ファイルパス（相対）: {audio_path if 'audio_path' in locals() else '不明'}
音声ファイルパス（絶対）: {absolute_path}
ファイル存在確認: {os.path.exists(audio_path) if 'audio_path' in locals() else False}

エラー詳細:
{error_detail}"""
        
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
    print("サーバーを起動中...")
    print("ブラウザで http://127.0.0.1:5000 にアクセスしてください")
    app.run(debug=True, host='127.0.0.1', port=5000)
