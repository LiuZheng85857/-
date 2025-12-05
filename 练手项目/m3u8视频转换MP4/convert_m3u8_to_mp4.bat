@echo off
chcp 65001 >nul
echo 正在将 m3u8 转换为 MP4...
echo.

REM 检查 ffmpeg 是否可用
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误：找不到 ffmpeg
    echo 请先安装 ffmpeg
    echo 下载地址: https://ffmpeg.org/download.html
    echo 或使用包管理器安装:
    echo   - Windows: choco install ffmpeg 或 scoop install ffmpeg
    pause
    exit /b 1
)

REM 设置输入和输出文件路径
set INPUT_FILE=ed2db3d.comvideo122722.m3u8\index.m3u8
set OUTPUT_FILE=output.mp4

REM 检查输入文件是否存在
if not exist "%INPUT_FILE%" (
    echo 错误：找不到输入文件 %INPUT_FILE%
    pause
    exit /b 1
)

REM 转换为绝对路径
for %%F in ("%INPUT_FILE%") do set INPUT_FILE=%%~fF
for %%F in ("%OUTPUT_FILE%") do set OUTPUT_FILE=%%~fF

echo 输入文件: %INPUT_FILE%
echo 输出文件: %OUTPUT_FILE%
echo.

REM 执行转换
REM -i: 输入文件
REM -c copy: 直接复制流（不重新编码，速度快）
REM -bsf:a aac_adtstoasc: 处理音频流
REM -y: 覆盖输出文件（如果存在）
ffmpeg -i "%INPUT_FILE%" -c copy -bsf:a aac_adtstoasc -y "%OUTPUT_FILE%"

if %errorlevel% equ 0 (
    echo.
    echo 转换成功！
    echo 输出文件: %OUTPUT_FILE%
) else (
    echo.
    echo 转换失败，请检查错误信息
)

pause


