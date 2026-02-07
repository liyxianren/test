import os
from datetime import timedelta
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """基础配置类"""
    # Flask基础配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

    # 数据库配置
    # 优先使用Zeabur提供的数据库URL
    DATABASE_URL = os.getenv('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        # 将postgres://转换为postgresql://（SQLAlchemy要求）
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    elif not DATABASE_URL:
        # 本地开发使用SQLite
        DATABASE_URL = 'sqlite:///diary.db'

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT配置
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-string')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES_HOURS', 24)))

    # Redis配置（可选）
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    # COZE API配置
    COZE_API_KEY = os.getenv('COZE_API_KEY')
    COZE_BOT_ID = os.getenv('COZE_BOT_ID')
    COZE_BASE_URL = os.getenv('COZE_BASE_URL', 'https://api.coze.com')

    # QWEN模型配置
    QWEN_API_KEY = os.getenv('QWEN_API_KEY')
    QWEN_MODEL_NAME = os.getenv('QWEN_MODEL_NAME', 'qwen-turbo')
    QWEN_BASE_URL = os.getenv('QWEN_BASE_URL', 'https://dashscope.aliyuncs.com/api/v1')

    # 文件上传配置
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    ALLOWED_EXTENSIONS = set(os.getenv('ALLOWED_EXTENSIONS', 'txt,pdf,png,jpg,jpeg,gif').split(','))

    # 应用配置
    APP_NAME = 'CBT情绪日记游戏'
    APP_VERSION = '1.0.0'

    # 安全配置
    BCRYPT_LOG_ROUNDS = 12
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False

    # 生产环境安全设置
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)

class TestingConfig(Config):
    """测试环境配置"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # 内存数据库

# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}