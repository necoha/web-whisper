#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prepare a Windows portable single-EXE package for Web Whisper.

What this script does (on Windows host):
- Builds the Python sidecar with PyInstaller (onefile)
- Builds the Tauri app with the `app` bundle target (no installer)
- Stages the app exe, resources, and sidecar into windows-release/stage
- Optionally includes WebView2 Fixed Runtime if present at windows-release/WebView2Runtime
- Generates an NSIS portable exe using windows-release/portable.nsi (requires makensis)

Usage:
  python windows-release/prepare_portable.py [--skip-build] [--output WebWhisper-Portable.exe]

Prerequisites on Windows:
- Node.js + pnpm
- Rust toolchain (MSVC)
- Python 3.10–3.12 with PyInstaller and project deps
- NSIS (makensis on PATH)
- Optional: WebView2 Fixed Runtime placed at windows-release/WebView2Runtime
"""

import argparse
import os
import shutil
import subprocess
from pathlib import Path
import sys
import platform

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
TAURI_TARGET = FRONTEND / "src-tauri" / "target" / "x86_64-pc-windows-msvc" / "release"
STAGE = ROOT / "windows-release" / "stage"
NSI_FILE = ROOT / "windows-release" / "portable.nsi"

def run(cmd, cwd=None, check=True):
    print("$", " ".join(map(str, cmd)))
    return subprocess.run(cmd, cwd=cwd or ROOT, check=check)

def build_backend():
    print("[1/4] Building backend sidecar (PyInstaller onefile)...")
    run([sys.executable, str(BACKEND / "build_sidecar.py")], cwd=BACKEND)
    exe = BACKEND / "dist" / "whisper-gui-core.exe"
    if not exe.exists():
        raise FileNotFoundError(f"Sidecar exe not found: {exe}")
    return exe

def build_frontend():
    print("[2/4] Building Tauri app (app bundle)...")
    # Build only the app bundle to avoid installer-only outputs
    run(["npx", "pnpm", "tauri", "build", "--", "--bundles", "app", "--target", "x86_64-pc-windows-msvc"], cwd=FRONTEND)

    # App bundle directory layout
    bundle_app = TAURI_TARGET / "bundle" / "app"
    if not bundle_app.exists():
        raise FileNotFoundError(f"Tauri app bundle not found: {bundle_app}")
    # Find the single app folder under app/ (productName)
    subdirs = [p for p in bundle_app.iterdir() if p.is_dir()]
    if not subdirs:
        raise FileNotFoundError(f"No app folder under: {bundle_app}")
    app_dir = subdirs[0]
    # Detect exe name
    exes = list(app_dir.glob("*.exe"))
    if not exes:
        raise FileNotFoundError(f"No exe found under: {app_dir}")
    app_exe = exes[0]
    return app_dir, app_exe

def stage_files(app_dir: Path, app_exe: Path, sidecar_exe: Path):
    print("[3/4] Staging files for portable package...")
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True, exist_ok=True)

    # Copy Tauri app dir contents (exe + resources)
    for item in app_dir.iterdir():
        dest = STAGE / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    # Ensure sidecar is next to app exe
    shutil.copy2(sidecar_exe, STAGE / sidecar_exe.name)

    # Optionally include WebView2 Fixed Runtime if present
    webview2 = ROOT / "windows-release" / "WebView2Runtime"
    if webview2.exists():
        print("Including WebView2 Fixed Runtime...")
        shutil.copytree(webview2, STAGE / "WebView2Runtime")

    print(f"Staged at: {STAGE}")

def build_portable_exe(output: str):
    print("[4/4] Building NSIS portable exe...")
    if not NSI_FILE.exists():
        raise FileNotFoundError(f"NSIS script missing: {NSI_FILE}")
    # Allow custom output name by passing /DOutFile=... to makensis
    cmd = ["makensis", f"/DOutFile={output}", str(NSI_FILE)]
    run(cmd, cwd=NSI_FILE.parent)
    print(f"Portable exe created: {NSI_FILE.parent / output}")

def main():
    if platform.system() != "Windows":
        print("Warning: This script is intended to run on Windows.")

    p = argparse.ArgumentParser(description="Prepare Windows portable exe")
    p.add_argument("--skip-build", action="store_true", help="Skip building backend/frontend; reuse existing artifacts")
    p.add_argument("--output", default="WebWhisper-Portable.exe", help="Output portable exe name")
    args = p.parse_args()

    sidecar_exe = BACKEND / "dist" / "whisper-gui-core.exe"
    app_dir = None
    app_exe = None

    if not args.skip_build:
        sidecar_exe = build_backend()
        app_dir, app_exe = build_frontend()
    else:
        # Try to discover existing build artifacts
        bundle_app = TAURI_TARGET / "bundle" / "app"
        subdirs = [p for p in bundle_app.iterdir() if p.is_dir()] if bundle_app.exists() else []
        if not subdirs:
            print("No existing Tauri app artifacts found. Remove --skip-build.")
            sys.exit(1)
        app_dir = subdirs[0]
        exes = list(app_dir.glob("*.exe"))
        if not exes:
            print("No Tauri exe found. Remove --skip-build.")
            sys.exit(1)
        app_exe = exes[0]
        if not sidecar_exe.exists():
            print("Sidecar exe missing. Remove --skip-build.")
            sys.exit(1)

    stage_files(app_dir, app_exe, sidecar_exe)

    try:
        build_portable_exe(args.output)
    except FileNotFoundError:
        print("makensis not found. Install NSIS and ensure makensis is on PATH.")
        print("You can still run makensis manually:")
        print(f"  cd {NSI_FILE.parent}")
        print(f"  makensis /DOutFile={args.output} portable.nsi")

if __name__ == "__main__":
    main()

