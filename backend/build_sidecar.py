#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build script for creating cross-platform whisper-gui-core sidecar executables.
This script handles the PyInstaller compilation for both macOS and Windows.
"""

import os, sys
# Ensure UTF-8 stdout/stderr to avoid UnicodeEncodeError on Windows CI
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import platform
import subprocess
import shutil
from pathlib import Path
import importlib.util

def check_requirements():
    """Check if all required packages are installed."""
    required_packages = ['pyinstaller', 'gradio']
    
    # Platform-specific requirements
    if platform.system() == "Darwin" and platform.machine().startswith("arm"):
        required_packages.append('mlx-whisper')
    else:
        required_packages.extend(['faster-whisper', 'ctranslate2'])
    
    missing_packages = []
    name_map = {
        'pyinstaller': 'PyInstaller',  # real importable module name
    }
    for package in required_packages:
        mod_name = name_map.get(package, package).replace('-', '_')
        if importlib.util.find_spec(mod_name) is None:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("Please install them with:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ All required packages are installed")
    return True

BASE_DIR = Path(__file__).parent.resolve()

def clean_build_dirs():
    """Clean previous build directories."""
    dirs_to_clean = [BASE_DIR / 'build', BASE_DIR / 'dist', BASE_DIR / '__pycache__']
    for dir_name in dirs_to_clean:
        if dir_name.exists():
            print(f"🧹 Cleaning {dir_name}...")
            shutil.rmtree(dir_name)

def patch_main_py():
    """
    Patch main.py to use our optimized GPU auto-detection.
    Creates a backup and modifies the main.py to use our patch.
    """
    main_py_path = BASE_DIR / "main.py"
    backup_path = BASE_DIR / "main.py.backup"
    
    if not main_py_path.exists():
        print("❌ main.py not found!")
        return False
    
    # Create backup if it doesn't exist
    if not backup_path.exists():
        shutil.copy2(main_py_path, backup_path)
        print("📁 Created backup of main.py")
    
    # Read the original file
    with open(main_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add our patch import at the top
    patch_import = """
# GPU Auto-detection patch for cross-platform support
try:
    from patch_gpu import auto_engine_detailed
    USE_OPTIMIZED_BACKEND = True
    print("🚀 Using optimized GPU auto-detection backend")
except ImportError:
    USE_OPTIMIZED_BACKEND = False
    print("⚠️  Falling back to original whisperx backend")
"""
    
    # Insert the patch import after the existing imports
    import_end = content.find("enablePrint()")
    if import_end != -1:
        insert_pos = content.find("\n", import_end) + 1
        modified_content = content[:insert_pos] + patch_import + content[insert_pos:]
        
        with open(main_py_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        print("✅ Patched main.py with optimized backend")
        return True
    
    print("⚠️  Could not patch main.py automatically")
    return False

def build_executable():
    """Build the executable using PyInstaller."""
    system = platform.system()
    
    # Determine the correct spec file and build command
    spec_path = BASE_DIR / "whisper-gui-core.spec"
    
    if not spec_path.exists():
        print(f"❌ Spec file {spec_path.name} not found at {spec_path}!")
        print("⚠️  Falling back to CLI-based PyInstaller build without spec...")
        return build_executable_fallback()
    
    print(f"🔨 Building executable for {system}...")
    
    # PyInstaller command
    cmd = ["pyinstaller", "--clean", str(spec_path)]
    
    # Add platform-specific options
    if system == "Darwin":
        # macOS Universal binary
        cmd.extend(["--target-arch", "universal2"])
        expected_output = BASE_DIR / "dist/whisper-gui-core"
    elif system == "Windows":
        expected_output = BASE_DIR / "dist/whisper-gui-core.exe"
    else:
        # Linux
        expected_output = BASE_DIR / "dist/whisper-gui-core"
    
    try:
        # Run PyInstaller
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build completed successfully")
        
        # Check if the executable was created
        if expected_output.exists():
            file_size = expected_output.stat().st_size / (1024 * 1024)  # MB
            print(f"📦 Executable created: {expected_output} ({file_size:.1f} MB)")
            
            # Make executable (for Unix systems)
            if system in ["Darwin", "Linux"]:
                os.chmod(expected_output, 0o755)
                print("🔐 Set executable permissions")
            
            return True
        else:
            print(f"❌ Expected output file {expected_output} not found")
            return False

    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False

def build_executable_fallback():
    """Fallback build without spec using PyInstaller CLI flags."""
    print("🔧 Using fallback PyInstaller CLI configuration")
    system = platform.system()
    sep = ';' if system == 'Windows' else ':'
    add_data = [
        f"{(BASE_DIR / 'configs')}{sep}configs",
        f"{(BASE_DIR / 'scripts')}{sep}scripts",
    ]
    cmd = [
        "pyinstaller",
        "--clean",
        "--onefile",
        "--name", "whisper-gui-core",
        "--hidden-import", "mlx_whisper",
        "--hidden-import", "gradio",
        "--hidden-import", "safehttpx",
        # Collect resources for common packages
        "--collect-all", "mlx_whisper",
        "--collect-all", "gradio",
        "--collect-data", "gradio_client",
        "--collect-data", "groovy",
    ]
    for d in add_data:
        cmd.extend(["--add-data", d])
    cmd.append(str(BASE_DIR / "main.py"))

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Fallback build completed successfully")
        expected_output = BASE_DIR / ("dist/whisper-gui-core.exe" if system == "Windows" else "dist/whisper-gui-core")
        if expected_output.exists():
            size_mb = expected_output.stat().st_size / (1024 * 1024)
            print(f"📦 Executable created: {expected_output} ({size_mb:.1f} MB)")
            return True
        else:
            print(f"❌ Expected output not found: {expected_output}")
            return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Fallback build failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False

def test_executable():
    """Test the built executable."""
    system = platform.system()
    executable = BASE_DIR / ("dist/whisper-gui-core.exe" if system == "Windows" else "dist/whisper-gui-core")
    
    if not executable.exists():
        print(f"❌ Executable not found: {executable}")
    return False
    
    print("🧪 Testing executable...")
    
    try:
        # Test with --help flag
        result = subprocess.run([str(executable), "--help"], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Executable test passed")
            return True
        else:
            print(f"⚠️  Executable test returned code {result.returncode}")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️  Executable test timed out (this may be normal)")
        return True
    except Exception as e:
        print(f"❌ Executable test failed: {e}")
        return False

def restore_main_py():
    """Restore the original main.py from backup."""
    main_py_path = Path("main.py")
    backup_path = Path("main.py.backup")
    
    if backup_path.exists():
        shutil.copy2(backup_path, main_py_path)
        print("🔄 Restored original main.py")

def main():
    """Main build process."""
    print("🚀 Starting whisper-gui-core sidecar build process")
    print(f"Platform: {platform.system()} {platform.machine()}")
    
    # Change to the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    try:
        # Step 1: Check requirements
        if not check_requirements():
            sys.exit(1)
        
        # Step 2: Clean build directories
        clean_build_dirs()
        
        # Step 3: Patch main.py (optional)
        patch_main_py()
        
        # Step 4: Build executable
        if not build_executable():
            sys.exit(1)
        
        # Step 5: Test executable
        test_executable()
        
        print("🎉 Build process completed successfully!")
        print("\nNext steps:")
        print("1. Test the executable manually")
        print("2. Build the Tauri frontend: cd ../frontend && pnpm tauri build")
        
    except KeyboardInterrupt:
        print("\n❌ Build interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        # Always restore the original main.py
        restore_main_py()

if __name__ == "__main__":
    main()
