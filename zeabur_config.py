"""
Zeabur平台配置文件
用于处理Zeabur云端数据库连接和其他服务配置
"""

import os
import urllib.parse
from config import Config

class ZeaburConfig:
    """Zeabur平台专用配置"""

    @staticmethod
    def get_database_url():
        """
        获取Zeabur数据库连接URL
        支持多种数据库服务格式
        """
        # 首先检查Zeabur提供的数据库URL
        database_url = os.getenv('DATABASE_URL')

        if database_url:
            # PostgreSQL URL格式转换
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            return database_url

        # 检查Zeabur特定的环境变量
        # PostgreSQL服务
        pg_host = os.getenv('POSTGRES_HOST')
        pg_port = os.getenv('POSTGRES_PORT', '5432')
        pg_user = os.getenv('POSTGRES_USER')
        pg_password = os.getenv('POSTGRES_PASSWORD')
        pg_database = os.getenv('POSTGRES_DB')

        if all([pg_host, pg_user, pg_password, pg_database]):
            # 构建PostgreSQL连接URL
            encoded_password = urllib.parse.quote_plus(pg_password)
            return f'postgresql://{pg_user}:{encoded_password}@{pg_host}:{pg_port}/{pg_database}'

        # MySQL服务 - 使用您提供的Zeabur MySQL配置
        mysql_host = os.getenv('MYSQL_HOST', 'hkg1.clusters.zeabur.com')
        mysql_port = os.getenv('MYSQL_PORT', '32570')
        mysql_user = os.getenv('MYSQL_USER', 'root')
        mysql_password = os.getenv('MYSQL_PASSWORD', 'q37sTw1xgc2h46589NbdZFzMAnPrpEm0')
        mysql_database = os.getenv('MYSQL_DATABASE', 'zeabur')

        if all([mysql_host, mysql_user, mysql_password, mysql_database]):
            # 构建MySQL连接URL
            encoded_password = urllib.parse.quote_plus(mysql_password)
            return f'mysql+pymysql://{mysql_user}:{encoded_password}@{mysql_host}:{mysql_port}/{mysql_database}'

        # 默认使用SQLite
        return 'sqlite:///diary.db'

    @staticmethod
    def get_redis_url():
        """获取Redis连接URL"""
        redis_url = os.getenv('REDIS_URL')
        if redis_url:
            return redis_url

        # 检查Zeabur Redis服务
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = os.getenv('REDIS_PORT', '6379')
        redis_password = os.getenv('REDIS_PASSWORD')
        redis_db = os.getenv('REDIS_DB', '0')

        if redis_password:
            return f'redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}'
        else:
            return f'redis://{redis_host}:{redis_port}/{redis_db}'

    @staticmethod
    def get_port():
        """获取应用端口（Zeabur会自动分配）"""
        return int(os.getenv('PORT', 5000))

    @staticmethod
    def get_bind_address():
        """获取绑定地址"""
        return os.getenv('BIND_ADDRESS', '0.0.0.0')

    @staticmethod
    def is_production():
        """判断是否为生产环境"""
        return os.getenv('FLASK_ENV', 'development') == 'production'

    @staticmethod
    def get_coze_config():
        """获取COZE API配置"""
        return {
            'api_key': os.getenv('COZE_API_KEY'),
            'bot_id': os.getenv('COZE_BOT_ID'),
            'base_url': os.getenv('COZE_BASE_URL', 'https://api.coze.com'),
            'user_id': os.getenv('COZE_USER_ID', 'cbt_diary_user')
        }

    @staticmethod
    def get_qwen_config():
        """获取QWEN模型配置"""
        return {
            'api_key': os.getenv('QWEN_API_KEY'),
            'model_name': os.getenv('QWEN_MODEL_NAME', 'qwen-turbo'),
            'base_url': os.getenv('QWEN_BASE_URL', 'https://dashscope.aliyuncs.com/api/v1')
        }

    @staticmethod
    def get_all_configs():
        """获取所有配置信息"""
        return {
            'database_url': ZeaburConfig.get_database_url(),
            'redis_url': ZeaburConfig.get_redis_url(),
            'port': ZeaburConfig.get_port(),
            'bind_address': ZeaburConfig.get_bind_address(),
            'is_production': ZeaburConfig.is_production(),
            'coze_config': ZeaburConfig.get_coze_config(),
            'qwen_config': ZeaburConfig.get_qwen_config()
        }

# 更新app.py中的配置
def update_app_config(app):
    """更新Flask应用配置以适配Zeabur"""

    # 数据库配置
    app.config['SQLALCHEMY_DATABASE_URI'] = ZeaburConfig.get_database_url()

    # Redis配置
    redis_url = ZeaburConfig.get_redis_url()
    if redis_url:
        app.config['REDIS_URL'] = redis_url

    # 端口配置
    app.config['PORT'] = ZeaburConfig.get_port()
    app.config['BIND_ADDRESS'] = ZeaburConfig.get_bind_address()

    # 其他Zeabur相关配置
    app.config['COZE_CONFIG'] = ZeaburConfig.get_coze_config()
    app.config['QWEN_CONFIG'] = ZeaburConfig.get_qwen_config()

    return app

# Zeabur部署检查清单
zeabur_deployment_checklist = {
    'required_env_vars': [
        'SECRET_KEY',
        'JWT_SECRET_KEY',
        'COZE_API_KEY',
        'COZE_BOT_ID',
        'QWEN_API_KEY'
    ],
    'optional_env_vars': [
        'DATABASE_URL',  # Zeabur会自动提供
        'REDIS_URL',     # 可选的Redis服务
        'FLASK_ENV',
        'PORT'
    ],
    'zeabur_services': [
        'PostgreSQL Database',
        'Redis Cache (Optional)',
        'Application Hosting'
    ]
}