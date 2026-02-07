@echo off
chcp 65001
echo ========================================
echo CBT情绪日记游戏 - 启动服务
echo ========================================
echo.

:: 检查虚拟环境
if not exist venv (
    echo [错误] 未找到虚拟环境，请先运行 deploy.bat 进行部署
    pause
    exit /b 1
)

:: 激活虚拟环境
call venv\Scripts\activate.bat

:: 检查环境配置
if not exist .env (
    echo [错误] 未找到.env文件，请创建.env文件并配置环境变量
    pause
    exit /b 1
)

:: 获取端口配置
set PORT=5000
for /f "tokens=2 delims==" %%a in ('findstr "^PORT=" .env') do set PORT=%%a

echo [启动] 正在启动Flask应用...
echo [信息] 访问地址: http://localhost:%PORT%
echo [信息] 按 Ctrl+C 停止服务
echo.

:: 启动应用（开发模式）
python app.py

pause
