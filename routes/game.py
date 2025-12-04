from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import GameState, db
from datetime import datetime

bp = Blueprint('game', __name__)

@bp.route('/state', methods=['GET'])
@jwt_required()
def get_game_state():
    """
    获取游戏状态

    返回用户的完整游戏状态，包括：
    - 核心属性：mental_health_score, stress_level, growth_potential
    - 游戏资源：coins, level, total_diaries
    - 计算属性：diaries_to_next_level
    """
    try:
        user_id = get_jwt_identity()

        # 获取或创建游戏状态（增量模式初始化）
        game_state = GameState.query.filter_by(user_id=user_id).first()
        if not game_state:
            game_state = GameState(
                user_id=user_id,
                mental_health_score=50,
                stress_level=50,
                growth_potential=50,
                coins=0,
                level=1,
                total_diaries=0
            )
            db.session.add(game_state)
            db.session.commit()

        return jsonify({
            'success': True,
            'game_state': game_state.to_dict()
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get game state: {str(e)}'}), 500

@bp.route('/update', methods=['POST'])
@jwt_required()
def update_game_state():
    """更新游戏状态"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        game_state = GameState.query.filter_by(user_id=user_id).first()
        if not game_state:
            return jsonify({'error': 'Game state not found'}), 404

        # 更新游戏状态
        if 'current_level' in data:
            game_state.current_level = data['current_level']
        if 'game_difficulty' in data:
            game_state.game_difficulty = data['game_difficulty']
        if 'character_stats' in data:
            game_state.character_stats = data['character_stats']
        if 'unlocked_features' in data:
            game_state.unlocked_features = data['unlocked_features']

        game_state.last_active = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'message': 'Game state updated successfully',
            'game_state': game_state.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update game state: {str(e)}'}), 500

@bp.route('/progress', methods=['GET'])
@jwt_required()
def get_game_progress():
    """获取游戏进度"""
    try:
        user_id = get_jwt_identity()

        # 这里可以添加更复杂的进度计算逻辑
        game_state = GameState.query.filter_by(user_id=user_id).first()
        if not game_state:
            return jsonify({'error': 'Game state not found'}), 404

        progress = {
            'current_level': game_state.current_level,
            'total_play_time': game_state.total_play_time,
            'character_stats': game_state.character_stats,
            'unlocked_features': game_state.unlocked_features,
            'completion_percentage': min(100, (game_state.current_level / 10) * 100)
        }

        return jsonify({
            'progress': progress
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get game progress: {str(e)}'}), 500