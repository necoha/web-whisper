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

def _load_product_name() -> str:
    import json
    conf = FRONTEND / "src-tauri" / "tauri.conf.json"
    with open(conf, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("productName", "Web Whisper")

def _load_binary_name() -> str:
    """Read Cargo package name to determine exe name (e.g., web-whisper.exe)."""
    import tomllib
    cargo = FRONTEND / "src-tauri" / "Cargo.toml"
    with open(cargo, "rb") as f:
        data = tomllib.load(f)
    pkg = data.get("package", {})
    name = pkg.get("name", "web-whisper")
    return f"{name}.exe"

def _find_app_exe() -> tuple[Path, Path]:
    """Locate the built app exe across possible Tauri layouts.

    Search priority:
    1) Release binary beside target (Cargo-built): target/.../release/<crate>.exe
    2) Any exe matching productName in bundle/ (nsis/app) excluding installers
    3) Any exe under bundle/app/<ProductName>/
    """
    product = _load_product_name()
    binary_name = _load_binary_name()

    # 1) Direct release binary
    release_exe = TAURI_TARGET / binary_name
    if release_exe.exists():
        return release_exe.parent, release_exe

    # 2) Look under bundle/ for product exe
    bundle_root = TAURI_TARGET / "bundle"
    candidates: list[Path] = []
    if bundle_root.exists():
        # Exact productName.exe
        exact = list(bundle_root.rglob(f"{product}.exe"))
        candidates.extend(exact)
        if not candidates:
            low = product.lower().replace(" ", "")
            for p in bundle_root.rglob("*.exe"):
                name = p.name.lower()
                if any(x in name for x in ["setup", "installer", "nsis", "msi"]):
                    continue
                simple = name.replace(" ", "")
                if low in simple:
                    candidates.append(p)

    if candidates:
        app_exe = max(candidates, key=lambda p: p.stat().st_size)
        return app_exe.parent, app_exe

    raise FileNotFoundError(
        f"Could not locate app exe for productName '{product}' or binary '{binary_name}' under {TAURI_TARGET}"
    )

def build_frontend():
    print("[2/4] Building Tauri app (bundle)...")
    # Build with default bundles or nsis; caller (CI) may build separately
    run(["npx", "pnpm", "tauri", "build", "--", "--target", "x86_64-pc-windows-msvc"], cwd=FRONTEND)
    return _find_app_exe()

def stage_files(app_dir: Path, app_exe: Path, sidecar_exe: Path):
    print("[3/4] Staging files for portable package...")
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True, exist_ok=True)

    # Copy Tauri app executable and nearby resources if present
    shutil.copy2(app_exe, STAGE / app_exe.name)
    # Copy common runtime folders if they exist (resource locations vary by bundler)
    for folder in ("resources", "data", "bin"):
        src = app_dir / folder
        if src.exists() and src.is_dir():
            shutil.copytree(src, STAGE / folder)

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
        # Try to discover existing build artifacts (nsis/app agnostic)
        app_dir, app_exe = _find_app_exe()
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
