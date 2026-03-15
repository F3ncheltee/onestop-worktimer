# Publishing a Release (with .exe for download)

Use this when you want to publish a new version and offer **WorkTrackTimer.exe** for one-click download.

## Prerequisites

- Latest changes pushed: `git push origin main`
- Built .exe exists: `dist\WorkTrackTimer.exe` (run `python build_exe.py` or `build_and_package.bat` if needed)

## Steps

1. **Open Releases**
   - Go to: **https://github.com/F3ncheltee/onestop-worktimer/releases**
   - Click **"Draft a new release"** (or "Create a new release")

2. **Choose a tag**
   - Click **"Choose a tag"** → type a new tag, e.g. `v1.0.0` → **"Create new tag: v1.0.0 on publish"**
   - Release title: e.g. `v1.0.0` or `OneStop-Worktimer v1.0.0`

3. **Describe the release** (optional)
   - e.g. "First release. Single .exe, no install required. Download and run."

4. **Attach the .exe**
   - In **Assets**, click **"Attach binaries by dropping them here or selecting them"**
   - Select: `D:\onestopWorkTimer\onestop-worktimer\dist\WorkTrackTimer.exe`
   - (Or drag the file into the browser.)

5. **Publish**
   - Click **"Publish release"**.

After that, the [Releases](https://github.com/F3ncheltee/onestop-worktimer/releases) page will list the new version and users can download **WorkTrackTimer.exe** directly.
