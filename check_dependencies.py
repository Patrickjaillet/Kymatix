import sys
import shutil
import importlib.util
import os

def check_package(package_name, import_name=None):
    """Checks if a Python package is installed."""
    if import_name is None:
        import_name = package_name
    
    print(f"Checking {package_name}...", end=" ")
    # find_spec is preferred over simple import to avoid side effects
    if importlib.util.find_spec(import_name) is not None:
        print("OK")
        return True
    else:
        print("MISSING")
        return False

def check_ffmpeg():
    """Checks if FFmpeg is available in PATH or current directory."""
    print("Checking FFmpeg...", end=" ")
    
    # Check in system PATH
    if shutil.which("ffmpeg"):
        print("OK (Found in PATH)")
        return True
    
    # Check in current directory (as per README instructions)
    local_ffmpeg = os.path.join(os.getcwd(), "ffmpeg.exe")
    if os.path.exists(local_ffmpeg):
        print(f"OK (Found in {local_ffmpeg})")
        return True
        
    print("MISSING")
    return False

def check_carabiner():
    """Checks if Carabiner is available (for Ableton Link)."""
    print("Checking Carabiner...", end=" ")
    if shutil.which("Carabiner") or os.path.exists("Carabiner.exe"):
        print("OK")
        return True
    print("MISSING (Optional for Link)")
    return False

def main():
    print("--- Verifying Dependencies for KYMATIX STUDIO ---")
    
    # List of (Package Name, Import Name)
    required_packages = [
        ("librosa", "librosa"),
        ("pygame", "pygame"),
        ("PyQt6", "PyQt6"),
        ("PyOpenGL", "OpenGL"),
        ("numpy", "numpy"),
        ("SpoutGL", "SpoutGL"),
        ("sacn", "sacn"),
        ("pyaudio", "pyaudio"),
    ]
    
    missing_packages = []
    for pkg_name, import_name in required_packages:
        if not check_package(pkg_name, import_name):
            missing_packages.append(pkg_name)
            
    ffmpeg_ok = check_ffmpeg()
    check_carabiner()
    
    print("\n--- Summary ---")
    if not missing_packages and ffmpeg_ok:
        print("✅ All dependencies are installed and ready!")
        sys.exit(0)
    else:
        if missing_packages:
            print(f"❌ Missing Python packages: {', '.join(missing_packages)}")
            print(f"   Run: pip install {' '.join(missing_packages)}")
        
        if not ffmpeg_ok:
            print("❌ FFmpeg is missing.")
            print("   Please download FFmpeg and add it to your PATH or place ffmpeg.exe in this folder.")
            
        sys.exit(1)

if __name__ == "__main__":
    main()