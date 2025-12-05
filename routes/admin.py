# 管理员路由模块
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from extensions import db
from models import User, EmotionDiary, EmotionAnalysis, Postcard, AdventureSession, AccessLog, GameState

bp = Blueprint('admin', __name__)


def admin_required(fn):
    """管理员权限验证装饰器"""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        # 支持字符串或整数类型的user_id
        if isinstance(user_id, str):
            user_id = int(user_id)
        user = User.query.get(user_id)
        if not user or not user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403
        return fn(*args, **kwargs)
    return wrapper


# ==================== 认证相关 ====================

@bp.route('/login', methods=['POST'])
def admin_login():
    """管理员登录"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': '用户名或密码错误'}), 401

    if not user.is_admin:
        return jsonify({'error': '非管理员账户'}), 403

    # 更新登录信息
    user.last_login_at = datetime.utcnow()
    user.login_count = (user.login_count or 0) + 1
    db.session.commit()

    # 生成JWT token
    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        'message': '登录成功',
        'token': access_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'is_admin': user.is_admin
        }
    })


@bp.route('/check', methods=['GET'])
@admin_required
def check_admin():
    """验证管理员状态"""
    user_id = get_jwt_identity()
    if isinstance(user_id, str):
        user_id = int(user_id)
    user = User.query.get(user_id)
    return jsonify({
        'is_admin': True,
        'user': {
            'id': user.id,
            'username': user.username
        }
    })


# ==================== 统计数据 ====================

@bp.route('/stats/overview', methods=['GET'])
@admin_required
def get_overview_stats():
    """获取网站概览统计"""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    # 用户统计
    total_users = User.query.count()
    today_new_users = User.query.filter(User.created_at >= today_start).count()
    week_new_users = User.query.filter(User.created_at >= week_start).count()
    active_users = User.query.filter(User.is_active == True).count()

    # 日记统计
    total_diaries = EmotionDiary.query.count()
    today_diaries = EmotionDiary.query.filter(EmotionDiary.created_at >= today_start).count()
    week_diaries = EmotionDiary.query.filter(EmotionDiary.created_at >= week_start).count()
    analyzed_diaries = EmotionDiary.query.filter(EmotionDiary.analysis_status == 'completed').count()

    # 明信片统计
    total_postcards = Postcard.query.count()
    completed_postcards = Postcard.query.filter(Postcard.status == 'completed').count()

    # 访问量统计
    total_visits = AccessLog.query.count()
    today_visits = AccessLog.query.filter(AccessLog.created_at >= today_start).count()
    week_visits = AccessLog.query.filter(AccessLog.created_at >= week_start).count()

    # 独立访客（按IP去重）
    today_unique_visitors = db.session.query(func.count(func.distinct(AccessLog.ip_address))).filter(
        AccessLog.created_at >= today_start
    ).scalar() or 0

    return jsonify({
        'users': {
            'total': total_users,
            'today_new': today_new_users,
            'week_new': week_new_users,
            'active': active_users
        },
        'diaries': {
            'total': total_diaries,
            'today': today_diaries,
            'week': week_diaries,
            'analyzed': analyzed_diaries
        },
        'postcards': {
            'total': total_postcards,
            'completed': completed_postcards
        },
        'visits': {
            'total': total_visits,
            'today': today_visits,
            'week': week_visits,
            'today_unique': today_unique_visitors
        }
    })


@bp.route('/stats/traffic', methods=['GET'])
@admin_required
def get_traffic_stats():
    """获取流量统计（按天）"""
    days = request.args.get('days', 7, type=int)
    days = min(days, 90)  # 最多90天

    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    # 按天分组统计访问量
    daily_stats = db.session.query(
        func.date(AccessLog.created_at).label('date'),
        func.count(AccessLog.id).label('visits'),
        func.count(func.distinct(AccessLog.ip_address)).label('unique_visitors')
    ).filter(
        AccessLog.created_at >= start_date
    ).group_by(
        func.date(AccessLog.created_at)
    ).order_by(
        func.date(AccessLog.created_at)
    ).all()

    result = []
    for stat in daily_stats:
        result.append({
            'date': str(stat.date),
            'visits': stat.visits,
            'unique_visitors': stat.unique_visitors
        })

    return jsonify({'traffic': result, 'days': days})


@bp.route('/stats/users-trend', methods=['GET'])
@admin_required
def get_users_trend():
    """获取用户增长趋势"""
    days = request.args.get('days', 30, type=int)
    days = min(days, 90)

    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    # 按天分组统计新用户
    daily_users = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('new_users')
    ).filter(
        User.created_at >= start_date
    ).group_by(
        func.date(User.created_at)
    ).order_by(
        func.date(User.created_at)
    ).all()

    result = []
    for stat in daily_users:
        result.append({
            'date': str(stat.date),
            'new_users': stat.new_users
        })

    return jsonify({'trend': result, 'days': days})


@bp.route('/stats/diaries-trend', methods=['GET'])
@admin_required
def get_diaries_trend():
    """获取日记发布趋势"""
    days = request.args.get('days', 30, type=int)
    days = min(days, 90)

    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    daily_diaries = db.session.query(
        func.date(EmotionDiary.created_at).label('date'),
        func.count(EmotionDiary.id).label('diaries')
    ).filter(
        EmotionDiary.created_at >= start_date
    ).group_by(
        func.date(EmotionDiary.created_at)
    ).order_by(
        func.date(EmotionDiary.created_at)
    ).all()

    result = []
    for stat in daily_diaries:
        result.append({
            'date': str(stat.date),
            'diaries': stat.diaries
        })

    return jsonify({'trend': result, 'days': days})


# ==================== 用户管理 ====================

@bp.route('/users', methods=['GET'])
@admin_required
def list_users():
    """获取用户列表（分页、搜索）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')

    query = User.query

    if search:
        query = query.filter(
            (User.username.contains(search)) |
            (User.email.contains(search))
        )

    query = query.order_by(desc(User.created_at))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    users = []
    for user in pagination.items:
        user_dict = user.to_admin_dict()
        # 添加明信片数量
        user_dict['postcard_count'] = Postcard.query.filter_by(user_id=user.id).count()
        users.append(user_dict)

    return jsonify({
        'users': users,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })


@bp.route('/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user_detail(user_id):
    """获取用户详情"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404

    user_dict = user.to_admin_dict()

    # 获取游戏状态
    game_state = GameState.query.filter_by(user_id=user_id).first()
    user_dict['game_state'] = game_state.to_dict() if game_state else None

    # 获取明信片数量
    user_dict['postcard_count'] = Postcard.query.filter_by(user_id=user_id).count()

    # 获取最近日记
    recent_diaries = EmotionDiary.query.filter_by(user_id=user_id).order_by(
        desc(EmotionDiary.created_at)
    ).limit(5).all()
    user_dict['recent_diaries'] = [d.to_dict() for d in recent_diaries]

    return jsonify(user_dict)


@bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """修改用户信息"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404

    data = request.get_json()

    # 更新用户名
    if 'username' in data and data['username']:
        existing = User.query.filter(User.username == data['username'], User.id != user_id).first()
        if existing:
            return jsonify({'error': '用户名已存在'}), 400
        user.username = data['username']

    # 更新邮箱
    if 'email' in data and data['email']:
        existing = User.query.filter(User.email == data['email'], User.id != user_id).first()
        if existing:
            return jsonify({'error': '邮箱已存在'}), 400
        user.email = data['email']

    # 更新激活状态
    if 'is_active' in data:
        user.is_active = bool(data['is_active'])

    # 更新管理员状态（不能取消自己的管理员权限）
    current_user_id = get_jwt_identity()
    if isinstance(current_user_id, str):
        current_user_id = int(current_user_id)
    if 'is_admin' in data and user_id != current_user_id:
        user.is_admin = bool(data['is_admin'])

    user.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'message': '用户信息已更新',
        'user': user.to_admin_dict()
    })


@bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_user_password(user_id):
    """重置用户密码"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404

    data = request.get_json()
    new_password = data.get('new_password')

    if not new_password or len(new_password) < 6:
        return jsonify({'error': '密码长度至少6位'}), 400

    user.password_hash = generate_password_hash(new_password)
    user.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'message': '密码已重置'})


@bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """删除用户（级联删除所有数据）"""
    # 不能删除自己
    current_user_id = get_jwt_identity()
    if isinstance(current_user_id, str):
        current_user_id = int(current_user_id)
    if user_id == current_user_id:
        return jsonify({'error': '不能删除自己的账户'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404

    # 删除用户的明信片图片文件
    from services.postcard_service import delete_postcard_image
    postcards = Postcard.query.filter_by(user_id=user_id).all()
    for postcard in postcards:
        if postcard.image_url:
            delete_postcard_image(postcard.image_url)

    # 删除用户（级联删除日记、分析、游戏数据等）
    db.session.delete(user)
    db.session.commit()

    return jsonify({'message': f'用户 {user.username} 已删除'})


# ==================== 日记管理 ====================

@bp.route('/diaries', methods=['GET'])
@admin_required
def list_diaries():
    """获取所有日记列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    user_id = request.args.get('user_id', type=int)
    search = request.args.get('search', '')

    query = EmotionDiary.query

    if user_id:
        query = query.filter(EmotionDiary.user_id == user_id)

    if search:
        query = query.filter(EmotionDiary.content.contains(search))

    query = query.order_by(desc(EmotionDiary.created_at))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    diaries = []
    for diary in pagination.items:
        diary_dict = diary.to_dict()
        # 添加用户信息
        user = User.query.get(diary.user_id)
        diary_dict['username'] = user.username if user else 'Unknown'
        # 添加内容摘要
        diary_dict['content_preview'] = diary.content[:100] + '...' if len(diary.content) > 100 else diary.content
        # 添加明信片信息
        postcard = Postcard.query.filter_by(diary_id=diary.id).first()
        diary_dict['has_postcard'] = postcard is not None
        diaries.append(diary_dict)

    return jsonify({
        'diaries': diaries,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })


@bp.route('/diaries/<int:diary_id>', methods=['GET'])
@admin_required
def get_diary_detail(diary_id):
    """获取日记详情"""
    diary = EmotionDiary.query.get(diary_id)
    if not diary:
        return jsonify({'error': '日记不存在'}), 404

    diary_dict = diary.to_dict()

    # 添加用户信息
    user = User.query.get(diary.user_id)
    diary_dict['username'] = user.username if user else 'Unknown'

    # 添加分析结果
    if diary.analysis:
        diary_dict['analysis'] = diary.analysis.to_dict()

    # 添加明信片信息
    postcard = Postcard.query.filter_by(diary_id=diary_id).first()
    diary_dict['postcard'] = postcard.to_dict() if postcard else None

    # 添加探险信息
    adventure = AdventureSession.query.filter_by(diary_id=diary_id).first()
    diary_dict['adventure'] = adventure.to_dict() if adventure else None

    return jsonify(diary_dict)


@bp.route('/diaries/<int:diary_id>', methods=['DELETE'])
@admin_required
def admin_delete_diary(diary_id):
    """删除日记（包含明信片和图片）"""
    diary = EmotionDiary.query.get(diary_id)
    if not diary:
        return jsonify({'error': '日记不存在'}), 404

    # 删除明信片图片文件
    from services.postcard_service import delete_postcard_image
    postcard = Postcard.query.filter_by(diary_id=diary_id).first()
    if postcard and postcard.image_url:
        delete_postcard_image(postcard.image_url)

    # 删除明信片记录
    if postcard:
        db.session.delete(postcard)

    # 删除探险记录
    adventure = AdventureSession.query.filter_by(diary_id=diary_id).first()
    if adventure:
        db.session.delete(adventure)

    # 删除日记（级联删除分析）
    db.session.delete(diary)
    db.session.commit()

    return jsonify({'message': '日记已删除'})


# ==================== 明信片管理 ====================

@bp.route('/postcards', methods=['GET'])
@admin_required
def list_postcards():
    """获取所有明信片列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    user_id = request.args.get('user_id', type=int)
    status = request.args.get('status', '')

    query = Postcard.query

    if user_id:
        query = query.filter(Postcard.user_id == user_id)

    if status:
        query = query.filter(Postcard.status == status)

    query = query.order_by(desc(Postcard.created_at))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    postcards = []
    for postcard in pagination.items:
        postcard_dict = postcard.to_dict()
        # 添加用户信息
        user = User.query.get(postcard.user_id)
        postcard_dict['username'] = user.username if user else 'Unknown'
        postcards.append(postcard_dict)

    return jsonify({
        'postcards': postcards,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })


@bp.route('/postcards/<int:postcard_id>', methods=['DELETE'])
@admin_required
def delete_postcard(postcard_id):
    """删除明信片（包含图片文件）"""
    postcard = Postcard.query.get(postcard_id)
    if not postcard:
        return jsonify({'error': '明信片不存在'}), 404

    # 删除图片文件
    from services.postcard_service import delete_postcard_image
    if postcard.image_url:
        delete_postcard_image(postcard.image_url)

    # 删除记录
    db.session.delete(postcard)
    db.session.commit()

    return jsonify({'message': '明信片已删除'})


# ==================== 访问日志 ====================

@bp.route('/logs', methods=['GET'])
@admin_required
def list_access_logs():
    """获取访问日志列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    path_filter = request.args.get('path', '')

    query = AccessLog.query

    if path_filter:
        query = query.filter(AccessLog.path.contains(path_filter))

    query = query.order_by(desc(AccessLog.created_at))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    logs = [log.to_dict() for log in pagination.items]

    return jsonify({
        'logs': logs,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })
