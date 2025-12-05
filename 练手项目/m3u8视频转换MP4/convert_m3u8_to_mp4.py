#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 m3u8 文件转换为 MP4 视频
需要安装 ffmpeg-python: pip install ffmpeg-python
或者使用 subprocess 直接调用 ffmpeg
"""

import os
import subprocess
import sys

def convert_m3u8_to_mp4(m3u8_path, output_path):
    """
    使用 ffmpeg 将 m3u8 转换为 MP4
    """
    # 获取 m3u8 文件的绝对路径
    m3u8_abs_path = os.path.abspath(m3u8_path)
    
    # 检查 m3u8 文件是否存在
    if not os.path.exists(m3u8_abs_path):
        print(f"错误：找不到文件 {m3u8_abs_path}")
        return False
    
    # 构建 ffmpeg 命令
    # -i: 输入文件
    # -c copy: 直接复制流（不重新编码，速度快）
    # -bsf:a aac_adtstoasc: 处理音频流（如果需要）
    # -y: 覆盖输出文件（如果存在）
    cmd = [
        'ffmpeg',
        '-i', m3u8_abs_path,
        '-c', 'copy',
        '-bsf:a', 'aac_adtstoasc',
        '-y',  # 覆盖输出文件
        output_path
    ]
    
    print(f"正在转换: {m3u8_abs_path} -> {output_path}")
    print(f"执行命令: {' '.join(cmd)}")
    
    try:
        # 执行转换
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        print("转换成功！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"转换失败: {e}")
        if e.stderr:
            print(f"错误信息: {e.stderr}")
        return False
    except FileNotFoundError:
        print("错误：找不到 ffmpeg。请先安装 ffmpeg。")
        print("下载地址: https://ffmpeg.org/download.html")
        print("或使用包管理器安装:")
        print("  - Windows: choco install ffmpeg 或 scoop install ffmpeg")
        print("  - 或下载后解压，将 bin 目录添加到 PATH")
        return False

if __name__ == '__main__':
    # 默认路径
    m3u8_file = r'ed2db3d.comvideo122722.m3u8\index.m3u8'
    output_file = 'output.mp4'
    
    # 如果提供了命令行参数，使用参数
    if len(sys.argv) > 1:
        m3u8_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    success = convert_m3u8_to_mp4(m3u8_file, output_file)
    sys.exit(0 if success else 1)


