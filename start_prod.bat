@echo off
chcp 65001
echo ========================================
echo CBT情绪日记游戏 - 生产环境启动
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

echo [启动] 正在使用Gunicorn启动应用...
echo [信息] 访问地址: http://localhost:%PORT%
echo [信息] 工作进程: 4
echo [信息] 按 Ctrl+C 停止服务
echo.

:: 使用Gunicorn启动（生产模式）
gunicorn -w 4 -b 0.0.0.0:%PORT% --timeout 120 --access-logfile - --error-logfile - app:app

pause
