# -*- coding: utf-8 -*-

import os
import subprocess
import sys
import threading
import shutil
import time
import re
import winreg
from tkinter import (
    Tk, Label, Button, Entry, filedialog, messagebox, 
    Text, Scrollbar, ttk, Frame
)

class M3U8ConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("M3U8 转 MP4 转换工具")
        self.root.geometry("700x500")
        self.root.resizable(True, True)
        
        # 变量
        self.input_file = ""
        self.output_file = ""
        self.output_folder_path = ""  # 存储输出文件夹路径
        self.ffmpeg_installed = False
        self.installing_ffmpeg = False  # 防止重复触发安装
        self.ffmpeg_path = None  # 存储 ffmpeg 的完整路径
        
        # 创建界面
        self.create_widgets()
        
        # 启动时检查 FFmpeg
        self.check_ffmpeg()
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # 标题
        title_label = Label(
            main_frame, 
            text="M3U8 转 MP4 转换工具", 
            font=("Microsoft YaHei", 16, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # FFmpeg 状态
        self.ffmpeg_status_frame = Frame(main_frame)
        self.ffmpeg_status_frame.pack(fill='x', pady=(0, 15))
        
        self.ffmpeg_status_label = Label(
            self.ffmpeg_status_frame, 
            text="正在检查 FFmpeg...", 
            font=("Microsoft YaHei", 10),
            fg="orange"
        )
        self.ffmpeg_status_label.pack(side='left')
        
        self.install_ffmpeg_btn = Button(
            self.ffmpeg_status_frame,
            text="自动安装 FFmpeg",
            command=self.install_ffmpeg,
            state='disabled',
            bg="#4CAF50",
            fg="white",
            font=("Microsoft YaHei", 9)
        )
        self.install_ffmpeg_btn.pack(side='left', padx=(10, 0))
        
        # 输入文件选择
        input_frame = Frame(main_frame)
        input_frame.pack(fill='x', pady=(0, 10))
        
        Label(
            input_frame, 
            text="输入文件 (M3U8):", 
            font=("Microsoft YaHei", 10)
        ).pack(anchor='w')
        
        input_file_frame = Frame(input_frame)
        input_file_frame.pack(fill='x', pady=(5, 0))
        
        self.input_entry = Entry(
            input_file_frame, 
            font=("Microsoft YaHei", 9),
            state='readonly'
        )
        self.input_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        Button(
            input_file_frame,
            text="选择文件...",
            command=self.select_input_file,
            font=("Microsoft YaHei", 9)
        ).pack(side='left', padx=(0, 5))
        
        Button(
            input_file_frame,
            text="选择文件夹...",
            command=self.select_input_folder,
            font=("Microsoft YaHei", 9)
        ).pack(side='left')
        
        # 输出文件选择
        output_frame = Frame(main_frame)
        output_frame.pack(fill='x', pady=(0, 10))
        
        Label(
            output_frame, 
            text="输出文件 (MP4):", 
            font=("Microsoft YaHei", 10)
        ).pack(anchor='w')
        
        output_file_frame = Frame(output_frame)
        output_file_frame.pack(fill='x', pady=(5, 0))
        
        self.output_entry = Entry(
            output_file_frame, 
            font=("Microsoft YaHei", 9)
        )
        self.output_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        self.output_entry.insert(0, "output.mp4")
        self.output_entry.config(state='normal')
        
        Button(
            output_file_frame,
            text="浏览...",
            command=self.select_output_file,
            font=("Microsoft YaHei", 9)
        ).pack(side='left')
        
        # 转换按钮
        self.convert_btn = Button(
            main_frame,
            text="开始转换",
            command=self.start_conversion,
            bg="#2196F3",
            fg="white",
            font=("Microsoft YaHei", 12, "bold"),
            state='disabled',
            pady=10
        )
        self.convert_btn.pack(fill='x', pady=(15, 10))
        
        # 进度行（显示百分比与预计剩余时间）
        self.progress_line_label = Label(
            main_frame,
            text="进度：--% | 预计剩余：--:--:--",
            font=("Microsoft YaHei", 9),
            fg="gray"
        )
        self.progress_line_label.pack(fill='x', pady=(0, 10))
        
        # 状态显示
        self.status_label = Label(
            main_frame,
            text="准备就绪",
            font=("Microsoft YaHei", 9),
            fg="gray"
        )
        self.status_label.pack(anchor='w')
        
        # 日志显示区域
        log_frame = Frame(main_frame)
        log_frame.pack(fill='both', expand=True, pady=(10, 0))
        
        Label(
            log_frame,
            text="转换日志:",
            font=("Microsoft YaHei", 9)
        ).pack(anchor='w')
        
        log_text_frame = Frame(log_frame)
        log_text_frame.pack(fill='both', expand=True, pady=(5, 0))
        
        scrollbar = Scrollbar(log_text_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.log_text = Text(
            log_text_frame,
            height=8,
            font=("Consolas", 9),
            yscrollcommand=scrollbar.set,
            wrap='word'
        )
        self.log_text.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.log_text.yview)
    
    def log(self, message):
        """添加日志"""
        self.log_text.insert('end', message + '\n')
        self.log_text.see('end')
        self.root.update()
    
    def check_ffmpeg(self):
        """检查 FFmpeg 是否已安装"""
        self.log("正在检查 FFmpeg 安装状态...")
        
        # 首先检查 D 盘上的 FFmpeg
        d_ffmpeg_exe = r"D:\ffmpeg-8.0-essentials_build\bin\ffmpeg.exe"
        if os.path.exists(d_ffmpeg_exe):
            try:
                result = subprocess.run(
                    [d_ffmpeg_exe, '-version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    # 如果 D 盘上有 ffmpeg 但不在 PATH 中，在后台线程中配置
                    bin_dir = os.path.dirname(d_ffmpeg_exe)
                    current_path = os.environ.get('PATH', '')
                    if bin_dir not in current_path:
                        self.log("检测到 D 盘上的 FFmpeg，但未在 PATH 中，正在后台配置...")
                        # 在后台线程中配置环境变量，避免阻塞 GUI
                        thread = threading.Thread(target=self._configure_path_in_thread, args=(bin_dir,))
                        thread.daemon = True
                        thread.start()
                    else:
                        self.log("✓ D 盘上的 FFmpeg 已在 PATH 中")
                    
                    self.ffmpeg_installed = True
                    self.ffmpeg_path = d_ffmpeg_exe  # 保存完整路径
                    self.ffmpeg_status_label.config(
                        text="✓ FFmpeg 已安装 (D盘)",
                        fg="green"
                    )
                    self.install_ffmpeg_btn.config(state='disabled')
                    self.log("✓ FFmpeg 检测成功！(D盘)")
                    self.update_convert_button_state()
                    return True
            except Exception as e:
                self.log(f"检查 D 盘 FFmpeg 时出错: {e}")
        
        # 检查 ffmpeg 是否在 PATH 中
        ffmpeg_path = shutil.which('ffmpeg')
        
        if ffmpeg_path:
            try:
                # 尝试运行 ffmpeg 获取版本信息
                result = subprocess.run(
                    ['ffmpeg', '-version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    self.ffmpeg_installed = True
                    self.ffmpeg_path = ffmpeg_path  # 保存路径
                    self.ffmpeg_status_label.config(
                        text="✓ FFmpeg 已安装",
                        fg="green"
                    )
                    self.install_ffmpeg_btn.config(state='disabled')
                    self.log("✓ FFmpeg 检测成功！")
                    self.update_convert_button_state()
                    return True
            except Exception as e:
                self.log(f"检查 FFmpeg 时出错: {e}")
        
        # FFmpeg 未安装
        self.ffmpeg_installed = False
        self.ffmpeg_status_label.config(
            text="✗ FFmpeg 未安装",
            fg="red"
        )
        self.install_ffmpeg_btn.config(state='normal')
        self.log("✗ FFmpeg 未安装，正在尝试自动安装...")
        # 自动触发安装（如果还没有在安装中）
        if not self.installing_ffmpeg:
            self.installing_ffmpeg = True
            self.install_ffmpeg()
        self.update_convert_button_state()
        return False
    
    def install_ffmpeg(self):
        """自动安装 FFmpeg"""
        if self.installing_ffmpeg:
            return  # 已经在安装中，避免重复触发
        self.installing_ffmpeg = True
        self.install_ffmpeg_btn.config(state='disabled')
        self.ffmpeg_status_label.config(text="正在安装 FFmpeg...", fg="orange")
        self.log("\n开始安装 FFmpeg...")
        
        # 在后台线程中安装
        thread = threading.Thread(target=self._install_ffmpeg_thread)
        thread.daemon = True
        thread.start()
    
    def _install_ffmpeg_thread(self):
        """在后台线程中安装 FFmpeg"""
        try:
            # 首先检查 D 盘上是否已经存在 FFmpeg
            d_ffmpeg_dir = r"D:\ffmpeg-8.0-essentials_build"
            if os.path.exists(d_ffmpeg_dir) and os.path.isdir(d_ffmpeg_dir):
                bin_dir = os.path.join(d_ffmpeg_dir, "bin")
                if os.path.exists(bin_dir):
                    self.log("检测到 D 盘上的 FFmpeg，开始配置环境变量...")
                    if self._add_to_path(bin_dir):
                        self.log("✓ D 盘 FFmpeg 配置成功！")
                        self.refresh_environment()
                        time.sleep(2)
                        self.installing_ffmpeg = False
                        self.root.after(0, lambda: self.check_ffmpeg())
                        return
            
            # 尝试使用本地 ffmpeg-8.0-essentials_build 文件夹（如果还在当前目录）
            local_ffmpeg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg-8.0-essentials_build')
            if os.path.exists(local_ffmpeg_dir) and os.path.isdir(local_ffmpeg_dir):
                self.log("检测到本地 FFmpeg 安装包，开始安装到 D 盘...")
                if self._install_from_local_package(local_ffmpeg_dir):
                    self.log("✓ 使用本地安装包安装成功！")
                    self.refresh_environment()
                    # 等待一下让环境变量生效
                    time.sleep(2)
                    self.installing_ffmpeg = False
                    self.root.after(0, lambda: self.check_ffmpeg())
                    return
            
            # 尝试使用 winget（Windows 10/11 自带）
            self.log("尝试使用 winget 安装...")
            result = subprocess.run(
                ['winget', 'install', '--id', 'Gyan.FFmpeg', '--silent', '--accept-package-agreements', '--accept-source-agreements'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                self.log("✓ 使用 winget 安装成功！")
                # 刷新环境变量
                self.refresh_environment()
                self.installing_ffmpeg = False
                self.root.after(0, lambda: self.check_ffmpeg())
                return
            
            # 尝试使用 choco
            self.log("尝试使用 Chocolatey 安装...")
            result = subprocess.run(
                ['choco', 'install', 'ffmpeg', '-y'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                self.log("✓ 使用 Chocolatey 安装成功！")
                self.refresh_environment()
                self.installing_ffmpeg = False
                self.root.after(0, lambda: self.check_ffmpeg())
                return
            
            # 尝试使用 scoop
            self.log("尝试使用 Scoop 安装...")
            result = subprocess.run(
                ['scoop', 'install', 'ffmpeg'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                self.log("✓ 使用 Scoop 安装成功！")
                self.refresh_environment()
                self.installing_ffmpeg = False
                self.root.after(0, lambda: self.check_ffmpeg())
                return
            
            # 所有方法都失败
            self.log("✗ 自动安装失败，未找到可用的包管理器")
            self.log("请手动安装 FFmpeg:")
            self.log("  1. 访问 https://www.gyan.dev/ffmpeg/builds/")
            self.log("  2. 下载并解压 FFmpeg")
            self.log("  3. 将 bin 目录添加到 PATH 环境变量")
            self.root.after(0, lambda: messagebox.showerror(
                "安装失败",
                "自动安装失败。\n\n请手动安装 FFmpeg:\n"
                "1. 访问 https://www.gyan.dev/ffmpeg/builds/\n"
                "2. 下载并解压 FFmpeg\n"
                "3. 将 bin 目录添加到 PATH 环境变量\n"
                "4. 重新启动此程序"
            ))
            self.root.after(0, lambda: self.ffmpeg_status_label.config(
                text="✗ 安装失败，请手动安装",
                fg="red"
            ))
            self.root.after(0, lambda: self.install_ffmpeg_btn.config(state='normal'))
            self.installing_ffmpeg = False
            
        except FileNotFoundError:
            self.log("✗ 未找到可用的包管理器")
            self.root.after(0, lambda: messagebox.showerror(
                "安装失败",
                "未找到可用的包管理器（winget/choco/scoop）。\n\n请手动安装 FFmpeg。"
            ))
            self.root.after(0, lambda: self.ffmpeg_status_label.config(
                text="✗ 安装失败，请手动安装",
                fg="red"
            ))
            self.root.after(0, lambda: self.install_ffmpeg_btn.config(state='normal'))
            self.installing_ffmpeg = False
        except subprocess.TimeoutExpired:
            self.log("✗ 安装超时")
            self.root.after(0, lambda: messagebox.showerror("安装失败", "安装超时，请稍后重试"))
            self.root.after(0, lambda: self.ffmpeg_status_label.config(
                text="✗ 安装失败，请手动安装",
                fg="red"
            ))
            self.root.after(0, lambda: self.install_ffmpeg_btn.config(state='normal'))
            self.installing_ffmpeg = False
        except Exception as e:
            self.log(f"✗ 安装出错: {e}")
            self.root.after(0, lambda: messagebox.showerror("安装失败", f"安装出错: {e}"))
            self.root.after(0, lambda: self.ffmpeg_status_label.config(
                text="✗ 安装失败，请手动安装",
                fg="red"
            ))
            self.root.after(0, lambda: self.install_ffmpeg_btn.config(state='normal'))
            self.installing_ffmpeg = False
    
    def _install_from_local_package(self, local_dir):
        """从本地安装包安装 FFmpeg 到 D 盘并配置环境变量"""
        try:
            # 目标路径：D:\ffmpeg-8.0-essentials_build
            target_dir = r"D:\ffmpeg-8.0-essentials_build"
            bin_dir = os.path.join(target_dir, "bin")
            
            # 检查 D 盘是否存在
            if not os.path.exists("D:\\"):
                self.log("✗ D 盘不存在，无法安装")
                return False
            
            # 如果目标目录已存在，检查是否可用
            if os.path.exists(target_dir):
                if os.path.exists(bin_dir) and os.path.exists(os.path.join(bin_dir, "ffmpeg.exe")):
                    self.log(f"目标目录已存在且可用: {target_dir}")
                    # 直接配置环境变量即可
                    if self._add_to_path(bin_dir):
                        self.log("✓ 环境变量配置成功")
                        return True
                    else:
                        self.log("✗ 环境变量配置失败")
                        return False
                else:
                    self.log(f"目标目录已存在但无效，正在删除: {target_dir}")
                    try:
                        shutil.rmtree(target_dir)
                    except Exception as e:
                        self.log(f"删除旧目录失败: {e}")
                        return False
            
            # 复制文件夹到 D 盘
            self.log(f"正在复制 FFmpeg 到 D 盘: {target_dir}")
            try:
                shutil.copytree(local_dir, target_dir)
                self.log(f"✓ 复制完成")
            except Exception as e:
                self.log(f"✗ 复制失败: {e}")
                return False
            
            # 检查 bin 目录是否存在
            if not os.path.exists(bin_dir):
                self.log(f"✗ bin 目录不存在: {bin_dir}")
                return False
            
            # 配置环境变量
            self.log("正在配置环境变量...")
            if self._add_to_path(bin_dir):
                self.log("✓ 环境变量配置成功")
                return True
            else:
                self.log("✗ 环境变量配置失败")
                return False
                
        except Exception as e:
            self.log(f"✗ 安装过程出错: {e}")
            import traceback
            self.log(traceback.format_exc())
            return False
    
    def _add_to_path(self, bin_dir):
        """将目录添加到系统 PATH 环境变量"""
        try:
            # 先尝试添加到用户环境变量（不需要管理员权限，更安全）
            try:
                user_key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Environment",
                    0,
                    winreg.KEY_ALL_ACCESS
                )
                try:
                    current_path, _ = winreg.QueryValueEx(user_key, "Path")
                except FileNotFoundError:
                    current_path = ""
                
                path_list = current_path.split(os.pathsep) if current_path else []
                if bin_dir not in path_list:
                    if current_path:
                        new_path = current_path + os.pathsep + bin_dir
                    else:
                        new_path = bin_dir
                    winreg.SetValueEx(user_key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                    winreg.CloseKey(user_key)
                    return True
                else:
                    winreg.CloseKey(user_key)
                    return True
            except Exception as e:
                # 如果用户环境变量配置失败，尝试系统环境变量
                pass
            
            # 尝试打开系统环境变量注册表项（需要管理员权限）
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                0,
                winreg.KEY_ALL_ACCESS
            )
            
            # 读取当前的 PATH 值
            try:
                current_path, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                current_path = ""
            
            # 检查是否已经存在
            path_list = current_path.split(os.pathsep) if current_path else []
            if bin_dir in path_list:
                self.log("PATH 中已包含该目录")
                winreg.CloseKey(key)
                return True
            
            # 添加到 PATH
            if current_path:
                new_path = current_path + os.pathsep + bin_dir
            else:
                new_path = bin_dir
            
            # 写入新的 PATH 值
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
            winreg.CloseKey(key)
            
            # 通知系统环境变量已更改
            self.refresh_environment()
            
            return True
            
        except PermissionError:
            # 权限不足，已经尝试过用户环境变量了，直接返回 False
            return False
        except Exception as e:
            self.log(f"✗ 配置环境变量出错: {e}")
            import traceback
            self.log(traceback.format_exc())
            return False
    
    def _configure_path_in_thread(self, bin_dir):
        """在后台线程中配置 PATH 环境变量"""
        try:
            if self._add_to_path(bin_dir):
                self.root.after(0, lambda: self.log("✓ 环境变量配置完成"))
                # 刷新环境变量（在后台线程中执行，避免阻塞）
                self.refresh_environment()
            else:
                self.root.after(0, lambda: self.log("⚠ 环境变量配置失败，但可以使用完整路径运行"))
        except Exception as e:
            self.root.after(0, lambda: self.log(f"⚠ 配置环境变量时出错: {e}"))
    
    def refresh_environment(self):
        """刷新环境变量（Windows）"""
        if sys.platform == 'win32':
            try:
                # 重新加载环境变量
                import ctypes
                from ctypes import wintypes
                
                # 通知系统环境变量已更改（使用异步方式，避免阻塞）
                try:
                    user32 = ctypes.windll.user32
                    user32.SendMessageW(
                        wintypes.HWND(-1),  # HWND_BROADCAST
                        0x001A,  # WM_SETTINGCHANGE
                        0,
                        'Environment'
                    )
                except Exception:
                    # 如果 SendMessageW 失败，不影响程序运行
                    pass
            except Exception as e:
                # 刷新环境变量失败不影响程序运行
                pass
    
    def select_input_file(self):
        """选择输入文件"""
        filename = filedialog.askopenfilename(
            title="选择 M3U8 文件",
            filetypes=[
                ("M3U8 文件", "*.m3u8"),
                ("所有文件", "*.*")
            ]
        )
        if filename:
            self.input_file = filename
            self.input_entry.config(state='normal')
            self.input_entry.delete(0, 'end')
            self.input_entry.insert(0, filename)
            self.input_entry.config(state='readonly')
            # 自动生成输出文件名
            self._update_output_filename(filename)
            self.update_convert_button_state()
            self.log(f"已选择输入文件: {filename}")
    
    def select_input_folder(self):
        """选择输入文件夹（自动查找 m3u8 文件）"""
        folder = filedialog.askdirectory(
            title="选择包含 M3U8 文件的文件夹"
        )
        if folder:
            # 在文件夹中查找 m3u8 文件
            m3u8_file = self._find_m3u8_in_folder(folder)
            if m3u8_file:
                self.input_file = m3u8_file
                self.input_entry.config(state='normal')
                self.input_entry.delete(0, 'end')
                self.input_entry.insert(0, m3u8_file)
                self.input_entry.config(state='readonly')
                # 保存输出文件夹路径，用于生成输出文件名
                self.output_folder_path = folder
                # 自动生成输出文件名（基于文件夹名）
                self._update_output_filename_from_folder(folder)
                self.update_convert_button_state()
                self.log(f"已选择文件夹: {folder}")
                self.log(f"找到 M3U8 文件: {m3u8_file}")
            else:
                messagebox.showwarning(
                    "未找到文件",
                    f"在文件夹中未找到 M3U8 文件:\n{folder}\n\n请确保文件夹中包含 .m3u8 文件"
                )
                self.log(f"在文件夹中未找到 M3U8 文件: {folder}")
    
    def _find_m3u8_in_folder(self, folder):
        """在文件夹中查找 m3u8 文件"""
        # 优先查找 index.m3u8
        index_m3u8 = os.path.join(folder, "index.m3u8")
        if os.path.exists(index_m3u8):
            return index_m3u8
        
        # 查找所有 .m3u8 文件
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith('.m3u8'):
                    return os.path.join(root, file)
        
        return None
    
    def _update_output_filename(self, input_path):
        """根据输入文件路径自动更新输出文件名"""
        # 获取输入文件的目录和文件名（不含扩展名）
        input_dir = os.path.dirname(input_path)
        input_name = os.path.splitext(os.path.basename(input_path))[0]
        
        # 生成输出文件路径
        output_name = f"{input_name}.mp4"
        output_path = os.path.join(input_dir, output_name)
        
        # 更新输出文件输入框
        self.output_entry.delete(0, 'end')
        self.output_entry.insert(0, output_path)
        self.log(f"自动设置输出文件: {output_path}")
    
    def _update_output_filename_from_folder(self, folder_path):
        """根据输入文件夹路径自动更新输出文件名"""
        # 获取文件夹名（不含路径）
        folder_name = os.path.basename(folder_path)
        
        # 如果文件夹名以 .m3u8 结尾，去掉这个后缀
        if folder_name.lower().endswith('.m3u8'):
            folder_name = folder_name[:-5]  # 去掉 .m3u8
        
        # 生成输出文件路径（保存在输入文件夹的父目录）
        parent_dir = os.path.dirname(folder_path)
        output_name = f"{folder_name}.mp4"
        output_path = os.path.join(parent_dir, output_name)
        
        # 更新输出文件输入框
        self.output_entry.delete(0, 'end')
        self.output_entry.insert(0, output_path)
        self.log(f"自动设置输出文件: {output_path}")
    
    def _delete_source_files(self, input_path):
        """删除源文件或源文件夹"""
        try:
            # 如果之前选择了文件夹，删除整个文件夹
            if self.output_folder_path and os.path.exists(self.output_folder_path):
                self.log(f"正在删除源文件夹: {self.output_folder_path}")
                try:
                    shutil.rmtree(self.output_folder_path)
                    self.log(f"✓ 源文件夹已删除: {self.output_folder_path}")
                except Exception as e:
                    self.log(f"✗ 删除源文件夹失败: {e}")
            # 否则只删除 m3u8 文件
            elif os.path.exists(input_path) and os.path.isfile(input_path):
                self.log(f"正在删除源文件: {input_path}")
                try:
                    os.remove(input_path)
                    self.log(f"✓ 源文件已删除: {input_path}")
                except Exception as e:
                    self.log(f"✗ 删除源文件失败: {e}")
        except Exception as e:
            self.log(f"✗ 删除源文件时出错: {e}")
    
    def select_output_file(self):
        """选择输出文件"""
        filename = filedialog.asksaveasfilename(
            title="保存 MP4 文件",
            defaultextension=".mp4",
            filetypes=[
                ("MP4 文件", "*.mp4"),
                ("所有文件", "*.*")
            ]
        )
        if filename:
            self.output_file = filename
            self.output_entry.delete(0, 'end')
            self.output_entry.insert(0, filename)
            self.log(f"已选择输出文件: {filename}")
    
    def update_convert_button_state(self):
        """更新转换按钮状态"""
        if self.ffmpeg_installed and self.input_file:
            self.convert_btn.config(state='normal')
        else:
            self.convert_btn.config(state='disabled')
    
    def start_conversion(self):
        """开始转换"""
        if not self.ffmpeg_installed:
            messagebox.showerror("错误", "FFmpeg 未安装，无法转换")
            return
        
        self.input_file = self.input_entry.get()
        self.output_file = self.output_entry.get()
        
        if not self.input_file:
            messagebox.showerror("错误", "请选择输入文件")
            return
        
        if not self.output_file:
            messagebox.showerror("错误", "请指定输出文件")
            return
        
        if not os.path.exists(self.input_file):
            messagebox.showerror("错误", f"输入文件不存在: {self.input_file}")
            return
        
        # 禁用按钮
        self.convert_btn.config(state='disabled')
        self.status_label.config(text="正在转换...", fg="blue")
        self.progress_line_label.config(text="进度：0.0% | 预计剩余：计算中...", fg="blue")
        
        # 在后台线程中转换
        thread = threading.Thread(target=self._convert_thread)
        thread.daemon = True
        thread.start()
    
    def _convert_thread(self):
        """在后台线程中执行转换"""
        try:
            input_path = os.path.abspath(self.input_file)
            output_path = os.path.abspath(self.output_file)
            
            self.log(f"\n开始转换...")
            self.log(f"输入文件: {input_path}")
            self.log(f"输出文件: {output_path}")
            
            # 预估总时长（优先从 m3u8 汇总 EXTINF，其次尝试 ffprobe）
            total_duration_sec = self._estimate_duration_seconds(input_path)
            if total_duration_sec:
                self.root.after(0, lambda: self.progress_line_label.config(
                    text=f"进度：0.0% | 预计剩余：--:--:-- (总时长 {self._format_hhmmss(total_duration_sec)})",
                    fg="blue"
                ))
            else:
                self.root.after(0, lambda: self.progress_line_label.config(
                    text="进度：--% | 预计剩余：--:--:-- (正在解析总时长)",
                    fg="blue"
                ))

            # 获取 ffmpeg 路径（优先使用完整路径，如果环境变量未生效也能工作）
            if self.ffmpeg_path and os.path.exists(self.ffmpeg_path):
                ffmpeg_cmd = self.ffmpeg_path
            else:
                # 尝试从 PATH 中查找
                ffmpeg_cmd = shutil.which('ffmpeg') or 'ffmpeg'
            
            # 构建 ffmpeg 命令
            cmd = [
                ffmpeg_cmd,
                '-i', input_path,
                '-c', 'copy',
                '-bsf:a', 'aac_adtstoasc',
                '-y',  # 覆盖输出文件
                output_path
            ]
            
            self.log(f"执行命令: {' '.join(cmd)}")
            
            # 执行转换
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            # 实时读取输出
            start_wall = time.time()
            last_update_ts = 0.0
            progress_time_sec = 0.0
            while True:
                output = process.stderr.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self.log(output.strip())
                    # 解析 ffmpeg 进度时间字段，如 time=00:01:23.45
                    match = re.search(r"time=(\d{2}):(\d{2}):(\d{2})(?:[\.,](\d{1,2}))?", output)
                    if match:
                        hh = int(match.group(1))
                        mm = int(match.group(2))
                        ss = int(match.group(3))
                        ff = match.group(4)
                        frac = (int(ff) / (10 ** len(ff))) if ff else 0.0
                        progress_time_sec = hh * 3600 + mm * 60 + ss + frac

                        # 若总时长未知，尝试从 ffprobe 获取一次
                        if not total_duration_sec:
                            total_duration_sec = self._probe_duration_seconds(input_path)

                        now = time.time()
                        if now - last_update_ts >= 0.5:
                            last_update_ts = now
                            if total_duration_sec and total_duration_sec > 0:
                                ratio = min(max(progress_time_sec / total_duration_sec, 0.0), 1.0)
                                percent = ratio * 100.0
                                elapsed_wall = now - start_wall
                                eta_sec = int(elapsed_wall * (1.0 / ratio - 1.0)) if ratio > 0 else 0
                                self.root.after(0, lambda p=percent, e=eta_sec, t=total_duration_sec: self.progress_line_label.config(
                                    text=f"进度：{p:.1f}% | 预计剩余：{self._format_hhmmss(e)} (总时长 {self._format_hhmmss(t)})",
                                    fg="blue"
                                ))
                            else:
                                self.root.after(0, lambda pt=progress_time_sec: self.progress_line_label.config(
                                    text=f"已处理：{self._format_hhmmss(int(pt))} | 正在估算总时长...",
                                    fg="blue"
                                ))
            
            returncode = process.poll()
            
            if returncode == 0:
                self.log("\n✓ 转换成功！")
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    size_mb = file_size / (1024 * 1024)
                    self.log(f"输出文件大小: {size_mb:.2f} MB")
                
                # 删除源文件
                self._delete_source_files(input_path)
                
                # 完成时将进度显示为 100%
                self.root.after(0, lambda: self.progress_line_label.config(
                    text="进度：100.0% | 预计剩余：00:00:00",
                    fg="green"
                ))
                
                self.root.after(0, lambda: messagebox.showinfo(
                    "转换成功",
                    f"转换完成！\n\n输出文件: {output_path}\n\n源文件已删除。"
                ))
                self.root.after(0, lambda: self.status_label.config(
                    text="转换成功！", fg="green"
                ))
            else:
                error_msg = process.stderr.read()
                self.log(f"\n✗ 转换失败 (返回码: {returncode})")
                self.log(f"错误信息: {error_msg}")
                self.root.after(0, lambda: messagebox.showerror(
                    "转换失败",
                    f"转换失败，请查看日志了解详情。"
                ))
                self.root.after(0, lambda: self.status_label.config(
                    text="转换失败", fg="red"
                ))
        
        except Exception as e:
            self.log(f"\n✗ 转换出错: {e}")
            self.root.after(0, lambda: messagebox.showerror(
                "转换失败",
                f"转换出错: {e}"
            ))
            self.root.after(0, lambda: self.status_label.config(
                text="转换失败", fg="red"
            ))
        
        finally:
            # 恢复按钮状态
            self.root.after(0, lambda: self.convert_btn.config(state='normal'))
            self.root.after(0, lambda: self.update_convert_button_state())

    def _format_hhmmss(self, seconds):
        seconds = int(max(0, seconds))
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _estimate_duration_seconds(self, input_path):
        """尝试从 m3u8 文件汇总 #EXTINF 得到总时长，失败则返回 None"""
        try:
            if os.path.isfile(input_path) and input_path.lower().endswith('.m3u8'):
                total = 0.0
                with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('#EXTINF:'):
                            # 格式: #EXTINF:10.000,
                            try:
                                val = line.split(':', 1)[1]
                                val = val.split(',')[0]
                                total += float(val)
                            except Exception:
                                continue
                return int(total) if total > 0 else None
        except Exception:
            pass
        # 退化到 ffprobe
        return self._probe_duration_seconds(input_path)

    def _probe_duration_seconds(self, input_path):
        """通过 ffprobe 读取总时长，失败返回 None"""
        try:
            # 获取 ffprobe 路径（优先使用完整路径）
            if self.ffmpeg_path:
                ffprobe_path = self.ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe')
                if not os.path.exists(ffprobe_path):
                    ffprobe_path = 'ffprobe'
            else:
                ffprobe_path = shutil.which('ffprobe') or 'ffprobe'
            
            result = subprocess.run(
                [ffprobe_path, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', input_path],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=10
            )
            if result.returncode == 0:
                val = result.stdout.strip()
                if val:
                    dur = float(val)
                    return int(dur) if dur > 0 else None
        except Exception:
            return None
        return None


def main():
    root = Tk()
    app = M3U8ConverterGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()

