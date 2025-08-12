#!/bin/bash

# GitHub setup script for Web Whisper
# This script helps you set up the GitHub repository and configure it for automated builds

set -e

echo "🎤 Web Whisper - GitHub Setup Script"
echo "======================================"

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed."
    echo "📥 Install it with: brew install gh"
    echo "🔗 Or visit: https://cli.github.com/"
    exit 1
fi

# Check if user is logged in
if ! gh auth status &> /dev/null; then
    echo "🔐 Please log in to GitHub CLI first:"
    echo "gh auth login"
    exit 1
fi

# Get repository name
read -p "📝 Enter GitHub repository name (default: web-whisper): " REPO_NAME
REPO_NAME=${REPO_NAME:-web-whisper}

echo ""
echo "🚀 Setting up GitHub repository: $REPO_NAME"

# Create GitHub repository
echo "📁 Creating GitHub repository..."
gh repo create "$REPO_NAME" \
    --public \
    --description "Cross-platform speech-to-text application with GPU acceleration" \
    --clone=false \
    --add-readme=false

# Get the repository URL
REPO_URL=$(gh repo view "$REPO_NAME" --json url -q '.url')
echo "✅ Repository created: $REPO_URL"

# Add GitHub remote
if git remote get-url github &> /dev/null; then
    echo "🔄 Updating GitHub remote..."
    git remote set-url github "${REPO_URL}.git"
else
    echo "➕ Adding GitHub remote..."
    git remote add github "${REPO_URL}.git"
fi

# Copy GitHub-specific README
if [ -f "README-GITHUB.md" ]; then
    echo "📋 Setting up GitHub README..."
    cp README-GITHUB.md README.md
    git add README.md
fi

# Add and commit GitHub Actions workflow
echo "⚙️  Committing GitHub Actions workflow..."
git add .github/workflows/build.yml
git add .

# Commit changes
git commit -m "feat: Add GitHub Actions workflow for cross-platform builds

- Automated Windows and macOS builds
- Release creation with artifacts
- Python environment setup
- Comprehensive CI/CD pipeline

🤖 Generated with Claude Code" || echo "⚠️  No changes to commit"

# Push to GitHub
echo "📤 Pushing to GitHub..."
git push github main

echo ""
echo "🎉 GitHub repository setup complete!"
echo "🔗 Repository: $REPO_URL"
echo ""
echo "📋 Next steps:"
echo "1. Visit your repository on GitHub"
echo "2. Create a release tag to trigger the build:"
echo "   git tag v1.0.0"
echo "   git push github v1.0.0"
echo "3. Check the Actions tab for build progress"
echo "4. Download builds from the Releases page"
echo ""
echo "🔧 Manual release creation:"
echo "   gh release create v1.0.0 --title \"Web Whisper v1.0.0\" --generate-notes"

# Enable GitHub Actions if needed
echo "🔧 Configuring repository settings..."
gh api repos/:owner/"$REPO_NAME" --method PATCH --field allow_auto_merge=false
gh api repos/:owner/"$REPO_NAME" --method PATCH --field has_issues=true
gh api repos/:owner/"$REPO_NAME" --method PATCH --field has_discussions=true

echo "✅ Setup complete! 🎊"