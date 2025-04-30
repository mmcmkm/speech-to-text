@echo off
chcp 65001 > nul

echo リソースディレクトリの作成を開始します...

:: リソースディレクトリの作成
if not exist "resources" (
    mkdir resources
    echo resources ディレクトリを作成しました。
) else (
    echo resources ディレクトリは既に存在します。
)

echo.
echo 以下のファイルを resources ディレクトリに配置してください：
echo - icon.png （アプリケーションアイコン）
echo.
echo 完了しました。
pause 