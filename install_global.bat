@echo off
chcp 65001
setlocal enabledelayedexpansion

echo Installing required packages...

cd /d "%~dp0"
REM 実行ディレクトリに移動してからrequirements.txtを使用
pip install -r requirements.txt
if errorlevel 1 (
    echo Error occurred during installation.
) else (
    echo Installation completed successfully.
)

pause 