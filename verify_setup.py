#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verification script for Web Whisper setup.
This script checks all components and dependencies to ensure the setup is correct.
"""

import os
import sys
import platform
import subprocess
from pathlib import Path

def print_header(title):
    """Print a formatted header."""
    print(f"\n{'='*20} {title} {'='*20}")

def check_item(name, condition, success_msg, error_msg):
    """Check a condition and print result."""
    if condition:
        print(f"✅ {name}: {success_msg}")
        return True
    else:
        print(f"❌ {name}: {error_msg}")
        return False

def check_python_environment():
    """Check Python environment and packages."""
    print_header("Python Environment")
    
    checks_passed = 0
    total_checks = 0
    
    # Check Python version
    total_checks += 1
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if check_item("Python Version", 
                  sys.version_info >= (3, 8),
                  f"Python {python_version}",
                  f"Python {python_version} (need 3.8+)"):
        checks_passed += 1
    
    # Check pyenv
    total_checks += 1
    try:
        result = subprocess.run(["pyenv", "version"], capture_output=True, text=True)
        pyenv_active = "whisper-gui" in result.stdout
        if check_item("pyenv Environment", 
                      pyenv_active,
                      "whisper-gui environment active",
                      "whisper-gui environment not active"):
            checks_passed += 1
    except FileNotFoundError:
        check_item("pyenv", False, "", "pyenv not installed")
    
    # Check required packages
    packages = [
        ('gradio', 'Gradio web interface'),
        ('torch', 'PyTorch'),
        ('numpy', 'NumPy'),
        ('tqdm', 'Progress bars')
    ]
    
    # Add platform-specific packages
    if platform.system() == "Darwin" and platform.machine().startswith("arm"):
        packages.append(('mlx_whisper', 'MLX Whisper (Apple Silicon)'))
    else:
        packages.append(('faster_whisper', 'faster-whisper'))
    
    for pkg_name, description in packages:
        total_checks += 1
        try:
            __import__(pkg_name.replace('-', '_'))
            if check_item(f"Package {pkg_name}", True, description, ""):
                checks_passed += 1
        except ImportError:
            check_item(f"Package {pkg_name}", False, "", f"{description} not installed")
    
    return checks_passed, total_checks

def check_gpu_detection():
    """Check GPU auto-detection functionality."""
    print_header("GPU Detection")
    
    checks_passed = 0
    total_checks = 1
    
    try:
        # Import our GPU detection
        sys.path.append(str(Path(__file__).parent / "backend"))
        from patch_gpu import auto_engine, auto_engine_detailed
        
        # Test basic engine
        engine = auto_engine()
        detailed_engine = auto_engine_detailed()
        
        system = platform.system()
        machine = platform.machine()
        
        if system == "Darwin" and machine.startswith("arm"):
            expected_backend = "MLX backend for Apple Silicon"
        elif system == "Windows":
            expected_backend = "faster-whisper backend with CUDA/CPU"
        else:
            expected_backend = f"faster-whisper backend on {system}"
        
        if check_item("GPU Auto-detection", 
                      engine is not None and detailed_engine is not None,
                      f"Successfully loaded {expected_backend}",
                      "Failed to initialize GPU detection"):
            checks_passed += 1
            
    except Exception as e:
        check_item("GPU Auto-detection", False, "", f"Error: {e}")
    
    return checks_passed, total_checks

def check_node_environment():
    """Check Node.js and frontend setup."""
    print_header("Node.js Environment")
    
    checks_passed = 0
    total_checks = 0
    
    # Check Node.js
    total_checks += 1
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        node_version = result.stdout.strip()
        if check_item("Node.js", 
                      result.returncode == 0,
                      f"Version {node_version}",
                      "Not installed"):
            checks_passed += 1
    except FileNotFoundError:
        check_item("Node.js", False, "", "Not installed")
    
    # Check pnpm
    total_checks += 1
    try:
        result = subprocess.run(["npx", "pnpm", "--version"], capture_output=True, text=True)
        pnpm_version = result.stdout.strip()
        if check_item("pnpm", 
                      result.returncode == 0,
                      f"Version {pnpm_version}",
                      "Not available"):
            checks_passed += 1
    except:
        check_item("pnpm", False, "", "Not available")
    
    # Check Tauri CLI
    frontend_dir = Path(__file__).parent / "frontend"
    if frontend_dir.exists():
        total_checks += 1
        package_json = frontend_dir / "package.json"
        if check_item("Frontend Structure", 
                      package_json.exists(),
                      "package.json found",
                      "package.json missing"):
            checks_passed += 1
    
    return checks_passed, total_checks

def check_project_structure():
    """Check project files and structure."""
    print_header("Project Structure")
    
    checks_passed = 0
    total_checks = 0
    
    root_dir = Path(__file__).parent
    
    # Check key files and directories
    items_to_check = [
        ("Backend Directory", root_dir / "backend", "Backend code directory"),
        ("Frontend Directory", root_dir / "frontend", "Frontend code directory"), 
        ("GPU Patch", root_dir / "backend" / "patch_gpu.py", "GPU auto-detection"),
        ("PyInstaller Spec", root_dir / "backend" / "whisper-gui-core.spec", "Build specification"),
        ("Tauri Config", root_dir / "frontend" / "src-tauri" / "tauri.conf.json", "Tauri configuration"),
        ("Build Script", root_dir / "build.py", "Complete build script"),
        ("CLAUDE.md", root_dir / "CLAUDE.md", "Development guide"),
        ("README.md", root_dir / "README.md", "Project documentation")
    ]
    
    for name, path, description in items_to_check:
        total_checks += 1
        if check_item(name, 
                      path.exists(),
                      description,
                      f"Missing: {path}"):
            checks_passed += 1
    
    return checks_passed, total_checks

def main():
    """Run all verification checks."""
    print("🔍 Web Whisper Setup Verification")
    print(f"Platform: {platform.system()} {platform.machine()}")
    
    total_passed = 0
    total_checks = 0
    
    # Run all check categories
    categories = [
        ("Python Environment", check_python_environment),
        ("GPU Detection", check_gpu_detection),
        ("Node.js Environment", check_node_environment),
        ("Project Structure", check_project_structure)
    ]
    
    for category_name, check_function in categories:
        try:
            passed, total = check_function()
            total_passed += passed
            total_checks += total
            print(f"\n{category_name}: {passed}/{total} checks passed")
        except Exception as e:
            print(f"\n❌ {category_name} check failed: {e}")
    
    # Summary
    print_header("Summary")
    print(f"Overall: {total_passed}/{total_checks} checks passed")
    
    if total_passed == total_checks:
        print("🎉 All checks passed! Your Web Whisper setup is ready.")
        print("\nNext steps:")
        print("1. Test GPU detection: cd backend && python patch_gpu.py")
        print("2. Build the project: python build.py")
        print("3. Run in development: cd frontend && npm run tauri:dev")
        return True
    else:
        print("⚠️  Some checks failed. Please address the issues above.")
        print("\nFor help, see:")
        print("- README.md for setup instructions")
        print("- CLAUDE.md for development guide")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)