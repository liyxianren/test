from flask import Flask, render_template, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from sqlalchemy import inspect, text
from urllib.parse import quote_plus

# 导入扩展和模型
from extensions import db, init_extensions
from models import User, EmotionDiary, EmotionAnalysis, GameState, GameProgress, Postcard, AdventureSession, UserItem, AccessLog
from routes import auth_bp, diary_bp, upload_bp, analysis_bp, game_bp, postcard_bp, adventure_bp, admin_bp

# 加载环境变量（override=True 确保.env文件优先于系统环境变量）
load_dotenv(override=True)

# 打印AI模型配置（仅在调试模式下）
if os.getenv('FLASK_DEBUG', '').lower() == 'true':
    print(f"[启动] AI模型: ZHIPU={os.getenv('ZHIPU_MODEL_NAME')}, POSTCARD={os.getenv('ZHIPU_POSTCARD_MODEL')}")

# 创建Flask应用
app = Flask(__name__)

# 处理反向代理的 X-Forwarded-* 头（Zeabur/Nginx等）
# 这让 Flask 正确识别 HTTPS 协议，避免 Mixed Content 错误
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,      # X-Forwarded-For: 真实客户端IP
    x_proto=1,    # X-Forwarded-Proto: 原始协议(https)
    x_host=1,     # X-Forwarded-Host: 原始主机名
    x_prefix=1    # X-Forwarded-Prefix: URL前缀
)

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
            'reset_token_expires': 'DATETIME',
            # 管理员字段
            'is_admin': 'BOOLEAN DEFAULT 0',
            'last_login_at': 'DATETIME',
            'login_count': 'INTEGER DEFAULT 0'
        },
        'emotion_diaries': {
            'trigger_event': 'TEXT',
            'images': 'JSON',
            'score_applied': 'BOOLEAN DEFAULT 0'
        },
        'emotion_analysis': {
            'analysis_payload': 'JSON'
        },
        'game_states': {
            'mental_health_score': 'INTEGER DEFAULT 50',
            'stress_level': 'INTEGER DEFAULT 50',
            'growth_potential': 'INTEGER DEFAULT 50',
            # 新增游戏资源字段
            'coins': 'INTEGER DEFAULT 0',
            'level': 'INTEGER DEFAULT 1',
            'total_diaries': 'INTEGER DEFAULT 0',
            'created_at': 'DATETIME'
        },
        'postcards': {
            # 明信片表的所有字段（通过db.create_all创建，这里仅做兼容性检查）
            'image_url': 'VARCHAR(500)',
            'image_prompt': 'TEXT',
            'location_name': 'VARCHAR(100)',
            'message': 'TEXT',
            'status': 'VARCHAR(20) DEFAULT "pending"',
            'emotion_tags': 'JSON',
            'emotion_intensity': 'INTEGER',
            'mental_health_score': 'INTEGER',
            'generated_at': 'DATETIME',
            'is_read': 'BOOLEAN DEFAULT 0',
            'read_at': 'DATETIME',
            # 探险收获
            'stat_changes': 'JSON',
            'coins_earned': 'INTEGER DEFAULT 0'
        },
        'adventure_sessions': {
            # 探险会话表字段
            'scene_name': 'VARCHAR(100)',
            'monsters': 'JSON',
            'challenges': 'JSON',
            'current_challenge': 'INTEGER DEFAULT 0',
            'coins_earned': 'INTEGER DEFAULT 0',
            'items_earned': 'JSON',
            'stat_changes': 'JSON',
            'started_at': 'DATETIME',
            'completed_at': 'DATETIME'
        },
        'user_items': {
            # 用户道具表字段
            'item_name_zh': 'VARCHAR(50)',
            'item_type': 'VARCHAR(20) DEFAULT "healing"',
            'quantity': 'INTEGER DEFAULT 1',
            'effect_type': 'VARCHAR(30)',
            'effect_value': 'INTEGER DEFAULT 0'
        },
        'access_logs': {
            # 访问日志表字段
            'ip_address': 'VARCHAR(50)',
            'user_agent': 'VARCHAR(500)',
            'path': 'VARCHAR(200)',
            'method': 'VARCHAR(10)',
            'user_id': 'INTEGER',
            'status_code': 'INTEGER'
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
                        col_type_upper = column_type.upper()
                        if col_type_upper.startswith('BOOLEAN') and engine_name == 'sqlite':
                            column_type_sql = 'INTEGER DEFAULT 0'
                        elif col_type_upper == 'JSON' and engine_name == 'sqlite':
                            column_type_sql = 'TEXT'

                        connection.execute(
                            text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type_sql}')
                        )
                        if table_name == 'emotion_diaries' and column_name == 'score_applied':
                            # 旧日记默认视为已计分，避免重复影响GameState
                            connection.execute(text('UPDATE emotion_diaries SET score_applied = 1 WHERE score_applied IS NULL OR score_applied = 0'))
    except Exception as schema_error:
        app.logger.warning(f"Schema check failed: {schema_error}")


ensure_schema_updates()

# 注册蓝图
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(diary_bp, url_prefix='/api/diary')
app.register_blueprint(upload_bp, url_prefix='/api')
app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
app.register_blueprint(game_bp, url_prefix='/api/game')
app.register_blueprint(postcard_bp, url_prefix='/api/postcard')
app.register_blueprint(adventure_bp, url_prefix='/api/adventure')
app.register_blueprint(admin_bp, url_prefix='/api/admin')


# ==================== 访问日志中间件 ====================

@app.before_request
def log_request():
    """记录访问日志"""
    # 跳过静态文件、健康检查和管理员访问日志API
    skip_paths = ['/static', '/api/health', '/api/admin/logs', '/image/', '/game/']
    for skip in skip_paths:
        if request.path.startswith(skip):
            return

    # 跳过favicon
    if request.path == '/favicon.ico':
        return

    try:
        # 尝试获取当前登录用户ID
        from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
        user_id = None
        try:
            verify_jwt_in_request(optional=True)
            identity = get_jwt_identity()
            if identity:
                user_id = int(identity) if isinstance(identity, str) else identity
        except:
            pass

        log = AccessLog(
            ip_address=request.remote_addr or 'unknown',
            user_agent=(request.user_agent.string[:500] if request.user_agent else 'unknown'),
            path=request.path[:200],
            method=request.method,
            user_id=user_id
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        # 日志记录失败不影响正常请求
        db.session.rollback()


# ==================== 创建默认管理员 ====================

def create_default_admin():
    """创建默认管理员账户"""
    try:
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@localhost',
                password_hash=generate_password_hash('kongbai123'),
                is_admin=True,
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            print("[启动] 默认管理员账户已创建: admin / kongbai123")
        elif not admin.is_admin:
            # 如果admin用户存在但不是管理员，升级为管理员
            admin.is_admin = True
            db.session.commit()
            print("[启动] 已将admin用户升级为管理员")
    except Exception as e:
        db.session.rollback()
        print(f"[警告] 创建管理员失败: {e}")


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

@app.route('/diary/<int:diary_id>/result')
def diary_result(diary_id):
    """日记分析结果页面"""
    return render_template('diary_result.html', diary_id=diary_id)

@app.route('/game')
def game():
    """游戏数值页面"""
    return render_template('game.html')

@app.route('/postcards')
def postcards():
    """明信片列表页面"""
    return render_template('postcards.html')

@app.route('/postcard/<int:postcard_id>')
def postcard_detail(postcard_id):
    """明信片详情页面"""
    return render_template('postcard_detail.html', postcard_id=postcard_id)

@app.route('/adventure/<int:diary_id>')
def adventure_page(diary_id):
    """探险游戏页面"""
    return render_template('adventure.html', diary_id=diary_id)


# ==================== 管理后台页面路由 ====================

@app.route('/admin')
@app.route('/admin/')
def admin_index():
    """管理后台首页（重定向到登录）"""
    return render_template('admin/login.html')

@app.route('/admin/login')
def admin_login_page():
    """管理员登录页面"""
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    """管理后台仪表盘"""
    return render_template('admin/dashboard.html')

@app.route('/admin/users')
def admin_users():
    """用户管理页面"""
    return render_template('admin/users.html')

@app.route('/admin/users/<int:user_id>')
def admin_user_detail(user_id):
    """用户详情页面"""
    return render_template('admin/user_detail.html', user_id=user_id)

@app.route('/admin/diaries')
def admin_diaries():
    """日记管理页面"""
    return render_template('admin/diaries.html')

@app.route('/admin/postcards')
def admin_postcards():
    """明信片管理页面"""
    return render_template('admin/postcards.html')


# 静态文件服务：game文件夹
@app.route('/game/<path:filename>')
def serve_game_assets(filename):
    """服务game文件夹中的静态资源"""
    from flask import send_from_directory
    game_folder = os.path.join(app.root_path, 'game')
    return send_from_directory(game_folder, filename)


# 静态文件服务：/image/ 目录（Zeabur持久化存储）
@app.route('/image/<path:filename>')
def serve_image_assets(filename):
    """
    服务/image/目录中的静态资源
    Zeabur部署时，/image/ 是持久化存储目录
    本地开发时，可以通过环境变量 IMAGE_FOLDER 指定目录
    """
    from flask import send_from_directory
    image_folder = os.environ.get('IMAGE_FOLDER', '/image')
    return send_from_directory(image_folder, filename)


if __name__ == '__main__':
    with app.app_context():
        # 创建表（如果不存在）
        db.create_all()
        print(f"数据库连接: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
        # 创建默认管理员
        create_default_admin()

    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
