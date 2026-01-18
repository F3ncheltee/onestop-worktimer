import os
import sys
import subprocess

def create_shortcut():
    """
    Creates a Windows desktop shortcut for WorkTrack Timer.
    Uses VBScript to avoid external dependencies like pywin32.
    """
    try:
        # Paths
        current_dir = os.path.dirname(os.path.abspath(__file__))
        target_script = os.path.join(current_dir, "app", "main.py")
        python_exe = sys.executable
        icon_path = os.path.join(current_dir, "app", "resources", "icon.ico") # Placeholder if exists, else default

        # Desktop path
        desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
        shortcut_path = os.path.join(desktop, "WorkTrack Timer.lnk")

        # Arguments: run as module or script
        # Best to run python -m app.main from root
        # Target: python.exe
        # Arguments: -m app.main
        # Working Dir: current_dir
        
        args = f"-m app.main"

        # VBScript content
        vbs_script = f"""
            Set oWS = WScript.CreateObject("WScript.Shell")
            sLinkFile = "{shortcut_path}"
            Set oLink = oWS.CreateShortcut(sLinkFile)
            oLink.TargetPath = "{python_exe}"
            oLink.Arguments = "{args}"
            oLink.WorkingDirectory = "{current_dir}"
            oLink.WindowStyle = 1
            oLink.Description = "WorkTrack Timer"
            oLink.Save
        """
        
        vbs_file = os.path.join(current_dir, "create_shortcut.vbs")
        
        with open(vbs_file, "w") as f:
            f.write(vbs_script)
            
        # Execute VBS
        subprocess.run(["cscript", "//Nologo", vbs_file], check=True)
        
        # Cleanup
        os.remove(vbs_file)
        
        print(f"Shortcut created successfully on Desktop: {shortcut_path}")
        
    except Exception as e:
        print(f"Failed to create shortcut: {e}")

if __name__ == "__main__":
    create_shortcut()
