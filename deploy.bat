@echo off
chcp 65001
echo ========================================
echo CBT情绪日记游戏 - 部署脚本
echo ========================================
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo [1/5] 检查虚拟环境...
if not exist venv (
    echo 创建虚拟环境...
    python -m venv venv
)

echo [2/5] 激活虚拟环境...
call venv\Scripts\activate.bat

echo [3/5] 安装依赖包...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo [4/5] 检查环境配置...
if not exist .env (
    echo [警告] 未找到.env文件，请创建.env文件并配置环境变量
    echo 参考.env.example文件
    pause
    exit /b 1
)

echo [5/5] 检查数据库连接...
python -c "from app import app, db; app.app_context().push(); db.engine.connect(); print('[成功] 数据库连接正常')"
if errorlevel 1 (
    echo [错误] 数据库连接失败，请检查.env中的DATABASE_URL配置
    pause
    exit /b 1
)

echo.
echo ========================================
echo 部署完成！
echo ========================================
echo.
echo 启动应用请运行: start.bat
echo.
pause
