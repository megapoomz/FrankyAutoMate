@echo off
setlocal enabledelayedexpansion

set APP_NAME=FrankyAutoMate
set MAIN_SCRIPT=main.py
set EXE_NAME=FrankyAutoMate.exe

:: 0. Extract Version from autoclick.py
echo [0/4] Extracting version from core\constants.py...
set VERSION=
for /f "tokens=2 delims==" %%a in ('findstr /C:"APP_VERSION =" core\constants.py') do (
    set VERSION=%%a
)
set VERSION=!VERSION:"=!
set VERSION=!VERSION: =!

if "!VERSION!"=="" (
    echo [ERROR] Could not extract version from autoclick.py
    pause
    exit /b 1
)

echo ===================================================
echo     Build Script for %APP_NAME% v!VERSION!
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

:: 3. Build EXE
echo [2/4] Building EXE with PyInstaller...

:: Check for UPX
set UPX_CMD=
if exist "upx\upx.exe" (
    echo    - UPX found: Using compression...
    set UPX_CMD=--upx-dir="upx"
)

if exist "FrankyAutoMate.spec" (
    echo    - Using existing .spec file
    pyinstaller !UPX_CMD! --clean "FrankyAutoMate.spec"
) else if not exist "icon.ico" (
    echo [WARNING] icon.ico not found. Building without icon...
    pyinstaller --noconsole --onefile --name "%APP_NAME%" !UPX_CMD! --clean "%MAIN_SCRIPT%"
) else (
    echo    - Using icon: icon.ico
    pyinstaller --noconsole --onefile --name "%APP_NAME%" --icon="icon.ico" !UPX_CMD! --clean "%MAIN_SCRIPT%"
)

if not exist "dist\%EXE_NAME%" (
    echo [ERROR] Build failed! EXE not found.
    pause
    exit /b 1
)

:: 4. Create Update ZIP
echo [3/4] Creating Update ZIP...
set ZIP_NAME=%APP_NAME%_v!VERSION!_Update.zip
powershell -Command "Compress-Archive -Path 'dist\%EXE_NAME%' -DestinationPath '!ZIP_NAME!' -Force"
echo    - Created: !ZIP_NAME!

:: 5. Create Installer (Optional)
echo [4/4] Checking for Inno Setup...
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    echo    - Inno Setup found. Compiling installer...
    %ISCC% /DMyAppVersion="!VERSION!" setup_script.iss
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
echo  - ZIP: !ZIP_NAME!
if exist Output (
    echo  - Installer: Output\Setup_%APP_NAME%_v!VERSION!.exe
)
echo ===================================================
pause
