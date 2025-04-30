import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from pathlib import Path
import ctypes

# Windowsでコンソールウィンドウを非表示にする
if sys.platform == "win32":
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# 自作モジュールのインポート
from services.recorder import AudioRecorder
from services.transcription import TranscriptionService
from utils.clipboard import copy_to_clipboard
from ui.main_window import MainWindow
from utils.logger import Logger

def set_app_user_model_id():
    """Windowsのタスクバーで独立したアイコンとして表示するための設定"""
    try:
        # AppUserModelIDの設定
        app_id = "SpeechToText.App"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception as e:
        Logger.get_logger(__name__).warning(f"AppUserModelIDの設定に失敗しました: {str(e)}")

def main():
    """メインアプリケーションの実行関数"""
    # ロガーの初期化
    logger = Logger("speech_to_text")
    app_logger = logger.get_logger(__name__)
    
    # 環境変数のチェック
    if not os.environ.get('GEMINI_API_KEY'):
        error_msg = "GEMINI_API_KEY環境変数が設定されていません"
        app_logger.error(error_msg)
        print(f"エラー: {error_msg}")
        print("環境変数を設定してから再度実行してください")
        sys.exit(1)
    
    # アプリケーション初期化
    app = QApplication(sys.argv)
    
    # Windowsのタスクバー設定
    if sys.platform == "win32":
        set_app_user_model_id()
    
    # アプリケーション名とアイコンの設定
    app.setApplicationName("Speech to Text")
    app.setApplicationDisplayName("Speech to Text")
    
    # アイコンの設定
    icon_path = Path("resources/icon.png")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
        app_logger.info(f"アイコンを設定しました: {icon_path}")
    else:
        app_logger.warning(f"アイコンファイルが見つかりません: {icon_path}")
    
    try:
        app_logger.info("アプリケーションを開始します")
        
        # サービスの初期化
        recorder = AudioRecorder()
        transcription_service = TranscriptionService()
        
        # メインウィンドウの作成
        import utils.clipboard as clipboard_module
        window = MainWindow(recorder, transcription_service, clipboard_module)
        
        # ウィンドウのアイコン設定
        if icon_path.exists():
            window.setWindowIcon(QIcon(str(icon_path)))
        
        window.show()
        
        app_logger.info("メインウィンドウを表示しました")
        
        # イベントループ開始
        sys.exit(app.exec())
        
    except Exception as e:
        error_msg = f"予期せぬエラーが発生しました: {str(e)}"
        app_logger.error(error_msg, exc_info=True)
        print(f"エラー: {error_msg}")
        sys.exit(1)

if __name__ == "__main__":
    main() 