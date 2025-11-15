from flask import Flask, render_template, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from sqlalchemy import inspect, text
from urllib.parse import quote_plus

# 导入扩展和模型
from extensions import db, init_extensions
from models import User, EmotionDiary, EmotionAnalysis, GameState, GameProgress
from routes import auth_bp, diary_bp, upload_bp

# 加载环境变量
load_dotenv()

# 创建Flask应用
app = Flask(__name__)

# 基础配置
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')


def resolve_database_url():
    """根据环境动态解析数据库配置，Zeabur 默认走 MySQL。"""
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        return db_url

    # Zeabur 绑定的 MySQL 服务会注入这些变量
    mysql_host = os.getenv('MYSQL_HOST') or os.getenv('DB_HOST')
    mysql_port = os.getenv('MYSQL_PORT') or os.getenv('DB_PORT') or '3306'
    mysql_user = os.getenv('MYSQL_USER') or os.getenv('DB_USER')
    mysql_password = os.getenv('MYSQL_PASSWORD') or os.getenv('DB_PASSWORD')
    mysql_database = os.getenv('MYSQL_DATABASE') or os.getenv('DB_NAME')

    if all([mysql_host, mysql_user, mysql_password, mysql_database]):
        encoded_password = quote_plus(mysql_password)
        return f'mysql+pymysql://{mysql_user}:{encoded_password}@{mysql_host}:{mysql_port}/{mysql_database}?charset=utf8mb4'

    # 回退到本地 sqlite（开发/测试场景）
    sqlite_path = os.getenv('SQLITE_PATH', 'diary.db')
    return f'sqlite:///{sqlite_path}'


app.config['SQLALCHEMY_DATABASE_URI'] = resolve_database_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-string')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# 数据库配置优化 - 简化版本避免云端兼容性问题
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 5,
    'pool_recycle': 3600,
    'pool_pre_ping': True  # 添加连接检查
}

# 初始化扩展
init_extensions(app)


def ensure_schema_updates():
    """Ensure critical schema patches are applied when migrations haven't run."""
    schema_updates = {
        'users': {
            'reset_token': 'VARCHAR(255)',
            'reset_token_expires': 'DATETIME'
        },
        'emotion_diaries': {
            'trigger_event': 'TEXT',
            'images': 'JSON'
        },
        'emotion_analysis': {
            'analysis_payload': 'JSON'
        }
    }

    try:
        with app.app_context():
            inspector = inspect(db.engine)
            existing_tables = set(inspector.get_table_names())

            engine_name = db.engine.url.get_backend_name()

            for table_name, columns in schema_updates.items():
                if table_name not in existing_tables:
                    continue

                existing_columns = {col['name'] for col in inspector.get_columns(table_name)}
                missing = {
                    column_name: column_type
                    for column_name, column_type in columns.items()
                    if column_name not in existing_columns
                }

                if not missing:
                    continue

                with db.engine.begin() as connection:
                    for column_name, column_type in missing.items():
                        column_type_sql = column_type
                        if column_type.upper() == 'JSON' and engine_name == 'sqlite':
                            column_type_sql = 'TEXT'

                        connection.execute(
                            text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type_sql}')
                        )
    except Exception as schema_error:
        app.logger.warning(f"Schema check failed: {schema_error}")


ensure_schema_updates()

# 注册蓝图
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(diary_bp, url_prefix='/api/diary')
app.register_blueprint(upload_bp, url_prefix='/api')

# 主页路由
@app.route('/')
def index():
    return render_template('index.html')

# 登录页面路由
@app.route('/login')
def login_page():
    return render_template('login.html')

# 注册页面路由
@app.route('/register')
def register_page():
    return render_template('register.html')

# 重置密码页面路由
@app.route('/reset-password/<token>')
def reset_password_page(token):
    return render_template('reset_password.html', token=token)

# 健康检查API
@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })


# 页面路由（不需要JWT验证，前端JavaScript会检查登录状态）
@app.route('/profile')
def profile():
    """个人资料页面"""
    return render_template('profile.html')

@app.route('/diary')
def diary_list():
    """日记列表页面"""
    return render_template('diary_list.html')

@app.route('/diary/new')
def diary_new():
    """写新日记页面（步骤式引导）"""
    return render_template('diary_new.html')

@app.route('/diary/<int:diary_id>')
def diary_detail(diary_id):
    """日记详情页面"""
    return render_template('diary_detail.html', diary_id=diary_id)

@app.route('/diary/<int:diary_id>/edit')
def diary_edit(diary_id):
    """编辑日记页面"""
    return render_template('diary_edit.html', diary_id=diary_id)

@app.route('/game')
def game():
    """游戏数值页面"""
    return render_template('game.html')


if __name__ == '__main__':
    with app.app_context():
        # 创建表（如果不存在）
        db.create_all()
        print(f"数据库连接: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")

    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
