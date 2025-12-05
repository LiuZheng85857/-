import sys
import time
import audioop
import pyaudio
import queue
import os
import tempfile
import wave
import numpy as np
import torch
import whisper  # 核心库
from googletrans import Translator
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QComboBox, QPushButton, 
                             QTextEdit, QProgressBar, QSplitter, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# ================= 配置参数 =================
# 麦克风采样配置
CHUNK = 1024 
FORMAT = pyaudio.paInt16 
CHANNELS = 1 
RATE = 16000  # Whisper 最佳采样率是 16000Hz
SILENCE_THRESHOLD = 500   
PAUSE_LIMIT = 1.0  # 停顿多久算一句 (Whisper 需要较完整的句子，建议设长一点)

# 模型选择: "tiny", "base", "small", "medium", "large"
# base: 速度快，准确率尚可 (推荐 CPU 使用)
# small: 准确率高，速度稍慢 (推荐 GPU 使用)
MODEL_SIZE = "base" 

# ================= 样式表 =================
STYLESHEET = """
QMainWindow { background-color: #f5f6fa; }
QLabel { font-family: "Microsoft YaHei"; font-size: 14px; color: #2f3640; }
QComboBox { padding: 8px; border: 1px solid #dcdde1; border-radius: 5px; background-color: white; }
QPushButton { padding: 10px 20px; border-radius: 6px; font-family: "Microsoft YaHei"; font-weight: bold; color: white; border: none; }
QPushButton#btnStart { background-color: #4cd137; }
QPushButton#btnStart:hover { background-color: #44bd32; }
QPushButton#btnStart:disabled { background-color: #b2bec3; }
QPushButton#btnStop { background-color: #e84118; }
QPushButton#btnStop:hover { background-color: #c23616; }
QPushButton#btnStop:disabled { background-color: #b2bec3; }
QTextEdit { border: 1px solid #dcdde1; border-radius: 6px; background-color: white; padding: 10px; font-size: 14px; }
QProgressBar { border: 1px solid #dcdde1; border-radius: 5px; text-align: center; background-color: #ffffff; height: 15px; }
QProgressBar::chunk { background-color: #00a8ff; border-radius: 5px; }
"""

# ================= 音频录制线程 =================
class AudioRecorderThread(QThread):
    sig_volume = pyqtSignal(int)
    sig_status = pyqtSignal(str)
    sig_audio_file = pyqtSignal(str) # 发送临时文件路径
    
    def __init__(self, mic_index):
        super().__init__()
        self.mic_index = mic_index
        self.is_running = True
        self.p = pyaudio.PyAudio()
        self.energy_threshold = SILENCE_THRESHOLD

    def run(self):
        stream = None
        try:
            stream = self.p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                                 input=True, input_device_index=self.mic_index,
                                 frames_per_buffer=CHUNK)
            
            self.sig_status.emit("正在校准环境噪音...")
            
            # 校准
            temp_energy = []
            for _ in range(30): # 稍微久一点
                if not self.is_running: break
                data = stream.read(CHUNK, exception_on_overflow=False)
                rms = audioop.rms(data, 2)
                temp_energy.append(rms)
                time.sleep(0.02)
            
            if temp_energy:
                avg = sum(temp_energy) / len(temp_energy)
                self.energy_threshold = max(avg * 1.5, 300)
                self.sig_status.emit(f"就绪 (AI模型加载中...)")

            frames = []
            silent_chunks = 0
            has_speech = False
            max_silent_chunks = int(PAUSE_LIMIT * (RATE / CHUNK))
            
            while self.is_running:
                data = stream.read(CHUNK, exception_on_overflow=False)
                rms = audioop.rms(data, 2)
                level = min(int(rms / 100), 100)
                self.sig_volume.emit(level)
                
                if rms > self.energy_threshold:
                    has_speech = True
                    silent_chunks = 0
                    frames.append(data)
                else:
                    if has_speech:
                        frames.append(data)
                        silent_chunks += 1
                        if silent_chunks > max_silent_chunks:
                            # 句尾检测：保存为临时wav文件
                            self.save_and_send(frames)
                            frames = []
                            has_speech = False
                            silent_chunks = 0
                    else:
                        if len(frames) > 10: frames.pop(0)
                        frames.append(data)

        except Exception as e:
            self.sig_status.emit(f"麦克风错误: {e}")
        finally:
            if stream: stream.stop_stream(); stream.close()
            self.p.terminate()

    def save_and_send(self, frames):
        try:
            # 创建临时文件
            fd, path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            
            with wave.open(path, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(self.p.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
            
            self.sig_status.emit("正在 AI 识别中...")
            self.sig_audio_file.emit(path)
        except Exception as e:
            print(f"File Error: {e}")

    def stop(self):
        self.is_running = False
        self.wait()

# ================= AI 识别与翻译线程 (核心) =================
class WhisperWorker(QThread):
    sig_result = pyqtSignal(str, str) # jp, cn
    sig_status = pyqtSignal(str)      # 专门用于回传“加载完成”状态

    def __init__(self):
        super().__init__()
        self.queue = queue.Queue()
        self.is_running = True
        self.model = None
        self.translator = Translator()

    def add_task(self, file_path):
        self.queue.put(file_path)

    def run(self):
        # 1. 线程启动时加载模型 (只加载一次，耗时)
        if self.model is None:
            try:
                # 检查是否有显卡
                device = "cuda" if torch.cuda.is_available() else "cpu"
                print(f"正在加载 Whisper 模型 ({MODEL_SIZE}) 到 {device}...")
                self.model = whisper.load_model(MODEL_SIZE, device=device)
                self.sig_status.emit("✅ AI 模型加载完成，请开始说话")
            except Exception as e:
                self.sig_status.emit(f"模型加载失败: {e}")
                return

        while self.is_running:
            try:
                file_path = self.queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                # 2. 调用 Whisper 进行识别
                # initial_prompt 有助于引导模型识别为日语
                result = self.model.transcribe(file_path, language="ja", fp16=False) 
                jp_text = result["text"].strip()
                
                # 删除临时文件
                try: os.remove(file_path)
                except: pass

                if not jp_text: continue

                # 3. 翻译 (日 -> 中)
                # 注：Whisper 其实也可以直接 translate task，但那是转英文。
                # 这里我们用 googletrans 翻译识别出来的日语文本，或者你可以再次用 deepL
                trans_res = self.translator.translate(jp_text, src='ja', dest='zh-cn')
                cn_text = trans_res.text
                
                self.sig_result.emit(jp_text, cn_text)
                
            except Exception as e:
                print(f"Transcribe Error: {e}")

    def stop(self):
        self.is_running = False
        self.wait()

# ================= 主窗口 (保持不变) =================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI 智能会议翻译 (Whisper + PyQt5)")
        self.resize(750, 850)
        self.setStyleSheet(STYLESHEET)
        
        self.audio_thread = None
        self.whisper_thread = None
        
        self.init_ui()
        self.refresh_mics()

    def init_ui(self):
        main = QWidget()
        self.setCentralWidget(main)
        layout = QVBoxLayout(main)
        
        # Top
        top = QHBoxLayout()
        top.addWidget(QLabel("🎤 麦克风:"))
        self.combo_mics = QComboBox()
        self.combo_mics.currentIndexChanged.connect(self.on_mic_change_preview)
        top.addWidget(self.combo_mics, 1)
        btn_ref = QPushButton("刷新")
        btn_ref.clicked.connect(self.refresh_mics)
        top.addWidget(btn_ref)
        layout.addLayout(top)
        
        # Vol
        layout.addWidget(QLabel("实时音量:"))
        self.pb_vol = QProgressBar()
        self.pb_vol.setRange(0, 100)
        self.pb_vol.setValue(0)
        layout.addWidget(self.pb_vol)
        
        # Buttons
        h = QHBoxLayout()
        self.btn_start = QPushButton("启动 AI 翻译")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.clicked.connect(self.start_app)
        
        self.btn_stop = QPushButton("停止")
        self.btn_stop.setObjectName("btnStop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_app)
        h.addWidget(self.btn_start)
        h.addWidget(self.btn_stop)
        layout.addLayout(h)
        
        # Text
        splitter = QSplitter(Qt.Vertical)
        self.txt_jp = QTextEdit(); self.txt_jp.setPlaceholderText("AI 正在准备中..."); self.txt_jp.setReadOnly(True)
        self.txt_cn = QTextEdit(); self.txt_cn.setPlaceholderText("翻译将显示在这里..."); self.txt_cn.setReadOnly(True)
        self.txt_cn.setStyleSheet("color: blue; font-weight: bold; font-size: 16px;")
        splitter.addWidget(self.txt_jp)
        splitter.addWidget(self.txt_cn)
        layout.addWidget(splitter)
        
        self.lbl_status = QLabel("就绪")
        self.statusBar().addWidget(self.lbl_status)
        
        self.preview_thread = None
        self.start_preview()

    def refresh_mics(self):
        self.combo_mics.blockSignals(True)
        self.combo_mics.clear()
        try:
            p = pyaudio.PyAudio()
            info = p.get_host_api_info_by_index(0)
            numdevices = info.get('deviceCount')
            for i in range(0, numdevices):
                if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                    name = p.get_device_info_by_host_api_device_index(0, i).get('name')
                    self.combo_mics.addItem(f"{i}: {name}", i)
            p.terminate()
        except: pass
        self.combo_mics.blockSignals(False)
        self.start_preview()

    def start_preview(self):
        self.stop_preview()
        if self.combo_mics.count() > 0:
            idx = self.combo_mics.currentData()
            if idx is not None:
                self.preview_thread = AudioRecorderThread(idx)
                self.preview_thread.sig_volume.connect(self.pb_vol.setValue)
                self.preview_thread.start()

    def stop_preview(self):
        if self.preview_thread:
            self.preview_thread.stop()
            self.preview_thread = None
            self.pb_vol.setValue(0)

    def on_mic_change_preview(self):
        if self.btn_start.isEnabled():
            self.start_preview()

    def start_app(self):
        idx = self.combo_mics.currentData()
        if idx is None: return
        self.stop_preview()
        
        # 1. 启动 Whisper 线程
        self.lbl_status.setText("正在加载 AI 模型 (首次运行可能需要几分钟)...")
        self.whisper_thread = WhisperWorker()
        self.whisper_thread.sig_result.connect(self.update_text)
        self.whisper_thread.sig_status.connect(self.on_model_loaded) # 监听模型加载状态
        self.whisper_thread.start()
        
        # 2. 启动录音线程
        self.audio_thread = AudioRecorderThread(idx)
        self.audio_thread.sig_volume.connect(self.pb_vol.setValue)
        self.audio_thread.sig_status.connect(self.update_status_safe)
        self.audio_thread.sig_audio_file.connect(self.whisper_thread.add_task) # 传递文件路径
        self.audio_thread.start()
        
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.combo_mics.setEnabled(False)

    def on_model_loaded(self, msg):
        self.lbl_status.setText(msg)

    def update_status_safe(self, msg):
        # 只有当模型已经加载完毕，录音线程的状态才覆盖显示
        if "加载" not in self.lbl_status.text():
             self.lbl_status.setText(msg)

    def stop_app(self):
        if self.audio_thread: self.audio_thread.stop()
        if self.whisper_thread: self.whisper_thread.stop()
        
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.combo_mics.setEnabled(True)
        self.lbl_status.setText("已停止")
        self.start_preview()

    def update_text(self, jp, cn):
        self.txt_jp.append(jp)
        self.txt_cn.append(cn)
        self.txt_jp.verticalScrollBar().setValue(self.txt_jp.verticalScrollBar().maximum())
        self.txt_cn.verticalScrollBar().setValue(self.txt_cn.verticalScrollBar().maximum())
        self.lbl_status.setText("【监听中】AI 准备就绪...")

    def closeEvent(self, e):
        self.stop_preview()
        self.stop_app()
        e.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())