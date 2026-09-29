@echo off
REM ============================================================
REM  日常推送脚本（不含任何 token，可安全留在仓库里）
REM
REM  首次使用需先设置一次 token（只存到本机 git 凭据管理器，不进仓库）：
REM      git config --global credential.helper manager
REM      然后任意 push 一次，按提示输入用户名 + token 作为密码
REM
REM  用法：双击本文件即可
REM ============================================================
setlocal

set "GIT=C:\Users\Admin\.workbuddy\binaries\PortableGit\versions\1.2.0\mingw64\bin\git.exe"
set "EXEC=C:\Users\Admin\.workbuddy\binaries\PortableGit\versions\1.2.0\mingw64\bin"
set "SRC=%~dp0"
set "PROXY=http://127.0.0.1:12450"

REM 这个 PortableGit 的 helper 不在默认 libexec 里，必须显式指定
set "GIT_EXEC_PATH=%EXEC%"

REM 清掉环境里那个失效的代理（64789），只用下面显式指定的可用代理
set "HTTP_PROXY="
set "HTTPS_PROXY="
set "http_proxy="
set "https_proxy="

cd /d "%SRC%"

set "MSG=%~1"
if "%MSG%"=="" set "MSG=update: 日常更新"

echo [1/3] 暂存改动 ...
"%GIT%" add -A

echo [2/3] 提交 ...
"%GIT%" commit -m "%MSG%"
if errorlevel 1 echo (没有新改动，继续推送)

echo [3/3] 推送 ...
"%GIT%" -c http.proxy="%PROXY%" -c http.version=HTTP/1.1 push origin main

if errorlevel 1 (
  echo.
  echo [FAIL] 推送失败。若提示认证，请先执行：
  echo     "%GIT%" config --global credential.helper manager
  echo   然后重跑本脚本，按提示输入用户名和 token。
) else (
  echo.
  echo [OK] 已推送到 https://github.com/holocolo/firstwebsite
)
pause
