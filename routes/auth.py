from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import User, db
from datetime import datetime, timedelta
import secrets

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.get_json()

        # 验证必填字段
        if not data.get('username'):
            return jsonify({'error': '用户名不能为空'}), 400
        if not data.get('email'):
            return jsonify({'error': '邮箱不能为空'}), 400
        if not data.get('password'):
            return jsonify({'error': '密码不能为空'}), 400

        username = data['username'].strip()
        email = data['email'].strip().lower()
        password = data['password']

        # 验证输入格式
        if len(username) < 3 or len(username) > 50:
            return jsonify({'error': '用户名长度必须在3-50个字符之间'}), 400

        if len(password) < 6:
            return jsonify({'error': '密码长度至少6个字符'}), 400

        # 检查用户名和邮箱是否已存在
        if User.query.filter_by(username=username).first():
            return jsonify({'error': '用户名已存在'}), 409

        if User.query.filter_by(email=email).first():
            return jsonify({'error': '邮箱已被注册'}), 409

        # 创建新用户
        password_hash = generate_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            profile_data=data.get('profile_data', {})
        )

        db.session.add(new_user)
        db.session.commit()

        # 创建访问令牌
        access_token = create_access_token(identity=str(new_user.id))

        return jsonify({
            'message': '注册成功',
            'access_token': access_token,
            'user': new_user.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'注册失败: {str(e)}'}), 500

@bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()

        # 验证必填字段
        if not data.get('username') or not data.get('password'):
            return jsonify({'error': '用户名和密码不能为空'}), 400

        username = data['username'].strip()
        password = data['password']

        # 查找用户（支持用户名或邮箱）
        user = User.query.filter(
            (User.username == username) | (User.email == username.lower())
        ).first()

        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({'error': '用户名或密码错误'}), 401

        if not user.is_active:
            return jsonify({'error': '账户已被停用'}), 403

        # 更新最后活跃时间
        user.updated_at = datetime.utcnow()
        db.session.commit()

        # 创建访问令牌
        access_token = create_access_token(identity=str(user.id))

        return jsonify({
            'message': '登录成功',
            'access_token': access_token,
            'user': user.to_dict()
        }), 200

    except Exception as e:
        return jsonify({'error': f'登录失败: {str(e)}'}), 500

@bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """获取用户资料"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'user': user.to_dict()
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get profile: {str(e)}'}), 500

@bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """更新用户资料"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()

        # 更新允许修改的字段
        if 'profile_data' in data:
            user.profile_data = data['profile_data']

        if 'email' in data and data['email'] != user.email:
            # 检查新邮箱是否已存在
            existing_user = User.query.filter_by(email=data['email']).first()
            if existing_user and existing_user.id != user_id:
                return jsonify({'error': 'Email already exists'}), 409
            user.email = data['email'].strip().lower()

        user.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update profile: {str(e)}'}), 500

@bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """修改密码"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()
        old_password = data.get('old_password')
        new_password = data.get('new_password')

        if not old_password or not new_password:
            return jsonify({'error': 'Old password and new password are required'}), 400

        if len(new_password) < 6:
            return jsonify({'error': 'New password must be at least 6 characters'}), 400

        # 验证旧密码
        if not check_password_hash(user.password_hash, old_password):
            return jsonify({'error': 'Old password is incorrect'}), 401

        # 更新密码
        user.password_hash = generate_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'message': 'Password changed successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to change password: {str(e)}'}), 500

@bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """忘记密码 - 生成重置令牌"""
    try:
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({'error': '邮箱不能为空'}), 400

        user = User.query.filter_by(email=email.strip().lower()).first()

        if not user:
            return jsonify({'error': '该邮箱未注册'}), 404

        # 生成重置令牌
        reset_token = secrets.token_urlsafe(32)
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)  # 1小时有效期
        db.session.commit()

        # 在实际生产环境中，这里应该发送邮件
        # 现在直接返回令牌用于测试
        return jsonify({
            'message': '密码重置令牌已生成',
            'reset_token': reset_token,  # 生产环境应该通过邮件发送
            'expires_in': '1小时'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'生成重置令牌失败: {str(e)}'}), 500

@bp.route('/reset-password', methods=['POST'])
def reset_password():
    """重置密码"""
    try:
        data = request.get_json()
        reset_token = data.get('reset_token')
        new_password = data.get('new_password')

        if not reset_token or not new_password:
            return jsonify({'error': '重置令牌和新密码不能为空'}), 400

        if len(new_password) < 6:
            return jsonify({'error': '密码长度至少6个字符'}), 400

        # 查找用户
        user = User.query.filter_by(reset_token=reset_token).first()

        if not user:
            return jsonify({'error': '无效的重置令牌'}), 400

        # 检查令牌是否过期
        if user.reset_token_expires < datetime.utcnow():
            return jsonify({'error': '重置令牌已过期'}), 400

        # 重置密码
        user.password_hash = generate_password_hash(new_password)
        user.reset_token = None
        user.reset_token_expires = None
        user.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'message': '密码重置成功'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'密码重置失败: {str(e)}'}), 500