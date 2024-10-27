@echo off
rem Ensure we are in the directory containing the batch file
cd /d "%~dp0"
echo Current directory: %cd%


rem Specify the full path to main_v4.py to avoid confusion
set SCRIPT_PATH="%cd%\main.py"

rem Verify paths
echo Python path: "python "
echo Script path: %SCRIPT_PATH%

rem Run the Python script
python %SCRIPT_PATH%

rem Pause to keep the window open
pause
