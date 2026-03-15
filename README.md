# OneStop-Worktimer

A simple, offline-only desktop timer for tracking work sessions, designed for friction-free productivity.

## Features

- **Start/Stop Timer**: Single click to start and stop sessions.
- **Countdown Mode**: Set a target time and get notified when it ends (supports overtime tracking).
- **Analytics**: Visual overview of your work hours (Today, Week, Month, and 14-day history chart).
- **Projects**: Tag sessions with projects for better organization.
- **History & Export**: View past sessions, filter by date/search, edit/add past sessions, and export to CSV/Excel.
- **Offline Storage**: All data is stored locally in `worktrack.db` (SQLite), created in the same folder as the app when you first run it—one database per user/machine. No cloud, no telemetry.
- **System Tray**: Minimized app stays in the system tray.
- **Idle Detection**: Warns you if you've been away for more than 5 minutes.

## Installation (For Users)

**Option A: Single Executable (Recommended for quick install)**
1.  **Download**: Get `WorkTrackTimer.exe` from the [Releases](https://github.com/F3ncheltee/onestop-worktimer/releases) page on GitHub (or build it yourself—see *Building the Executable* below).
2.  **Install**: No installation required! Place the file anywhere (e.g., Desktop or Documents).
3.  **Run**: Double-click `WorkTrackTimer.exe`. A `worktrack.db` file will be created in the same folder for your sessions.
4.  **Uninstall**: Delete the `.exe` and the `worktrack.db` file in that folder.

**Option B: Python Source**
1.  Ensure Python 3.8+ is installed.
2.  Clone this repository.
3.  Install dependencies: `pip install -r requirements.txt`
4.  Run via: `python -m app.main`

## Building the Executable

If you want to build the `.exe` file yourself (e.g., after modifying the code):

1.  Open the project folder in a terminal.
2.  Run the build batch file:
    ```cmd
    build_and_package.bat
    ```
3.  Once finished, the new `WorkTrackTimer.exe` will appear in the `dist/` folder.

## Usage

*   **Start/Stop**: Click **START** to begin tracking. Click **STOP** to finish.
*   **Projects**: Use the dropdown to select a project, or click `+` to add a new one.
*   **Countdown**: Toggle "Countdown" mode to set a timer (e.g., 45 minutes).
*   **History**: Click "View History / Export" to see past sessions, edit mistakes, or export data to Excel/CSV.
*   **Analytics**: Click "Analytics" to see charts of your progress.
*   **Minimize**: Closing the window minimizes the app to the System Tray. Double-click the tray icon to restore it.
*   **Hotkeys**: `Ctrl+Alt+S` to toggle start/stop (functionality depends on OS permissions).
