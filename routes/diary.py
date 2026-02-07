from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import EmotionDiary, db, User, GameState, Postcard, AdventureSession
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import sys

bp = Blueprint('diary', __name__)

# 线程池用于后台任务
_executor = ThreadPoolExecutor(max_workers=2)

@bp.route('/', methods=['GET'])
@jwt_required()
def get_diaries():
    """获取用户的日记列表"""
    try:
        user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)

        # 限制每页数量
        limit = min(limit, 50)

        # 查询用户的日记
        query = EmotionDiary.query.filter_by(user_id=user_id).order_by(EmotionDiary.created_at.desc())

        # Flask-SQLAlchemy 3.x 需要通过 db.paginate 获取分页结果
        diaries = db.paginate(
            query,
            page=page,
            per_page=limit,
            error_out=False
        )

        return jsonify({
            'diaries': [diary.to_dict() for diary in diaries.items],
            'pagination': {
                'page': diaries.page,
                'pages': diaries.pages,
                'per_page': diaries.per_page,
                'total': diaries.total,
                'has_prev': diaries.has_prev,
                'has_next': diaries.has_next
            }
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get diaries: {str(e)}'}), 500

@bp.route('/recent', methods=['GET'])
def get_recent_diaries():
    """获取最新的日记（公开，用于首页展示）"""
    try:
        # 获取最近10条日记（匿名显示）
        diaries = EmotionDiary.query.order_by(EmotionDiary.created_at.desc()).limit(10).all()

        # 匿名化处理，不显示用户敏感信息
        result = []
        for diary in diaries:
            diary_data = diary.to_dict()
            # 移除内容中的敏感信息，只显示前100个字符
            if len(diary_data['content']) > 100:
                diary_data['content'] = diary_data['content'][:100] + '...'
            result.append(diary_data)

        return jsonify({
            'diaries': result
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get recent diaries: {str(e)}'}), 500

@bp.route('/', methods=['POST'])
@jwt_required()
def create_diary():
    """创建新的日记"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        # 验证必填字段
        if not data.get('content') or not data['content'].strip():
            return jsonify({'error': 'Content is required'}), 400

        content = data['content'].strip()
        emotion_tags = data.get('emotion_tags', [])
        emotion_score = data.get('emotion_score', {})
        trigger_event = data.get('trigger_event', '').strip() if data.get('trigger_event') else None
        images = data.get('images', [])

        # 确保用户有GameState（增量模式初始化）
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
            db.session.flush()

        # 创建新日记（标记未计分）
        new_diary = EmotionDiary(
            user_id=user_id,
            content=content,
            emotion_tags=emotion_tags,
            emotion_score=emotion_score,
            trigger_event=trigger_event,
            images=images,
            score_applied=False
        )

        db.session.add(new_diary)
        db.session.commit()

        diary_id = new_diary.id
        diary_data = new_diary.to_dict()

        # 日记创建完成后，立即触发后台生成明信片
        # 分数和金币仍在游戏完成时计算
        print(f"[日记创建] 日记创建成功，ID: {diary_id}", file=sys.stderr)

        # 后台生成明信片（不阻塞响应）
        try:
            from services.postcard_service import create_postcard_async
            intensity = emotion_score.get('intensity', 5) if isinstance(emotion_score, dict) else 5
            create_postcard_async(
                user_id=user_id,
                diary_id=diary_id,
                emotions=emotion_tags or [],
                intensity=intensity,
                mental_health_score=game_state.mental_health_score if game_state else 50,
                diary_content=content,
                trigger_event=trigger_event
            )
            print(f"[日记创建] 明信片生成已触发", file=sys.stderr)
        except Exception as e:
            print(f"[日记创建] 明信片生成触发失败（不影响日记保存）: {e}", file=sys.stderr)

        # 后台预生成探险题目（不阻塞响应）
        try:
            from services.adventure_service import create_adventure_async
            create_adventure_async(
                user_id=user_id,
                diary_id=diary_id,
                diary_content=content,
                emotion_tags=emotion_tags or [],
                emotion_score=emotion_score,
                trigger_event=trigger_event
            )
            print(f"[日记创建] 探险题目生成已触发", file=sys.stderr)
        except Exception as e:
            print(f"[日记创建] 探险题目生成触发失败（不影响日记保存）: {e}", file=sys.stderr)

        return jsonify({
            'message': 'Diary created successfully',
            'diary': diary_data
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create diary: {str(e)}'}), 500

@bp.route('/<int:diary_id>', methods=['GET'])
@jwt_required()
def get_diary(diary_id):
    """获取单篇日记详情"""
    try:
        user_id = get_jwt_identity()

        # 查询日记
        diary = EmotionDiary.query.filter_by(id=diary_id, user_id=user_id).first()

        if not diary:
            return jsonify({'error': 'Diary not found'}), 404

        # 获取关联的分析结果
        diary_data = diary.to_dict()
        if diary.analysis:
            diary_data['analysis'] = diary.analysis.to_dict()

        # 获取关联的明信片
        postcard = Postcard.query.filter_by(diary_id=diary_id, user_id=user_id).first()
        if postcard:
            diary_data['postcard'] = {
                'id': postcard.id,
                'status': postcard.status,
                'location_name': postcard.location_name,
                'message': postcard.message,
                'image_url': postcard.image_url,
                'generated_at': postcard.generated_at.isoformat() if postcard.generated_at else None
            }

        return jsonify({
            'diary': diary_data
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get diary: {str(e)}'}), 500

@bp.route('/<int:diary_id>', methods=['PUT'])
@jwt_required()
def update_diary(diary_id):
    """更新日记"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        # 查询日记
        diary = EmotionDiary.query.filter_by(id=diary_id, user_id=user_id).first()

        if not diary:
            return jsonify({'error': 'Diary not found'}), 404

        # 更新内容
        if 'content' in data:
            content = data['content'].strip()
            if not content:
                return jsonify({'error': 'Content cannot be empty'}), 400
            diary.content = content

        # 更新情绪标签
        if 'emotion_tags' in data:
            diary.emotion_tags = data['emotion_tags']

        # 更新情绪强度
        if 'emotion_score' in data:
            diary.emotion_score = data['emotion_score']

        # 更新触发事件
        if 'trigger_event' in data:
            trigger_event = data['trigger_event'].strip() if data['trigger_event'] else None
            diary.trigger_event = trigger_event

        # 更新图片
        if 'images' in data:
            diary.images = data['images']

        # 重置分析状态
        diary.analysis_status = 'pending'
        diary.updated_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'message': 'Diary updated successfully',
            'diary': diary.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update diary: {str(e)}'}), 500

@bp.route('/<int:diary_id>', methods=['DELETE'])
@jwt_required()
def delete_diary(diary_id):
    """删除日记（同时删除关联的明信片和图片文件）"""
    try:
        user_id = get_jwt_identity()

        # 查询日记
        diary = EmotionDiary.query.filter_by(id=diary_id, user_id=user_id).first()

        if not diary:
            return jsonify({'error': 'Diary not found'}), 404

        # 1. 先删除关联的明信片图片文件
        postcard = Postcard.query.filter_by(diary_id=diary_id, user_id=user_id).first()
        if postcard and postcard.image_url:
            try:
                from services.postcard_service import delete_postcard_image
                delete_postcard_image(postcard.image_url)
                print(f"[日记删除] 已删除明信片图片: {postcard.image_url}", file=sys.stderr)
            except Exception as img_err:
                print(f"[日记删除] 删除明信片图片失败（不影响日记删除）: {img_err}", file=sys.stderr)

        # 2. 删除明信片数据库记录（如果没有设置级联删除）
        if postcard:
            db.session.delete(postcard)
            print(f"[日记删除] 已删除明信片记录 #{postcard.id}", file=sys.stderr)

        # 3. 删除探险会话记录
        adventure = AdventureSession.query.filter_by(diary_id=diary_id, user_id=user_id).first()
        if adventure:
            db.session.delete(adventure)
            print(f"[日记删除] 已删除探险记录 #{adventure.id}", file=sys.stderr)

        # 4. 删除日记（会级联删除EmotionAnalysis）
        db.session.delete(diary)
        db.session.commit()

        print(f"[日记删除] 日记 #{diary_id} 及关联数据删除成功", file=sys.stderr)

        return jsonify({
            'message': 'Diary deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"[日记删除] 删除失败: {str(e)}", file=sys.stderr)
        return jsonify({'error': f'Failed to delete diary: {str(e)}'}), 500

@bp.route('/stats', methods=['GET'])
@jwt_required()
def get_diary_stats():
    """获取日记统计信息"""
    try:
        user_id = get_jwt_identity()

        # 计算统计信息
        total_diaries = EmotionDiary.query.filter_by(user_id=user_id).count()

        # 最近7天的日记数量
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_diaries = EmotionDiary.query.filter(
            EmotionDiary.user_id == user_id,
            EmotionDiary.created_at >= seven_days_ago
        ).count()

        # 按情绪标签统计
        all_diaries = EmotionDiary.query.filter_by(user_id=user_id).all()
        emotion_stats = {}

        for diary in all_diaries:
            for tag in diary.emotion_tags:
                if tag not in emotion_stats:
                    emotion_stats[tag] = 0
                emotion_stats[tag] += 1

        user = db.session.get(User, user_id)
        weeks_since_signup = 1
        if user and user.created_at:
            days_since_signup = max(1, (datetime.utcnow() - user.created_at).days)
            weeks_since_signup = max(1, days_since_signup / 7)

        return jsonify({
            'total_diaries': total_diaries,
            'recent_diaries': recent_diaries,
            'emotion_stats': emotion_stats,
            'avg_diaries_per_week': round(total_diaries / weeks_since_signup, 2)
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get diary stats: {str(e)}'}), 500

@bp.route('/search', methods=['GET'])
@jwt_required()
def search_diaries():
    """搜索日记"""
    try:
        user_id = get_jwt_identity()

        # 获取搜索参数
        keyword = request.args.get('keyword', '').strip()
        emotion_tag = request.args.get('emotion_tag', '').strip()
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')

        # 基础查询
        query = EmotionDiary.query.filter_by(user_id=user_id)

        # 关键词搜索
        if keyword:
            query = query.filter(EmotionDiary.content.contains(keyword))

        # 情绪标签筛选（兼容MySQL和SQLite的JSON查询）
        if emotion_tag:
            # 使用LIKE模式匹配JSON数组中的标签
            query = query.filter(EmotionDiary.emotion_tags.like(f'%"{emotion_tag}"%'))

        # 日期范围筛选
        if date_from:
            try:
                # 支持 YYYY-MM-DD 或 YYYY-MM-DDTHH:MM:SS 格式
                from_date = datetime.fromisoformat(date_from.replace('T', ' ').split('.')[0])
                query = query.filter(EmotionDiary.created_at >= from_date)
            except ValueError:
                pass

        if date_to:
            try:
                # 支持 YYYY-MM-DD 或 YYYY-MM-DDTHH:MM:SS 格式
                to_date_str = date_to.replace('T', ' ').split('.')[0]
                to_date = datetime.fromisoformat(to_date_str)
                # 如果只有日期没有时间，则包含整天
                if len(date_to) <= 10:
                    to_date = to_date + timedelta(days=1) - timedelta(seconds=1)
                query = query.filter(EmotionDiary.created_at <= to_date)
            except ValueError:
                pass

        # 执行查询
        diaries = query.order_by(EmotionDiary.created_at.desc()).all()

        return jsonify({
            'diaries': [diary.to_dict() for diary in diaries],
            'total': len(diaries)
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to search diaries: {str(e)}'}), 500

@bp.route('/<int:diary_id>/ai-analyze', methods=['POST'])
@jwt_required()
def analyze_diary_with_ai(diary_id):
    """使用AI分析日记的CBT内容"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}

        # 查询日记
        diary = EmotionDiary.query.filter_by(id=diary_id, user_id=user_id).first()

        if not diary:
            return jsonify({'error': 'Diary not found'}), 404

        # 导入分析服务
        try:
            from routes.analysis import EmotionAnalysisService
            analysis_service = EmotionAnalysisService()
        except ImportError:
            return jsonify({'error': 'Analysis service not available'}), 500

        # 准备分析数据
        analysis_data = {
            'content': diary.content,
            'emotion_tags': data.get('emotions', diary.emotion_tags),
            'trigger_event': data.get('trigger_event', diary.trigger_event),
            'intensity': data.get('intensity', diary.emotion_score.get('intensity') if diary.emotion_score else 5)
        }

        # 调用AI分析（CBT专用prompt）
        try:
            analysis_result = analysis_service.analyze_cbt_content(
                diary_id=diary.id,
                content=analysis_data['content'],
                emotions=analysis_data['emotion_tags'],
                trigger_event=analysis_data['trigger_event'],
                intensity=analysis_data['intensity']
            )

            # 更新日记状态
            diary.analysis_status = 'completed'
            db.session.commit()

            return jsonify({
                'message': 'Analysis completed successfully',
                'analysis': analysis_result
            }), 200

        except Exception as analysis_error:
            # AI分析失败，返回友好错误
            return jsonify({
                'error': 'AI analysis failed',
                'message': str(analysis_error),
                'fallback': {
                    'overall_emotion': analysis_data['emotion_tags'][0] if analysis_data['emotion_tags'] else '未知',
                    'emotion_intensity': analysis_data['intensity'] / 10.0,
                    'suggestions': [
                        '尝试识别引发这种情绪的具体想法',
                        '思考这些想法是否有事实依据',
                        '寻找更平衡的视角看待问题'
                    ]
                }
            }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to analyze diary: {str(e)}'}), 500


@bp.route('/<int:diary_id>/ai-analyze-stream', methods=['GET', 'POST', 'OPTIONS'])
def analyze_diary_stream(diary_id):
    """流式AI分析日记（SSE）"""
    from flask import Response, stream_with_context
    from flask_jwt_extended import verify_jwt_in_request
    import json
    import traceback

    # 处理OPTIONS请求（CORS预检）
    if request.method == 'OPTIONS':
        return '', 200

    try:
        # 手动验证JWT token（支持URL参数）
        try:
            # EventSource不支持header，从URL参数获取token
            token_from_url = request.args.get('token')
            if token_from_url:
                from flask_jwt_extended import decode_token
                decoded = decode_token(token_from_url)
                user_id = decoded['sub']
                print(f"[流式分析] URL token验证成功，用户ID: {user_id}, 日记ID: {diary_id}", file=sys.stderr)
            else:
                verify_jwt_in_request()
                user_id = get_jwt_identity()
                print(f"[流式分析] JWT验证成功，用户ID: {user_id}, 日记ID: {diary_id}", file=sys.stderr)
        except Exception as jwt_error:
            print(f"[流式分析错误] JWT验证失败: {jwt_error}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return jsonify({'error': 'Unauthorized', 'detail': str(jwt_error)}), 401

        # 尝试获取JSON数据，如果失败则使用空字典
        try:
            request_data = request.get_json(force=True, silent=True) or {}
            print(f"[流式分析] 请求数据: {request_data}", file=sys.stderr)
        except Exception as e:
            print(f"[流式分析错误] 解析请求数据失败: {e}", file=sys.stderr)
            request_data = {}
    except Exception as e:
        print(f"[流式分析错误] 初始化失败: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return jsonify({'error': str(e)}), 500

    def generate():
        try:
            # 查询日记
            diary = EmotionDiary.query.filter_by(id=diary_id, user_id=user_id).first()

            if not diary:
                yield f"data: {json.dumps({'type': 'error', 'data': {'message': 'Diary not found'}})}\n\n"
                return

            # 导入分析服务
            try:
                from routes.analysis import EmotionAnalysisService
                analysis_service = EmotionAnalysisService()
            except ImportError:
                yield f"data: {json.dumps({'type': 'error', 'data': {'message': 'Analysis service not available'}})}\n\n"
                return

            # 准备分析数据
            analysis_data = {
                'content': diary.content,
                'emotion_tags': request_data.get('emotions', diary.emotion_tags),
                'trigger_event': request_data.get('trigger_event', diary.trigger_event),
                'intensity': request_data.get('intensity', diary.emotion_score.get('intensity') if diary.emotion_score else 5)
            }

            # 流式调用AI分析
            full_analysis_data = None
            for event in analysis_service.analyze_cbt_content_stream(
                content=analysis_data['content'],
                emotions=analysis_data['emotion_tags'],
                trigger_event=analysis_data['trigger_event'],
                intensity=analysis_data['intensity']
            ):
                # 发送SSE事件
                yield f"data: {json.dumps(event)}\n\n"

                # 如果是游戏数据，保存到变量中用于后续存储
                if event['type'] == 'game_data':
                    full_analysis_data = event['data']

            # 保存分析结果到数据库
            if full_analysis_data:
                from datetime import datetime
                analysis_result = {
                    'user_message': full_analysis_data.get('user_message', ''),
                    'overall_emotion': full_analysis_data['overall_emotion'],
                    'emotion_intensity': full_analysis_data['emotion_intensity'],
                    'cognitive_distortions': full_analysis_data['cognitive_distortions'],
                    'suggestions': full_analysis_data['suggestions'],
                    'recommended_game': full_analysis_data['recommended_game'],
                    'game_values': full_analysis_data['game_values'],
                    'emotion_analysis': full_analysis_data['emotion_analysis'],
                    'challenges': full_analysis_data['challenges'],
                    'recommendations': full_analysis_data['recommendations'],
                    'ai_model_version': full_analysis_data['ai_model_version'],
                    'analysis_timestamp': datetime.utcnow().isoformat()
                }

                # 调用保存方法
                analysis_service._save_analysis_result(diary_id, analysis_result)

                # 更新日记状态
                diary.analysis_status = 'completed'
                db.session.commit()

            # 发送完成事件
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',  # 禁用Nginx缓冲
            'Connection': 'keep-alive'
        }
    )
