import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QComboBox, QSpinBox, QTextEdit, QLabel,
    QGroupBox, QFileDialog, QMessageBox, QHeaderView, QCheckBox,
    QSplitter, QWidget, QFormLayout, QProgressBar, QApplication,
    QTabWidget, QTreeWidget, QTreeWidgetItem, QDateEdit, QSlider
)
from PySide6.QtCore import Qt, QThread, Signal, QDate
from PySide6.QtGui import QFont, QIcon
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
from services.dictionary import DictionaryService, DictionaryEntry, CategoryManager
from utils.logger import Logger

class DetailedStatisticsDialog(QDialog):
    """詳細統計表示ダイアログ"""
    
    def __init__(self, dictionary_service: DictionaryService, parent=None):
        super().__init__(parent)
        self.dictionary_service = dictionary_service
        self.setup_ui()
        self.load_statistics()
    
    def setup_ui(self):
        """UIの設定"""
        self.setWindowTitle("詳細統計情報")
        self.setModal(True)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # タブウィジェット
        tab_widget = QTabWidget()
        
        # 使用頻度ランキングタブ
        usage_tab = QWidget()
        usage_layout = QVBoxLayout(usage_tab)
        
        usage_layout.addWidget(QLabel("使用頻度ランキング（上位10件）"))
        self.usage_tree = QTreeWidget()
        self.usage_tree.setHeaderLabels(["順位", "読み", "表記", "カテゴリ", "使用回数"])
        usage_layout.addWidget(self.usage_tree)
        
        tab_widget.addTab(usage_tab, "使用頻度")
        
        # 最近のエントリタブ
        recent_tab = QWidget()
        recent_layout = QVBoxLayout(recent_tab)
        
        recent_layout.addWidget(QLabel("最近追加されたエントリ（上位10件）"))
        self.recent_tree = QTreeWidget()
        self.recent_tree.setHeaderLabels(["読み", "表記", "カテゴリ", "作成日時"])
        recent_layout.addWidget(self.recent_tree)
        
        tab_widget.addTab(recent_tab, "最近追加")
        
        # カテゴリ別統計タブ
        category_tab = QWidget()
        category_layout = QVBoxLayout(category_tab)
        
        category_layout.addWidget(QLabel("カテゴリ別統計"))
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderLabels(["カテゴリ", "エントリ数", "総使用回数", "平均優先度", "最多使用エントリ"])
        category_layout.addWidget(self.category_tree)
        
        tab_widget.addTab(category_tab, "カテゴリ別")
        
        layout.addWidget(tab_widget)
        
        # 閉じるボタン
        close_button = QPushButton("閉じる")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
    
    def load_statistics(self):
        """統計データの読み込み"""
        detailed_stats = self.dictionary_service.get_detailed_statistics()
        
        # 使用頻度ランキング
        self.usage_tree.clear()
        for i, entry in enumerate(detailed_stats["usage_ranking"], 1):
            item = QTreeWidgetItem([
                str(i),
                entry["reading"],
                entry["display"],
                entry["category"],
                str(entry["usage_count"])
            ])
            self.usage_tree.addTopLevelItem(item)
        
        # 最近追加されたエントリ
        self.recent_tree.clear()
        for entry in detailed_stats["recent_entries"]:
            # ISO形式の日時を読みやすい形式に変換
            try:
                created_dt = datetime.fromisoformat(entry["created_at"])
                created_str = created_dt.strftime("%Y-%m-%d %H:%M")
            except:
                created_str = entry["created_at"]
            
            item = QTreeWidgetItem([
                entry["reading"],
                entry["display"],
                entry["category"],
                created_str
            ])
            self.recent_tree.addTopLevelItem(item)
        
        # カテゴリ別統計
        self.category_tree.clear()
        for category, details in detailed_stats["category_details"].items():
            most_used = details["most_used"]
            most_used_str = f"{most_used['reading']} → {most_used['display']} ({most_used['usage_count']}回)" if most_used else "なし"
            
            item = QTreeWidgetItem([
                category,
                str(details["count"]),
                str(details["total_usage"]),
                f"{details['avg_priority']:.1f}",
                most_used_str
            ])
            self.category_tree.addTopLevelItem(item)

class AdvancedSearchDialog(QDialog):
    """高度な検索ダイアログ"""
    
    def __init__(self, dictionary_service: DictionaryService, parent=None):
        super().__init__(parent)
        self.dictionary_service = dictionary_service
        self.setup_ui()
    
    def setup_ui(self):
        """UIの設定"""
        self.setWindowTitle("高度な検索")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # 検索条件
        conditions_group = QGroupBox("検索条件")
        conditions_layout = QFormLayout(conditions_group)
        
        # テキスト検索
        self.query_edit = QLineEdit()
        self.query_edit.setPlaceholderText("読み、表記、備考で検索...")
        conditions_layout.addRow("検索テキスト:", self.query_edit)
        
        # カテゴリフィルタ
        self.category_combo = QComboBox()
        self.category_combo.addItem("全カテゴリ")
        self.category_combo.addItems(CategoryManager.get_available_categories())
        conditions_layout.addRow("カテゴリ:", self.category_combo)
        
        # 使用回数フィルタ
        usage_layout = QHBoxLayout()
        self.min_usage_spin = QSpinBox()
        self.min_usage_spin.setRange(0, 1000)
        usage_layout.addWidget(self.min_usage_spin)
        usage_layout.addWidget(QLabel("〜"))
        self.max_usage_spin = QSpinBox()
        self.max_usage_spin.setRange(0, 1000)
        self.max_usage_spin.setValue(1000)
        usage_layout.addWidget(self.max_usage_spin)
        usage_widget = QWidget()
        usage_widget.setLayout(usage_layout)
        conditions_layout.addRow("使用回数:", usage_widget)
        
        # 優先度フィルタ
        priority_layout = QHBoxLayout()
        self.min_priority_spin = QSpinBox()
        self.min_priority_spin.setRange(1, 100)
        self.min_priority_spin.setValue(1)
        priority_layout.addWidget(self.min_priority_spin)
        priority_layout.addWidget(QLabel("〜"))
        self.max_priority_spin = QSpinBox()
        self.max_priority_spin.setRange(1, 100)
        self.max_priority_spin.setValue(100)
        priority_layout.addWidget(self.max_priority_spin)
        priority_widget = QWidget()
        priority_widget.setLayout(priority_layout)
        conditions_layout.addRow("優先度:", priority_widget)
        
        # ソート設定
        sort_layout = QHBoxLayout()
        self.sort_by_combo = QComboBox()
        self.sort_by_combo.addItems(["優先度", "使用回数", "作成日時", "読み", "表記"])
        sort_layout.addWidget(self.sort_by_combo)
        
        self.sort_order_combo = QComboBox()
        self.sort_order_combo.addItems(["降順", "昇順"])
        sort_layout.addWidget(self.sort_order_combo)
        sort_widget = QWidget()
        sort_widget.setLayout(sort_layout)
        conditions_layout.addRow("ソート:", sort_widget)
        
        layout.addWidget(conditions_group)
        
        # ボタン
        button_layout = QHBoxLayout()
        
        self.search_button = QPushButton("検索")
        self.search_button.clicked.connect(self.accept)
        button_layout.addWidget(self.search_button)
        
        self.cancel_button = QPushButton("キャンセル")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def get_search_params(self):
        """検索パラメータを取得"""
        # ソート設定の変換
        sort_by_map = {
            "優先度": "priority",
            "使用回数": "usage_count", 
            "作成日時": "created_at",
            "読み": "reading",
            "表記": "display"
        }
        
        sort_order_map = {
            "降順": "desc",
            "昇順": "asc"
        }
        
        return {
            "query": self.query_edit.text().strip(),
            "category": self.category_combo.currentText() if self.category_combo.currentText() != "全カテゴリ" else None,
            "min_usage": self.min_usage_spin.value(),
            "max_usage": self.max_usage_spin.value() if self.max_usage_spin.value() < 1000 else None,
            "min_priority": self.min_priority_spin.value(),
            "max_priority": self.max_priority_spin.value(),
            "sort_by": sort_by_map[self.sort_by_combo.currentText()],
            "sort_order": sort_order_map[self.sort_order_combo.currentText()]
        }

# 既存のDictionaryWindowクラスに機能を追加するための拡張
class DictionaryWindowEnhanced:
    """辞書管理ウィンドウの拡張機能"""
    
    @staticmethod
    def add_enhanced_features(window):
        """既存のDictionaryWindowに拡張機能を追加"""
        # 高度な検索ボタンを追加
        advanced_search_button = QPushButton("高度な検索")
        advanced_search_button.clicked.connect(lambda: DictionaryWindowEnhanced.show_advanced_search(window))
        
        # ツールバーに追加（既存の検索エリアの後に）
        toolbar_layout = window.findChild(QHBoxLayout)
        if toolbar_layout:
            toolbar_layout.addWidget(advanced_search_button)
    
    @staticmethod
    def show_advanced_search(parent_window):
        """高度な検索ダイアログを表示"""
        dialog = AdvancedSearchDialog(parent_window.dictionary_service, parent_window)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_search_params()
            
            # 高度な検索を実行
            results = parent_window.dictionary_service.search_entries_advanced(**params)
            
            # 結果をテーブルに表示
            DictionaryWindowEnhanced.display_search_results(parent_window, results)
    
    @staticmethod
    def display_search_results(parent_window, results):
        """検索結果をテーブルに表示"""
        table = parent_window.table
        table.setRowCount(len(results))
        
        for row, entry in enumerate(results):
            table.setItem(row, 0, QTableWidgetItem(entry.reading))
            table.setItem(row, 1, QTableWidgetItem(entry.display))
            table.setItem(row, 2, QTableWidgetItem(entry.category))
            table.setItem(row, 3, QTableWidgetItem(str(entry.priority)))
            table.setItem(row, 4, QTableWidgetItem(str(entry.usage_count)))
            table.setItem(row, 5, QTableWidgetItem(entry.notes))
            
            # エントリオブジェクトを行に関連付け
            item = table.item(row, 0)
            if item:
                item.setData(Qt.ItemDataRole.UserRole, entry)
        
        # 検索結果の件数を表示
        QMessageBox.information(parent_window, "検索完了", f"検索結果: {len(results)}件のエントリが見つかりました。")
    
    @staticmethod
    def show_detailed_statistics(parent_window):
        """詳細統計ダイアログを表示"""
        dialog = DetailedStatisticsDialog(parent_window.dictionary_service, parent_window)
        dialog.exec() 