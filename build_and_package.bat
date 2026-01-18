@echo off
echo Installing WorkTrack Timer Dependencies...
pip install -r requirements.txt

echo.
echo Building WorkTrack Timer Executable...
python build_exe.py

if exist "dist\WorkTrackTimer.exe" (
    echo.
    echo ========================================================
    echo SUCCESS! The executable has been created.
    echo You can find it in the 'dist' folder: WorkTrackTimer.exe
    echo.
    echo You can copy this single file anywhere and run it.
    echo No installation required for the user.
    echo ========================================================
    
    :: Optional: Create a shortcut on the desktop for testing
    set /p create_shortcut="Do you want to create a shortcut on your Desktop? (y/n): "
    if /i "%create_shortcut%"=="y" (
        python create_shortcut.py
    )
) else (
    echo.
    echo Build failed. Please check the error messages above.
)

pause
