import PyInstaller.__main__
import os
import shutil

def build_exe():
    """
    Builds the standalone executable using PyInstaller.
    """
    print("Building executable...")
    
    # Clean previous builds
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("dist"):
        shutil.rmtree("dist")
        
    # PyInstaller arguments
    args = [
        'app/main.py',                      # Entry point
        '--name=WorkTrackTimer',            # Name of the exe
        '--noconsole',                      # Hide console window
        '--onefile',                        # Single exe file (easier for distribution)
        '--windowed',                       # Windows subsystem
        '--clean',                          # Clean cache
        # Imports that might be missed
        '--hidden-import=pynput.keyboard._win32',
        '--hidden-import=pynput.mouse._win32',
        '--hidden-import=sqlite3',
    ]
    
    # Add resources folder and icon only if they exist
    if os.path.exists("app/resources"):
        args.append('--add-data=app/resources;app/resources')
    if os.path.exists("app/resources/icon.ico"):
        args.append('--icon=app/resources/icon.ico')

    try:
        PyInstaller.__main__.run(args)
        print("\nBuild successful!")
        print(f"Executable is located at: {os.path.abspath('dist/WorkTrackTimer.exe')}")
    except Exception as e:
        print(f"\nBuild failed: {e}")

if __name__ == "__main__":
    build_exe()
