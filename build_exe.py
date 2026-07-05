import PyInstaller.__main__
import os
import shutil
import tempfile

DB_NAME = "worktrack.db"


def _preserve_live_data():
    """Stash dist/worktrack.db before cleaning dist/, restore after build."""
    stash_dir = tempfile.mkdtemp(prefix="wtt_build_stash_")
    stash_path = os.path.join(stash_dir, DB_NAME)
    stashed_size = 0

    db_path = os.path.join("dist", DB_NAME)
    if os.path.exists(db_path) and os.path.getsize(db_path) > 0:
        shutil.copy2(db_path, stash_path)
        stashed_size = os.path.getsize(stash_path)
        print(f"Preserved {db_path} ({stashed_size} bytes).")

    def restore():
        if stashed_size == 0:
            shutil.rmtree(stash_dir, ignore_errors=True)
            return
        os.makedirs("dist", exist_ok=True)
        dest = os.path.join("dist", DB_NAME)
        dest_size = os.path.getsize(dest) if os.path.exists(dest) else -1
        if dest_size < stashed_size:
            shutil.copy2(stash_path, dest)
            print(f"Restored {dest}.")
        shutil.rmtree(stash_dir, ignore_errors=True)

    return restore


def build_exe():
    print("Building executable...")
    restore_live_data = _preserve_live_data()
    try:
        if os.path.exists("build"):
            shutil.rmtree("build")
        if os.path.exists("dist"):
            shutil.rmtree("dist")

        args = [
            "app/main.py",
            "--name=WorkTrackTimer",
            "--noconsole",
            "--onefile",
            "--windowed",
            "--clean",
            "--hidden-import=pynput.keyboard._win32",
            "--hidden-import=pynput.mouse._win32",
            "--hidden-import=sqlite3",
        ]
        if os.path.exists("app/web"):
            args.append("--add-data=app/web;app/web")
        if os.path.exists("app/resources"):
            args.append("--add-data=app/resources;app/resources")
        if os.path.exists("app/resources/icon.ico"):
            args.append("--icon=app/resources/icon.ico")

        try:
            PyInstaller.__main__.run(args)
            print("\nBuild successful!")
            print(f"Output: {os.path.abspath('dist/WorkTrackTimer.exe')}")
        except Exception as e:
            print(f"\nBuild failed: {e}")
    finally:
        restore_live_data()


if __name__ == "__main__":
    build_exe()
