from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QTextEdit, QLabel, QMessageBox, QApplication,
    QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox, QFormLayout, QProgressBar,
    QComboBox
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
import threading
import time
from utils.settings import Settings

class MainWindow(QMainWindow):
    # シグナル定義
    transcription_complete = Signal(str)
    recording_status_changed = Signal(bool)
    silence_detected = Signal()
    
    def __init__(self, recorder, transcription_service, clipboard_module):
        """メインウィンドウの初期化
        
        Args:
            recorder: 音声録音クラスのインスタンス
            transcription_service: 文字起こしサービスのインスタンス
            clipboard_module: クリップボード操作モジュール
        """
        super().__init__()
        
        self.recorder = recorder
        self.transcription_service = transcription_service
        self.clipboard_module = clipboard_module
        self.settings = Settings()
        
        self.recording_thread = None
        self.transcription_thread = None
        self.is_recording = False
        
        # 無音検出用のタイマー
        self.silence_timer = QTimer()
        self.silence_timer.timeout.connect(self.check_silence)
        
        self.init_ui()
        self.load_settings()
        self.setup_connections()
    
    def load_settings(self):
        """保存された設定を読み込む"""
        # モデルの設定
        saved_model = self.settings.get("model")
        if saved_model:
            try:
                self.transcription_service.set_model(saved_model)
                index = self.model_combo.findData(saved_model)
                if index >= 0:
                    self.model_combo.setCurrentIndex(index)
            except ValueError:
                pass
        
        # 文字起こしモードの設定
        saved_mode = self.settings.get("transcription_mode")
        if saved_mode:
            try:
                self.transcription_service.set_mode(saved_mode)
                index = self.mode_combo.findData(saved_mode)
                if index >= 0:
                    self.mode_combo.setCurrentIndex(index)
            except ValueError:
                pass
        
        # 無音検出の設定
        self.silence_detection_checkbox.setChecked(self.settings.get("silence_detection", True))
        self.silence_threshold_spinbox.setValue(self.settings.get("silence_threshold", 0.01))
        self.silence_duration_spinbox.setValue(self.settings.get("silence_duration", 20))
        
        # 録音クラスの設定を更新
        self.update_silence_settings()
    
    def save_settings(self):
        """現在の設定を保存する"""
        # モデルの設定
        self.settings.set("model", self.transcription_service.get_current_model())
        
        # 文字起こしモードの設定
        self.settings.set("transcription_mode", self.transcription_service.get_current_mode())
        
        # 無音検出の設定
        self.settings.set("silence_detection", self.silence_detection_checkbox.isChecked())
        self.settings.set("silence_threshold", self.silence_threshold_spinbox.value())
        self.settings.set("silence_duration", self.silence_duration_spinbox.value())
    
    def init_ui(self):
        """UIの初期化"""
        self.setWindowTitle("音声文字起こしツール")
        
        # ウィンドウの位置とサイズを復元
        pos, size = self.settings.get_window_geometry()
        self.move(pos)
        self.resize(size)
        
        # 最大化状態を復元
        if self.settings.get_window_state():
            self.showMaximized()
        
        # メインウィジェット
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # メインレイアウト
        main_layout = QVBoxLayout(main_widget)
        
        # モデル選択グループ
        model_group = QGroupBox("モデル設定")
        model_layout = QFormLayout()
        
        # モデル選択コンボボックス
        self.model_combo = QComboBox()
        available_models = self.transcription_service.get_available_models()
        for model_name, description in available_models.items():
            self.model_combo.addItem(f"{model_name} - {description}", model_name)
        
        # 現在のモデルを選択
        current_model = self.transcription_service.get_current_model()
        index = self.model_combo.findData(current_model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        
        model_layout.addRow("使用するモデル:", self.model_combo)

        # 文字起こしモード選択コンボボックス
        self.mode_combo = QComboBox()
        available_modes = self.transcription_service.get_available_modes()
        for mode_id, mode_info in available_modes.items():
            self.mode_combo.addItem(f"{mode_info['name']} - {mode_info['description']}", mode_id)
        
        # 現在のモードを選択
        current_mode = self.transcription_service.get_current_mode()
        index = self.mode_combo.findData(current_mode)
        if index >= 0:
            self.mode_combo.setCurrentIndex(index)
        
        model_layout.addRow("文字起こしモード:", self.mode_combo)
        
        model_group.setLayout(model_layout)
        main_layout.addWidget(model_group)
        
        # 設定グループ
        settings_group = QGroupBox("録音設定")
        settings_layout = QFormLayout()
        
        # 無音検出の有効/無効
        self.silence_detection_checkbox = QCheckBox("無音検出を有効にする")
        self.silence_detection_checkbox.setChecked(True)
        settings_layout.addRow(self.silence_detection_checkbox)
        
        # 無音検出の閾値
        self.silence_threshold_spinbox = QDoubleSpinBox()
        self.silence_threshold_spinbox.setRange(0.001, 1.0)
        self.silence_threshold_spinbox.setValue(0.01)
        self.silence_threshold_spinbox.setSingleStep(0.001)
        self.silence_threshold_spinbox.setDecimals(3)
        settings_layout.addRow("無音検出閾値:", self.silence_threshold_spinbox)
        
        # 無音継続時間
        self.silence_duration_spinbox = QSpinBox()
        self.silence_duration_spinbox.setRange(1, 60)
        self.silence_duration_spinbox.setValue(20)
        self.silence_duration_spinbox.setSuffix(" 秒")
        settings_layout.addRow("無音継続時間:", self.silence_duration_spinbox)
        
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)
        
        # テキスト表示エリア
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlaceholderText("ここに文字起こし結果が表示されます")
        main_layout.addWidget(self.text_edit)
        
        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)
        
        # 録音状態表示ラベル
        self.recording_label = QLabel()
        self.recording_label.setAlignment(Qt.AlignCenter)
        self.recording_label.setStyleSheet("""
            QLabel {
                color: #f44336;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        main_layout.addWidget(self.recording_label)
        
        # ボタンレイアウト
        button_layout = QHBoxLayout()
        
        # 録音ボタン
        self.record_button = QPushButton("録音開始")
        self.record_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        button_layout.addWidget(self.record_button)
        
        # 停止ボタン
        self.stop_button = QPushButton("録音停止")
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        button_layout.addWidget(self.stop_button)
        
        # クリアボタン
        self.clear_button = QPushButton("一時ファイルを削除")
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #757575;
            }
        """)
        button_layout.addWidget(self.clear_button)
        
        main_layout.addLayout(button_layout)
        
        # コピーボタン
        self.copy_button = QPushButton("クリップボードにコピー")
        self.copy_button.setEnabled(False)
        main_layout.addWidget(self.copy_button)
    
    def setup_connections(self):
        """シグナル/スロット接続の設定"""
        self.record_button.clicked.connect(self.start_recording)
        self.stop_button.clicked.connect(self.stop_recording)
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.model_combo.currentIndexChanged.connect(self.change_model)
        self.mode_combo.currentIndexChanged.connect(self.change_mode)
        
        # カスタムシグナル
        self.transcription_complete.connect(self.update_transcription)
        self.recording_status_changed.connect(self.update_recording_status)
        self.silence_detected.connect(self.handle_silence_detection)
        
        # 設定変更時の接続
        self.silence_detection_checkbox.stateChanged.connect(self.update_silence_settings)
        self.silence_threshold_spinbox.valueChanged.connect(self.update_silence_settings)
        self.silence_duration_spinbox.valueChanged.connect(self.update_silence_settings)
    
    def change_model(self, index):
        """モデルを変更する

        Args:
            index (int): 選択されたモデルのインデックス
        """
        model_name = self.model_combo.itemData(index)
        try:
            self.transcription_service.set_model(model_name)
            self.save_settings()
        except ValueError as e:
            QMessageBox.warning(self, "エラー", str(e))
            # 元のモデルに戻す
            current_model = self.transcription_service.get_current_model()
            index = self.model_combo.findData(current_model)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
    
    def change_mode(self, index):
        """文字起こしモードを変更する

        Args:
            index (int): 選択されたモードのインデックス
        """
        mode_id = self.mode_combo.itemData(index)
        try:
            self.transcription_service.set_mode(mode_id)
            self.save_settings()
        except ValueError as e:
            QMessageBox.warning(self, "エラー", str(e))
            # 元のモードに戻す
            current_mode = self.transcription_service.get_current_mode()
            index = self.mode_combo.findData(current_mode)
            if index >= 0:
                self.mode_combo.setCurrentIndex(index)
    
    def update_silence_settings(self):
        """無音検出の設定を更新"""
        if self.silence_detection_checkbox.isChecked():
            self.recorder.silence_threshold = self.silence_threshold_spinbox.value()
            self.recorder.silence_duration = self.silence_duration_spinbox.value()
            # 設定を保存
            self.settings.set("silence_threshold", self.silence_threshold_spinbox.value())
            self.settings.set("silence_duration", self.silence_duration_spinbox.value())
            self.settings.set("silence_detection", True)
        else:
            self.settings.set("silence_detection", False)
    
    def start_recording(self):
        """録音開始処理"""
        if self.is_recording:
            return
        
        # 設定の更新
        self.update_silence_settings()
        
        # 録音開始
        success = self.recorder.start_recording()
        if not success:
            QMessageBox.warning(self, "エラー", "録音を開始できませんでした")
            return
        
        # 録音スレッド開始
        self.recording_thread = threading.Thread(target=self.recording_worker)
        self.recording_thread.daemon = True
        self.recording_thread.start()
        
        # 無音検出タイマー開始
        if self.silence_detection_checkbox.isChecked():
            self.silence_timer.start(1000)  # 1秒ごとにチェック
        
        # UI更新
        self.recording_status_changed.emit(True)
    
    def stop_recording(self):
        """録音停止処理"""
        if not self.is_recording:
            return
        
        # 無音検出タイマー停止
        self.silence_timer.stop()
        
        # 録音停止
        audio_file = self.recorder.stop_recording()
        if not audio_file:
            QMessageBox.warning(self, "エラー", "録音を停止できませんでした")
            return
        
        # プログレスバーを表示
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        
        # 文字起こし処理をスレッドで実行
        self.transcription_thread = threading.Thread(
            target=self.transcription_worker, 
            args=(audio_file,)
        )
        self.transcription_thread.daemon = True
        self.transcription_thread.start()
        
        # UI更新
        self.recording_status_changed.emit(False)
    
    def recording_worker(self):
        """録音ワーカースレッド"""
        self.is_recording = True
        
        while self.is_recording:
            self.recorder.record_frame()
            time.sleep(0.01)  # スリープを入れて CPU 使用率を下げる
    
    def check_silence(self):
        """無音検出のチェック"""
        if self.is_recording and self.recorder.is_silence_detected():
            self.silence_detected.emit()
    
    @Slot()
    def handle_silence_detection(self):
        """無音検出時の処理"""
        if self.is_recording:
            self.stop_recording()
            QMessageBox.information(self, "無音検出", "一定時間の無音が検出されたため、録音を停止しました。")
    
    def start_transcription(self, audio_file):
        """文字起こしを開始する"""
        try:
            # プログレスバーを表示
            self.progress_bar.setValue(0)
            self.progress_bar.show()
            
            # 文字起こしスレッドを開始
            self.transcription_thread = threading.Thread(
                target=self.transcription_worker,
                args=(audio_file,)
            )
            self.transcription_thread.daemon = True
            self.transcription_thread.start()
            
        except Exception as e:
            self.progress_bar.hide()
            QMessageBox.warning(self, "エラー", f"文字起こしの開始に失敗しました: {str(e)}")
    
    def transcription_worker(self, audio_file):
        """文字起こしを実行するワーカースレッド"""
        try:
            # 文字起こしを実行
            text = self.transcription_service.transcribe_audio(audio_file)
            
            # メインスレッドでUIを更新
            self.transcription_complete.emit(text)
            
        except Exception as e:
            self.transcription_complete.emit(f"エラー: {str(e)}")
        finally:
            # プログレスバーを非表示
            self.progress_bar.hide()
    
    @Slot(str)
    def update_transcription(self, text):
        """文字起こし結果を表示する"""
        self.text_edit.setText(text)
        
        # クリップボードにコピー
        if not text.startswith("エラー:"):
            self.copy_to_clipboard()
    
    @Slot(bool)
    def update_recording_status(self, is_recording):
        """録音状態に基づいてUI更新
        
        Args:
            is_recording (bool): 録音中かどうか
        """
        self.is_recording = is_recording
        self.record_button.setEnabled(not is_recording)
        self.stop_button.setEnabled(is_recording)
        self.copy_button.setEnabled(False)
        
        if is_recording:
            self.text_edit.clear()
            self.progress_bar.setValue(0)
            self.progress_bar.show()
            self.recording_label.setText("録音中...")
            self.recording_label.setStyleSheet("""
                QLabel {
                    color: #f44336;
                    font-size: 14px;
                    font-weight: bold;
                    animation: blink 1s infinite;
                }
                @keyframes blink {
                    0% { opacity: 1; }
                    50% { opacity: 0.5; }
                    100% { opacity: 1; }
                }
            """)
        else:
            self.progress_bar.hide()
            self.recording_label.clear()
            self.recording_label.setStyleSheet("")
    
    def copy_to_clipboard(self):
        """テキストをクリップボードにコピー"""
        text = self.text_edit.toPlainText()
        if text:
            success = self.clipboard_module.copy_to_clipboard(text)
            if success:
                QApplication.beep()  # コピー通知音
    
    def closeEvent(self, event):
        """ウィンドウを閉じる際の処理"""
        # 録音中なら停止
        if self.is_recording:
            self.recorder.stop_recording()
            self.is_recording = False
        
        # 無音検出タイマーを停止
        self.silence_timer.stop()
        
        # ウィンドウの位置とサイズを保存
        if not self.isMaximized():
            self.settings.set_window_geometry(self.pos(), self.size())
        self.settings.set_window_state(self.isMaximized())
        
        # その他の設定を保存
        self.save_settings()
        
        # イベントを受け入れる
        event.accept()

    def clear_temp_files(self):
        """一時ファイルをクリアする"""
        try:
            deleted_count = self.recorder.clear_temp_files()
            if deleted_count > 0:
                QMessageBox.information(self, "一時ファイル削除", f"{deleted_count}個の一時ファイルを削除しました")
            else:
                QMessageBox.information(self, "一時ファイル削除", "削除する一時ファイルはありませんでした")
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"一時ファイルの削除に失敗しました: {str(e)}") 