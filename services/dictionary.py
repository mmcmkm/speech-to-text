import json
import os
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from utils.logger import Logger

class DictionaryEntry:
    """辞書エントリを表すクラス"""
    
    def __init__(self, reading: str, display: str, category: str = "その他", 
                 priority: int = 50, notes: str = "", entry_id: Optional[str] = None):
        self.id = entry_id or self._generate_id()
        self.reading = reading.strip()
        self.display = display.strip()
        self.category = category
        self.priority = priority
        self.notes = notes
        self.usage_count = 0
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.last_used: Optional[str] = None
    
    def _generate_id(self) -> str:
        """一意のIDを生成"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "reading": self.reading,
            "display": self.display,
            "category": self.category,
            "priority": self.priority,
            "notes": self.notes,
            "usage_count": self.usage_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_used": self.last_used
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DictionaryEntry':
        """辞書形式から復元"""
        entry = cls(
            reading=data["reading"],
            display=data["display"],
            category=data.get("category", "その他"),
            priority=data.get("priority", 50),
            notes=data.get("notes", ""),
            entry_id=data.get("id")
        )
        entry.usage_count = data.get("usage_count", 0)
        entry.created_at = data.get("created_at", entry.created_at)
        entry.updated_at = data.get("updated_at", entry.updated_at)
        entry.last_used = data.get("last_used")
        return entry
    
    def update_usage(self):
        """使用実績を更新"""
        self.usage_count += 1
        self.last_used = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

class CategoryManager:
    """カテゴリ管理クラス"""
    
    # 自動カテゴリ推定のパターン
    AUTO_CATEGORY_PATTERNS = {
        "人名": {
            "suffixes": ["さん", "くん", "ちゃん", "先生", "部長", "課長", "社長", "専務", "常務", "取締役"],
            "patterns": ["田中", "佐藤", "山田", "高橋", "渡辺", "太郎", "花子", "一郎", "次郎"]
        },
        "会社名": {
            "suffixes": ["株式会社", "有限会社", "合同会社", "Corporation", "Inc", "Ltd", "Co"],
            "patterns": ["商事", "システム", "テクノロジー", "ソリューション", "サービス"]
        },
        "地名": {
            "suffixes": ["市", "区", "町", "村", "県", "都", "府", "駅", "空港", "港"],
            "patterns": ["東京", "大阪", "名古屋", "横浜", "神戸", "福岡", "札幌", "仙台"]
        },
        "専門用語": {
            "patterns": ["API", "システム", "データベース", "アルゴリズム", "フレームワーク", "ライブラリ"]
        }
    }
    
    @classmethod
    def predict_category(cls, reading: str, display: str) -> str:
        """読みと表記からカテゴリを推定"""
        for category, patterns in cls.AUTO_CATEGORY_PATTERNS.items():
            # サフィックスチェック
            if "suffixes" in patterns:
                for suffix in patterns["suffixes"]:
                    if display.endswith(suffix):
                        return category
            
            # パターンチェック
            if "patterns" in patterns:
                for pattern in patterns["patterns"]:
                    if pattern in display:
                        return category
        
        return "その他"
    
    @classmethod
    def get_available_categories(cls) -> List[str]:
        """利用可能なカテゴリ一覧を取得"""
        return list(cls.AUTO_CATEGORY_PATTERNS.keys()) + ["その他"]

class PriorityManager:
    """優先度管理クラス"""
    
    @classmethod
    def calculate_auto_priority(cls, reading: str, display: str, usage_count: int = 0) -> int:
        """自動優先度計算"""
        base_priority = 50  # 基本優先度
        
        # 使用頻度による調整（最大30ポイント）
        frequency_bonus = min(usage_count * 3, 30)
        
        # 一般的な名前かどうかの判定
        common_bonus = cls._get_common_name_bonus(display)
        
        # 文字数による調整（短い方が一般的）
        length_bonus = max(0, 5 - len(display))
        
        priority = base_priority + frequency_bonus + common_bonus + length_bonus
        return max(1, min(100, priority))  # 1-100の範囲に制限
    
    @classmethod
    def _get_common_name_bonus(cls, display: str) -> int:
        """一般的な名前のボーナス計算"""
        common_names = ["田中", "佐藤", "山田", "高橋", "渡辺", "東京", "大阪", "名古屋"]
        return 10 if any(name in display for name in common_names) else 0

class DictionaryService:
    """固有名詞辞書サービス"""
    
    def __init__(self, dictionary_dir: str = "data/dictionaries"):
        self.logger = Logger.get_logger(__name__)
        self.dictionary_dir = Path(dictionary_dir)
        self.dictionary_dir.mkdir(parents=True, exist_ok=True)
        
        self.entries: Dict[str, List[DictionaryEntry]] = {}  # reading -> [entries]
        self.enabled = True
        self.current_file: Optional[str] = None
        
        # デフォルト辞書の読み込み
        self.load_default_dictionary()
    
    def load_default_dictionary(self):
        """デフォルト辞書の読み込み"""
        default_file = self.dictionary_dir / "default.json"
        if default_file.exists():
            self.load_dictionary(str(default_file))
        else:
            self.logger.info("デフォルト辞書が見つかりません。新規作成します")
            self.create_default_dictionary()
    
    def create_default_dictionary(self):
        """デフォルト辞書の作成"""
        default_entries = [
            DictionaryEntry("やまだ", "山田", "人名", 60, "一般的な姓"),
            DictionaryEntry("たなか", "田中", "人名", 60, "一般的な姓"),
            DictionaryEntry("さとう", "佐藤", "人名", 60, "一般的な姓"),
            DictionaryEntry("とうきょう", "東京", "地名", 70, "首都"),
            DictionaryEntry("おおさか", "大阪", "地名", 65, "関西の主要都市"),
        ]
        
        for entry in default_entries:
            self.add_entry(entry)
        
        default_file = self.dictionary_dir / "default.json"
        self.save_dictionary(str(default_file))
        self.current_file = str(default_file)
        self.logger.info(f"デフォルト辞書を作成しました: {default_file}")
    
    def add_entry(self, entry: DictionaryEntry) -> bool:
        """エントリを追加"""
        try:
            if entry.reading not in self.entries:
                self.entries[entry.reading] = []
            
            # 同じ表記が既に存在するかチェック
            for existing in self.entries[entry.reading]:
                if existing.display == entry.display:
                    self.logger.warning(f"同じエントリが既に存在します: {entry.reading} -> {entry.display}")
                    return False
            
            self.entries[entry.reading].append(entry)
            
            # 優先度順にソート
            self.entries[entry.reading].sort(key=lambda x: x.priority, reverse=True)
            
            self.logger.info(f"エントリを追加しました: {entry.reading} -> {entry.display}")
            return True
            
        except Exception as e:
            self.logger.error(f"エントリ追加中にエラーが発生しました: {str(e)}")
            return False
    
    def update_entry(self, old_reading: str, old_display: str, updated_entry: DictionaryEntry) -> bool:
        """エントリを更新"""
        try:
            # 既存エントリを検索
            old_entry = None
            if old_reading in self.entries:
                for entry in self.entries[old_reading]:
                    if entry.display == old_display:
                        old_entry = entry
                        break
            
            if old_entry is None:
                self.logger.warning(f"更新対象のエントリが見つかりません: {old_reading} -> {old_display}")
                # 新規エントリとして追加
                return self.add_entry(updated_entry)
            
            # 使用実績を保持
            updated_entry.usage_count = old_entry.usage_count
            updated_entry.created_at = old_entry.created_at
            updated_entry.last_used = old_entry.last_used
            updated_entry.updated_at = datetime.now().isoformat()
            
            # 古いエントリを削除
            self.remove_entry(old_reading, old_display)
            
            # 新しいエントリを追加
            if self.add_entry(updated_entry):
                self.logger.info(f"エントリを更新しました: {old_reading} -> {old_display} から {updated_entry.reading} -> {updated_entry.display}")
                return True
            else:
                self.logger.error(f"エントリの更新に失敗しました: {updated_entry.reading} -> {updated_entry.display}")
                return False
                
        except Exception as e:
            self.logger.error(f"エントリ更新中にエラーが発生しました: {str(e)}")
            return False
    
    def remove_entry(self, reading: str, display: str) -> bool:
        """エントリを削除"""
        try:
            if reading not in self.entries:
                return False
            
            self.entries[reading] = [
                entry for entry in self.entries[reading] 
                if entry.display != display
            ]
            
            # 空になった場合は読みキーも削除
            if not self.entries[reading]:
                del self.entries[reading]
            
            self.logger.info(f"エントリを削除しました: {reading} -> {display}")
            return True
            
        except Exception as e:
            self.logger.error(f"エントリ削除中にエラーが発生しました: {str(e)}")
            return False
    
    def get_entries_for_reading(self, reading: str) -> List[DictionaryEntry]:
        """指定した読みのエントリ一覧を取得"""
        return self.entries.get(reading, [])
    
    def get_all_entries(self) -> List[DictionaryEntry]:
        """全エントリを取得"""
        all_entries = []
        for entries in self.entries.values():
            all_entries.extend(entries)
        return all_entries
    
    def search_entries(self, query: str, category: Optional[str] = None) -> List[DictionaryEntry]:
        """エントリを検索"""
        results = []
        for entries in self.entries.values():
            for entry in entries:
                # クエリマッチング
                if (query.lower() in entry.reading.lower() or 
                    query.lower() in entry.display.lower() or
                    query.lower() in entry.notes.lower()):
                    
                    # カテゴリフィルタ
                    if category is None or entry.category == category:
                        results.append(entry)
        
        return results
    
    def update_entry_usage(self, reading: str, display: str):
        """エントリの使用実績を更新"""
        if reading in self.entries:
            for entry in self.entries[reading]:
                if entry.display == display:
                    entry.update_usage()
                    # 使用実績に基づいて優先度を再計算
                    entry.priority = PriorityManager.calculate_auto_priority(
                        entry.reading, entry.display, entry.usage_count
                    )
                    break
            
            # 優先度順に再ソート
            self.entries[reading].sort(key=lambda x: x.priority, reverse=True)
    
    def load_dictionary(self, file_path: str) -> bool:
        """辞書ファイルを読み込み"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.entries.clear()
            
            for entry_data in data.get("dictionary_entries", []):
                entry = DictionaryEntry.from_dict(entry_data)
                if entry.reading not in self.entries:
                    self.entries[entry.reading] = []
                self.entries[entry.reading].append(entry)
            
            # 各読みのエントリを優先度順にソート
            for reading in self.entries:
                self.entries[reading].sort(key=lambda x: x.priority, reverse=True)
            
            self.current_file = file_path
            self.logger.info(f"辞書を読み込みました: {file_path} ({len(self.get_all_entries())}件)")
            return True
            
        except Exception as e:
            self.logger.error(f"辞書読み込み中にエラーが発生しました: {str(e)}")
            return False
    
    def save_dictionary(self, file_path: Optional[str] = None) -> bool:
        """辞書ファイルを保存"""
        try:
            if file_path is None:
                file_path = self.current_file
            
            if file_path is None:
                file_path = str(self.dictionary_dir / "custom.json")
            
            data = {
                "dictionary_entries": [entry.to_dict() for entry in self.get_all_entries()],
                "created_at": datetime.now().isoformat(),
                "version": "1.0"
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.current_file = file_path
            self.logger.info(f"辞書を保存しました: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"辞書保存中にエラーが発生しました: {str(e)}")
            return False
    
    def import_from_csv(self, csv_path: str) -> Tuple[int, int, int]:
        """CSVファイルから辞書をインポート
        
        Returns:
            Tuple[int, int, int]: (成功件数, 重複件数, エラー件数)
        """
        success_count = 0
        duplicate_count = 0
        error_count = 0
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row_num, row in enumerate(reader, start=2):  # ヘッダー行を考慮して2から開始
                    try:
                        # 行が空の場合はスキップ
                        if not row or all(not value for value in row.values()):
                            continue
                        
                        # 安全な文字列取得（Noneチェック）
                        reading_raw = row.get('読み')
                        display_raw = row.get('表記')
                        category_raw = row.get('カテゴリ')
                        notes_raw = row.get('備考')
                        
                        # None チェックと文字列変換
                        reading = str(reading_raw).strip() if reading_raw is not None else ''
                        display = str(display_raw).strip() if display_raw is not None else ''
                        category = str(category_raw).strip() if category_raw is not None else ''
                        notes = str(notes_raw).strip() if notes_raw is not None else ''
                        
                        # 必須フィールドのチェック
                        if not reading or not display or reading == 'None' or display == 'None':
                            self.logger.warning(f"行{row_num}: 読みまたは表記が空です (読み: '{reading}', 表記: '{display}')")
                            error_count += 1
                            continue
                        
                        # 優先度の処理（数値変換エラーを防ぐ）
                        priority_raw = row.get('優先度')
                        try:
                            if priority_raw is not None and str(priority_raw).strip():
                                priority = int(float(str(priority_raw).strip()))
                            else:
                                priority = 50
                        except (ValueError, TypeError):
                            priority = 50
                        
                        # 使用回数の処理（CSVエクスポート時に追加されるフィールド）
                        usage_count_raw = row.get('使用回数')
                        try:
                            if usage_count_raw is not None and str(usage_count_raw).strip():
                                usage_count = int(float(str(usage_count_raw).strip()))
                            else:
                                usage_count = 0
                        except (ValueError, TypeError):
                            usage_count = 0
                        
                        # カテゴリが空の場合は自動推定
                        if not category or category == 'None':
                            category = CategoryManager.predict_category(reading, display)
                        
                        # 重複チェック
                        is_duplicate = False
                        if reading in self.entries:
                            for existing in self.entries[reading]:
                                if existing.display == display:
                                    self.logger.info(f"行{row_num}: 重複エントリをスキップしました: {reading} -> {display}")
                                    duplicate_count += 1
                                    is_duplicate = True
                                    break
                        
                        if is_duplicate:
                            continue
                        
                        # エントリを作成して追加
                        entry = DictionaryEntry(reading, display, category, priority, notes)
                        entry.usage_count = usage_count  # 使用回数を設定
                        
                        # 重複チェックを回避して直接追加
                        if reading not in self.entries:
                            self.entries[reading] = []
                        
                        self.entries[reading].append(entry)
                        # 優先度順にソート
                        self.entries[reading].sort(key=lambda x: x.priority, reverse=True)
                        
                        self.logger.info(f"行{row_num}: エントリを追加しました: {reading} -> {display}")
                        success_count += 1
                            
                    except Exception as e:
                        self.logger.warning(f"行{row_num}: CSV行の処理中にエラー: {str(e)} (行データ: {row})")
                        error_count += 1
            
            self.logger.info(f"CSV インポート完了: 成功 {success_count}件, 重複 {duplicate_count}件, エラー {error_count}件")
            return success_count, duplicate_count, error_count
            
        except Exception as e:
            self.logger.error(f"CSV インポート中にエラーが発生しました: {str(e)}")
            return 0, 0, 1
    
    def export_to_csv(self, csv_path: str) -> bool:
        """辞書をCSVファイルにエクスポート"""
        try:
            with open(csv_path, 'w', encoding='utf-8', newline='') as f:
                fieldnames = ['読み', '表記', 'カテゴリ', '優先度', '備考', '使用回数']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                writer.writeheader()
                
                for entry in self.get_all_entries():
                    writer.writerow({
                        '読み': entry.reading,
                        '表記': entry.display,
                        'カテゴリ': entry.category,
                        '優先度': entry.priority,
                        '備考': entry.notes,
                        '使用回数': entry.usage_count
                    })
            
            self.logger.info(f"CSV エクスポート完了: {csv_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"CSV エクスポート中にエラーが発生しました: {str(e)}")
            return False
    
    def generate_prompt_dictionary(self, max_entries: int = 100) -> str:
        """Gemini API用の辞書プロンプトを生成"""
        if not self.enabled or not self.entries:
            return ""
        
        prompt_text = "以下の固有名詞辞書を参考にして、正確な表記で文字起こしを行ってください：\n\n"
        
        # カテゴリ別に整理
        categories = {}
        all_entries = self.get_all_entries()
        
        # 優先度と使用頻度でソート
        all_entries.sort(key=lambda x: (x.priority, x.usage_count), reverse=True)
        
        # 最大エントリ数に制限
        limited_entries = all_entries[:max_entries]
        
        for entry in limited_entries:
            if entry.category not in categories:
                categories[entry.category] = []
            categories[entry.category].append(entry)
        
        # カテゴリ別に辞書情報を追加
        for category, entries in categories.items():
            prompt_text += f"【{category}】\n"
            for entry in entries:
                prompt_text += f"- {entry.reading} → {entry.display}"
                if entry.notes:
                    prompt_text += f" ({entry.notes})"
                prompt_text += "\n"
            prompt_text += "\n"
        
        return prompt_text
    
    def set_enabled(self, enabled: bool):
        """辞書機能の有効/無効を設定"""
        self.enabled = enabled
        self.logger.info(f"辞書機能を{'有効' if enabled else '無効'}にしました")
    
    def is_enabled(self) -> bool:
        """辞書機能が有効かどうかを確認"""
        return self.enabled
    
    def get_statistics(self) -> Dict:
        """辞書の統計情報を取得"""
        all_entries = self.get_all_entries()
        categories = {}
        total_usage = 0
        used_entries = 0
        
        for entry in all_entries:
            if entry.category not in categories:
                categories[entry.category] = {"count": 0, "usage": 0}
            categories[entry.category]["count"] += 1
            categories[entry.category]["usage"] += entry.usage_count
            
            total_usage += entry.usage_count
            if entry.usage_count > 0:
                used_entries += 1
        
        return {
            "total_entries": len(all_entries),
            "total_readings": len(self.entries),
            "total_usage": total_usage,
            "used_entries": used_entries,
            "unused_entries": len(all_entries) - used_entries,
            "categories": categories,
            "enabled": self.enabled,
            "current_file": self.current_file
        }
    
    def get_detailed_statistics(self) -> Dict:
        """詳細な統計情報を取得"""
        all_entries = self.get_all_entries()
        
        # 使用頻度ランキング（上位10件）
        usage_ranking = sorted(all_entries, key=lambda x: x.usage_count, reverse=True)[:10]
        
        # 最近追加されたエントリ（上位10件）
        recent_entries = sorted(all_entries, key=lambda x: x.created_at, reverse=True)[:10]
        
        # 最近使用されたエントリ（上位10件）
        recently_used = [e for e in all_entries if e.last_used]
        recently_used = sorted(recently_used, key=lambda x: x.last_used or "", reverse=True)[:10]
        
        # カテゴリ別詳細統計
        category_details = {}
        for entry in all_entries:
            if entry.category not in category_details:
                category_details[entry.category] = {
                    "count": 0,
                    "total_usage": 0,
                    "avg_priority": 0,
                    "most_used": None,
                    "entries": []
                }
            
            cat_detail = category_details[entry.category]
            cat_detail["count"] += 1
            cat_detail["total_usage"] += entry.usage_count
            cat_detail["entries"].append(entry)
            
            # 最も使用されているエントリを更新
            if cat_detail["most_used"] is None or entry.usage_count > cat_detail["most_used"].usage_count:
                cat_detail["most_used"] = entry
        
        # 平均優先度を計算とmost_usedの辞書化
        for category, details in category_details.items():
            if details["count"] > 0:
                details["avg_priority"] = sum(e.priority for e in details["entries"]) / details["count"]
            
            # most_usedを辞書形式に変換
            if details["most_used"]:
                most_used_entry = details["most_used"]
                details["most_used"] = {
                    "reading": most_used_entry.reading,
                    "display": most_used_entry.display,
                    "usage_count": most_used_entry.usage_count
                }
            
            del details["entries"]  # メモリ節約のため削除
        
        return {
            "usage_ranking": [{"reading": e.reading, "display": e.display, "usage_count": e.usage_count, "category": e.category} for e in usage_ranking],
            "recent_entries": [{"reading": e.reading, "display": e.display, "created_at": e.created_at, "category": e.category} for e in recent_entries],
            "recently_used": [{"reading": e.reading, "display": e.display, "last_used": e.last_used, "usage_count": e.usage_count} for e in recently_used],
            "category_details": category_details
        }
    
    def search_entries_advanced(self, query: str = "", category: Optional[str] = None, 
                               min_usage: int = 0, max_usage: Optional[int] = None,
                               min_priority: int = 1, max_priority: int = 100,
                               date_from: Optional[str] = None, date_to: Optional[str] = None,
                               sort_by: str = "priority", sort_order: str = "desc") -> List[DictionaryEntry]:
        """高度な検索機能
        
        Args:
            query: 検索クエリ（読み、表記、備考で検索）
            category: カテゴリフィルタ
            min_usage: 最小使用回数
            max_usage: 最大使用回数
            min_priority: 最小優先度
            max_priority: 最大優先度
            date_from: 作成日時の開始日（ISO形式）
            date_to: 作成日時の終了日（ISO形式）
            sort_by: ソート基準（priority, usage_count, created_at, reading, display）
            sort_order: ソート順（asc, desc）
        
        Returns:
            List[DictionaryEntry]: 検索結果
        """
        results = []
        
        for entries in self.entries.values():
            for entry in entries:
                # テキスト検索
                if query:
                    query_lower = query.lower()
                    if not (query_lower in entry.reading.lower() or 
                           query_lower in entry.display.lower() or
                           query_lower in entry.notes.lower()):
                        continue
                
                # カテゴリフィルタ
                if category and entry.category != category:
                    continue
                
                # 使用回数フィルタ
                if entry.usage_count < min_usage:
                    continue
                if max_usage is not None and entry.usage_count > max_usage:
                    continue
                
                # 優先度フィルタ
                if entry.priority < min_priority or entry.priority > max_priority:
                    continue
                
                # 日付フィルタ
                if date_from and entry.created_at < date_from:
                    continue
                if date_to and entry.created_at > date_to:
                    continue
                
                results.append(entry)
        
        # ソート
        reverse = sort_order == "desc"
        if sort_by == "priority":
            results.sort(key=lambda x: x.priority, reverse=reverse)
        elif sort_by == "usage_count":
            results.sort(key=lambda x: x.usage_count, reverse=reverse)
        elif sort_by == "created_at":
            results.sort(key=lambda x: x.created_at, reverse=reverse)
        elif sort_by == "reading":
            results.sort(key=lambda x: x.reading, reverse=reverse)
        elif sort_by == "display":
            results.sort(key=lambda x: x.display, reverse=reverse)
        
        return results 