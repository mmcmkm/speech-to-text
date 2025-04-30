@echo off
chcp 65001 > nul
start /min pythonw main.py

REM 仮想環境が存在しない場合は作成
if not exist venv (
    echo 仮想環境を作成しています...
    python -m venv venv
    call venv\Scripts\activate
    echo pipをアップデートしています...
    python -m pip install --upgrade pip
    echo パッケージをインストールしています...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

REM 環境変数が設定されているか確認
if "%GEMINI_API_KEY%"=="" (
    echo エラー: GEMINI_API_KEYが設定されていません
    echo 先に環境変数を設定してください
    pause
    exit /b 1
)

REM アプリケーション実行
python main.py

REM 終了時に仮想環境を抜ける
call deactivate 