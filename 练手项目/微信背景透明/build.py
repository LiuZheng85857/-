import os
import subprocess
import sys
import shutil

# --- 配置区域 ---
TARGET_SCRIPT = "WeChat_Transparent_V 2.0.py"  # 你的主代码文件名
EXE_NAME = "透明工具 V2.0"  # 生成的 exe 名字
ICON_FILE = "app_icon.ico"  # 图标文件


# ----------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def install_pyinstaller():
    """检查并安装 PyInstaller"""
    try:
        import PyInstaller
        print("Checking: PyInstaller 已安装")
    except ImportError:
        print("Checking: 未检测到 PyInstaller，正在安装...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyinstaller", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"])


def clean_build_folders():
    """清理之前的构建残留，防止缓存导致的问题"""
    folders = ['build', 'dist', '__pycache__']
    for folder in folders:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                print(f"Cleaned: {folder}")
            except Exception as e:
                print(f"Failed to clean {folder}: {e}")

    spec_file = f"{EXE_NAME}.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)


def build_exe():
    """执行打包命令"""
    target_path = os.path.join(SCRIPT_DIR, TARGET_SCRIPT)
    if not os.path.exists(target_path):
        print(f"Error: 找不到文件 '{TARGET_SCRIPT}'，请确保它和本脚本在同一目录下。")
        input("按回车键退出...")
        return

    # 检查图标文件是否存在
    icon_path = None
    icon_candidate = os.path.join(SCRIPT_DIR, ICON_FILE)
    if os.path.exists(icon_candidate):
        icon_path = icon_candidate
        print(f"Info: 找到图标文件: {ICON_FILE}")
    else:
        print(f"Warning: 未找到图标文件 '{ICON_FILE}'，将使用默认图标")

    print("Start: 开始打包...")

    # PyInstaller 命令参数详解：
    # -F : 生成单个 exe 文件 (Onefile)
    # -w : 运行且不显示黑色命令行窗口 (Windowed / Noconsole)
    # --uac-admin : 运行时自动请求管理员权限 (重要！修改窗口属性通常需要此权限)
    # --clean : 清除缓存
    # --name : 指定生成文件的名字
    # --icon : 指定图标文件（.ico格式）

    cmd = [
        "pyinstaller",
        "-F",
        "-w",
        "--uac-admin",
        "--clean",
        f"--name={EXE_NAME}",
    ]
    
    # 如果图标文件存在，添加图标参数
    if icon_path:
        cmd.append(f"--icon={icon_path}")
    
    cmd.append(target_path)

    try:
        subprocess.check_call(cmd)
        print("\n" + "=" * 30)
        print("SUCCESS: 打包成功！")
        print(f"请在 dist 文件夹中查看 {EXE_NAME}.exe")
        print("=" * 30 + "\n")

        # 自动打开 dist 文件夹
        if os.path.exists("dist"):
            os.startfile("dist")

    except subprocess.CalledProcessError:
        print("\nERROR: 打包过程中出错。")


if __name__ == "__main__":
    print("--- Python 打包工具 ---")
    os.chdir(SCRIPT_DIR)  # 确保从任意目录调用时都能定位资源
    install_pyinstaller()
    clean_build_folders()
    build_exe()
    input("按回车键退出...")