# Web Whisper - GitHub Repository

🎤 Cross-platform speech-to-text application powered by OpenAI Whisper AI with GPU acceleration.

> **Note**: This GitHub repository is dedicated to **Windows builds only**. For macOS builds and full development resources, see the main [GitLab repository](https://gitlab-cxj.cisco.com/ktsutsum/web-whisper).

[![Windows Build](https://github.com/ktsutsum/web-whisper/workflows/Windows%20Build/badge.svg)](https://github.com/ktsutsum/web-whisper/actions)
[![Release](https://img.shields.io/github/v/release/ktsutsum/web-whisper)](https://github.com/ktsutsum/web-whisper/releases)
[![Platform](https://img.shields.io/badge/platform-Windows%2064--bit-blue)](https://github.com/ktsutsum/web-whisper/releases)

## 🚀 Features

- **Windows NVIDIA CUDA**: GPU acceleration for compatible graphics cards
- **Smart File Saving**: Automatic text export with error recovery  
- **Drag & Drop Interface**: Simple audio file processing
- **High Accuracy**: Whisper Large-v3 model for superior transcription
- **Multiple Formats**: MP3, WAV, M4A, FLAC, MP4, AVI, MOV, MKV support
- **Offline Processing**: No internet required after initial setup

## 📦 Download

Download the latest Windows release from the [Releases](../../releases) page:

- **web-whisper-windows-x64.msi** - Recommended MSI installer
- **web-whisper-windows-x64-installer.exe** - Alternative EXE installer

### System Requirements

**Windows:**
- Windows 10/11 (64-bit)
- 4GB RAM minimum, 8GB recommended
- NVIDIA GPU with CUDA support (optional, for acceleration)
- ~2GB free disk space for models

## 🛠 Installation

1. Download the MSI or EXE installer from [Releases](../../releases)
2. Run the installer and follow the prompts
3. Launch "Web Whisper" from the Start Menu

## ⚡ Performance

- **GPU Acceleration**: Automatically detects and enables NVIDIA CUDA if available
- **CPU Fallback**: Works on systems without compatible GPUs
- **Model Caching**: Downloads models once, uses offline thereafter
- **Memory Optimized**: Efficient processing for large audio files

## 🔧 Building from Source

### Prerequisites

```powershell
# Install dependencies
choco install nodejs python rust
npm install -g pnpm@8
```

### Build Steps

```bash
# Clone repository
git clone https://github.com/your-username/web-whisper.git
cd web-whisper

# Setup Python environment
cd backend
python -m pip install -r requirements.txt
cd ..

# Build frontend
cd frontend
pnpm install
pnpm tauri build --target x86_64-pc-windows-msvc
```

## 🏗 CI/CD

This repository uses GitHub Actions for automated Windows builds:

- **Continuous Integration**: Builds on every push to main/develop
- **Release Automation**: Creates releases on version tags
- **Artifact Storage**: Windows installers and executables

## 📁 Repository Structure

```
web-whisper/
├── .github/workflows/     # GitHub Actions CI/CD
├── backend/              # Python backend (whisper-gui)
├── frontend/             # Tauri + React frontend
└── releases/             # Build artifacts
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test on Windows
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Repositories

- **Main Development**: [GitLab Repository](https://gitlab-cxj.cisco.com/ktsutsum/web-whisper) (macOS builds, full documentation)
- **Windows Builds**: This GitHub repository

---

Built with ❤️ using [Tauri](https://tauri.app/), [Rust](https://rust-lang.org/), [TypeScript](https://www.typescriptlang.org/), and [Python](https://python.org/).