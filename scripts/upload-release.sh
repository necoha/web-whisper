#!/bin/bash

# Release upload script for Web Whisper
# Combines macOS (from GitLab CI) and Windows (manual) artifacts

set -e

VERSION=${1:-}
GITLAB_TOKEN=${2:-$GITLAB_TOKEN}
PROJECT_ID=${3:-$CI_PROJECT_ID}

if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version> [gitlab_token] [project_id]"
    echo "Example: $0 v1.0.0"
    exit 1
fi

if [ -z "$GITLAB_TOKEN" ]; then
    echo "Error: GITLAB_TOKEN not set"
    echo "Set it as environment variable or pass as second argument"
    exit 1
fi

if [ -z "$PROJECT_ID" ]; then
    echo "Error: PROJECT_ID not set"
    echo "Set CI_PROJECT_ID or pass as third argument"
    exit 1
fi

BASE_URL="https://gitlab.com/api/v4"
RELEASES_DIR="releases"

echo "🚀 Creating release $VERSION for project $PROJECT_ID"

# Create releases directory if it doesn't exist
mkdir -p "$RELEASES_DIR"

# Check for macOS artifacts (from GitLab CI)
MACOS_DMG_EXISTS=false
MACOS_APP_EXISTS=false

if [ -f "$RELEASES_DIR/web-whisper-macos-dmg-"*".zip" ]; then
    MACOS_DMG_FILE=$(ls "$RELEASES_DIR"/web-whisper-macos-dmg-*.zip | head -1)
    MACOS_DMG_EXISTS=true
    echo "✅ Found macOS DMG: $(basename "$MACOS_DMG_FILE")"
fi

if [ -f "$RELEASES_DIR/web-whisper-macos-app-"*".zip" ]; then
    MACOS_APP_FILE=$(ls "$RELEASES_DIR"/web-whisper-macos-app-*.zip | head -1)
    MACOS_APP_EXISTS=true
    echo "✅ Found macOS App: $(basename "$MACOS_APP_FILE")"
fi

# Check for Windows artifacts (manual upload)
WINDOWS_MSI_EXISTS=false
WINDOWS_INSTALLER_EXISTS=false

if [ -f "$RELEASES_DIR/web-whisper-windows-msi-"*".zip" ]; then
    WINDOWS_MSI_FILE=$(ls "$RELEASES_DIR"/web-whisper-windows-msi-*.zip | head -1)
    WINDOWS_MSI_EXISTS=true
    echo "✅ Found Windows MSI: $(basename "$WINDOWS_MSI_FILE")"
fi

if [ -f "$RELEASES_DIR/web-whisper-windows-installer-"*".zip" ]; then
    WINDOWS_INSTALLER_FILE=$(ls "$RELEASES_DIR"/web-whisper-windows-installer-*.zip | head -1)
    WINDOWS_INSTALLER_EXISTS=true
    echo "✅ Found Windows Installer: $(basename "$WINDOWS_INSTALLER_FILE")"
fi

# Summary
echo ""
echo "📋 Release Summary:"
echo "   macOS DMG: $([ "$MACOS_DMG_EXISTS" = true ] && echo "✅" || echo "❌")"
echo "   macOS App: $([ "$MACOS_APP_EXISTS" = true ] && echo "✅" || echo "❌")"
echo "   Windows MSI: $([ "$WINDOWS_MSI_EXISTS" = true ] && echo "✅" || echo "❌")"
echo "   Windows Installer: $([ "$WINDOWS_INSTALLER_EXISTS" = true ] && echo "✅" || echo "❌")"

if [ "$MACOS_DMG_EXISTS" = false ] && [ "$MACOS_APP_EXISTS" = false ] && [ "$WINDOWS_MSI_EXISTS" = false ] && [ "$WINDOWS_INSTALLER_EXISTS" = false ]; then
    echo ""
    echo "❌ No artifacts found! Please ensure builds are completed and artifacts are in releases/ directory"
    echo ""
    echo "Expected structure:"
    echo "releases/"
    echo "├── web-whisper-macos-dmg-*.zip     (from GitLab CI)"
    echo "├── web-whisper-macos-app-*.zip     (from GitLab CI)"
    echo "├── web-whisper-windows-msi-*.zip   (manual upload)"
    echo "└── web-whisper-windows-installer-*.zip (manual upload)"
    exit 1
fi

echo ""
read -p "Continue with release creation? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Release cancelled"
    exit 0
fi

# Create GitLab release
echo "📦 Creating GitLab release..."

RELEASE_DATA=$(cat <<EOF
{
  "tag_name": "$VERSION",
  "name": "Web Whisper $VERSION",
  "description": "## Web Whisper $VERSION\\n\\n🎤 Cross-platform speech-to-text application powered by OpenAI Whisper AI with GPU acceleration.\\n\\n### 🚀 Features\\n- **Apple Silicon (MLX + Metal)**: Native GPU acceleration for M1/M2/M3 Macs\\n- **Windows NVIDIA CUDA**: GPU acceleration for compatible graphics cards\\n- **Smart File Saving**: Automatic text export with error recovery\\n- **Drag & Drop Interface**: Simple audio file processing\\n- **High Accuracy**: Whisper Large-v3 model for superior transcription\\n- **Multiple Formats**: MP3, WAV, M4A, FLAC, MP4, AVI, MOV, MKV support\\n\\n### 📦 Downloads\\nChoose the package for your platform:\\n\\n$([ "$WINDOWS_MSI_EXISTS" = true ] && echo "- **Windows 64-bit MSI**: Recommended installer for Windows 10/11\\n")$([ "$WINDOWS_INSTALLER_EXISTS" = true ] && echo "- **Windows 64-bit EXE**: Alternative installer format\\n")$([ "$MACOS_DMG_EXISTS" = true ] && echo "- **macOS Universal DMG**: Native app for Apple Silicon + Intel Macs\\n")$([ "$MACOS_APP_EXISTS" = true ] && echo "- **macOS App Bundle**: Direct .app bundle for advanced users\\n")\\n### 🛠 Installation\\n- **Windows**: Download MSI/EXE, run installer, follow prompts\\n- **macOS**: Download DMG, open and drag to Applications folder\\n\\n### ⚡ Performance\\n- GPU acceleration automatically detected and enabled\\n- Offline processing - no internet required after setup\\n- Optimized for modern hardware architectures\\n\\nBuilt with ❤️ using Tauri, Rust, TypeScript, and Python."
}
EOF
)

RELEASE_RESPONSE=$(curl -s -w "\\n%{http_code}" -X POST \
  -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  -H "Content-Type: application/json" \
  "$BASE_URL/projects/$PROJECT_ID/releases" \
  -d "$RELEASE_DATA")

HTTP_CODE=$(echo "$RELEASE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$RELEASE_RESPONSE" | head -n -1)

if [ "$HTTP_CODE" != "201" ]; then
    echo "❌ Failed to create release. HTTP code: $HTTP_CODE"
    echo "Response: $RESPONSE_BODY"
    exit 1
fi

echo "✅ Release created successfully!"

# Upload artifacts as release assets
echo "📤 Uploading release assets..."

upload_asset() {
    local file_path="$1"
    local asset_name="$2"
    local link_type="$3"
    
    if [ -f "$file_path" ]; then
        echo "  Uploading $(basename "$file_path")..."
        
        # First, upload the file
        UPLOAD_RESPONSE=$(curl -s -w "\\n%{http_code}" -X POST \
          -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
          -F "file=@$file_path" \
          "$BASE_URL/projects/$PROJECT_ID/uploads")
        
        UPLOAD_HTTP_CODE=$(echo "$UPLOAD_RESPONSE" | tail -n1)
        UPLOAD_BODY=$(echo "$UPLOAD_RESPONSE" | head -n -1)
        
        if [ "$UPLOAD_HTTP_CODE" != "201" ]; then
            echo "    ❌ Failed to upload file. HTTP code: $UPLOAD_HTTP_CODE"
            return 1
        fi
        
        # Extract upload URL
        UPLOAD_URL=$(echo "$UPLOAD_BODY" | grep -o '"url":"[^"]*"' | cut -d'"' -f4)
        FULL_URL="https://gitlab.com$UPLOAD_URL"
        
        # Create release link
        LINK_DATA=$(cat <<EOF
{
  "name": "$asset_name",
  "url": "$FULL_URL",
  "link_type": "$link_type"
}
EOF
)
        
        LINK_RESPONSE=$(curl -s -w "\\n%{http_code}" -X POST \
          -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
          -H "Content-Type: application/json" \
          "$BASE_URL/projects/$PROJECT_ID/releases/$VERSION/assets/links" \
          -d "$LINK_DATA")
        
        LINK_HTTP_CODE=$(echo "$LINK_RESPONSE" | tail -n1)
        
        if [ "$LINK_HTTP_CODE" != "201" ]; then
            echo "    ❌ Failed to create release link. HTTP code: $LINK_HTTP_CODE"
            return 1
        fi
        
        echo "    ✅ Uploaded successfully"
    fi
}

# Upload all available artifacts
if [ "$MACOS_DMG_EXISTS" = true ]; then
    upload_asset "$MACOS_DMG_FILE" "macOS Universal DMG" "package"
fi

if [ "$MACOS_APP_EXISTS" = true ]; then
    upload_asset "$MACOS_APP_FILE" "macOS App Bundle" "package"
fi

if [ "$WINDOWS_MSI_EXISTS" = true ]; then
    upload_asset "$WINDOWS_MSI_FILE" "Windows 64-bit MSI Installer" "package"
fi

if [ "$WINDOWS_INSTALLER_EXISTS" = true ]; then
    upload_asset "$WINDOWS_INSTALLER_FILE" "Windows 64-bit EXE Installer" "package"
fi

echo ""
echo "🎉 Release $VERSION created successfully!"
echo "🔗 View release: https://gitlab.com/$CI_PROJECT_PATH/-/releases/$VERSION"
echo ""

# Instructions for missing artifacts
if [ "$WINDOWS_MSI_EXISTS" = false ] || [ "$WINDOWS_INSTALLER_EXISTS" = false ]; then
    echo "📝 To add Windows artifacts later:"
    echo "   1. Build Windows version using docs/windows-build.md"
    echo "   2. Place artifacts in releases/ directory"
    echo "   3. Run this script again with the same version"
fi