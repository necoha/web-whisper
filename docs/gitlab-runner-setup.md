# GitLab Runner Setup Guide

This guide explains how to set up GitLab Runners for building Web Whisper across different platforms.

## Overview

Web Whisper requires both Windows and macOS runners for cross-platform builds:

- **Windows Runner**: For building Windows MSI/EXE installers with CUDA support
- **macOS Runner**: For building Universal macOS DMG with Apple Silicon (MLX) support

## Runner Requirements

### Windows Runner
- **OS**: Windows 10/11 or Windows Server 2019/2022
- **Architecture**: x64 (AMD64)
- **Docker**: Docker Desktop or Docker Engine
- **Hardware**: 4+ CPU cores, 8GB+ RAM, 50GB+ storage
- **Optional**: NVIDIA GPU for testing CUDA acceleration

### macOS Runner
- **OS**: macOS 11+ (Big Sur or newer)
- **Architecture**: Apple Silicon (M1/M2/M3) or Intel x64
- **Hardware**: 4+ CPU cores, 8GB+ RAM, 50GB+ storage
- **Required**: Xcode Command Line Tools

## Setup Instructions

### 1. Windows Runner Setup

#### Option A: Docker-based Runner (Recommended)

```powershell
# Install GitLab Runner
$url = "https://gitlab-runner-downloads.s3.amazonaws.com/latest/binaries/gitlab-runner-windows-amd64.exe"
Invoke-WebRequest -Uri $url -OutFile "C:\GitLab-Runner\gitlab-runner.exe"

# Register runner
cd C:\GitLab-Runner
.\gitlab-runner.exe register `
  --url "https://gitlab-cxj.cisco.com/" `
  --token "YOUR_REGISTRATION_TOKEN" `
  --executor docker `
  --docker-image "mcr.microsoft.com/windows/servercore:ltsc2022" `
  --tag-list "windows,docker" `
  --description "Web Whisper Windows Builder"

# Install and start service
.\gitlab-runner.exe install
.\gitlab-runner.exe start
```

#### Option B: Shell-based Runner

```powershell
# Register shell runner
.\gitlab-runner.exe register `
  --url "https://gitlab-cxj.cisco.com/" `
  --token "YOUR_REGISTRATION_TOKEN" `
  --executor shell `
  --tag-list "windows,shell" `
  --description "Web Whisper Windows Shell"

# Install dependencies
# Chocolatey
Set-ExecutionPolicy Bypass -Scope Process -Force
iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))

# Development tools
choco install nodejs --version=20.17.0 -y
choco install rust -y
choco install python --version=3.11.9 -y
npm install -g pnpm@8
```

### 2. macOS Runner Setup

#### Install GitLab Runner

```bash
# Download and install
sudo curl --output /usr/local/bin/gitlab-runner \
  "https://gitlab-runner-downloads.s3.amazonaws.com/latest/binaries/gitlab-runner-darwin-amd64"
sudo chmod +x /usr/local/bin/gitlab-runner

# Register runner
sudo gitlab-runner register \
  --url "https://gitlab-cxj.cisco.com/" \
  --token "YOUR_REGISTRATION_TOKEN" \
  --executor shell \
  --tag-list "macos,shell" \
  --description "Web Whisper macOS Builder"

# Install and start service
cd ~
gitlab-runner install
gitlab-runner start
```

#### Setup Build Environment

```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install node@20 python@3.11
npm install -g pnpm@8

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source ~/.cargo/env
rustup target add universal-apple-darwin

# Install pyenv for Python management (optional but recommended)
brew install pyenv pyenv-virtualenv
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.zshrc
```

## Runner Configuration

### GitLab Project Settings

1. **Navigate to**: Project → Settings → CI/CD → Runners
2. **Copy Registration Token**: Use this token in the setup commands above
3. **Configure Runner Tags**: Ensure runners have appropriate tags:
   - Windows: `windows`, `docker` or `shell`
   - macOS: `macos`, `shell`

### Runner Tags in `.gitlab-ci.yml`

The CI configuration uses these tags to select appropriate runners:

```yaml
build-windows:
  tags:
    - windows
    - docker

build-macos:
  tags:
    - macos
    - shell
```

## Testing the Setup

### Trigger a Build

```bash
# Create and push a tag to trigger build
git tag v1.0.1
git push origin v1.0.1
```

### Monitor Pipeline

1. **Navigate to**: Project → CI/CD → Pipelines
2. **Check Status**: Monitor build progress for both platforms
3. **View Logs**: Click on jobs to see detailed build output
4. **Download Artifacts**: Access built packages from the pipeline page

## Troubleshooting

### Common Windows Issues

1. **Docker not found**: Install Docker Desktop for Windows
2. **PowerShell execution policy**: Run `Set-ExecutionPolicy RemoteSigned`
3. **Chocolatey installation fails**: Run PowerShell as Administrator
4. **Rust target missing**: Run `rustup target add x86_64-pc-windows-msvc`

### Common macOS Issues

1. **Xcode tools missing**: Run `xcode-select --install`
2. **Python version conflicts**: Use pyenv to manage Python versions
3. **Permission denied**: Check file permissions and runner user access
4. **Universal target missing**: Run `rustup target add universal-apple-darwin`

### Runner Registration Issues

1. **Invalid token**: Get a fresh registration token from GitLab project settings
2. **Network connectivity**: Ensure runner can reach GitLab instance
3. **Runner not appearing**: Check runner service status and restart if needed

## Alternative: Shared Runners

If setting up dedicated runners is not feasible, consider using:

1. **GitLab.com Shared Runners**: For open-source projects
2. **Cloud CI Services**: GitHub Actions, CircleCI, Azure DevOps
3. **Docker-based CI**: Using GitLab CI with Docker-in-Docker

## Security Considerations

- **Isolated Environments**: Use separate VMs/containers for runners
- **Limited Permissions**: Run with minimal required privileges  
- **Regular Updates**: Keep runner software and dependencies updated
- **Network Security**: Configure firewalls and access controls

## Support

For runner setup issues:
1. Check GitLab Runner documentation
2. Review CI/CD pipeline logs
3. Test builds locally before pushing
4. Contact your GitLab administrator for enterprise instances