# M3U8 转 MP4 转换说明

## 方法一：使用 FFmpeg（推荐）

### 安装 FFmpeg

#### 方法 A：使用包管理器（最简单）

如果你安装了 **Chocolatey**：
```powershell
choco install ffmpeg
```

如果你安装了 **Scoop**：
```powershell
scoop install ffmpeg
```

#### 方法 B：手动安装

1. 访问 https://www.gyan.dev/ffmpeg/builds/ 下载 FFmpeg
2. 选择 "ffmpeg-release-essentials.zip" 下载
3. 解压到任意目录（如 `C:\ffmpeg`）
4. 将 `C:\ffmpeg\bin` 添加到系统 PATH 环境变量
5. 重新打开命令行窗口

### 使用方法

安装 ffmpeg 后，双击运行 `convert_m3u8_to_mp4.bat` 或在命令行执行：

```powershell
python convert_m3u8_to_mp4.py
```

或直接使用 ffmpeg 命令：

```powershell
ffmpeg -i "ed2db3d.comvideo122722.m3u8\index.m3u8" -c copy -bsf:a aac_adtstoasc -y output.mp4
```

## 方法二：使用 Python 脚本（需要先安装 ffmpeg）

即使使用 Python 脚本，底层仍然需要 ffmpeg。所以请先按照方法一安装 ffmpeg。

## 转换说明

- **输入文件**：`ed2db3d.comvideo122722.m3u8\index.m3u8`
- **输出文件**：`output.mp4`
- **转换方式**：使用 `-c copy` 参数，直接复制流，不重新编码，速度快且质量无损

## 注意事项

1. 确保所有 `.ts` 文件都在 `index` 目录下
2. 转换过程可能需要几分钟，取决于视频大小
3. 如果转换失败，请检查：
   - ffmpeg 是否正确安装
   - 所有 .ts 文件是否完整
   - 磁盘空间是否充足

## 快速安装 FFmpeg（Windows）

如果上述方法都不方便，可以：

1. 访问 https://github.com/BtbN/FFmpeg-Builds/releases
2. 下载最新的 `ffmpeg-master-latest-win64-gpl.zip`
3. 解压到 `C:\ffmpeg`
4. 在 PowerShell（管理员）中执行：
   ```powershell
   [Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\ffmpeg\bin", [EnvironmentVariableTarget]::Machine)
   ```
5. 重新打开命令行窗口


