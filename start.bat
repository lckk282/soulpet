@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title SoulPet 启动器

set ROOT=%~dp0
cd /d "%ROOT%"

echo.
echo   SoulPet - 你的私有 AI 宠物
echo   ----------------------------------------

REM 1) 找 Python
set PY=
where python >nul 2>nul && set PY=python
if "!PY!"=="" (
  where py >nul 2>nul && set PY=py
)
if "!PY!"=="" (
  echo   [x] 没检测到 Python。请先安装 Python 3.11 及以上：https://www.python.org/downloads/
  echo       安装时记得勾选 "Add Python to PATH"
  pause
  exit /b 1
)

for /f "tokens=*" %%v in ('!PY! -c "import sys;print(sys.version_info.major*100+sys.version_info.minor)"') do set V=%%v
if !V! LSS 311 (
  echo   [x] Python 版本过低（当前 !V!）。请升级到 3.11 及以上。
  pause
  exit /b 1
)
echo   [1/4] Python 就绪

REM 2) 依赖
if not exist ".venv\Scripts\python.exe" (
  echo   [2/4] 首次运行，正在准备虚拟环境（约 1-3 分钟）...
  !PY! -m venv .venv
  if errorlevel 1 (
    echo   [x] 创建虚拟环境失败
    pause
    exit /b 1
  )
  ".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt
  if errorlevel 1 (
    echo   [x] 依赖安装失败，请检查网络后重试
    pause
    exit /b 1
  )
) else (
  echo   [2/4] 虚拟环境已存在
)

REM 3) 启动
echo   [3/4] 正在拉起服务，浏览器会自动弹出...
echo         关闭服务请运行 stop.bat 或直接关掉本窗口
echo.
".venv\Scripts\python.exe" launcher\launcher.py %*

echo.
echo   服务已停止。
pause
endlocal
