import ctypes
import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QLabel, QSlider, QPushButton)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon

# --- Windows API 常量 ---
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
LWA_ALPHA = 0x2
user32 = ctypes.windll.user32

# 全局变量
wechat_hwnd = 0
current_target_alpha = 100  # 记录用户想要的目标透明度


# 定义结构体用于获取窗口矩形
class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)]


def is_target_window(hwnd):
    """
    判断逻辑：
    只要类名对，哪怕最小化（不可见）也锁定它
    """
    # 1. 获取类名
    class_buff = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, class_buff, 256)
    class_name = class_buff.value

    # 2. 获取标题
    length = user32.GetWindowTextLengthW(hwnd)
    title_buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, title_buff, length + 1)
    title = title_buff.value

    # --- 核心判断 ---
    # 只要是微信的主窗口类名，就认定是它（不管是否最小化）
    if class_name == "WeChatMainWndForPC":
        return True

    # 备用：按标题找（必须可见且有尺寸）
    if title == "微信" and user32.IsWindowVisible(hwnd):
        rect = RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        if (rect.right - rect.left) > 200:
            return True

    return False


def find_wechat():
    """遍历查找"""
    found_hwnds = []

    def enum_callback(hwnd, lParam):
        if is_target_window(hwnd):
            found_hwnds.append(hwnd)
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.EnumWindows(WNDENUMPROC(enum_callback), 0)

    return found_hwnds[0] if found_hwnds else 0


def apply_transparency(hwnd, alpha_pct):
    """
    强制应用透明度
    即使窗口在后台，也可以设置属性，这样弹出来时就是透明的
    """
    if hwnd == 0: return False

    try:
        alpha_val = int((alpha_pct / 100) * 255)
        if alpha_val < 3: alpha_val = 3  # 保护底线（1%对应约2.55，设置为3）

        # 1. 强制获取并修改样式（防止微信刷新后丢失 WS_EX_LAYERED 属性）
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if not (style & WS_EX_LAYERED):
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED)

        # 2. 设置透明度值
        user32.SetLayeredWindowAttributes(hwnd, 0, alpha_val, LWA_ALPHA)
        return True
    except:
        return False


def update_logic(window):
    """
    主逻辑：
    寻找句柄 -> 应用透明度 -> 更新界面文字
    """
    global wechat_hwnd

    # 1. 如果句柄丢失或无效，重新查找
    if wechat_hwnd == 0 or not user32.IsWindow(wechat_hwnd):
        wechat_hwnd = find_wechat()

    # 2. 如果找到了句柄
    if wechat_hwnd != 0:
        # 【关键】每次都重新应用一遍，防止微信从托盘恢复时重置了样式
        apply_transparency(wechat_hwnd, current_target_alpha)

        # 检查 status_label 是否存在（防止程序关闭时报错）
        try:
            if user32.IsWindowVisible(wechat_hwnd):
                status_text = f"状态: 已连接 (前台活跃) | 透明度: {int(current_target_alpha)}%"
                window.status_label.setText(status_text)
                window.status_label.setStyleSheet("color: green;")
            else:
                # 最小化状态
                status_text = f"状态: 已连接 (后台潜伏) | 预设: {int(current_target_alpha)}%"
                window.status_label.setText(status_text)
                window.status_label.setStyleSheet("color: #DAA520;")  # 金色
        except:
            pass
    else:
        try:
            window.status_label.setText("状态: 未检测到微信")
            window.status_label.setStyleSheet("color: red;")
        except:
            pass


def on_slider_change(window, val):
    global current_target_alpha
    current_target_alpha = float(val)
    # 只有当 value_label 已经被创建时才去更新它
    try:
        window.value_label.setText(f"{int(current_target_alpha)}%")
        # 滑动时立即触发一次更新
        update_logic(window)
    except:
        pass


def restore_and_exit(window):
    global wechat_hwnd
    if wechat_hwnd:
        apply_transparency(wechat_hwnd, 100)
    window.close()


# --- 工具函数 ---
def resource_path(filename):
    """
    处理 PyInstaller 单文件模式下的资源路径。
    - 开发环境：使用脚本所在目录
    - 打包后：使用 PyInstaller 临时解压目录（sys._MEIPASS）
    """
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, filename)


# --- GUI 构建 (PyQt5) ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
        # 创建定时器用于自动守护
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: update_logic(self))
        self.timer.start(800)  # 每隔 0.8 秒刷新一次
        
        # 延迟启动一次更新
        QTimer.singleShot(500, lambda: update_logic(self))
    
    def init_ui(self):
        self.setWindowTitle("微信透明工具 V2.0")
        self.setGeometry(100, 100, 320, 220)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        # 设置窗口图标
        icon_path = resource_path("app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # 1. 顶部提示
        tip_label = QLabel("支持在最小化时预设透明度")
        tip_label.setFont(QFont("微软雅黑", 10))
        tip_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(tip_label)
        
        # 2. 数值显示
        self.value_label = QLabel("100%")
        self.value_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)
        
        # 3. 状态标签
        self.status_label = QLabel("初始化中...")
        self.status_label.setStyleSheet("color: gray;")
        self.status_label.setFont(QFont("宋体", 9))
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 4. 滑块
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(1)
        self.slider.setMaximum(100)
        self.slider.setValue(100)
        self.slider.valueChanged.connect(lambda val: on_slider_change(self, val))
        
        # 美化滑块样式
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #E0E0E0, stop:1 #F5F5F5);
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #4CAF50, stop:1 #45a049);
                border: 2px solid #ffffff;
                width: 20px;
                height: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #66BB6A, stop:1 #4CAF50);
                border: 2px solid #ffffff;
            }
            QSlider::handle:horizontal:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #388E3C, stop:1 #2E7D32);
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4CAF50, stop:1 #66BB6A);
                border: 1px solid #4CAF50;
                height: 8px;
                border-radius: 4px;
            }
        """)
        
        layout.addWidget(self.slider)
        
        # 5. 按钮
        self.btn = QPushButton("恢复正常并退出")
        self.btn.clicked.connect(lambda: restore_and_exit(self))
        layout.addWidget(self.btn)
        
        # 6. 底部提示
        bottom_tip = QLabel("提示：如无效，请右键【以管理员身份运行】")
        bottom_tip.setStyleSheet("color: gray;")
        bottom_tip.setFont(QFont("宋体", 8))
        bottom_tip.setAlignment(Qt.AlignCenter)
        layout.addWidget(bottom_tip)
        
        # 添加弹性空间
        layout.addStretch()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序图标
    icon_path = resource_path("app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())