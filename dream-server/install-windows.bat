@echo off
:: Dream Server Windows Installer - Batch Entry Point
:: This bypasses PowerShell execution policy issues
::
:: Usage: Double-click or run from cmd:
::   install-windows.bat
::   install-windows.bat -DryRun
::   install-windows.bat -All

setlocal enabledelayedexpansion

:: Get script directory
set "SCRIPT_DIR=%~dp0"

:: Check if running as admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ============================================================
    echo   Dream Server Installer
    echo ============================================================
    echo.
    echo This installer requires Administrator privileges.
    echo Right-click and select "Run as administrator"
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

:: Check PowerShell exists
where powershell >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: PowerShell not found
    exit /b 1
)

:: Run the PowerShell installer with bypass
echo.
echo ============================================================
echo   Dream Server Installer for Windows
echo ============================================================
echo.
echo Starting installation...
echo.

powershell -ExecutionPolicy Bypass -NoProfile -File "%SCRIPT_DIR%install.ps1" %*

:: Capture exit code
set EXIT_CODE=%errorlevel%

if %EXIT_CODE% neq 0 (
    echo.
    echo Installation failed with error code: %EXIT_CODE%
    echo.
    echo Press any key to exit...
    pause >nul
)

exit /b %EXIT_CODE%
