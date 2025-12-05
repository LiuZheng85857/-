import sys
import time
import audioop
import pyaudio
import queue
import speech_recognition as sr
from googletrans import Translator
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QComboBox, QPushButton, 
                             QTextEdit, QProgressBar, QSplitter, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# ================= 配置参数 =================
CHUNK = 1024                # 每次读取的音频块大小
FORMAT = pyaudio.paInt16    # 16位深度
CHANNELS = 1                # 单声道
RATE = 44100                # 采样率
SILENCE_THRESHOLD = 500     # 默认静音阈值 (会自动调整)
PAUSE_LIMIT = 0.8           # 停顿多少秒算一句话结束

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

# ================= 生产者：音频录制线程 (负责音量和录音) =================
class AudioRecorderThread(QThread):
    sig_volume = pyqtSignal(int)          # 发送音量信号
    sig_status = pyqtSignal(str)          # 发送状态文字
    sig_audio_data = pyqtSignal(object)   # 发送录好的音频给翻译线程
    
    def __init__(self, mic_index):
        super().__init__()
        self.mic_index = mic_index
        self.is_running = True
        self.p = pyaudio.PyAudio()
        self.energy_threshold = SILENCE_THRESHOLD

    def run(self):
        stream = None
        try:
            stream = self.p.open(format=FORMAT,
                                 channels=CHANNELS,
                                 rate=RATE,
                                 input=True,
                                 input_device_index=self.mic_index,
                                 frames_per_buffer=CHUNK)
            
            self.sig_status.emit("正在校准环境噪音...")
            
            # 1. 简易校准
            temp_energy = []
            for _ in range(20):
                if not self.is_running: break
                data = stream.read(CHUNK, exception_on_overflow=False)
                rms = audioop.rms(data, 2)
                temp_energy.append(rms)
                time.sleep(0.05)
            
            if temp_energy:
                avg = sum(temp_energy) / len(temp_energy)
                self.energy_threshold = max(avg * 1.5, 300)
                self.sig_status.emit(f"就绪 (阈值:{int(self.energy_threshold)}) - 请说话")

            # 2. 录音循环
            frames = []
            silent_chunks = 0
            has_speech = False
            max_silent_chunks = int(PAUSE_LIMIT * (RATE / CHUNK))
            
            while self.is_running:
                data = stream.read(CHUNK, exception_on_overflow=False)
                rms = audioop.rms(data, 2)
                
                # --- 实时发送音量给UI (这就是你要的功能) ---
                level = min(int(rms / 100), 100)
                self.sig_volume.emit(level)
                
                # --- 简单的 VAD (语音活动检测) ---
                if rms > self.energy_threshold:
                    has_speech = True
                    silent_chunks = 0
                    frames.append(data)
                else:
                    if has_speech:
                        frames.append(data)
                        silent_chunks += 1
                        if silent_chunks > max_silent_chunks:
                            # 这里的逻辑：说话停止后，把录音打包发出去
                            raw = b''.join(frames)
                            audio_obj = sr.AudioData(raw, RATE, 2)
                            self.sig_audio_data.emit(audio_obj)
                            self.sig_status.emit("正在翻译...")
                            
                            frames = []
                            has_speech = False
                            silent_chunks = 0
                    else:
                        # 没说话时，只保留一点点缓存，防止内存溢出
                        if len(frames) > 10: frames.pop(0)
                        frames.append(data)

        except Exception as e:
            self.sig_status.emit(f"麦克风错误: {e}")
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            self.p.terminate()

    def stop(self):
        self.is_running = False
        self.wait()

# ================= 消费者：翻译线程 (后台处理) =================
class TranslatorWorker(QThread):
    sig_result = pyqtSignal(str, str) # 发送 (原文, 译文)
    sig_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.queue = queue.Queue()
        self.is_running = True
        self.recognizer = sr.Recognizer()
        self.translator = Translator()

    def add_task(self, audio_data):
        self.queue.put(audio_data)

    def run(self):
        while self.is_running:
            try:
                audio = self.queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                # 识别
                jp = self.recognizer.recognize_google(audio, language="ja-JP")
                # 翻译
                res = self.translator.translate(jp, src='ja', dest='zh-cn')
                cn = res.text
                self.sig_result.emit(jp, cn)
            except sr.UnknownValueError:
                pass 
            except Exception as e:
                self.sig_error.emit(str(e))

    def stop(self):
        self.is_running = False
        self.wait()

# ================= 主窗口 =================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("同声传译 V3.0 (修复版)")
        self.resize(700, 800)
        self.setStyleSheet(STYLESHEET)
        
        self.audio_thread = None
        self.trans_thread = None
        
        self.init_ui()
        self.refresh_mics()

    def init_ui(self):
        main = QWidget()
        self.setCentralWidget(main)
        layout = QVBoxLayout(main)
        
        # 顶部
        top = QHBoxLayout()
        top.addWidget(QLabel("🎤 麦克风:"))
        self.combo_mics = QComboBox()
        self.combo_mics.currentIndexChanged.connect(self.on_mic_change_preview)
        top.addWidget(self.combo_mics, 1)
        btn_ref = QPushButton("刷新")
        btn_ref.clicked.connect(self.refresh_mics)
        top.addWidget(btn_ref)
        layout.addLayout(top)
        
        # 音量
        layout.addWidget(QLabel("实时音量:"))
        self.pb_vol = QProgressBar()
        self.pb_vol.setRange(0, 100)
        self.pb_vol.setValue(0)
        layout.addWidget(self.pb_vol)
        
        # 按钮
        h = QHBoxLayout()
        self.btn_start = QPushButton("开始翻译")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.clicked.connect(self.start_app)
        
        self.btn_stop = QPushButton("停止")
        self.btn_stop.setObjectName("btnStop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_app)
        h.addWidget(self.btn_start)
        h.addWidget(self.btn_stop)
        layout.addLayout(h)
        
        # 文本
        splitter = QSplitter(Qt.Vertical)
        self.txt_jp = QTextEdit(); self.txt_jp.setPlaceholderText("🇯🇵 日语..."); self.txt_jp.setReadOnly(True)
        self.txt_cn = QTextEdit(); self.txt_cn.setPlaceholderText("🇨🇳 中文..."); self.txt_cn.setReadOnly(True)
        self.txt_cn.setStyleSheet("color: blue; font-weight: bold; font-size: 16px;")
        
        splitter.addWidget(self.txt_jp)
        splitter.addWidget(self.txt_cn)
        layout.addWidget(splitter)
        
        self.lbl_status = QLabel("就绪")
        self.statusBar().addWidget(self.lbl_status)
        
        # 预览用线程
        self.preview_thread = None
        self.start_preview()

    def refresh_mics(self):
        self.combo_mics.blockSignals(True)
        self.combo_mics.clear()
        try:
            mics = sr.Microphone.list_microphone_names()
            for i, m in enumerate(mics):
                self.combo_mics.addItem(f"{i}: {m}", i)
        except:
            self.combo_mics.addItem("无法读取麦克风")
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
        
        # 启动翻译线程
        self.trans_thread = TranslatorWorker()
        self.trans_thread.sig_result.connect(self.update_text)
        self.trans_thread.start()
        
        # 启动录音线程
        self.audio_thread = AudioRecorderThread(idx)
        self.audio_thread.sig_volume.connect(self.pb_vol.setValue) # 确保翻译时也更新UI
        self.audio_thread.sig_status.connect(self.lbl_status.setText)
        self.audio_thread.sig_audio_data.connect(self.trans_thread.add_task)
        self.audio_thread.start()
        
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.combo_mics.setEnabled(False)

    def stop_app(self):
        if self.audio_thread: self.audio_thread.stop()
        if self.trans_thread: self.trans_thread.stop()
        
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.combo_mics.setEnabled(True)
        self.lbl_status.setText("已停止")
        self.start_preview()

    def update_text(self, jp, cn):
        self.txt_jp.append(jp)
        self.txt_cn.append(cn)
        self.lbl_status.setText("【监听中】请继续...")

    def closeEvent(self, e):
        self.stop_preview()
        self.stop_app()
        e.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())