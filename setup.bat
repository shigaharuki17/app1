@echo off
chcp 65001 >nul
cd /d "%~dp0"
py -3.14 --version
if errorlevel 1 (
    echo 请先安装 Python 3.14，并确保 py 命令可用。
    pause
    exit /b 1
)
if not exist ".venv\Scripts\python.exe" py -3.14 -m venv .venv
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo 安装失败，请检查上面的错误信息。
    pause
    exit /b 1
)
echo 环境已就绪。配置 .env 后，双击 run.bat 启动。
pause
