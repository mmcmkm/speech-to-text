import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path

class Logger:
    _instance = None
    _initialized = False

    def __new__(cls, app_name: str):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, app_name: str):
        if not Logger._initialized:
            self.app_name = app_name
            self.log_dir = Path("logs")
            self.handlers = []
            self._setup_logging()
            Logger._initialized = True

    def _setup_logging(self):
        """ログ設定の初期化"""
        # ログディレクトリの作成
        self.log_dir.mkdir(exist_ok=True)

        # ログファイル名の設定
        date_str = datetime.now().strftime("%Y%m%d")
        log_file = self.log_dir / f"{self.app_name}_{date_str}.log"
        error_log_file = self.log_dir / f"{self.app_name}_error_{date_str}.log"

        # ログフォーマットの設定
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 通常ログの設定
        file_handler = self._create_file_handler(log_file, formatter, logging.INFO)
        self.handlers.append(file_handler)

        # エラーログの設定
        error_handler = self._create_file_handler(error_log_file, formatter, logging.ERROR)
        self.handlers.append(error_handler)

        # コンソール出力の設定
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        self.handlers.append(console_handler)

    def _create_file_handler(self, log_file: Path, formatter: logging.Formatter, level: int):
        """ファイルハンドラーの作成"""
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=256 * 1024,  # 256KB
            backupCount=5,
            encoding='utf-8'
        )
        handler.setFormatter(formatter)
        handler.setLevel(level)
        return handler

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """指定された名前のロガーを取得"""
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        
        # 既存のハンドラーをクリア
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            
        # シングルトンインスタンスからハンドラーを追加
        if Logger._instance:
            for handler in Logger._instance.handlers:
                logger.addHandler(handler)
        
        return logger 