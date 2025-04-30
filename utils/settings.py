import json
import os
from pathlib import Path
from utils.logger import Logger
from PySide6.QtCore import QSettings, QPoint, QSize

class Settings:
    """設定を管理するクラス"""
    
    def __init__(self):
        """設定の初期化"""
        self.logger = Logger("speech_to_text").get_logger(__name__)
        self.settings_file = Path.home() / ".speech_to_text" / "settings.json"
        self.settings = self._load_settings()
        self.settings_q = QSettings("SpeechToText", "Settings")
    
    def _load_settings(self):
        """設定ファイルから設定を読み込む"""
        default_settings = {
            "model": "gemini-2.0-pro",
            "silence_detection": True,
            "silence_threshold": 0.01,
            "silence_duration": 20
        }
        
        try:
            if self.settings_file.exists():
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    # デフォルト設定とマージ（新しい設定項目の追加に対応）
                    return {**default_settings, **settings}
            else:
                # 設定ファイルが存在しない場合はデフォルト設定を保存
                self._save_settings(default_settings)
                return default_settings
        except Exception as e:
            self.logger.error(f"設定の読み込みに失敗しました: {str(e)}")
            return default_settings
    
    def _save_settings(self, settings):
        """設定をファイルに保存する"""
        try:
            # 設定ディレクトリが存在しない場合は作成
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"設定の保存に失敗しました: {str(e)}")
    
    def get(self, key, default=None):
        """設定値を取得する

        Args:
            key (str): 設定のキー
            default: デフォルト値

        Returns:
            設定値
        """
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """設定値を保存する

        Args:
            key (str): 設定のキー
            value: 保存する値
        """
        self.settings[key] = value
        self._save_settings(self.settings)
    
    def get_all(self):
        """すべての設定を取得する"""
        return self.settings.copy()
    
    def save(self):
        """設定を保存する"""
        self.settings_q.sync()
    
    def get_window_geometry(self):
        """ウィンドウの位置とサイズを取得する

        Returns:
            tuple: (位置, サイズ) のタプル
        """
        pos = self.settings_q.value("window/position", QPoint(100, 100))
        size = self.settings_q.value("window/size", QSize(800, 600))
        return pos, size
    
    def set_window_geometry(self, pos, size):
        """ウィンドウの位置とサイズを保存する

        Args:
            pos (QPoint): ウィンドウの位置
            size (QSize): ウィンドウのサイズ
        """
        self.settings_q.setValue("window/position", pos)
        self.settings_q.setValue("window/size", size)
    
    def get_window_state(self):
        """ウィンドウの状態（最大化など）を取得する

        Returns:
            bool: 最大化されているかどうか
        """
        return self.settings_q.value("window/maximized", False, type=bool)
    
    def set_window_state(self, is_maximized):
        """ウィンドウの状態を保存する

        Args:
            is_maximized (bool): 最大化されているかどうか
        """
        self.settings_q.setValue("window/maximized", is_maximized) 