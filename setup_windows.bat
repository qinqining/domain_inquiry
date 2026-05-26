@echo off
chcp 65001 >nul
setlocal EnableExtensions

:: 在仓库根目录执行（与 run.bat 同级）
cd /d "%~dp0"
set "ROOT=%CD%"

echo ==================================================
echo   domain_inquiry · Windows 首次安装
echo ==================================================
echo 项目目录: %ROOT%
echo.

:: ---------- 1. 检查 Python ----------
where python >nul 2>&1
if errorlevel 1 (
  echo [错误] 未找到 Python。请先安装 Python 3.10 或更高版本：
  echo   https://www.python.org/downloads/
  echo 安装时务必勾选 「Add python.exe to PATH」
  echo.
  pause
  exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
echo [OK] 已检测到 Python %PYVER%

:: ---------- 2. 虚拟环境 + 依赖 ----------
if not exist ".venv\Scripts\python.exe" (
  echo.
  echo [安装] 创建虚拟环境 .venv ...
  python -m venv .venv
  if errorlevel 1 (
    echo [错误] 创建虚拟环境失败
    pause
    exit /b 1
  )
)

echo [安装] 安装依赖包 ...
".venv\Scripts\python.exe" -m pip install -q --upgrade pip
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo [错误] pip 安装失败，请检查网络
  pause
  exit /b 1
)
echo [OK] 依赖安装完成

:: ---------- 3. 配置文件 ----------
if not exist ".env" (
  copy /y ".env.example" ".env" >nul
  echo.
  echo [重要] 已生成 .env ，请用记事本填写：
  echo   - ALIYUN_ACCESS_KEY_ID / SECRET
  echo   - DEEPSEEK_API_KEY
  echo 文件位置: %ROOT%\.env
  echo.
  set /p "OPENENV=是否现在打开 .env 编辑？(Y/n): "
  if /i not "%OPENENV%"=="n" notepad "%ROOT%\.env"
) else (
  echo [OK] 已存在 .env ，跳过
)

:: ---------- 4. 桌面快捷启动 ----------
set "DESKTOP=%USERPROFILE%\Desktop"
if exist "%USERPROFILE%\OneDrive\Desktop\" set "DESKTOP=%USERPROFILE%\OneDrive\Desktop"

set "LAUNCHER=%DESKTOP%\域名工具.bat"
(
  echo @echo off
  echo chcp 65001 ^>nul
  echo cd /d "%ROOT%"
  echo if not exist ".venv\Scripts\python.exe" ^(
  echo   echo 请先双击运行项目里的 setup_windows.bat 完成安装
  echo   pause
  echo   exit /b 1
  echo ^)
  echo ".venv\Scripts\python.exe" main.py run
  echo if errorlevel 1 pause
) > "%LAUNCHER%"

echo.
echo ==================================================
echo   安装完成
echo ==================================================
echo 桌面已创建: %LAUNCHER%
echo 以后双击「域名工具」即可使用。
echo.
echo 若移动了项目文件夹，请重新运行本 setup_windows.bat
echo ==================================================
pause
endlocal
