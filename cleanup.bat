@echo off
chcp 65001 >nul
echo ============================================
echo   FrankyAutoMate - Cleanup Utility
echo ============================================
echo.

:: --- Python Cache ---
echo [1/5] Cleaning __pycache__ ...
for /d /r "%~dp0" %%d in (__pycache__) do (
    if exist "%%d" (
        rmdir /s /q "%%d"
        echo   Removed: %%d
    )
)

:: --- .pyc files ---
echo [2/5] Cleaning .pyc files ...
for /r "%~dp0" %%f in (*.pyc) do (
    del /q "%%f"
    echo   Removed: %%f
)

:: --- Build artifacts ---
echo [3/5] Cleaning build folder ...
if exist "%~dp0build" (
    rmdir /s /q "%~dp0build"
    echo   Removed: build\
)

echo [4/5] Cleaning dist folder ...
if exist "%~dp0dist" (
    rmdir /s /q "%~dp0dist"
    echo   Removed: dist\
)

:: --- Log files ---
echo [5/5] Cleaning log files ...
for %%f in ("%~dp0*.log") do (
    del /q "%%f"
    echo   Removed: %%f
)

:: --- Optional: .spec file ---
if exist "%~dp0*.spec" (
    del /q "%~dp0*.spec"
    echo   Removed: *.spec
)

echo.
echo ============================================
echo   Cleanup Complete!
echo ============================================
pause
