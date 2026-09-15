@echo off
setlocal
echo =======================================================
echo Launching Parallel MCTS Orienteering Problem Visualizer...
echo =======================================================

set "TARGET_FILE=%~dp0orienteering_viz\index.html"

:: Check Google Chrome (64-bit & 32-bit)
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    echo Opening in Google Chrome...
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "%TARGET_FILE%"
    exit /b
)
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    echo Opening in Google Chrome...
    start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" "%TARGET_FILE%"
    exit /b
)

:: Check Microsoft Edge
if exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" (
    echo Opening in Microsoft Edge...
    start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" "%TARGET_FILE%"
    exit /b
)
if exist "C:\Program Files\Microsoft\Edge\Application\msedge.exe" (
    echo Opening in Microsoft Edge...
    start "" "C:\Program Files\Microsoft\Edge\Application\msedge.exe" "%TARGET_FILE%"
    exit /b
)

:: Fallback to default web browser protocol
echo Opening in default browser...
start msedge "%TARGET_FILE%" 2>nul || start chrome "%TARGET_FILE%" 2>nul || start "" "%TARGET_FILE%"
exit /b
