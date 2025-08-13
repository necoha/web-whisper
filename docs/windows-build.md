# Windows Build Instructions

This document describes how to build the Windows version of Web Whisper manually and integrate it with GitLab CI/CD.

## Overview

Since GitLab CI focuses on macOS builds, Windows builds are handled separately using one of these methods:

1. **Local Windows development machine**
2. **GitHub Actions** (separate repository)
3. **Azure DevOps** or other Windows CI services

## Prerequisites

### Windows Development Environment

```powershell
# Install Chocolatey (as Administrator)
Set-ExecutionPolicy Bypass -Scope Process -Force
iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))

# Install dependencies
choco install nodejs --version=20.17.0 -y
choco install rust -y
choco install python --version=3.11.9 -y
choco install git -y

# Install pnpm
npm install -g pnpm@8

# Add Rust target
rustup target add x86_64-pc-windows-msvc
```

## Build Process

### 1. Clone and Setup

```powershell
# Clone the repository
git clone <your-gitlab-repo-url>
cd web-whisper

# Setup Python backend
cd backend
python -m venv venv
venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
cd ..

# Setup frontend
cd frontend
pnpm install --frozen-lockfile
```

### 2. Build Backend Executable

```powershell
cd backend
venv\Scripts\activate.bat

# Build whisper-gui executable
pyinstaller main.py --onefile --name whisper-gui-core.exe \
  --collect-all faster_whisper --collect-all ctranslate2 \
  --hidden-import=faster_whisper --hidden-import=ctranslate2

# Test the executable
dist\whisper-gui-core.exe --help
```

### 3. Build Tauri Frontend

```powershell
cd frontend
pnpm tauri build --target x86_64-pc-windows-msvc
```

### 4. Locate Build Artifacts

After successful build, artifacts will be in:

```
frontend/src-tauri/target/x86_64-pc-windows-msvc/release/bundle/
├── msi/
│   └── Web Whisper_1.0.0_x64_en-US.msi
└── nsis/
    └── Web Whisper_1.0.0_x64-setup.exe
```

## Integration with GitLab CI

### Manual Artifact Upload

1. **Build locally** using the steps above
2. **Package artifacts**:
   ```powershell
   # Create release package
   mkdir releases
   cd frontend/src-tauri/target/x86_64-pc-windows-msvc/release/bundle
   
   # Package MSI
   Compress-Archive -Path msi\*.msi -DestinationPath ..\..\..\..\..\releases\web-whisper-windows-msi-v1.0.0.zip
   
   # Package NSIS installer
   Compress-Archive -Path nsis\*.exe -DestinationPath ..\..\..\..\..\releases\web-whisper-windows-installer-v1.0.0.zip
   ```

3. **Upload to GitLab**:
   ```bash
   # Using GitLab CLI (if available)
   glab release create v1.0.0 releases/web-whisper-windows-*.zip
   
   # Or upload via GitLab web interface:
   # Project > Releases > New Release > Upload files
   ```

### Automated Upload Script

Create `scripts/upload-windows-build.ps1`:

```powershell
param(
    [Parameter(Mandatory=$true)]
    [string]$Version,
    
    [Parameter(Mandatory=$true)]
    [string]$GitlabToken
)

$projectId = "your-project-id"
$baseUrl = "https://gitlab.com/api/v4"

# Package artifacts
Write-Host "Packaging Windows artifacts..."
$bundlePath = "frontend/src-tauri/target/x86_64-pc-windows-msvc/release/bundle"

if (Test-Path "$bundlePath/msi") {
    Compress-Archive -Path "$bundlePath/msi/*.msi" -DestinationPath "web-whisper-windows-msi-$Version.zip" -Force
}

if (Test-Path "$bundlePath/nsis") {
    Compress-Archive -Path "$bundlePath/nsis/*.exe" -DestinationPath "web-whisper-windows-installer-$Version.zip" -Force
}

# Upload to GitLab release
Write-Host "Uploading to GitLab release $Version..."
$headers = @{
    "PRIVATE-TOKEN" = $GitlabToken
}

# Upload MSI
if (Test-Path "web-whisper-windows-msi-$Version.zip") {
    $uri = "$baseUrl/projects/$projectId/releases/$Version/assets/links"
    $body = @{
        name = "Windows MSI Installer"
        url = "path/to/your/file"
        link_type = "package"
    }
    Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body ($body | ConvertTo-Json) -ContentType "application/json"
}

Write-Host "Upload completed!"
```

## Automated Options

### Option 1: GitHub Actions

Create a separate GitHub repository with GitHub Actions for Windows builds:

```yaml
# .github/workflows/windows-build.yml
name: Windows Build

on:
  workflow_dispatch:
    inputs:
      gitlab_ref:
        description: 'GitLab commit SHA'
        required: true

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - name: Download source from GitLab
        run: |
          curl -H "Authorization: Bearer ${{ secrets.GITLAB_TOKEN }}" \
            "${{ secrets.GITLAB_PROJECT_URL }}/repository/archive.zip?ref=${{ github.event.inputs.gitlab_ref }}" \
            -o source.zip
          
      - name: Extract and build
        run: |
          Expand-Archive source.zip -DestinationPath .
          # Follow build steps from above
          
      - name: Upload back to GitLab
        run: |
          # Upload artifacts back to GitLab release
```

### Option 2: Azure DevOps

Similar setup using Azure Pipelines with Windows agents.

## Troubleshooting

### Common Issues

1. **CUDA DLL not found**
   - Update NVIDIA drivers to 551.xx or higher
   - Install CUDA Toolkit if needed

2. **PyInstaller fails**
   - Ensure all dependencies are in requirements.txt
   - Use `--hidden-import` for missing modules

3. **Tauri build fails**
   - Check that Rust target is installed: `rustup target add x86_64-pc-windows-msvc`
   - Ensure Visual Studio Build Tools are installed

### Performance Tips

- Use local SSD for build directory
- Enable Windows Defender exclusions for build folders
- Close unnecessary applications during build

## Release Checklist

- [ ] Backend executable built and tested
- [ ] Frontend Tauri app built successfully
- [ ] Both MSI and NSIS installers created
- [ ] Artifacts packaged as zip files
- [ ] Version numbers updated
- [ ] Uploaded to GitLab release
- [ ] Release notes updated