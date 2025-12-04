# -*- coding: utf-8 -*-
"""
明信片路由模块

提供明信片相关的API接口：
- 获取明信片列表
- 获取单个明信片详情
- 标记明信片已读
- 获取未读数量
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Postcard, EmotionDiary, db
from datetime import datetime

bp = Blueprint('postcard', __name__)


@bp.route('/', methods=['GET'])
@jwt_required()
def get_postcards():
    """
    获取用户的明信片列表

    Query参数:
    - limit: 返回数量，默认20，最大100
    - offset: 偏移量，默认0
    - unread_only: 是否只返回未读，默认false

    返回:
    {
        postcards: [...],
        pagination: {total, limit, offset, has_more},
        unread_count: int
    }
    """
    try:
        user_id = get_jwt_identity()
        limit = min(request.args.get('limit', 20, type=int), 100)
        offset = request.args.get('offset', 0, type=int)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'

        # 构建查询
        query = Postcard.query.filter_by(user_id=user_id)

        if unread_only:
            query = query.filter_by(is_read=False)

        # 获取总数
        total = query.count()

        # 获取分页数据
        postcards = query.order_by(Postcard.created_at.desc()).offset(offset).limit(limit).all()

        # 获取未读数量
        unread_count = Postcard.query.filter_by(user_id=user_id, is_read=False).count()

        return jsonify({
            'postcards': [p.to_dict() for p in postcards],
            'pagination': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total
            },
            'unread_count': unread_count
        }), 200

    except Exception as e:
        return jsonify({'error': f'获取明信片列表失败: {str(e)}'}), 500


@bp.route('/<int:postcard_id>', methods=['GET'])
@jwt_required()
def get_postcard(postcard_id):
    """
    获取单个明信片详情

    返回:
    {
        postcard: {...},
        diary: {...}  // 关联的日记简要信息
    }
    """
    try:
        user_id = get_jwt_identity()

        postcard = Postcard.query.filter_by(id=postcard_id, user_id=user_id).first()
        if not postcard:
            return jsonify({'error': '明信片不存在'}), 404

        # 获取关联的日记信息
        diary = EmotionDiary.query.get(postcard.diary_id)
        diary_info = None
        if diary:
            diary_info = {
                'id': diary.id,
                'created_at': diary.created_at.isoformat(),
                'emotion_tags': diary.emotion_tags,
                'content_preview': diary.content[:100] + '...' if len(diary.content) > 100 else diary.content
            }

        return jsonify({
            'postcard': postcard.to_dict(),
            'diary': diary_info
        }), 200

    except Exception as e:
        return jsonify({'error': f'获取明信片详情失败: {str(e)}'}), 500


@bp.route('/<int:postcard_id>/read', methods=['POST'])
@jwt_required()
def mark_read(postcard_id):
    """
    标记明信片为已读

    返回:
    {
        success: true,
        postcard: {...}
    }
    """
    try:
        user_id = get_jwt_identity()

        postcard = Postcard.query.filter_by(id=postcard_id, user_id=user_id).first()
        if not postcard:
            return jsonify({'error': '明信片不存在'}), 404

        if not postcard.is_read:
            postcard.is_read = True
            postcard.read_at = datetime.utcnow()
            db.session.commit()

        return jsonify({
            'success': True,
            'postcard': postcard.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'标记已读失败: {str(e)}'}), 500


@bp.route('/unread-count', methods=['GET'])
@jwt_required()
def get_unread_count():
    """
    获取未读明信片数量

    返回:
    {
        unread_count: int
    }
    """
    try:
        user_id = get_jwt_identity()
        unread_count = Postcard.query.filter_by(user_id=user_id, is_read=False).count()

        return jsonify({
            'unread_count': unread_count
        }), 200

    except Exception as e:
        return jsonify({'error': f'获取未读数量失败: {str(e)}'}), 500


@bp.route('/latest', methods=['GET'])
@jwt_required()
def get_latest_postcard():
    """
    获取最新一张明信片

    返回:
    {
        postcard: {...} | null
    }
    """
    try:
        user_id = get_jwt_identity()

        postcard = Postcard.query.filter_by(user_id=user_id).order_by(Postcard.created_at.desc()).first()

        return jsonify({
            'postcard': postcard.to_dict() if postcard else None
        }), 200

    except Exception as e:
        return jsonify({'error': f'获取最新明信片失败: {str(e)}'}), 500


@bp.route('/by-diary/<int:diary_id>', methods=['GET'])
@jwt_required()
def get_postcard_by_diary(diary_id):
    """
    根据日记ID获取对应的明信片

    返回:
    {
        postcard: {...} | null
    }
    """
    try:
        user_id = get_jwt_identity()

        # 验证日记所有权
        diary = EmotionDiary.query.filter_by(id=diary_id, user_id=user_id).first()
        if not diary:
            return jsonify({'error': '日记不存在'}), 404

        postcard = Postcard.query.filter_by(diary_id=diary_id, user_id=user_id).first()

        return jsonify({
            'postcard': postcard.to_dict() if postcard else None
        }), 200

    except Exception as e:
        return jsonify({'error': f'获取明信片失败: {str(e)}'}), 500


@bp.route('/regenerate/<int:postcard_id>', methods=['POST'])
@jwt_required()
def regenerate_image(postcard_id):
    """
    重新生成明信片图片（当图片生成失败时使用）

    返回:
    {
        success: true,
        postcard: {...}
    }
    """
    try:
        user_id = get_jwt_identity()

        postcard = Postcard.query.filter_by(id=postcard_id, user_id=user_id).first()
        if not postcard:
            return jsonify({'error': '明信片不存在'}), 404

        # 只有text_only或failed状态的明信片可以重新生成
        if postcard.status not in ['text_only', 'failed']:
            return jsonify({'error': '该明信片不需要重新生成'}), 400

        # 导入服务
        from services.postcard_service import generate_postcard_image

        # 更新状态
        postcard.status = 'generating'
        db.session.commit()

        # 生成图片
        image_url = generate_postcard_image(postcard.image_prompt)

        if image_url:
            postcard.image_url = image_url
            postcard.status = 'completed'
            postcard.generated_at = datetime.utcnow()
        else:
            postcard.status = 'failed'

        db.session.commit()

        return jsonify({
            'success': bool(image_url),
            'postcard': postcard.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'重新生成失败: {str(e)}'}), 500
