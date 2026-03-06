@echo off
:: 解决中文乱码问题
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 路径设置
set "EXE_PATH=%~dp0DailyPaperTracker.exe"
set "CFG_PATH=%~dp0config.yaml"

if not exist "%CFG_PATH%" (
    echo [错误] 找不到配置文件: %CFG_PATH%
    pause
    exit /b
)

:: 提取时间并去除所有引号（单引号和双引号）
set "RUN_TIME="
for /f "tokens=2,3 delims=: " %%a in ('findstr "schedule_time" "%CFG_PATH%"') do (
    set "H=%%a"
    set "M=%%b"
    :: 去除单引号
    set "H=!H:'=!"
    set "M=!M:'=!"
    :: 去除双引号
    set "H=!H:"=!"
    set "M=!M:"=!"
    set "RUN_TIME=!H!:!M!"
)

:: 如果提取失败，设置默认值
if "!RUN_TIME!"=="" set "RUN_TIME=09:00"

echo ============================================
echo [检测] 程序路径: %EXE_PATH%
echo [检测] 设定时间: !RUN_TIME!
echo ============================================

echo 正在清理旧任务（如有）...
schtasks /delete /tn "DailyPaperTracker" /f >nul 2>&1

echo 正在创建新的 Windows 定时任务...
:: 使用引号包裹路径以防止空格导致失败，但时间必须是纯净的
schtasks /create /tn "DailyPaperTracker" /tr "'%EXE_PATH%' --task" /sc daily /st !RUN_TIME! /f

if !errorlevel! equ 0 (
    echo.
    echo [成功] 定时任务已同步！程序将在每天 !RUN_TIME! 自动运行。
    echo 提示：您可以关闭此窗口，任务已在后台生效。
) else (
    echo.
    echo [失败] 定时任务创建失败。
    echo 请检查：
    echo 1. 是否确实右键点击并选择了“以管理员身份运行”。
    echo 2. 时间格式是否正确（当前提取值为: !RUN_TIME!）。
)

echo.
pause