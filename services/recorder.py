import pyaudio
import wave
import numpy as np
import os
import tempfile
import time
import glob
from datetime import datetime, timedelta
import shutil

class AudioRecorder:
    def __init__(self, channels=1, rate=44100, chunk=1024, format_type=pyaudio.paInt16, 
                 silence_threshold=0.01, silence_duration=20):
        """音声録音クラスの初期化

        Args:
            channels (int): オーディオチャンネル数
            rate (int): サンプリングレート
            chunk (int): バッファサイズ
            format_type: PyAudioの形式定数
            silence_threshold (float): 無音と判定する閾値（0.0-1.0）
            silence_duration (int): 無音継続時間（秒）
        """
        self.channels = channels
        self.rate = rate
        self.chunk = chunk
        self.format = format_type
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.frames = []
        self.is_recording = False
        self.temp_file = None
        
        # 無音検出用の設定
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.last_sound_time = 0
        self.silence_detected = False
        
        # アプリケーション固有の一時ディレクトリの設定
        self.temp_dir = os.path.join(tempfile.gettempdir(), "speech_to_text_temp")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        
        # 古い一時ファイルのクリーンアップ
        self.cleanup_old_temp_files()
    
    def cleanup_old_temp_files(self):
        """古い一時ファイルを削除する"""
        try:
            # 24時間以上前の一時ファイルを削除
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            # 一時ディレクトリ内の.wavファイルを検索
            pattern = os.path.join(self.temp_dir, "speech_to_text_*.wav")
            
            for file_path in glob.glob(pattern):
                try:
                    # ファイルの最終更新時刻を取得
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    # 24時間以上前のファイルを削除
                    if file_time < cutoff_time:
                        os.remove(file_path)
                except Exception as e:
                    print(f"一時ファイルの削除に失敗しました: {file_path}, エラー: {str(e)}")
        except Exception as e:
            print(f"一時ファイルのクリーンアップに失敗しました: {str(e)}")
    
    def clear_temp_files(self):
        """すべての一時ファイルを手動で削除する"""
        try:
            # 一時ディレクトリ内の.wavファイルを検索
            pattern = os.path.join(self.temp_dir, "speech_to_text_*.wav")
            
            deleted_count = 0
            for file_path in glob.glob(pattern):
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"一時ファイルの削除に失敗しました: {file_path}, エラー: {str(e)}")
            
            return deleted_count
        except Exception as e:
            print(f"一時ファイルのクリーンアップに失敗しました: {str(e)}")
            return 0
    
    def start_recording(self):
        """録音を開始する"""
        if self.is_recording:
            return False
        
        # 前回の一時ファイルが残っている場合は削除
        if self.temp_file and os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
            except:
                pass
            self.temp_file = None
        
        self.frames = []
        self.stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        self.is_recording = True
        self.last_sound_time = time.time()
        self.silence_detected = False
        return True

    def stop_recording(self):
        """録音を停止し、一時ファイルに保存する"""
        if not self.is_recording:
            return None
        
        self.is_recording = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        # 前回の一時ファイルが残っている場合は削除
        if self.temp_file and os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
            except:
                pass
        
        # 一時ファイルの作成（タイムスタンプ付き）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.temp_file = os.path.join(self.temp_dir, f"speech_to_text_{timestamp}.wav")
        
        # WAVファイルに保存
        with wave.open(self.temp_file, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(self.frames))
        
        return self.temp_file
    
    def record_frame(self):
        """録音中のフレームを記録し、無音検出を行う"""
        if self.is_recording and self.stream:
            data = self.stream.read(self.chunk)
            self.frames.append(data)
            
            # 無音検出
            audio_data = np.frombuffer(data, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_data**2))
            normalized_rms = rms / 32768.0  # 16ビットオーディオの正規化
            
            if normalized_rms > self.silence_threshold:
                self.last_sound_time = time.time()
                self.silence_detected = False
            elif time.time() - self.last_sound_time > self.silence_duration:
                self.silence_detected = True
    
    def is_silence_detected(self):
        """無音が検出されたかどうかを返す"""
        return self.silence_detected
    
    def close(self):
        """リソースを解放する"""
        if self.stream:
            self.stream.close()
        self.audio.terminate()
        
        # 一時ファイルの削除
        if self.temp_file and os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
            except:
                pass
        
        # 古い一時ファイルのクリーンアップ
        self.cleanup_old_temp_files()
        
        # 一時ディレクトリが空の場合、ディレクトリも削除
        try:
            if os.path.exists(self.temp_dir) and not os.listdir(self.temp_dir):
                os.rmdir(self.temp_dir)
        except Exception as e:
            print(f"一時ディレクトリの削除に失敗しました: {str(e)}") 