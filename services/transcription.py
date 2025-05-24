import os
import google.genai as genai
from google.genai import types
import base64
import logging
from utils.logger import Logger
from services.dictionary import DictionaryService

class TranscriptionService:
    # 利用可能なモデルのリスト（無料枠対応）
    AVAILABLE_MODELS = {
        'gemini-2.5-pro-exp-03-25': '高精度な文字起こしに適した最新モデル（無料枠対応）',
        'gemini-2.5-flash-preview-04-17': '高速な文字起こしに適した最新モデル',
        'gemini-2.0-flash': '高速な文字起こしに適した安定版モデル',
        'gemini-1.5-pro': '高精度な文字起こしに適した従来モデル',
        'gemini-1.5-flash': '高速な文字起こしに適した従来モデル',
        'gemini-1.5-flash-8b': '軽量で高速な文字起こしに適した従来モデル'
    }

    # 文字起こしモードの定義
    TRANSCRIPTION_MODES = {
        'clean': {
            'name': 'クリーンモード',
            'description': 'ためらいやフィラーワードを削除し、自然な文章に整形します',
            'prompt': """
            This is an audio recording in Japanese. Please transcribe it accurately. 
            After transcription, please remove filler words and hesitations like 'えーと', 'あー', 'んー', etc. 
            Make the final text natural and clean while preserving all the meaningful content.
            Only return the cleaned transcription, nothing else.
            """
        },
        'detailed': {
            'name': '詳細モード',
            'description': 'ためらいやフィラーワードを含め、忠実に文字起こしします',
            'prompt': """
            This is an audio recording in Japanese. Please transcribe it exactly as spoken, 
            including all filler words, hesitations, and corrections. 
            Preserve the natural flow of speech and all verbal expressions.
            Only return the exact transcription, nothing else.
            """
        },
        'smart': {
            'name': 'スマートモード',
            'description': '訂正や言い直しを自動的に反映し、意図を理解した文章に整形します',
            'prompt': """
            This is an audio recording in Japanese. Please transcribe it intelligently.
            When the speaker corrects themselves (e.g., "10時に出かけます、いや間違った、いややっぱり11時です"), 
            use the final corrected version (e.g., "11時に出かけます").
            Remove all filler words and hesitations like 'えっと', 'えー', 'あのー', 'うーん', 'んー', 'あー', etc.
            Remove any unnecessary pauses or verbal tics that don't contribute to the meaning.
            Make the text natural and coherent while preserving the speaker's intended message.
            Only return the processed transcription, nothing else.
            """
        },
        'casual': {
            'name': '日常会話モード',
            'description': 'ためらいやフィラーワードを削除しつつ、口語表現を許容します',
            'prompt': """
            This is an audio recording in Japanese. Please transcribe it in a casual conversational style.
            Remove filler words and hesitations like 'えーと', 'あー', 'えっと', etc., but preserve colloquial expressions, slang, and informal wording typical in daily conversation.
            Do not include any punctuation marks such as commas (、) or periods (。).
            Only return the cleaned transcription in Japanese, nothing else.
            """
        }
    }

    def __init__(self, model_name='gemini-2.5-pro-exp-03-25', mode='clean'):
        """文字起こしサービスの初期化

        Args:
            model_name (str): 使用するモデルの名前
            mode (str): 文字起こしモード（'clean', 'detailed', 'smart', 'casual'）
        """
        self.logger = Logger.get_logger(__name__)
        
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            error_msg = "GEMINI_API_KEY環境変数が設定されていません"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Gemini APIの設定
        self.logger.info("Gemini APIの初期化を開始します")
        self.client = genai.Client(api_key=api_key)  # クライアントの初期化
        self.set_model(model_name)
        self.set_mode(mode)
        
        # 辞書サービスの初期化
        self.dictionary_service = DictionaryService()
        
        self.logger.info("Gemini APIの初期化が完了しました")
    
    def set_model(self, model_name):
        """使用するモデルを設定する

        Args:
            model_name (str): 使用するモデルの名前

        Raises:
            ValueError: 指定されたモデルが利用可能なモデルリストに存在しない場合
        """
        if model_name not in self.AVAILABLE_MODELS:
            error_msg = f"指定されたモデル '{model_name}' は利用できません。利用可能なモデル: {list(self.AVAILABLE_MODELS.keys())}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.model_name = model_name
        self.logger.info(f"モデルを '{model_name}' に設定しました")
    
    def set_mode(self, mode):
        """文字起こしモードを設定する

        Args:
            mode (str): 文字起こしモード（'clean', 'detailed', 'smart', 'casual'）

        Raises:
            ValueError: 指定されたモードが利用可能なモードリストに存在しない場合
        """
        if mode not in self.TRANSCRIPTION_MODES:
            error_msg = f"指定されたモード '{mode}' は利用できません。利用可能なモード: {list(self.TRANSCRIPTION_MODES.keys())}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.mode = mode
        self.logger.info(f"文字起こしモードを '{mode}' に設定しました")
    
    def get_available_models(self):
        """利用可能なモデルのリストを取得する

        Returns:
            dict: モデル名とその説明の辞書
        """
        return self.AVAILABLE_MODELS
    
    def get_available_modes(self):
        """利用可能な文字起こしモードのリストを取得する

        Returns:
            dict: モード名とその説明の辞書
        """
        return self.TRANSCRIPTION_MODES
    
    def get_current_model(self):
        """現在使用中のモデル名を取得する

        Returns:
            str: 現在使用中のモデル名
        """
        return self.model_name
    
    def get_current_mode(self):
        """現在使用中の文字起こしモードを取得する

        Returns:
            str: 現在使用中のモード名
        """
        return self.mode
    
    def transcribe_audio(self, audio_file_path):
        """音声ファイルから文字起こしを行う

        Args:
            audio_file_path (str): 音声ファイルのパス

        Returns:
            str: 文字起こしされたテキスト
        """
        self.logger.info(f"音声ファイルの処理を開始します: {audio_file_path}")
        
        if not os.path.exists(audio_file_path):
            error_msg = f"音声ファイルが見つかりません: {audio_file_path}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # 音声ファイルをbase64エンコードする
        self.logger.info("音声ファイルをbase64エンコードしています...")
        with open(audio_file_path, "rb") as audio_file:
            audio_data = audio_file.read()
            audio_base64 = base64.b64encode(audio_data).decode("utf-8")
            self.logger.debug(f"音声ファイルのサイズ: {len(audio_data)} bytes")
        
        # 音声データのMIMEタイプを設定
        mime_type = "audio/wav"
        
        # 現在のモードに対応するプロンプトを取得
        base_prompt = self.TRANSCRIPTION_MODES[self.mode]['prompt']
        
        # 辞書情報を含む拡張プロンプトを生成
        dictionary_prompt = self.dictionary_service.generate_prompt_dictionary()
        if dictionary_prompt:
            prompt = dictionary_prompt + "\n" + base_prompt
            self.logger.debug("辞書情報を含むプロンプトを使用します")
        else:
            prompt = base_prompt
            
        self.logger.debug(f"プロンプト: {prompt}")
        
        # 音声データとプロンプトを送信
        self.logger.info("Gemini APIにリクエストを送信しています...")
        try:
            model = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    prompt,
                    types.Part(
                        inline_data=types.Blob(
                            mime_type=mime_type,
                            data=audio_data
                        )
                    )
                ]
            )
            self.logger.debug(f"APIレスポンス: {model.text}")
        except Exception as e:
            error_msg = str(e)
            if "503" in error_msg and "overloaded" in error_msg:
                error_msg = "Gemini APIのサーバーが混雑しています。しばらく時間をおいて再度お試しください。"
            elif "429" in error_msg:
                error_msg = "APIの利用制限に達しました。しばらく時間をおいて再度お試しください。"
            elif "401" in error_msg:
                error_msg = "APIキーが無効です。APIキーの設定を確認してください。"
            else:
                error_msg = f"文字起こし中にエラーが発生しました: {str(e)}"
            
            self.logger.error(error_msg, exc_info=True)
            return error_msg
        
        # レスポンスからテキストを抽出
        if model.text:
            self.logger.info("文字起こしが正常に完了しました")
            # テキストのクリーンアップを実行
            cleaned_text = self.cleanup_text(model.text.strip())
            
            # 辞書エントリの使用回数を更新
            self._update_dictionary_usage(cleaned_text)
            
            return cleaned_text
        else:
            error_msg = "文字起こしに失敗しました。レスポンスが空です。"
            self.logger.error(error_msg)
            return error_msg
    
    def cleanup_text(self, text):
        """文字起こしテキストからフィラーワードを削除する
        
        Args:
            text (str): 文字起こしされたテキスト
            
        Returns:
            str: クリーンアップされたテキスト
        """
        self.logger.info("テキストのクリーンアップを開始します")
        self.logger.debug(f"クリーンアップ前のテキスト: {text}")
        
        # すでにGemini APIがクリーンアップしているが、念のため追加処理を実施
        fillers = ["えーと", "あー", "んー", "えっと", "まぁ", "あのー", "その", "なんか"]
        cleaned_text = text
        
        # フィラーワードの削除
        for filler in fillers:
            cleaned_text = cleaned_text.replace(filler + " ", "")
            cleaned_text = cleaned_text.replace(filler, "")
        
        # 半角スペースの削除
        cleaned_text = cleaned_text.replace(" ", "")
        
        self.logger.debug(f"クリーンアップ後のテキスト: {cleaned_text}")
        self.logger.info("テキストのクリーンアップが完了しました")
        
        return cleaned_text
    
    def get_dictionary_service(self) -> DictionaryService:
        """辞書サービスを取得する
        
        Returns:
            DictionaryService: 辞書サービスのインスタンス
        """
        return self.dictionary_service
    
    def set_dictionary_enabled(self, enabled: bool):
        """辞書機能の有効/無効を設定する
        
        Args:
            enabled (bool): 有効にする場合はTrue、無効にする場合はFalse
        """
        self.dictionary_service.set_enabled(enabled)
        self.logger.info(f"辞書機能を{'有効' if enabled else '無効'}にしました")
    
    def is_dictionary_enabled(self) -> bool:
        """辞書機能が有効かどうかを確認する
        
        Returns:
            bool: 有効な場合はTrue、無効な場合はFalse
        """
        return self.dictionary_service.is_enabled()
    
    def _update_dictionary_usage(self, transcribed_text: str):
        """文字起こし結果に基づいて辞書エントリの使用回数を更新する
        
        Args:
            transcribed_text (str): 文字起こしされたテキスト
        """
        if not self.dictionary_service.is_enabled():
            return
        
        try:
            # 全ての辞書エントリを取得
            all_entries = self.dictionary_service.get_all_entries()
            
            # 文字起こし結果に含まれる表記をチェック
            for entry in all_entries:
                if entry.display in transcribed_text:
                    # 使用回数を更新
                    self.dictionary_service.update_entry_usage(entry.reading, entry.display)
                    self.logger.debug(f"辞書エントリの使用回数を更新: {entry.reading} -> {entry.display}")
            
            # 使用実績が更新された場合は辞書を保存
            self.dictionary_service.save_dictionary()
            
        except Exception as e:
            self.logger.warning(f"辞書使用回数の更新中にエラーが発生しました: {str(e)}") 