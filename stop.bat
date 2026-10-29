@echo off
chcp 65001 >nul
setlocal
set ROOT=%~dp0
cd /d "%ROOT%"

if exist "data\backend.pid" (
  set /p PID=<data\backend.pid
  if defined PID (
    echo 正在停止 SoulPet（pid=!PID!）...
    taskkill /PID !PID! /T /F >nul 2>nul
    del /q data\backend.pid >nul 2>nul
    echo 已停止。
  ) else (
    echo 未找到进程号。
  )
) else (
  echo 未找到 data\backend.pid，可能服务未运行。
)
endlocal
