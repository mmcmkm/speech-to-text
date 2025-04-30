import win32clipboard
import win32con
import win32gui
import win32api
import time
from utils.logger import Logger

logger = Logger("speech_to_text").get_logger(__name__)

def copy_to_clipboard(text):
    """テキストをクリップボードにコピーし、可能であれば自動ペーストを試みる"""
    try:
        # クリップボードを開く
        win32clipboard.OpenClipboard()
        # クリップボードをクリア
        win32clipboard.EmptyClipboard()
        # テキストを設定
        win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
        # クリップボードを閉じる
        win32clipboard.CloseClipboard()
        
        # 自動ペーストを試みる
        try_auto_paste()
        
        return True
    except Exception as e:
        logger.error(f"クリップボード操作に失敗しました: {str(e)}")
        return False

def try_auto_paste():
    """アクティブウィンドウに自動ペーストを試みる"""
    try:
        # 現在のアクティブウィンドウを取得
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            # Ctrl+Vを送信
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)  # Ctrlキーを押す
            win32api.keybd_event(ord('V'), 0, 0, 0)  # Vキーを押す
            time.sleep(0.1)  # 少し待機
            win32api.keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)  # Vキーを離す
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)  # Ctrlキーを離す
            logger.info("自動ペーストを実行しました")
    except Exception as e:
        logger.warning(f"自動ペーストに失敗しました: {str(e)}")
        # エラーは無視して続行（自動ペーストは補助機能のため） 