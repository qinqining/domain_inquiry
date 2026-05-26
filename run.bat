@echo off
chcp 65001 >nul
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
) else (
  where python >nul 2>&1
  if errorlevel 1 (
    echo [错误] 未找到 Python。请先双击 setup_windows.bat 完成安装。
    echo 或从 https://www.python.org/downloads/ 安装并勾选 Add to PATH
    pause
    exit /b 1
  )
  set "PY=python"
  echo [提示] 建议先运行 setup_windows.bat 创建虚拟环境
)

"%PY%" main.py run
if errorlevel 1 pause
