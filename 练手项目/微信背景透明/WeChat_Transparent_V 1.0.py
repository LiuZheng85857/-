import ctypes
import tkinter as tk
from tkinter import ttk
from ctypes import wintypes

# --- Windows API 常量与定义 ---
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
LWA_ALPHA = 0x2
user32 = ctypes.windll.user32


# 定义 RECT 结构体用于获取窗口大小
class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)]


# 全局变量
wechat_hwnd = 0


def is_main_window(hwnd):
    """
    判断是否为真正的微信主窗口：
    1. 窗口可见
    2. 窗口标题是 '微信' 或 类名是 'WeChatMainWndForPC'
    3. 窗口大小正常（排除 0x0 或 1x1 的隐藏窗口）
    """
    if not user32.IsWindowVisible(hwnd):
        return False

    # 获取标题
    length = user32.GetWindowTextLengthW(hwnd)
    title_buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, title_buff, length + 1)
    title = title_buff.value

    # 获取类名
    class_buff = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, class_buff, 256)
    class_name = class_buff.value

    # 核心判断逻辑
    is_wechat = (title == "微信") or (class_name == "WeChatMainWndForPC")

    if is_wechat:
        # 进一步检查窗口大小，防止选中托盘气泡
        rect = RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        # 主窗口宽度和高度通常都大于 200 像素
        if width > 200 and height > 200:
            return True

    return False


def find_real_wechat_window():
    """
    遍历所有窗口，找到符合条件的那一个
    """
    found_hwnds = []

    # 定义回调函数
    def enum_callback(hwnd, lParam):
        if is_main_window(hwnd):
            found_hwnds.append(hwnd)
        return True  # 继续遍历

    # 注册回调类型
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.EnumWindows(WNDENUMPROC(enum_callback), 0)

    if found_hwnds:
        return found_hwnds[0]  # 返回找到的第一个符合条件的句柄
    return 0


def set_window_transparency(alpha_percentage):
    global wechat_hwnd

    # 每次设置前检查句柄有效性
    if wechat_hwnd == 0 or not user32.IsWindow(wechat_hwnd):
        wechat_hwnd = find_real_wechat_window()

    if wechat_hwnd == 0:
        status_label.config(text="未找到可见的微信窗口", fg="red")
        return

    status_label.config(text=f"锁定窗口句柄: {wechat_hwnd}", fg="green")

    # 【修改点1】限制最小透明度改为 10
    if alpha_percentage < 10:
        alpha_percentage = 10

    alpha_value = int((alpha_percentage / 100) * 255)

    try:
        # 1. 获取当前样式
        current_style = user32.GetWindowLongW(wechat_hwnd, GWL_EXSTYLE)
        # 2. 赋予分层属性
        if not (current_style & WS_EX_LAYERED):
            user32.SetWindowLongW(wechat_hwnd, GWL_EXSTYLE, current_style | WS_EX_LAYERED)
        # 3. 执行透明
        user32.SetLayeredWindowAttributes(wechat_hwnd, 0, alpha_value, LWA_ALPHA)
    except Exception as e:
        status_label.config(text=f"错误: {e}", fg="red")


def on_slider_change(val):
    percentage = float(val)
    value_label.config(text=f"{int(percentage)}%")
    set_window_transparency(percentage)


def restore_wechat():
    if wechat_hwnd != 0:
        set_window_transparency(100)
    root.destroy()


# --- GUI ---
root = tk.Tk()
root.title("微信透明工具")
root.geometry("300x200")
root.attributes("-topmost", True)

tk.Label(root, text="拖动滑块调节透明度", font=("微软雅黑", 10)).pack(pady=10)

# 先创建 label，再创建 slider
value_label = tk.Label(root, text="100%", font=("Arial", 12, "bold"))
value_label.pack()

# 先初始化 status_label
status_label = tk.Label(root, text="正在搜索微信...", fg="gray")

# 【修改点2】滑块范围 from_=10
slider = ttk.Scale(root, from_=10, to=100, orient="horizontal", command=on_slider_change)
slider.set(100)
slider.pack(fill="x", padx=20, pady=5)

status_label.pack(pady=5)

ttk.Button(root, text="恢复并退出", command=restore_wechat).pack(pady=10)

# 启动时搜索
wechat_hwnd = find_real_wechat_window()
if wechat_hwnd:
    status_label.config(text=f"已连接: {wechat_hwnd}", fg="green")
else:
    status_label.config(text="请确保微信在桌面上显示", fg="red")

root.mainloop()