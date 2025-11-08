from flask import Flask, render_template, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# 导入扩展和模型
from extensions import db, init_extensions
from models import User, EmotionDiary, EmotionAnalysis, GameState, GameProgress
from routes import auth_bp, diary_bp

# 加载环境变量
load_dotenv()

# 创建Flask应用
app = Flask(__name__)

# 基础配置
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///diary.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-string')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# 数据库配置优化
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 120,
    'pool_pre_ping': True,
    'connect_args': {
        'charset': 'utf8mb4'
    }
}

# 初始化扩展
init_extensions(app)

# 注册蓝图
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(diary_bp, url_prefix='/api/diary')

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


# 页面路由
@app.route('/profile')
@jwt_required()
def profile():
    """个人资料页面"""
    return render_template('profile.html')

@app.route('/diary')
@jwt_required()
def diary_list():
    """日记列表页面"""
    return render_template('diary_list.html')

@app.route('/diary/new')
@app.route('/diary/new')
@jwt_required()
def diary_new():
    """写新日记页面"""
    return render_template('diary_edit.html')

@app.route('/diary/<int:diary_id>')
@jwt_required()
def diary_detail(diary_id):
    """日记详情页面"""
    return render_template('diary_detail.html', diary_id=diary_id)

@app.route('/diary/<int:diary_id>/edit')
@jwt_required()
def diary_edit(diary_id):
    """编辑日记页面"""
    return render_template('diary_edit.html', diary_id=diary_id)


def upgrade_database():
    """升级数据库结构"""
    with app.app_context():
        try:
            # 检查是否需要添加重置令牌字段
            engine = db.engine
            inspector = db.inspect(engine)
            columns = inspector.get_columns('users')
            column_names = [col['name'] for col in columns]

            if 'reset_token' not in column_names:
                print("正在添加重置令牌字段...")
                with engine.connect() as conn:
                    conn.execute(db.text("""
                        ALTER TABLE users
                        ADD COLUMN reset_token VARCHAR(255),
                        ADD COLUMN reset_token_expires DATETIME
                    """))
                    conn.commit()
                print("重置令牌字段添加成功")

        except Exception as e:
            print(f"数据库升级失败: {e}")

if __name__ == '__main__':
    with app.app_context():
        # 先升级数据库结构
        upgrade_database()
        # 然后创建表（如果不存在）
        db.create_all()

    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)