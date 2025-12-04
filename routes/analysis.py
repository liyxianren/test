"""
情绪分析路由模块 - 简化版

核心功能：
- 统一的日记分析端点 (unified-analyze)
- 使用ChatGLM进行CBT分析
- 增量模式更新GameState
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import EmotionAnalysis, EmotionDiary, GameState, Postcard, db
from datetime import datetime
import json
import os
import re
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入智谱AI SDK
try:
    from zhipuai import ZhipuAI
except ImportError:
    ZhipuAI = None
    print("警告: 未安装 zhipuai 包，ChatGLM功能将不可用", file=sys.stderr)

# 导入Prompt模板
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from prompts.chatglm_prompts import get_unified_prompt, get_system_prompt
except ImportError:
    print("警告: 未找到chatglm_prompts模块，使用默认Prompt", file=sys.stderr)
    get_unified_prompt = None
    get_system_prompt = None

# 导入明信片服务
try:
    from services.postcard_service import create_postcard_async
except ImportError:
    print("警告: 未找到postcard_service模块，明信片功能将不可用", file=sys.stderr)
    create_postcard_async = None

bp = Blueprint('analysis', __name__)


# ==================== 工具函数 ====================

def clamp(value, min_val, max_val):
    """将数值限制在指定范围内"""
    return max(min_val, min(max_val, value))


def fallback_calculate(diary, game_state):
    """
    降级计算：当AI调用失败时使用本地规则计算
    """
    # 从emotion_score中提取intensity
    intensity = 5
    if isinstance(diary.emotion_score, dict):
        intensity = diary.emotion_score.get('intensity', 5)

    emotions = diary.emotion_tags or []

    # 简单的情绪映射规则
    positive_emotions = {'开心', '快乐', '平静', '感恩', '满足', '放松', '兴奋', '希望'}
    negative_emotions = {'焦虑', '担忧', '悲伤', '愤怒', '恐惧', '压力', '沮丧', '失望'}

    is_positive = any(e in positive_emotions for e in emotions)
    is_negative = any(e in negative_emotions for e in emotions)

    # 计算变化值
    if is_positive:
        mental_change = min(5, 1 + intensity // 3)
        stress_change = max(-5, -1 - intensity // 4)
        growth_change = 2
        coins = 25 + intensity * 2
    elif is_negative:
        mental_change = max(-3, -intensity // 4)
        stress_change = min(5, 1 + intensity // 3)
        growth_change = 1  # 写日记本身就是成长
        coins = 15 + intensity  # 负面情绪也给奖励
    else:
        mental_change = 1
        stress_change = 0
        growth_change = 2
        coins = 20

    return {
        'user_message': f'感谢你记录了今天的心情。无论是什么情绪，能够表达出来都是很好的第一步。继续加油！',
        'score_changes': {
            'mental_health_change': mental_change,
            'stress_level_change': stress_change,
            'growth_potential_change': growth_change
        },
        'reasoning': {
            'mental_health_reason': '基于你的情绪状态计算',
            'stress_level_reason': '基于你的情绪类型计算',
            'growth_potential_reason': '写日记本身就是成长'
        },
        'rewards': {
            'coins_earned': coins,
            'bonus_reason': '完成日记记录奖励'
        },
        'cbt_insights': {
            'cognitive_distortions': [],
            'core_beliefs': [],
            'automatic_thoughts': [],
            'recommendations': ['继续保持记录习惯', '尝试识别情绪背后的想法']
        },
        'highlights': ['完成了今天的情绪记录']
    }


# ==================== 核心API端点 ====================

@bp.route('/<int:diary_id>/unified-analyze', methods=['POST'])
@jwt_required()
def unified_analyze(diary_id):
    """
    统一的日记分析端点 - 增量模式

    功能：
    1. 单次ChatGLM调用（使用unified prompt）
    2. 返回：CBT分析 + 分数变化 + 金币奖励
    3. 单一事务更新GameState
    4. 幂等性：已分析的日记返回缓存结果

    返回：
    {
        success: true,
        user_message: "温暖的CBT分析",
        score_changes: {mental_health_change, stress_level_change, growth_potential_change},
        new_scores: {mental_health_score, stress_level, growth_potential},
        rewards: {coins_earned, bonus_reason, level_up, new_level},
        cbt_insights: {...},
        highlights: [...],
        game_state: {coins, level, total_diaries, diaries_to_next_level}
    }
    """
    try:
        user_id = get_jwt_identity()

        # 1. 验证日记存在且属于当前用户
        diary = EmotionDiary.query.filter_by(id=diary_id, user_id=user_id).first()
        if not diary:
            return jsonify({'error': '日记不存在'}), 404

        # 2. 检查是否已分析（幂等性）
        if diary.score_applied:
            # 返回已保存的分析结果
            existing_analysis = EmotionAnalysis.query.filter_by(diary_id=diary_id).first()
            game_state = GameState.query.filter_by(user_id=user_id).first()

            return jsonify({
                'success': True,
                'already_analyzed': True,
                'message': '该日记已分析过',
                'user_message': existing_analysis.analysis_payload.get('user_message', '') if existing_analysis and existing_analysis.analysis_payload else '',
                'new_scores': {
                    'mental_health_score': game_state.mental_health_score if game_state else 50,
                    'stress_level': game_state.stress_level if game_state else 50,
                    'growth_potential': game_state.growth_potential if game_state else 50
                },
                'game_state': game_state.to_dict() if game_state else None
            }), 200

        # 3. 获取或创建GameState
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

        # 4. 获取当前分数
        current_scores = {
            'mental_health_score': game_state.mental_health_score,
            'stress_level': game_state.stress_level,
            'growth_potential': game_state.growth_potential
        }

        # 5. 准备分析数据
        emotions = diary.emotion_tags or []
        intensity = 5
        if isinstance(diary.emotion_score, dict):
            intensity = diary.emotion_score.get('intensity', 5)

        # 6. 调用ChatGLM（统一Prompt）
        analysis_result = None
        use_fallback = False

        zhipu_api_key = os.getenv('ZHIPU_API_KEY')
        if zhipu_api_key and ZhipuAI and get_unified_prompt:
            try:
                client = ZhipuAI(api_key=zhipu_api_key)
                prompt = get_unified_prompt(
                    emotions=emotions,
                    trigger_event=diary.trigger_event or '',
                    intensity=intensity,
                    content=diary.content,
                    current_scores=current_scores
                )

                print(f"[统一分析] 开始调用ChatGLM，日记ID: {diary_id}", file=sys.stderr)

                # 使用GLM-4.5-X模型 - 高性能、强推理、极速响应
                model_name = os.getenv('ZHIPU_MODEL_NAME', 'glm-4.5-x')

                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": get_system_prompt() if get_system_prompt else "你是一位CBT情绪分析师。"},
                        {"role": "user", "content": prompt}
                    ],
                    thinking={"type": "disabled"},  # 关闭深度思考以提升速度
                    temperature=0.7,
                    max_tokens=4096  # 增加输出长度以获得更详细的分析
                )

                raw_response = response.choices[0].message.content.strip()
                print(f"[统一分析] ChatGLM响应长度: {len(raw_response)} 字符", file=sys.stderr)

                # 清理markdown代码块
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
                if json_match:
                    raw_response = json_match.group(1)

                # 解析JSON
                try:
                    analysis_result = json.loads(raw_response)
                except json.JSONDecodeError:
                    # 尝试提取JSON对象
                    json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
                    if json_match:
                        analysis_result = json.loads(json_match.group(0))
                    else:
                        raise

                print(f"[统一分析] JSON解析成功", file=sys.stderr)

            except Exception as e:
                print(f"[统一分析] ChatGLM调用失败: {str(e)}, 使用降级计算", file=sys.stderr)
                use_fallback = True
        else:
            print(f"[统一分析] ChatGLM未配置，使用降级计算", file=sys.stderr)
            use_fallback = True

        # 7. 使用降级计算（如果需要）
        if use_fallback or not analysis_result:
            analysis_result = fallback_calculate(diary, game_state)

        # 8. 提取并验证分数变化
        score_changes = analysis_result.get('score_changes', {})
        mental_change = clamp(score_changes.get('mental_health_change', 0), -5, 5)
        stress_change = clamp(score_changes.get('stress_level_change', 0), -5, 5)
        growth_change = clamp(score_changes.get('growth_potential_change', 0), -5, 5)

        # 9. 提取奖励
        rewards = analysis_result.get('rewards', {})
        coins_earned = clamp(rewards.get('coins_earned', 20), 10, 50)

        # 10. 更新GameState（单一事务）
        previous_scores = {
            'mental_health_score': game_state.mental_health_score,
            'stress_level': game_state.stress_level,
            'growth_potential': game_state.growth_potential
        }

        game_state.mental_health_score = clamp(game_state.mental_health_score + mental_change, 0, 100)
        game_state.stress_level = clamp(game_state.stress_level + stress_change, 0, 100)
        game_state.growth_potential = clamp(game_state.growth_potential + growth_change, 0, 100)
        game_state.coins += coins_earned
        game_state.total_diaries += 1
        game_state.last_active = datetime.utcnow()

        # 检查升级（每10篇日记升1级）
        old_level = game_state.level
        new_level = 1 + (game_state.total_diaries // 10)
        level_up = new_level > old_level
        if level_up:
            game_state.level = new_level

        # 11. 标记日记已分析
        diary.score_applied = True
        diary.analysis_status = 'completed'

        # 12. 保存分析结果到EmotionAnalysis
        existing_analysis = EmotionAnalysis.query.filter_by(diary_id=diary_id).first()
        if existing_analysis:
            existing_analysis.analysis_payload = analysis_result
            existing_analysis.analyzed_at = datetime.utcnow()
            existing_analysis.ai_model_version = os.getenv('ZHIPU_MODEL_NAME', 'glm-4-flash') if not use_fallback else 'fallback'
        else:
            new_analysis = EmotionAnalysis(
                diary_id=diary_id,
                overall_emotion=emotions[0] if emotions else 'unknown',
                emotion_intensity=intensity / 10.0,
                analysis_payload=analysis_result,
                analyzed_at=datetime.utcnow(),
                ai_model_version=os.getenv('ZHIPU_MODEL_NAME', 'glm-4-flash') if not use_fallback else 'fallback'
            )
            db.session.add(new_analysis)

        # 13. 提交事务
        db.session.commit()

        print(f"[统一分析] 分析完成，日记ID: {diary_id}, 金币+{coins_earned}, 升级: {level_up}", file=sys.stderr)

        # 13.5. 触发明信片生成（异步，不阻塞响应）
        postcard_data = None
        if create_postcard_async:
            try:
                postcard_data = create_postcard_async(
                    user_id=user_id,
                    diary_id=diary_id,
                    emotions=emotions,
                    intensity=intensity,
                    mental_health_score=game_state.mental_health_score,
                    diary_content=diary.content,
                    trigger_event=diary.trigger_event
                )
                print(f"[统一分析] 明信片生成已触发", file=sys.stderr)
            except Exception as e:
                print(f"[统一分析] 明信片生成失败（不影响主流程）: {str(e)}", file=sys.stderr)

        # 14. 构建完整响应
        response_data = {
            'success': True,
            'user_message': analysis_result.get('user_message', ''),
            'score_changes': {
                'mental_health_change': mental_change,
                'stress_level_change': stress_change,
                'growth_potential_change': growth_change
            },
            'previous_scores': previous_scores,
            'new_scores': {
                'mental_health_score': game_state.mental_health_score,
                'stress_level': game_state.stress_level,
                'growth_potential': game_state.growth_potential
            },
            'reasoning': analysis_result.get('reasoning', {}),
            'rewards': {
                'coins_earned': coins_earned,
                'bonus_reason': rewards.get('bonus_reason', '完成日记记录'),
                'level_up': level_up,
                'new_level': new_level if level_up else None
            },
            'cbt_insights': analysis_result.get('cbt_insights', {}),
            'highlights': analysis_result.get('highlights', []),
            'game_state': {
                'coins': game_state.coins,
                'level': game_state.level,
                'total_diaries': game_state.total_diaries,
                'diaries_to_next_level': 10 - (game_state.total_diaries % 10) if game_state.total_diaries % 10 != 0 else 10
            },
            'postcard': postcard_data  # 小狐狸明信片数据
        }

        return jsonify(response_data), 200

    except Exception as e:
        db.session.rollback()
        print(f"[统一分析] 错误: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'分析失败: {str(e)}'}), 500


@bp.route('/<int:diary_id>', methods=['GET'])
@jwt_required()
def get_analysis(diary_id):
    """获取日记的情绪分析结果"""
    try:
        user_id = get_jwt_identity()

        # 验证日记所有权
        diary = EmotionDiary.query.filter_by(id=diary_id, user_id=user_id).first()
        if not diary:
            return jsonify({'error': 'Diary not found'}), 404

        # 获取分析结果
        analysis = EmotionAnalysis.query.filter_by(diary_id=diary_id).first()

        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404

        return jsonify({
            'analysis': analysis.to_dict()
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get analysis: {str(e)}'}), 500


@bp.route('/history', methods=['GET'])
@jwt_required()
def get_analysis_history():
    """获取用户的情绪分析历史"""
    try:
        user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)

        # 限制每页数量
        limit = min(limit, 100)

        # 查询用户的分析历史
        query = db.session.query(EmotionAnalysis, EmotionDiary).join(
            EmotionDiary, EmotionAnalysis.diary_id == EmotionDiary.id
        ).filter(
            EmotionDiary.user_id == user_id
        ).order_by(EmotionAnalysis.analyzed_at.desc())

        # 分页
        results = query.paginate(page=page, per_page=limit, error_out=False)

        analysis_list = []
        for analysis, diary in results.items:
            analysis_data = analysis.to_dict()
            analysis_data['diary_content'] = diary.content[:100] + '...' if len(diary.content) > 100 else diary.content
            analysis_list.append(analysis_data)

        return jsonify({
            'analysis_history': analysis_list,
            'pagination': {
                'page': results.page,
                'pages': results.pages,
                'per_page': results.per_page,
                'total': results.total,
                'has_prev': results.has_prev,
                'has_next': results.has_next
            }
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get analysis history: {str(e)}'}), 500
