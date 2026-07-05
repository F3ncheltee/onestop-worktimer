# Publishing a release

## Before you publish

1. Push the latest code: `git push origin main`
2. Build the executable: `python build_exe.py`
3. Confirm `dist/WorkTrackTimer.exe` runs and loads the UI

## Create the release on GitHub

1. Open [Releases](https://github.com/F3ncheltee/onestop-worktimer/releases) → **Draft a new release**
2. Tag: e.g. `v2.0.0` → **Create new tag on publish**
3. Title: e.g. `v2.0.0`
4. Notes: short summary of changes (UI redesign, calendar, analytics, etc.)
5. Attach `dist/WorkTrackTimer.exe` under **Assets**
6. **Publish release**

Users download the `.exe` from the release page. Their database stays in the folder where they run the app — it is not bundled in the release binary.
