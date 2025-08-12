# 🎤 Web Whisper

Cross-platform speech-to-text application powered by OpenAI Whisper AI with GPU acceleration.

[![Build Status](https://github.com/ktsutsum/web-whisper/workflows/Build%20Web%20Whisper/badge.svg)](https://github.com/ktsutsum/web-whisper/actions)
[![Release](https://img.shields.io/github/v/release/ktsutsum/web-whisper)](https://github.com/ktsutsum/web-whisper/releases)
[![Platform](https://img.shields.io/badge/platform-Windows%20|%20macOS-blue)](https://github.com/ktsutsum/web-whisper/releases)

## ✨ Features

- **🚀 GPU Acceleration**: Apple Silicon (MLX + Metal) and NVIDIA CUDA support
- **💾 Smart File Saving**: Automatic text file export with error recovery
- **📱 Intuitive Interface**: Simple drag-and-drop audio file processing
- **🔧 High Accuracy**: Whisper Large-v3 model for superior transcription quality
- **🌐 Cross-Platform**: Native Windows and macOS applications
- **📁 Multiple Formats**: Support for MP3, WAV, M4A, FLAC, MP4, AVI, MOV, MKV

## 📦 Download

**[⬇️ Latest Release](https://github.com/ktsutsum/web-whisper/releases/latest)**

### System Requirements

#### macOS
- **Minimum**: macOS 11.0 (Big Sur)
- **Recommended**: macOS 13.0+ with Apple Silicon for GPU acceleration
- **Storage**: 2GB free space

#### Windows
- **Minimum**: Windows 10 64-bit
- **Recommended**: Windows 11 with NVIDIA GPU (GTX 1060+ / RTX series)
- **Storage**: 2GB free space
- **Optional**: CUDA 11.8+ for GPU acceleration

## 🚀 Quick Start

1. **Download** the installer for your platform
2. **Install** the application
   - **macOS**: Open DMG, drag to Applications folder
   - **Windows**: Run the MSI installer
3. **Launch** Web Whisper
4. **Drag & Drop** an audio file or click to browse
5. **Click** "転写を開始" to start transcription
6. **Save** results using the "💾 テキスト保存" button

## 🏗️ Architecture

```
┌─────────────┐             ┌──────────────┐
│  Tauri GUI  │──────────▶│ Python Engine │
│  (Rust+TS)  │             │   (Whisper)   │
└─────────────┘             └──────┬───────┘
                                   │
                            ┌──────▼───────┐
                            │ GPU Backend  │
                            │ MLX | CUDA   │
                            └──────────────┘
```

- **Frontend**: Tauri 2.x (Rust + TypeScript + React)
- **Backend**: Python with Whisper Large-v3
- **GPU Support**: MLX (Apple Silicon) / CUDA (Windows)

## 🛠️ Development

### Prerequisites

- **Node.js** 18+ and pnpm
- **Rust** 1.70+ with cross-compilation targets
- **Python** 3.11+ with virtual environment
- **System Dependencies**: 
  - macOS: Xcode Command Line Tools
  - Windows: Visual Studio Build Tools

### Setup

```bash
# Clone repository
git clone https://github.com/ktsutsum/web-whisper.git
cd web-whisper

# Install frontend dependencies
cd frontend
pnpm install

# Setup Python backend
cd ../backend
python -m venv web-whisper
source web-whisper/bin/activate  # or web-whisper\Scripts\activate.bat on Windows
pip install -r requirements.txt
```

### Development Commands

```bash
# Run in development mode
cd frontend
pnpm tauri dev

# Build for production
pnpm tauri build --target universal-apple-darwin  # macOS
pnpm tauri build --target x86_64-pc-windows-msvc  # Windows
```

### Docker Development

```bash
# Run backend in Docker
cd backend
docker-compose up

# Access at http://localhost:7860
```

## 🔄 CI/CD

Automated builds are configured for:
- **GitHub Actions**: Windows and macOS builds on tag push
- **GitLab CI/CD**: Alternative pipeline for Cisco environments

To create a release:
```bash
git tag v1.2.3
git push origin v1.2.3
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/ktsutsum/web-whisper/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ktsutsum/web-whisper/discussions)

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition model
- [MLX](https://github.com/ml-explore/mlx) - Apple Silicon acceleration
- [Tauri](https://tauri.app/) - Cross-platform application framework
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Efficient Whisper implementation

---

**Made with ❤️ for seamless speech-to-text transcription**