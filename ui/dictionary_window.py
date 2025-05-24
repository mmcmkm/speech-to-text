import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QComboBox, QSpinBox, QTextEdit, QLabel,
    QGroupBox, QFileDialog, QMessageBox, QHeaderView, QCheckBox,
    QSplitter, QWidget, QFormLayout, QProgressBar, QApplication
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QIcon
from pathlib import Path
from typing import List, Optional
from services.dictionary import DictionaryService, DictionaryEntry, CategoryManager
from utils.logger import Logger

class DictionaryImportThread(QThread):
    """CSV インポート用のワーカースレッド"""
    progress = Signal(int, int)  # success_count, total_count
    finished = Signal(int, int, int)  # success_count, duplicate_count, error_count
    error = Signal(str)
    
    def __init__(self, dictionary_service: DictionaryService, csv_path: str):
        super().__init__()
        self.dictionary_service = dictionary_service
        self.csv_path = csv_path
    
    def run(self):
        try:
            success_count, duplicate_count, error_count = self.dictionary_service.import_from_csv(self.csv_path)
            self.finished.emit(success_count, duplicate_count, error_count)
        except Exception as e:
            self.error.emit(str(e))

class DictionaryEntryDialog(QDialog):
    """辞書エントリの追加・編集ダイアログ"""
    
    def __init__(self, parent=None, entry: Optional[DictionaryEntry] = None):
        super().__init__(parent)
        self.entry = entry
        self.is_edit_mode = entry is not None
        self.setup_ui()
        
        if self.is_edit_mode:
            self.load_entry_data()
    
    def setup_ui(self):
        """UIの設定"""
        self.setWindowTitle("辞書エントリの編集" if self.is_edit_mode else "辞書エントリの追加")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # フォーム部分
        form_layout = QFormLayout()
        
        # 読み
        self.reading_edit = QLineEdit()
        self.reading_edit.setPlaceholderText("ひらがなで入力してください")
        form_layout.addRow("読み:", self.reading_edit)
        
        # 表記
        self.display_edit = QLineEdit()
        self.display_edit.setPlaceholderText("表示したい文字で入力してください")
        form_layout.addRow("表記:", self.display_edit)
        
        # カテゴリ
        self.category_combo = QComboBox()
        self.category_combo.addItems(CategoryManager.get_available_categories())
        self.category_combo.setEditable(True)
        form_layout.addRow("カテゴリ:", self.category_combo)
        
        # 優先度
        priority_layout = QHBoxLayout()
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 100)
        self.priority_spin.setValue(50)
        priority_layout.addWidget(self.priority_spin)
        
        self.auto_priority_btn = QPushButton("自動設定")
        self.auto_priority_btn.clicked.connect(self.auto_set_priority)
        priority_layout.addWidget(self.auto_priority_btn)
        
        priority_widget = QWidget()
        priority_widget.setLayout(priority_layout)
        form_layout.addRow("優先度:", priority_widget)
        
        # 備考
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setPlaceholderText("備考やメモを入力してください")
        form_layout.addRow("備考:", self.notes_edit)
        
        layout.addLayout(form_layout)
        
        # ボタン部分
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("保存" if self.is_edit_mode else "追加")
        self.ok_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("キャンセル")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # 読みと表記の変更時にカテゴリと優先度を自動設定
        self.reading_edit.textChanged.connect(self.on_text_changed)
        self.display_edit.textChanged.connect(self.on_text_changed)
    
    def on_text_changed(self):
        """テキスト変更時の処理"""
        if not self.is_edit_mode:  # 新規追加時のみ自動設定
            reading = self.reading_edit.text().strip()
            display = self.display_edit.text().strip()
            
            if reading and display:
                # カテゴリの自動推定
                predicted_category = CategoryManager.predict_category(reading, display)
                index = self.category_combo.findText(predicted_category)
                if index >= 0:
                    self.category_combo.setCurrentIndex(index)
    
    def auto_set_priority(self):
        """優先度の自動設定"""
        from services.dictionary import PriorityManager
        
        reading = self.reading_edit.text().strip()
        display = self.display_edit.text().strip()
        
        if reading and display:
            usage_count = self.entry.usage_count if self.entry else 0
            priority = PriorityManager.calculate_auto_priority(reading, display, usage_count)
            self.priority_spin.setValue(priority)
    
    def load_entry_data(self):
        """エントリデータの読み込み"""
        if self.entry:
            self.reading_edit.setText(self.entry.reading)
            self.display_edit.setText(self.entry.display)
            
            # カテゴリの設定
            index = self.category_combo.findText(self.entry.category)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
            else:
                self.category_combo.setCurrentText(self.entry.category)
            
            self.priority_spin.setValue(self.entry.priority)
            self.notes_edit.setPlainText(self.entry.notes)
    
    def get_entry_data(self) -> Optional[DictionaryEntry]:
        """入力されたデータからエントリを作成"""
        reading = self.reading_edit.text().strip()
        display = self.display_edit.text().strip()
        
        if not reading or not display:
            QMessageBox.warning(self, "入力エラー", "読みと表記は必須です。")
            return None
        
        category = self.category_combo.currentText().strip()
        priority = self.priority_spin.value()
        notes = self.notes_edit.toPlainText().strip()
        
        if self.is_edit_mode and self.entry:
            # 既存エントリの更新
            self.entry.reading = reading
            self.entry.display = display
            self.entry.category = category
            self.entry.priority = priority
            self.entry.notes = notes
            return self.entry
        else:
            # 新規エントリの作成
            return DictionaryEntry(reading, display, category, priority, notes)

class DictionaryWindow(QDialog):
    """辞書管理ウィンドウ"""
    
    def __init__(self, dictionary_service: DictionaryService, parent=None):
        super().__init__(parent)
        self.dictionary_service = dictionary_service
        self.logger = Logger.get_logger(__name__)
        self.setup_ui()
        self.load_dictionary_data()
    
    def setup_ui(self):
        """UIの設定"""
        self.setWindowTitle("固有名詞辞書管理")
        self.setModal(True)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # ツールバー
        toolbar_layout = QHBoxLayout()
        
        # 検索
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("検索:"))
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("読み、表記、備考で検索...")
        self.search_edit.textChanged.connect(self.filter_entries)
        search_layout.addWidget(self.search_edit)
        
        self.category_filter = QComboBox()
        self.category_filter.addItem("全カテゴリ")
        self.category_filter.addItems(CategoryManager.get_available_categories())
        self.category_filter.currentTextChanged.connect(self.filter_entries)
        search_layout.addWidget(self.category_filter)
        
        toolbar_layout.addLayout(search_layout)
        toolbar_layout.addStretch()
        
        # 辞書機能の有効/無効
        self.enable_checkbox = QCheckBox("辞書機能を有効にする")
        self.enable_checkbox.setChecked(self.dictionary_service.is_enabled())
        self.enable_checkbox.toggled.connect(self.toggle_dictionary)
        toolbar_layout.addWidget(self.enable_checkbox)
        
        layout.addLayout(toolbar_layout)
        
        # メインエリア
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左側: エントリ一覧
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # エントリ操作ボタン
        entry_buttons_layout = QHBoxLayout()
        
        self.add_button = QPushButton("追加")
        self.add_button.clicked.connect(self.add_entry)
        entry_buttons_layout.addWidget(self.add_button)
        
        self.edit_button = QPushButton("編集")
        self.edit_button.clicked.connect(self.edit_entry)
        entry_buttons_layout.addWidget(self.edit_button)
        
        self.delete_button = QPushButton("削除")
        self.delete_button.clicked.connect(self.delete_entry)
        entry_buttons_layout.addWidget(self.delete_button)
        
        entry_buttons_layout.addStretch()
        left_layout.addLayout(entry_buttons_layout)
        
        # エントリテーブル
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["読み", "表記", "カテゴリ", "優先度", "使用回数", "備考"])
        
        # テーブルの設定
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # 読み
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # 表記
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # カテゴリ
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # 優先度
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # 使用回数
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # 備考
        
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.itemDoubleClicked.connect(self.edit_entry)
        
        left_layout.addWidget(self.table)
        
        # 右側: ファイル操作
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 統計情報
        stats_group = QGroupBox("統計情報")
        stats_layout = QFormLayout(stats_group)
        
        self.total_entries_label = QLabel("0")
        stats_layout.addRow("総エントリ数:", self.total_entries_label)
        
        self.total_readings_label = QLabel("0")
        stats_layout.addRow("読み数:", self.total_readings_label)
        
        self.total_usage_label = QLabel("0")
        stats_layout.addRow("総使用回数:", self.total_usage_label)
        
        self.used_entries_label = QLabel("0")
        stats_layout.addRow("使用済みエントリ:", self.used_entries_label)
        
        self.current_file_label = QLabel("なし")
        stats_layout.addRow("現在のファイル:", self.current_file_label)
        
        # 詳細統計ボタン
        self.detailed_stats_button = QPushButton("詳細統計を表示")
        self.detailed_stats_button.clicked.connect(self.show_detailed_statistics)
        stats_layout.addRow("", self.detailed_stats_button)
        
        right_layout.addWidget(stats_group)
        
        # ファイル操作
        file_group = QGroupBox("ファイル操作")
        file_layout = QVBoxLayout(file_group)
        
        self.load_button = QPushButton("辞書を読み込み")
        self.load_button.clicked.connect(self.load_dictionary)
        file_layout.addWidget(self.load_button)
        
        self.save_button = QPushButton("辞書を保存")
        self.save_button.clicked.connect(self.save_dictionary)
        file_layout.addWidget(self.save_button)
        
        self.save_as_button = QPushButton("名前を付けて保存")
        self.save_as_button.clicked.connect(self.save_dictionary_as)
        file_layout.addWidget(self.save_as_button)
        
        file_layout.addWidget(QLabel(""))  # スペーサー
        
        self.import_csv_button = QPushButton("CSVをインポート")
        self.import_csv_button.clicked.connect(self.import_csv)
        file_layout.addWidget(self.import_csv_button)
        
        self.export_csv_button = QPushButton("CSVにエクスポート")
        self.export_csv_button.clicked.connect(self.export_csv)
        file_layout.addWidget(self.export_csv_button)
        
        right_layout.addWidget(file_group)
        right_layout.addStretch()
        
        # スプリッターに追加
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 200])
        
        layout.addWidget(splitter)
        
        # 閉じるボタン
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        
        self.close_button = QPushButton("閉じる")
        self.close_button.clicked.connect(self.accept)
        close_layout.addWidget(self.close_button)
        
        layout.addLayout(close_layout)
    
    def load_dictionary_data(self):
        """辞書データの読み込み"""
        self.table.setRowCount(0)
        entries = self.dictionary_service.get_all_entries()
        
        # エントリを優先度順にソート
        entries.sort(key=lambda x: (x.category, -x.priority, x.reading))
        
        self.table.setRowCount(len(entries))
        
        for row, entry in enumerate(entries):
            self.table.setItem(row, 0, QTableWidgetItem(entry.reading))
            self.table.setItem(row, 1, QTableWidgetItem(entry.display))
            self.table.setItem(row, 2, QTableWidgetItem(entry.category))
            self.table.setItem(row, 3, QTableWidgetItem(str(entry.priority)))
            self.table.setItem(row, 4, QTableWidgetItem(str(entry.usage_count)))
            self.table.setItem(row, 5, QTableWidgetItem(entry.notes))
            
            # エントリオブジェクトを行に関連付け
            item = self.table.item(row, 0)
            if item:
                item.setData(Qt.ItemDataRole.UserRole, entry)
        
        self.update_statistics()
    
    def update_statistics(self):
        """統計情報の更新"""
        stats = self.dictionary_service.get_statistics()
        
        self.total_entries_label.setText(str(stats["total_entries"]))
        self.total_readings_label.setText(str(stats["total_readings"]))
        self.total_usage_label.setText(str(stats.get("total_usage", 0)))
        self.used_entries_label.setText(f"{stats.get('used_entries', 0)} / {stats['total_entries']}")
        
        current_file = stats.get("current_file", "なし")
        if current_file and current_file != "なし":
            file_name = Path(current_file).name
            self.current_file_label.setText(file_name)
        else:
            self.current_file_label.setText("なし")
    
    def filter_entries(self):
        """エントリのフィルタリング"""
        search_text = self.search_edit.text().lower()
        category_filter = self.category_filter.currentText()
        
        for row in range(self.table.rowCount()):
            show_row = True
            
            # テキスト検索
            if search_text:
                reading_item = self.table.item(row, 0)
                display_item = self.table.item(row, 1)
                notes_item = self.table.item(row, 5)
                
                if reading_item and display_item and notes_item:
                    reading = reading_item.text().lower()
                    display = display_item.text().lower()
                    notes = notes_item.text().lower()
                    
                    if not (search_text in reading or search_text in display or search_text in notes):
                        show_row = False
            
            # カテゴリフィルタ
            if category_filter != "全カテゴリ":
                category_item = self.table.item(row, 2)
                if category_item:
                    category = category_item.text()
                    if category != category_filter:
                        show_row = False
            
            self.table.setRowHidden(row, not show_row)
    
    def toggle_dictionary(self, enabled: bool):
        """辞書機能の有効/無効切り替え"""
        self.dictionary_service.set_enabled(enabled)
        self.logger.info(f"辞書機能を{'有効' if enabled else '無効'}にしました")
    
    def add_entry(self):
        """エントリの追加"""
        dialog = DictionaryEntryDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            entry = dialog.get_entry_data()
            if entry and self.dictionary_service.add_entry(entry):
                # 辞書を保存
                self.dictionary_service.save_dictionary()
                self.load_dictionary_data()
                QMessageBox.information(self, "成功", "エントリを追加しました。")
            else:
                QMessageBox.warning(self, "エラー", "エントリの追加に失敗しました。")
    
    def edit_entry(self):
        """エントリの編集"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "選択エラー", "編集するエントリを選択してください。")
            return
        
        item = self.table.item(current_row, 0)
        if not item:
            return
            
        entry = item.data(Qt.ItemDataRole.UserRole)
        if not entry:
            return
        
        # 元の読みと表記を保存
        old_reading = entry.reading
        old_display = entry.display
        
        dialog = DictionaryEntryDialog(self, entry)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_entry = dialog.get_entry_data()
            if updated_entry:
                # エントリを更新
                if self.dictionary_service.update_entry(old_reading, old_display, updated_entry):
                    # エントリが実際に使用されたとして使用回数を更新
                    self.dictionary_service.update_entry_usage(updated_entry.reading, updated_entry.display)
                    # 辞書を保存
                    self.dictionary_service.save_dictionary()
                    self.load_dictionary_data()
                    QMessageBox.information(self, "成功", "エントリを更新しました。")
                else:
                    QMessageBox.warning(self, "エラー", "エントリの更新に失敗しました。")
            else:
                QMessageBox.warning(self, "エラー", "エントリデータの取得に失敗しました。")
    
    def delete_entry(self):
        """エントリの削除"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "選択エラー", "削除するエントリを選択してください。")
            return
        
        item = self.table.item(current_row, 0)
        if not item:
            return
            
        entry = item.data(Qt.ItemDataRole.UserRole)
        if not entry:
            return
        
        reply = QMessageBox.question(
            self, "削除確認", 
            f"エントリ「{entry.reading} → {entry.display}」を削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.dictionary_service.remove_entry(entry.reading, entry.display):
                # 辞書を保存
                self.dictionary_service.save_dictionary()
                self.load_dictionary_data()
                QMessageBox.information(self, "成功", "エントリを削除しました。")
            else:
                QMessageBox.warning(self, "エラー", "エントリの削除に失敗しました。")
    
    def load_dictionary(self):
        """辞書の読み込み"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "辞書ファイルを選択", "", "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            if self.dictionary_service.load_dictionary(file_path):
                self.load_dictionary_data()
                QMessageBox.information(self, "成功", "辞書を読み込みました。")
            else:
                QMessageBox.warning(self, "エラー", "辞書の読み込みに失敗しました。")
    
    def save_dictionary(self):
        """辞書の保存"""
        if self.dictionary_service.save_dictionary():
            self.update_statistics()
            QMessageBox.information(self, "成功", "辞書を保存しました。")
        else:
            QMessageBox.warning(self, "エラー", "辞書の保存に失敗しました。")
    
    def save_dictionary_as(self):
        """名前を付けて辞書を保存"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "辞書ファイルを保存", "", "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            if self.dictionary_service.save_dictionary(file_path):
                self.update_statistics()
                QMessageBox.information(self, "成功", "辞書を保存しました。")
            else:
                QMessageBox.warning(self, "エラー", "辞書の保存に失敗しました。")
    
    def import_csv(self):
        """CSVのインポート"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "CSVファイルを選択", "", "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            progress_dialog = None
            try:
                # プログレスダイアログの表示
                progress_dialog = QMessageBox(self)
                progress_dialog.setWindowTitle("インポート中")
                progress_dialog.setText("CSVファイルをインポートしています...")
                progress_dialog.setStandardButtons(QMessageBox.StandardButton.NoButton)
                progress_dialog.show()
                
                # アプリケーションのイベント処理を実行
                QApplication.processEvents()
                
                # インポート実行
                success_count, duplicate_count, error_count = self.dictionary_service.import_from_csv(file_path)
                
                # 結果表示
                if success_count > 0 or duplicate_count > 0:
                    # 辞書を保存（成功した項目がある場合）
                    if success_count > 0:
                        self.dictionary_service.save_dictionary()
                        self.load_dictionary_data()
                    
                    # 結果メッセージの作成
                    message_parts = []
                    if success_count > 0:
                        message_parts.append(f"追加: {success_count}件")
                    if duplicate_count > 0:
                        message_parts.append(f"重複スキップ: {duplicate_count}件")
                    if error_count > 0:
                        message_parts.append(f"エラー: {error_count}件")
                    
                    message = "\n".join(message_parts)
                    
                    if error_count > 0:
                        QMessageBox.warning(self, "インポート完了（一部エラー）", message)
                    else:
                        QMessageBox.information(self, "インポート完了", message)
                else:
                    QMessageBox.warning(self, "エラー", f"CSVのインポートに失敗しました。\nエラー: {error_count}件")
                    
            except Exception as e:
                self.logger.error(f"CSVインポート中にエラーが発生しました: {str(e)}")
                QMessageBox.critical(self, "エラー", f"CSVインポート中にエラーが発生しました:\n{str(e)}")
            finally:
                # プログレスダイアログを確実に閉じる
                if progress_dialog:
                    progress_dialog.close()
                    progress_dialog.deleteLater()
                    QApplication.processEvents()
    
    def export_csv(self):
        """CSVのエクスポート"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "CSVファイルを保存", "", "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            if self.dictionary_service.export_to_csv(file_path):
                QMessageBox.information(self, "成功", "CSVファイルにエクスポートしました。")
            else:
                QMessageBox.warning(self, "エラー", "CSVのエクスポートに失敗しました。")
    
    def show_detailed_statistics(self):
        """詳細統計を表示"""
        try:
            from ui.dictionary_window_enhanced import DictionaryWindowEnhanced
            DictionaryWindowEnhanced.show_detailed_statistics(self)
        except Exception as e:
            self.logger.error(f"詳細統計の表示中にエラーが発生しました: {str(e)}")
            QMessageBox.warning(self, "エラー", f"詳細統計の表示中にエラーが発生しました:\n{str(e)}") 