# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cross-platform standalone speech recognition application using "pyenv + whisper-gui + Tauri" architecture:
- **Frontend**: Tauri (Rust + React + TypeScript) with sidecar WebView integration
- **Backend**: whisper-gui (Gradio-based) with GPU auto-detection
- **Platform Support**: Apple Silicon/Intel macOS and Windows GPU acceleration
- **Model**: Whisper large-v3 with platform-optimized backends

## Architecture

```
┌─────────────┐             ┌──────────────┐
│  Tauri 主GUI │──WebView──▶│ whisper-gui  │  (Gradio)
│  (Rust)      │  http://127│ (sidecar exe)│
└─────────────┘◀─IPC(shell)─┴─────┬────────┘
        │ Python env = pyenv+venv  │
        │                          │OS判定
        │                          ▼
        │        ┌─────────mac─────────┐   ┌────────Windows────────┐
        └───────▶│ MLX + Metal GPU    │   │ faster-whisper + CUDA │
                 └────────────────────┘   └────────────────────────┘
                    （Whisper large-v3 モデル共通）
```

## Development Setup

### Prerequisites

**macOS:**
```bash
xcode-select --install
brew install pyenv pyenv-virtualenv
# Add to ~/.zshrc:
export PYENV_ROOT="$HOME/.pyenv"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
```

**Windows:**
```powershell
# Run as Administrator
Set-ExecutionPolicy Bypass -Scope Process -Force
iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
choco install pyenv-win
```

### Python Environment Setup

```bash
# Install Python 3.11.6 and create virtual environment
pyenv install 3.11.6
pyenv virtualenv 3.11.6 whisper-gui
pyenv local whisper-gui

# Install dependencies
pip install -r requirements.txt
pip install mlx-whisper faster-whisper ffmpeg-python
```

## Common Commands

### Development
```bash
# Activate environment
pyenv activate whisper-gui

# Run backend (whisper-gui)
cd backend
python main.py

# Run Tauri frontend
cd frontend
pnpm dev
```

### Building
```bash
# Build backend executables
# macOS Universal
pyinstaller main.py --onefile --name whisper-gui-core \
  --target-arch universal2 \
  --collect-all mlx_whisper

# Windows
pyinstaller main.py --onefile --name whisper-gui-core.exe \
  --collect-all faster_whisper --collect-all ctranslate2

# Build Tauri app
pnpm tauri build --target universal-apple-darwin  # macOS
pnpm tauri build --target x86_64-pc-windows-msvc  # Windows
```

### Testing
```bash
# Test backend executable
./whisper-gui-core --help

# Check GPU detection
# macOS: Look for "Using Metal device Apple M*"
# Windows: Monitor GPU usage with nvidia-smi
```

## Project Structure

```
web-whisper/
├── backend/              # whisper-gui fork
│   ├── main.py          # Gradio server
│   ├── patch_gpu.py     # GPU auto-detection
│   └── dist/            # PyInstaller outputs
├── frontend/            # Tauri + React
│   ├── src/
│   │   └── lib/boot.ts  # Sidecar management
│   └── tauri.conf.json  # Sidecar configuration
└── models/              # Offline model cache
```

## Key Implementation Details

### GPU Auto-Detection (patch_gpu.py)
- **macOS**: MLX with Metal GPU acceleration using `mlx-community/whisper-large-v3-mlx`
- **Windows**: faster-whisper with CUDA using `large-v3` model
- Platform detection via `platform.system()` and `platform.machine()`

### Tauri Sidecar Integration
- Backend runs as sidecar executable
- WebView redirects to Gradio server
- IPC communication for process management
- Automatic port detection and assignment

### Build Targets
- macOS Universal: `universal-apple-darwin` (ARM64 + x86_64)
- Windows: `x86_64-pc-windows-msvc` with VC++ Runtime

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Metal assert failed | Update to macOS 13+ |
| CUDA DLL not found | Update drivers to 551.xx+ |
| Gradio page blank | Port conflict - use `--server.port` option |
| Model download fails | Check network/use `--model-path` for offline |