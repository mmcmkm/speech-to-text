@echo off
chcp 65001 > nul
echo 音声文字起こしツールを起動しています...

REM 作業ディレクトリの設定
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM 環境変数が設定されているか確認
if "%GEMINI_API_KEY%"=="" (
    echo エラー: GEMINI_API_KEYが設定されていません
    echo 先に環境変数を設定してください
    pause
    exit /b 1
)

REM アプリケーション実行
python main.py
if errorlevel 1 (
    echo エラー: アプリケーションの実行に失敗しました
    pause
    exit /b 1
) 