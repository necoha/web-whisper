#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete build script for Web Whisper cross-platform application.
This script orchestrates the entire build process:
1. Backend sidecar compilation (PyInstaller)
2. Frontend Tauri application build
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path
import argparse

class WebWhisperBuilder:
    def __init__(self):
        self.root_dir = Path(__file__).parent.absolute()
        self.backend_dir = self.root_dir / "backend"
        self.frontend_dir = self.root_dir / "frontend"
        self.system = platform.system()
        self.machine = platform.machine()
        
    def log(self, message, level="INFO"):
        """Log messages with emoji indicators."""
        icons = {
            "INFO": "ℹ️ ",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "WARNING": "⚠️ ",
            "BUILDING": "🔨"
        }
        print(f"{icons.get(level, '')} {message}")
        # Optional extra spacing for readability
        if os.getenv("WEB_WHISPER_LOG_SPACING", "normal").lower() == "loose":
            print()
    
    def run_command(self, cmd, cwd=None, check=True):
        """Run a shell command with proper error handling."""
        if isinstance(cmd, str):
            cmd = cmd.split()
        
        cwd = cwd or self.root_dir
        self.log(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, cwd=cwd, check=check, 
                                  capture_output=True, text=True)
            return result
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed: {e}", "ERROR")
            self.log(f"stdout: {e.stdout}", "ERROR")
            self.log(f"stderr: {e.stderr}", "ERROR")
            raise e
    
    def check_python_environment(self):
        """Check if the correct Python environment is active."""
        self.log("Checking Python environment...")
        
        # Check if pyenv is active
        try:
            result = subprocess.run(["pyenv", "version"], capture_output=True, text=True)
            ver = result.stdout.strip()
            # Accept both legacy and current env names
            if "web-whisper" in ver or "whisper-gui" in ver:
                active = "web-whisper" if "web-whisper" in ver else "whisper-gui"
                self.log(f"✅ pyenv environment active: {active}")
                return True
        except Exception:
            pass
        
        # Check if required packages are available
        import importlib.util
        required_packages = ['gradio', 'torch']
        if self.system == "Darwin" and self.machine.startswith("arm"):
            required_packages.append('mlx_whisper')
        else:
            required_packages.append('faster_whisper')
        
        missing = []
        for pkg in required_packages:
            mod = pkg.replace('-', '_')
            if importlib.util.find_spec(mod) is None:
                missing.append(pkg)
        
        if missing:
            self.log(f"Missing packages: {missing}", "ERROR")
            self.log("Please activate the whisper-gui environment:", "INFO")
            self.log("pyenv activate whisper-gui", "INFO")
            return False
        
        return True
    
    def check_node_environment(self):
        """Check if Node.js and pnpm are available."""
        self.log("Checking Node.js environment...")
        
        try:
            # Check Node.js
            node_result = subprocess.run(["node", "--version"], 
                                       capture_output=True, text=True)
            self.log(f"Node.js version: {node_result.stdout.strip()}")
            
            # Check pnpm
            pnpm_result = subprocess.run(["npx", "pnpm", "--version"], 
                                       capture_output=True, text=True)
            self.log(f"pnpm version: {pnpm_result.stdout.strip()}")
            
            return True
        except Exception as e:
            self.log(f"Node.js/pnpm check failed: {e}", "ERROR")
            return False
    
    def build_backend_sidecar(self):
        """Build the backend sidecar executable."""
        self.log("Building backend sidecar...", "BUILDING")
        
        if not self.backend_dir.exists():
            self.log("Backend directory not found!", "ERROR")
            return False
        
        # Run the backend build script
        build_script = self.backend_dir / "build_sidecar.py"
        if build_script.exists():
            try:
                result = self.run_command(["python", str(build_script)], 
                                        cwd=self.backend_dir)
                self.log("Backend sidecar built successfully", "SUCCESS")
                return True
            except subprocess.CalledProcessError:
                self.log("Backend sidecar build failed", "ERROR")
                return False
        else:
            # Fallback: direct PyInstaller build
            try:
                self.run_command(["python", "-m", "PyInstaller", "--clean", 
                                "whisper-gui-core.spec"], cwd=self.backend_dir)
                self.log("Backend sidecar built successfully (fallback)", "SUCCESS")
                return True
            except:
                self.log("Backend sidecar build failed", "ERROR")
                return False
    
    def install_frontend_dependencies(self):
        """Install frontend dependencies."""
        self.log("Installing frontend dependencies...", "BUILDING")
        
        if not self.frontend_dir.exists():
            self.log("Frontend directory not found!", "ERROR")
            return False
        
        try:
            self.run_command(["npx", "pnpm", "install"], cwd=self.frontend_dir)
            self.log("Frontend dependencies installed", "SUCCESS")
            return True
        except subprocess.CalledProcessError:
            self.log("Failed to install frontend dependencies", "ERROR")
            return False
    
    def build_tauri_app(self, target=None):
        """Build the Tauri application."""
        self.log("Building Tauri application...", "BUILDING")
        
        cmd = ["npx", "pnpm", "tauri", "build"]
        
        # Add platform-specific target
        if target:
            cmd.extend(["--target", target])
        elif self.system == "Darwin":
            cmd.extend(["--target", "universal-apple-darwin"])
        elif self.system == "Windows":
            cmd.extend(["--target", "x86_64-pc-windows-msvc"])
        
        try:
            result = self.run_command(cmd, cwd=self.frontend_dir)
            self.log("Tauri application built successfully", "SUCCESS")
            
            # Show build output location
            if self.system == "Darwin":
                bundle_path = self.frontend_dir / "src-tauri/target/universal-apple-darwin/release/bundle"
            elif self.system == "Windows":
                bundle_path = self.frontend_dir / "src-tauri/target/x86_64-pc-windows-msvc/release/bundle"
            else:
                bundle_path = self.frontend_dir / "src-tauri/target/release/bundle"
            
            if bundle_path.exists():
                self.log(f"Build output: {bundle_path}")
            
            return True
        except subprocess.CalledProcessError:
            self.log("Tauri application build failed", "ERROR")
            return False
    
    def verify_build_outputs(self):
        """Verify that all expected build outputs exist."""
        self.log("Verifying build outputs...")
        
        # Check backend sidecar
        if self.system == "Windows":
            sidecar_path = self.backend_dir / "dist/whisper-gui-core.exe"
        else:
            sidecar_path = self.backend_dir / "dist/whisper-gui-core"
        
        if not sidecar_path.exists():
            self.log(f"Backend sidecar not found: {sidecar_path}", "ERROR")
            return False
        
        self.log(f"✅ Backend sidecar: {sidecar_path}")
        
        # Check Tauri app
        if self.system == "Darwin":
            app_path = self.frontend_dir / "src-tauri/target/universal-apple-darwin/release/bundle/macos/Web Whisper.app"
        elif self.system == "Windows":
            app_path = self.frontend_dir / "src-tauri/target/x86_64-pc-windows-msvc/release/bundle/msi"
        else:
            app_path = self.frontend_dir / "src-tauri/target/release/bundle"
        
        # Note: Tauri creates multiple bundle formats, so we just check the target directory
        target_dir = app_path.parent if self.system != "Linux" else app_path
        if target_dir.exists() and any(target_dir.iterdir()):
            self.log(f"✅ Tauri application bundles in: {target_dir}")
            return True
        else:
            self.log(f"Tauri application bundles not found in: {target_dir}", "ERROR")
            return False
    
    def build_all(self, target=None, skip_backend=False, skip_frontend=False):
        """Build the complete application."""
        self.log(f"Starting Web Whisper build on {self.system} {self.machine}")
        
        try:
            # Environment checks
            if not skip_backend and not self.check_python_environment():
                return False
            
            if not skip_frontend and not self.check_node_environment():
                return False
            
            # Build backend sidecar
            if not skip_backend:
                if not self.build_backend_sidecar():
                    return False
            
            # Build frontend
            if not skip_frontend:
                if not self.install_frontend_dependencies():
                    return False
                
                if not self.build_tauri_app(target):
                    return False
            
            # Verify outputs
            if not skip_backend and not skip_frontend:
                if not self.verify_build_outputs():
                    return False
            
            self.log("🎉 Web Whisper build completed successfully!", "SUCCESS")
            return True
            
        except KeyboardInterrupt:
            self.log("Build interrupted by user", "WARNING")
            return False
        except Exception as e:
            self.log(f"Unexpected error: {e}", "ERROR")
            return False

def main():
    parser = argparse.ArgumentParser(description="Build Web Whisper application")
    parser.add_argument("--target", help="Target platform (e.g., universal-apple-darwin)")
    parser.add_argument("--skip-backend", action="store_true", 
                       help="Skip backend sidecar build")
    parser.add_argument("--skip-frontend", action="store_true", 
                       help="Skip frontend Tauri build")
    parser.add_argument("--backend-only", action="store_true", 
                       help="Build only the backend sidecar")
    parser.add_argument("--frontend-only", action="store_true", 
                       help="Build only the frontend Tauri app")
    
    args = parser.parse_args()
    
    # Handle exclusive flags
    if args.backend_only:
        args.skip_frontend = True
    if args.frontend_only:
        args.skip_backend = True
    
    builder = WebWhisperBuilder()
    success = builder.build_all(
        target=args.target,
        skip_backend=args.skip_backend,
        skip_frontend=args.skip_frontend
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
