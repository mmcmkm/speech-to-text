@echo off
REM UTF-8コードページを設定（BOM付き）
chcp 65001 > nul
echo 必要なパッケージをインストールしています...

REM 必要なパッケージのインストール
pip install -r requirements.txt
pip install pywin32

echo インストールが完了しました。
pause 