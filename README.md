# Web Whisper - Cross-platform Speech Recognition

A high-performance, cross-platform speech-to-text application built with Tauri and optimized for both Apple Silicon and Windows GPU acceleration.

## 🏗️ Architecture

```
┌─────────────┐             ┌──────────────┐
│  Tauri GUI  │──WebView──▶│ whisper-gui  │  (Gradio)
│  (Rust)     │  http://127│ (sidecar exe)│
└─────────────┘◀─IPC(shell)─┴─────┬────────┘
        │ Python env = pyenv+venv  │
        │                          │OS Detection
        │                          ▼
        │        ┌─────────macOS────────┐   ┌────────Windows────────┐
        └───────▶│ MLX + Metal GPU     │   │ faster-whisper + CUDA │
                 └─────────────────────┘   └────────────────────────┘
                    （Whisper large-v3 model shared）
```

## ✨ Features

- **Cross-platform**: Native performance on macOS (Apple Silicon/Intel) and Windows
- **GPU Acceleration**: 
  - Apple Silicon: MLX with Metal GPU acceleration
  - Windows: CUDA acceleration with faster-whisper
  - Automatic fallback to CPU when GPU unavailable
- **High Accuracy**: Uses Whisper large-v3 model for best transcription quality
- **Standalone**: Self-contained executable with no external dependencies
- **Modern UI**: Clean Tauri-based interface with embedded Gradio backend

## 🚀 Quick Start

### Prerequisites

**macOS:**
```bash
xcode-select --install
brew install pyenv pyenv-virtualenv ffmpeg
```

**Windows:**
```powershell
# Run as Administrator
choco install pyenv-win
```

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd web-whisper
```

2. **Set up Python environment:**
```bash
# Install Python 3.11+ and create virtual environment
pyenv install 3.11.6
pyenv virtualenv 3.11.6 whisper-gui
pyenv local whisper-gui

# Install dependencies
pip install -r backend/requirements.txt
pip install mlx-whisper ffmpeg-python  # macOS
# OR
pip install faster-whisper ctranslate2  # Windows/Linux
```

3. **Install Node.js dependencies:**
```bash
cd frontend
npm install
```

## 🔧 Development

### Running in Development Mode

1. **Start the backend:**
```bash
cd backend
pyenv activate whisper-gui
python main.py
```

2. **Start the frontend:**
```bash
cd frontend
npm run tauri:dev
```

### Testing GPU Detection

```bash
cd backend
pyenv activate whisper-gui
python patch_gpu.py
```

Expected output:
- **macOS Apple Silicon**: "Using MLX backend for Apple Silicon"
- **Windows with NVIDIA**: "Using faster-whisper backend with CUDA" 
- **Other platforms**: "Using faster-whisper backend on [platform] with CPU/CUDA"

## 📦 Building

### Automated Build (Recommended)

```bash
# Build everything
python build.py

# Build options
python build.py --backend-only     # Build only the Python sidecar
python build.py --frontend-only    # Build only the Tauri app
python build.py --target universal-apple-darwin  # Specify target
```

### Manual Build Steps

1. **Build Backend Sidecar:**
```bash
cd backend
python build_sidecar.py
# OR manually:
pyinstaller --clean whisper-gui-core.spec
```

2. **Build Tauri Frontend:**
```bash
cd frontend
npm run tauri:build

# Platform-specific targets
npm run tauri:build -- --target universal-apple-darwin  # macOS Universal
npm run tauri:build -- --target x86_64-pc-windows-msvc  # Windows
```

## 📁 Project Structure

```
web-whisper/
├── backend/                    # Python backend
│   ├── main.py                # Original whisper-gui
│   ├── patch_gpu.py           # GPU auto-detection
│   ├── transcribe_optimized.py # Optimized transcription
│   ├── build_sidecar.py       # Sidecar build script
│   ├── whisper-gui-core.spec  # PyInstaller spec
│   └── dist/                  # Built executables
├── frontend/                   # Tauri frontend
│   ├── src/                   # TypeScript sources
│   ├── src-tauri/             # Rust Tauri backend
│   │   ├── tauri.conf.json    # Tauri configuration
│   │   └── src/main.rs        # Rust main
│   ├── package.json           # Node dependencies
│   └── vite.config.ts         # Vite config
├── build.py                   # Complete build script
└── CLAUDE.md                  # Development guide
```

## 🔍 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Metal assert failed" | Update to macOS 13+ |
| "CUDA DLL not found" | Update NVIDIA drivers to 551.xx+ |
| "Gradio page blank" | Port conflict - restart application |
| "Model download fails" | Check internet connection |
| "PyInstaller failed" | Ensure all dependencies installed |

### Debug Commands

```bash
# Test backend executable
./backend/dist/whisper-gui-core --help

# Check GPU detection
cd backend && python patch_gpu.py

# Verify Tauri configuration
cd frontend && npm run tauri info

# Test sidecar in Tauri
cd frontend && npm run tauri:dev
```

### GPU Acceleration Status

**Check Apple Silicon MLX:**
- Console should show "Using Metal device Apple M*"
- Activity Monitor should show GPU usage

**Check Windows CUDA:**
- Use `nvidia-smi` to monitor GPU utilization
- Console should show CUDA device information

## 🏁 Build Outputs

After successful build:

**macOS:**
- `backend/dist/whisper-gui-core` (Universal binary)
- `frontend/src-tauri/target/universal-apple-darwin/release/bundle/macos/Web Whisper.app`

**Windows:**
- `backend/dist/whisper-gui-core.exe`
- `frontend/src-tauri/target/x86_64-pc-windows-msvc/release/bundle/msi/Web Whisper_*.msi`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes following the existing code style
4. Test on your platform
5. Submit a pull request

## 📄 License

This project builds upon [whisper-gui](https://github.com/Pikurrot/whisper-gui) and follows its licensing terms.

## 🙏 Acknowledgments

- [whisper-gui](https://github.com/Pikurrot/whisper-gui) - Base Gradio interface
- [MLX](https://github.com/ml-explore/mlx) - Apple Silicon acceleration
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - CUDA acceleration
- [Tauri](https://tauri.app/) - Cross-platform desktop framework