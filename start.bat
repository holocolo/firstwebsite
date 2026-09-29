@echo off
chcp 65001 >nul
title 个人主页本地服务
cd /d "%~dp0"

echo.
echo ============================================================
echo   个人主页本地服务
echo ============================================================
echo.

set "PY=C:\Users\Admin\.workbuddy\binaries\python\envs\default\Scripts\python.exe"

if not exist "%PY%" (
  echo [错误] 找不到 Python：
  echo   %PY%
  echo.
  echo 请把 start.bat 里的 PY 变量改成你本机 python.exe 的完整路径。
  echo.
  pause
  exit /b 1
)

rem ---- 检查两个 Key（只做提示，不阻塞启动；server.py 内部还会从注册表兜底读一次）----
set "MISSING="
if "%REPLICATE_API_TOKEN%"=="" set "MISSING=%MISSING% REPLICATE_API_TOKEN"
if "%OPENROUTER_API_KEY%"=="" set "MISSING=%MISSING% OPENROUTER_API_KEY"

if not "%MISSING%"=="" (
  echo [提示] 当前窗口没有检测到这些环境变量：%MISSING%
  echo        天气功能不受影响，但对应的功能会报错。
  echo.
  echo        如果之前用 setx 设置过，服务仍可能正常读到（内置了注册表兜底）。
  echo        若确实没设过，在 PowerShell 里执行一次（永久生效）：
  echo            setx REPLICATE_API_TOKEN "r8_你的token"
  echo            setx OPENROUTER_API_KEY "sk-or-v1-你的key"
  echo.
  echo        Key 申请地址：
  echo            https://replicate.com/account/api-tokens
  echo            https://openrouter.ai/keys
  echo.
  echo        现在按任意键继续启动...
  pause >nul
)

echo 正在启动服务，浏览器将自动打开 http://127.0.0.1:8000
echo 关闭本窗口即可停止服务。
echo.

rem 3 秒后自动打开浏览器
start "" /b cmd /c "timeout /t 3 >nul & start http://127.0.0.1:8000"

"%PY%" server.py

echo.
echo 服务已停止。
pause
