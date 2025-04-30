import os
import google.genai as genai
from google.genai import types
import base64
import logging
from utils.logger import Logger

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
        }
    }

    def __init__(self, model_name='gemini-2.5-pro-exp-03-25', mode='clean'):
        """文字起こしサービスの初期化

        Args:
            model_name (str): 使用するモデルの名前
            mode (str): 文字起こしモード（'clean', 'detailed', 'smart'）
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
            mode (str): 文字起こしモード（'clean', 'detailed', 'smart'）

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
        prompt = self.TRANSCRIPTION_MODES[self.mode]['prompt']
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
                            data=audio_base64
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