# Windows版 Web Whisper ビルド手順

## 必要な環境

### 1. 開発環境
- **Windows 10/11** (64-bit)
- **Visual Studio 2022** または **Visual Studio Build Tools**
- **Node.js 18+** (LTS推奨)
- **Rust** (latest stable)
- **Python 3.11/3.12**
- **Git**

### 2. 必須ソフトウェア

#### Python環境
```powershell
# Python公式インストーラー推奨
# https://python.org からPython 3.11または3.12をインストール

# 仮想環境作成
python -m venv web-whisper
web-whisper\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt
```

#### FFmpeg
```powershell
# Chocolateyでインストール (推奨)
Set-ExecutionPolicy Bypass -Scope Process -Force
iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
choco install ffmpeg

# または手動インストール
# https://ffmpeg.org/download.html#build-windows
# C:\ffmpeg\bin にパスを通す
```

#### Node.js & pnpm
```powershell
# Node.js LTSをインストール
# https://nodejs.org

# pnpmインストール
npm install -g pnpm
```

#### Rust
```powershell
# Rustupインストール
# https://rustup.rs/
rustup target add x86_64-pc-windows-msvc
```

## ビルド手順

### 1. プロジェクトのセットアップ
```powershell
git clone <repository-url>
cd web-whisper

# Pythonバックエンドの準備
cd backend
python -m venv web-whisper
web-whisper\Scripts\activate
pip install -r requirements.txt

# フロントエンドの準備
cd ..\frontend
pnpm install
```

### 2. Windows用Pythonパッケージ
```powershell
# Windows版専用の依存関係
pip install faster-whisper
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 3. ビルド実行
```powershell
cd frontend
pnpm tauri build --target x86_64-pc-windows-msvc
```

### 4. 出力ファイル
ビルド成功後、以下に生成されます：
- **実行ファイル**: `src-tauri/target/x86_64-pc-windows-msvc/release/web-whisper.exe`
- **インストーラー**: `src-tauri/target/x86_64-pc-windows-msvc/release/bundle/msi/Web Whisper_0.1.0_x64_en-US.msi`

## 配布用パッケージ

### ポータブル版（単一EXE）

インストール不要で実行できる「単一EXE」を作成します。NSISで自己解凍し、一時フォルダに展開→実行→終了時にクリーンアップします。

前提:
- NSIS（`makensis` が PATH にあること）
- 既に backend 側car と Tauri アプリがビルド可能であること
- 任意: WebView2 Fixed Runtime を同梱したい場合、`windows-release/WebView2Runtime/` に配置

手順:
```powershell
# リポジトリルートで実行
python windows-release/prepare_portable.py --output WebWhisper-Portable.exe

# 既存のビルド成果物を使う場合（再ビルドをスキップ）
python windows-release/prepare_portable.py --skip-build --output WebWhisper-Portable.exe
```

生成物:
- `windows-release/WebWhisper-Portable.exe`（単一の自己解凍EXE）

注意:
- WebView2 ランタイムが未インストール環境では起動に失敗する場合があります。固定版ランタイム（Fixed Runtime）を `windows-release/WebView2Runtime/` に置くと同梱され、起動時に `WEBVIEW2_BROWSER_EXECUTABLE_FOLDER` が自動設定されます。
- 既存の Tauri `nsis`/`msi` バンドルは生成しません（`app` バンドルのみ）。

### オールインワンパッケージ（フォルダ配布）
```powershell
# 配布用フォルダ作成
mkdir web-whisper-windows
cd web-whisper-windows

# アプリケーション
copy ..\frontend\src-tauri\target\x86_64-pc-windows-msvc\release\web-whisper.exe .
mkdir backend
copy ..\backend\*.py backend\
copy ..\backend\requirements.txt backend\

# Python環境（オプション）
# 配布時にPython環境も同梱する場合
```

## トラブルシューティング

### よくある問題

1. **Python not found**
   - PATH環境変数にPythonが含まれているか確認
   - `py -V` または `python --version` で確認

2. **FFmpeg not found**
   - PATH環境変数にFFmpegが含まれているか確認
   - `ffmpeg -version` で確認

3. **CUDA利用時**
   - NVIDIA GPU Driver (551.xx以上)
   - CUDA Toolkit 11.8/12.x
   - cuDNN

4. **ビルドエラー**
   - Visual Studio Build Toolsが正しくインストールされているか確認
   - Rust toolchainが最新か確認: `rustup update`

## 推奨システム要件

### 最小要件
- **CPU**: x64互換プロセッサ
- **RAM**: 4GB以上
- **ストレージ**: 2GB以上の空き容量

### 推奨要件（CUDA使用）
- **GPU**: NVIDIA GTX 1060 / RTX 2060以上
- **VRAM**: 6GB以上
- **RAM**: 8GB以上
- **CUDA**: 11.8以上

## 配布用メモ

Windows版配布時に同梱すべきファイル：
- `web-whisper.exe` - メインアプリケーション
- `backend/` - Python転写スクリプト
- `requirements.txt` - Python依存関係
- `ffmpeg.exe` - 音声処理（オプション）
- `README-Windows.txt` - Windows用インストール手順
