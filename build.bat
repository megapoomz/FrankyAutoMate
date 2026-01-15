@echo off
setlocal

set APP_NAME=FrankyAutoMate
set VERSION=1.5.0
set MAIN_SCRIPT=main.py
set EXE_NAME=FrankyAutoMate.exe

echo ===================================================
echo     Build Script for %APP_NAME% v%VERSION%
echo ===================================================

:: 1. Check for PyInstaller
where pyinstaller >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller not found! Please install it:
    echo        pip install pyinstaller
    pause
    exit /b 1
)

:: 2. Cleanup
echo [1/4] Cleaning up previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del *.spec

:: 3. Build EXE
echo [2/4] Building EXE with PyInstaller...
pyinstaller --noconsole --onefile --name "%APP_NAME%" --icon="icon.ico" --clean "%MAIN_SCRIPT%"
:: Note: If you have an icon, change --icon=NONE to --icon=icon.ico

if not exist "dist\%EXE_NAME%" (
    echo [ERROR] Build failed! EXE not found.
    pause
    exit /b 1
)

:: 4. Create Update ZIP
echo [3/4] Creating Update ZIP...
set ZIP_NAME=%APP_NAME%_v%VERSION%_Update.zip
powershell -Command "Compress-Archive -Path 'dist\%EXE_NAME%' -DestinationPath '%ZIP_NAME%' -Force"
echo    - Created: %ZIP_NAME%

:: 5. Create Installer (Optional)
echo [4/4] Checking for Inno Setup...
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    echo    - Inno Setup found. Compiling installer...
    %ISCC% setup_script.iss
    echo    - Installer created in Output/ folder
) else (
    echo    [WARNING] Inno Setup compiler (ISCC.exe) not found at default location.
    echo    Skipping installer creation. (Install Inno Setup to enable this step)
)

echo ===================================================
echo     Build Complete!
echo ===================================================
echo [Locations]
echo  - EXE: dist\%EXE_NAME%
echo  - ZIP: %ZIP_NAME%
if exist Output (
    echo  - Installer: Output\Setup_%APP_NAME%_v%VERSION%.exe
)
echo ===================================================
pause
