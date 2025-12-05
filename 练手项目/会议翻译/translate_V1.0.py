import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import speech_recognition as sr
from googletrans import Translator
import threading
import pyaudio
import audioop  # 用于计算音量
import time

class TransApp:
    def __init__(self, root):
        self.root = root
        self.root.title("会议实时翻译 (日语 -> 中文)")
        self.root.geometry("600x750")
        
        # 核心对象
        self.recognizer = sr.Recognizer()
        self.translator = Translator()
        self.is_running = False
        self.is_listening_volume = True # 是否监听音量
        self.mic_list = []
        
        # --- UI 布局 ---
        
        # 1. 顶部设置区
        frame_top = ttk.LabelFrame(root, text="设置")
        frame_top.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(frame_top, text="选择麦克风:").grid(row=0, column=0, padx=5, pady=5)
        self.combo_mics = ttk.Combobox(frame_top, width=40, state="readonly")
        self.combo_mics.grid(row=0, column=1, padx=5, pady=5)
        self.combo_mics.bind("<<ComboboxSelected>>", self.on_mic_change)
        
        btn_refresh = ttk.Button(frame_top, text="刷新设备", command=self.refresh_mics)
        btn_refresh.grid(row=0, column=2, padx=5, pady=5)

        # 2. 音量监控区
        frame_vol = ttk.LabelFrame(root, text="麦克风测试 (实时音量)")
        frame_vol.pack(fill="x", padx=10, pady=5)
        
        self.pb_volume = ttk.Progressbar(frame_vol, orient="horizontal", length=560, mode="determinate")
        self.pb_volume.pack(padx=10, pady=10)
        
        # 3. 控制按钮
        frame_ctrl = ttk.Frame(root)
        frame_ctrl.pack(fill="x", padx=10, pady=5)
        
        self.btn_start = ttk.Button(frame_ctrl, text="开始实时翻译", command=self.start_translation)
        self.btn_start.pack(side="left", fill="x", expand=True, padx=5)
        
        self.btn_stop = ttk.Button(frame_ctrl, text="停止", command=self.stop_translation, state="disabled")
        self.btn_stop.pack(side="right", fill="x", expand=True, padx=5)

        # 4. 显示区域
        self.split_pane = tk.PanedWindow(root, orient="vertical")
        self.split_pane.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 日语原文区
        group_jp = ttk.LabelFrame(self.split_pane, text="日语原文 (识别中...)")
        self.txt_jp = scrolledtext.ScrolledText(group_jp, height=8, font=("Meiryo", 10))
        self.txt_jp.pack(fill="both", expand=True, padx=5, pady=5)
        self.split_pane.add(group_jp)
        
        # 中文翻译区
        group_cn = ttk.LabelFrame(self.split_pane, text="中文翻译")
        self.txt_cn = scrolledtext.ScrolledText(group_cn, height=8, font=("Microsoft YaHei", 10), fg="blue")
        self.txt_cn.pack(fill="both", expand=True, padx=5, pady=5)
        self.split_pane.add(group_cn)

        # 状态栏
        self.lbl_status = ttk.Label(root, text="就绪 - 请选择麦克风并测试音量", relief="sunken")
        self.lbl_status.pack(side="bottom", fill="x")

        # 初始化逻辑
        self.refresh_mics()
        # 启动音量监听线程
        self.thread_vol = threading.Thread(target=self.monitor_volume_loop, daemon=True)
        self.thread_vol.start()

    def refresh_mics(self):
        """刷新麦克风列表"""
        self.mic_list = sr.Microphone.list_microphone_names()
        if not self.mic_list:
            self.combo_mics['values'] = ["未检测到麦克风"]
        else:
            # 格式化显示：索引 - 名称
            display_list = [f"{i}: {name}" for i, name in enumerate(self.mic_list)]
            self.combo_mics['values'] = display_list
            self.combo_mics.current(0) # 默认选第一个

    def on_mic_change(self, event):
        """当用户切换麦克风时"""
        self.log_status(f"已切换麦克风: {self.combo_mics.get()}")

    def get_selected_mic_index(self):
        """获取当前选中的麦克风索引"""
        try:
            selection = self.combo_mics.get()
            index = int(selection.split(":")[0])
            return index
        except:
            return None

    def monitor_volume_loop(self):
        """后台线程：仅用于检测音量条动画"""
        p = pyaudio.PyAudio()
        stream = None
        current_idx = -1
        
        while True:
            # 如果正在翻译中，或者没有选择麦克风，暂停音量检测
            if self.is_running or not self.is_listening_volume:
                time.sleep(0.5)
                # 翻译开始时关闭流，释放设备给 SpeechRecognition 使用
                if stream is not None:
                    try:
                        stream.stop_stream()
                        stream.close()
                    except:
                        pass
                    stream = None
                continue

            try:
                # 获取当前选中的麦克风
                idx = self.get_selected_mic_index()
                if idx is None:
                    time.sleep(1)
                    continue
                
                # 如果设备变了，或者流断了，重新打开
                if stream is None or idx != current_idx:
                    if stream:
                        stream.stop_stream()
                        stream.close()
                    
                    try:
                        stream = p.open(format=pyaudio.paInt16,
                                        channels=1,
                                        rate=44100,
                                        input=True,
                                        input_device_index=idx,
                                        frames_per_buffer=1024)
                        current_idx = idx
                    except Exception as e:
                        # 某些设备可能不支持特定参数，忽略错误
                        time.sleep(1)
                        continue

                # 读取音频数据并计算音量
                data = stream.read(1024, exception_on_overflow=False)
                rms = audioop.rms(data, 2)  # 计算均方根（音量）
                
                # 简单的映射：将 rms 映射到 0-100
                level = min(rms / 200, 100) 
                
                # 更新 UI (必须在主线程更新，但这只是简单的变量赋值，Tkinter容错率较高，或者用 after)
                self.pb_volume['value'] = level
                
            except Exception as e:
                # print(f"音量检测错误: {e}")
                time.sleep(0.1)

    def start_translation(self):
        """开始按钮回调"""
        idx = self.get_selected_mic_index()
        if idx is None:
            messagebox.showerror("错误", "请先选择一个麦克风！")
            return

        self.is_running = True
        self.is_listening_volume = False # 停止音量监控，释放设备
        
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.combo_mics.config(state="disabled")
        self.pb_volume['value'] = 0 # 归零
        
        self.log_status("正在启动识别引擎...")
        
        # 启动翻译线程
        t = threading.Thread(target=self.run_recognition, args=(idx,), daemon=True)
        t.start()

    def stop_translation(self):
        """停止按钮回调"""
        self.is_running = False
        self.log_status("正在停止... 请等待当前句子处理完成")
        self.btn_stop.config(state="disabled")

    def run_recognition(self, device_index):
        """翻译核心逻辑（在独立线程运行）"""
        r = sr.Recognizer()
        r.dynamic_energy_threshold = True 
        r.pause_threshold = 0.8 # 说话停顿多久算一句话结束

        try:
            with sr.Microphone(device_index=device_index) as source:
                self.log_status("正在校准环境噪音... (请保持安静 1 秒)")
                r.adjust_for_ambient_noise(source, duration=1)
                self.log_status("【正在聆听日语】... (对着麦克风说话)")
                
                while self.is_running:
                    try:
                        # 1. 监听
                        # timeout: 如果多久没声音就报错(这里设None一直等)
                        # phrase_time_limit: 一句话最长录多久，避免死循环
                        audio = r.listen(source, timeout=None, phrase_time_limit=15)
                        
                        self.log_status("正在识别与翻译...")
                        
                        # 2. 识别 (日语)
                        text_jp = r.recognize_google(audio, language="ja-JP")
                        self.append_text(self.txt_jp, text_jp)
                        
                        # 3. 翻译 (日 -> 中)
                        res = self.translator.translate(text_jp, src='ja', dest='zh-cn')
                        text_cn = res.text
                        self.append_text(self.txt_cn, text_cn)
                        
                        self.log_status("【继续聆听】...")
                        
                    except sr.WaitTimeoutError:
                        continue
                    except sr.UnknownValueError:
                        # 没听清，忽略
                        pass 
                    except sr.RequestError:
                        self.log_status("网络错误，无法连接 Google 服务")
                        time.sleep(2)
                    except Exception as e:
                        self.log_status(f"错误: {e}")
                        
        except Exception as e:
            self.log_status(f"麦克风初始化失败: {e}")
        finally:
            # 恢复 UI 状态
            self.reset_ui()

    def reset_ui(self):
        """恢复界面可点击状态"""
        self.is_running = False
        self.is_listening_volume = True # 恢复音量条
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.combo_mics.config(state="readonly")
        self.log_status("已停止。")

    def append_text(self, widget, text):
        """向文本框追加内容"""
        widget.insert(tk.END, text + "\n")
        widget.see(tk.END) # 自动滚动到底部

    def log_status(self, msg):
        """更新底部状态栏"""
        self.lbl_status.config(text=msg)

if __name__ == "__main__":
    root = tk.Tk()
    # 尝试设置图标（如果有的话），没有就跳过
    # root.iconbitmap("icon.ico") 
    app = TransApp(root)
    root.mainloop()