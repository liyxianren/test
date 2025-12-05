"""
探险API路由 - CBT交互式探险游戏

提供探险会话的创建、挑战提交、完成/跳过等功能
支持AI动态生成挑战题目
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import json
import random
from extensions import db
from models import AdventureSession, UserItem, EmotionDiary, GameState, EmotionAnalysis, Postcard

adventure_bp = Blueprint('adventure', __name__)


# ==================== 从adventure_prompts导入配置 ====================
from prompts.adventure_prompts import (
    MONSTER_CONFIG,
    DISTORTION_TO_MONSTER,
    get_adventure_challenge_prompt,
    get_default_monsters_for_emotion
)

SCENE_NAMES_NEGATIVE = ['迷雾森林', '朦胧山谷', '云雾小径', '暗影峡谷', '薄雾湖畔']
SCENE_NAMES_POSITIVE = ['阳光草地', '彩虹桥', '欢乐花园', '晨曦小径', '星光湖畔']


@adventure_bp.route('/session/<int:diary_id>', methods=['GET', 'POST'])
@jwt_required()
def get_or_create_session(diary_id):
    """获取或创建探险会话 - 支持AI动态生成挑战"""
    user_id = get_jwt_identity()

    # 检查日记是否存在且属于当前用户
    diary = EmotionDiary.query.filter_by(id=diary_id, user_id=user_id).first()
    if not diary:
        return jsonify({'error': '日记不存在'}), 404

    # 检查是否已有探险会话
    session = AdventureSession.query.filter_by(diary_id=diary_id, user_id=user_id).first()

    if session:
        # 直接返回session数据
        result = session.to_dict()
        result['success'] = True
        result['is_new'] = False
        return jsonify(result)

    # 创建新的探险会话
    if request.method == 'POST':
        # 获取情绪分数
        emotion_score = 50  # 默认中性
        if diary.emotion_score:
            if isinstance(diary.emotion_score, dict):
                emotion_score = diary.emotion_score.get('intensity', 5) * 10
            elif isinstance(diary.emotion_score, (int, float)):
                emotion_score = diary.emotion_score

        # 判断正面/负面情绪
        is_positive = emotion_score >= 50

        # 尝试使用AI生成挑战
        monsters, challenges = generate_ai_challenges(
            diary.content,
            diary.emotion_tags or [],
            emotion_score,
            diary.trigger_event
        )

        # 选择场景
        if is_positive:
            scene_name = random.choice(SCENE_NAMES_POSITIVE)
        else:
            scene_name = random.choice(SCENE_NAMES_NEGATIVE)

        session = AdventureSession(
            user_id=user_id,
            diary_id=diary_id,
            status='pending',
            scene_name=scene_name,
            monsters=monsters,
            challenges=challenges,
            current_challenge=0
        )
        db.session.add(session)
        db.session.commit()

        # 直接返回session数据
        result = session.to_dict()
        result['success'] = True
        result['is_new'] = True
        return jsonify(result)

    return jsonify({'error': '探险会话不存在，请使用POST创建'}), 404


@adventure_bp.route('/<int:adventure_id>/start', methods=['POST'])
@jwt_required()
def start_adventure(adventure_id):
    """开始探险"""
    user_id = get_jwt_identity()
    session = AdventureSession.query.filter_by(id=adventure_id, user_id=user_id).first()

    if not session:
        return jsonify({'error': '探险会话不存在'}), 404

    if session.status != 'pending':
        return jsonify({'error': '探险已经开始或已完成'}), 400

    session.status = 'in_progress'
    session.started_at = datetime.utcnow()
    db.session.commit()

    # 直接返回session数据
    result = session.to_dict()
    result['success'] = True
    return jsonify(result)


@adventure_bp.route('/<int:adventure_id>/submit', methods=['POST'])
@jwt_required()
def submit_challenge(adventure_id):
    """提交挑战答案"""
    user_id = get_jwt_identity()
    session = AdventureSession.query.filter_by(id=adventure_id, user_id=user_id).first()

    if not session:
        return jsonify({'error': '探险会话不存在'}), 404

    if session.status != 'in_progress':
        return jsonify({'error': '探险未开始或已完成'}), 400

    data = request.get_json()
    # 兼容前端传递的两种参数名
    selected_answers = data.get('selected_ids', data.get('selected_answers', []))

    challenges = session.challenges or []
    current_idx = session.current_challenge

    if current_idx >= len(challenges):
        return jsonify({'error': '没有更多挑战'}), 400

    challenge = challenges[current_idx]
    correct_ids = challenge.get('correct_ids', [])

    # 检查答案是否正确
    is_correct = set(selected_answers) == set(correct_ids)

    # 更新挑战状态
    challenges[current_idx]['completed'] = True
    challenges[current_idx]['user_answers'] = selected_answers
    challenges[current_idx]['is_correct'] = is_correct

    # 更新怪物状态
    monsters = session.monsters or []
    if current_idx < len(monsters):
        monsters[current_idx]['defeated'] = is_correct

    session.challenges = challenges
    session.monsters = monsters

    # 计算奖励
    reward = None
    if is_correct and current_idx < len(monsters):
        monster = monsters[current_idx]
        monster_type = monster.get('type')
        if monster_type in MONSTER_CONFIG:
            monster_cfg = MONSTER_CONFIG[monster_type]
            reward = monster_cfg.get('reward', {}).copy()
            if not reward:
                reward = {'type': monster_cfg.get('reward', {}).get('type', 'stress_reduce'), 'value': 5}

    # 移动到下一个挑战
    session.current_challenge = current_idx + 1

    # 检查是否所有挑战完成
    all_completed = session.current_challenge >= len(challenges)

    db.session.commit()

    # 计算本次挑战获得的金币
    coins_this_challenge = 15 if is_correct else 0

    return jsonify({
        'success': True,
        'correct': is_correct,
        'correct_ids': correct_ids,
        'reward': reward,
        'coins_earned': coins_this_challenge,
        'challenge_index': current_idx,
        'next_challenge': session.current_challenge if not all_completed else None,
        'is_last': all_completed,
        'cbt_insight': challenge.get('explanation', '')
    })


@adventure_bp.route('/<int:adventure_id>/complete', methods=['POST'])
@jwt_required()
def complete_adventure(adventure_id):
    """完成探险并结算奖励"""
    user_id = get_jwt_identity()
    session = AdventureSession.query.filter_by(id=adventure_id, user_id=user_id).first()

    if not session:
        return jsonify({'error': '探险会话不存在'}), 404

    if session.status == 'completed':
        return jsonify({'error': '探险已完成'}), 400

    # 计算总奖励
    monsters = session.monsters or []
    defeated_count = sum(1 for m in monsters if m.get('defeated'))
    total_monsters = len(monsters)

    # 判断是否探险成功（至少击败一只怪物）
    is_success = defeated_count > 0
    completion_rate = (defeated_count / total_monsters * 100) if total_monsters > 0 else 0

    # 基础金币奖励（只有成功才有）
    if is_success:
        base_coins = 20
        coins_earned = base_coins + (defeated_count * 15)
    else:
        coins_earned = 0

    # 统计属性变化和道具
    stat_changes = {'mental_health': 0, 'stress': 0, 'growth': 0}
    items_earned = []

    for i, monster in enumerate(monsters):
        if monster.get('defeated'):
            monster_type = monster.get('type')
            if monster_type in MONSTER_CONFIG:
                monster_cfg = MONSTER_CONFIG[monster_type]
                reward = monster_cfg.get('reward', {})

                reward_item = {
                    'name': f"{monster_type}_reward",
                    'name_zh': monster_cfg.get('defeat_message', '击败奖励'),
                    'effect_type': reward.get('type', 'mental_boost'),
                    'effect_value': reward.get('value', 3)
                }
                items_earned.append(reward_item)

                # 累计属性变化
                effect_type = reward_item['effect_type']
                effect_value = reward_item['effect_value']
                if effect_type == 'stress_reduce':
                    stat_changes['stress'] -= effect_value
                elif effect_type == 'mental_boost':
                    stat_changes['mental_health'] += effect_value
                elif effect_type == 'growth_boost':
                    stat_changes['growth'] += effect_value

    # 获取日记
    diary = EmotionDiary.query.get(session.diary_id)

    # 更新GameState（只有成功才更新）
    game_state = GameState.query.filter_by(user_id=user_id).first()
    old_level = game_state.level if game_state else 1
    new_level = old_level

    if game_state and is_success:
        game_state.coins += coins_earned
        game_state.mental_health_score = max(0, min(100, game_state.mental_health_score + stat_changes['mental_health']))
        game_state.stress_level = max(0, min(100, game_state.stress_level + stat_changes['stress']))
        game_state.growth_potential = max(0, min(100, game_state.growth_potential + stat_changes['growth']))

        # 只有日记未计分才增加日记计数（防止重复计分）
        if diary and not diary.score_applied:
            game_state.total_diaries += 1
            diary.score_applied = True
            diary.analysis_status = 'completed'

            # 检查升级（每10篇日记升1级）
            new_level = 1 + (game_state.total_diaries // 10)
            if new_level > old_level:
                game_state.level = new_level
                coins_earned += 50  # 升级奖励
                game_state.coins += 50

        game_state.last_active = datetime.utcnow()

    # 添加道具到用户背包（只有成功才添加）
    if is_success:
        for item in items_earned:
            existing_item = UserItem.query.filter_by(
                user_id=user_id,
                item_name=item['name']
            ).first()
            if existing_item:
                existing_item.quantity += 1
            else:
                new_item = UserItem(
                    user_id=user_id,
                    item_name=item['name'],
                    item_name_zh=item['name_zh'],
                    item_type='healing',
                    effect_type=item['effect_type'],
                    effect_value=item['effect_value']
                )
                db.session.add(new_item)

    # 更新探险会话状态
    if is_success:
        session.status = 'completed'
    else:
        session.status = 'failed'  # 失败状态，可以重试

    session.completed_at = datetime.utcnow()
    session.coins_earned = coins_earned
    session.items_earned = items_earned
    session.stat_changes = stat_changes

    # 只有探险成功才创建/更新明信片
    postcard = None
    postcard_id = None

    # 构建探险结果（用于明信片生成）
    adventure_result = {
        'defeated_count': defeated_count,
        'total_monsters': total_monsters
    }

    if is_success:
        postcard = Postcard.query.filter_by(diary_id=session.diary_id, user_id=user_id).first()
        if postcard:
            postcard.stat_changes = stat_changes
            postcard.coins_earned = coins_earned
            print(f"[探险] 已更新明信片 #{postcard.id} 的探险收获")
        elif diary:
            # 明信片还不存在，创建一个pending状态的记录
            print(f"[探险] 探险成功，创建pending明信片")
            postcard = Postcard(
                user_id=user_id,
                diary_id=session.diary_id,
                location_name=session.scene_name or '迷雾森林',
                message='',  # 等待AI生成
                status='pending',  # 等待AI生成内容和图片
                emotion_tags=diary.emotion_tags or [],
                emotion_intensity=diary.emotion_score.get('intensity', 5) if isinstance(diary.emotion_score, dict) else 5,
                mental_health_score=game_state.mental_health_score if game_state else 50,
                stat_changes=stat_changes,
                coins_earned=coins_earned
            )
            db.session.add(postcard)
            db.session.flush()  # 获取ID

            # 触发后台生成明信片内容（传递探险结果）
            trigger_postcard_generation(postcard.id, diary, session.scene_name, adventure_result)

        postcard_id = postcard.id if postcard else None
    else:
        print(f"[探险] 探险失败，不生成明信片，用户可重试")

    db.session.commit()

    return jsonify({
        'success': True,
        'is_victory': is_success,
        'can_retry': not is_success,  # 失败可以重试
        'monsters_defeated': defeated_count,
        'total_monsters': total_monsters,
        'completion_rate': completion_rate,
        'coins_earned': coins_earned,
        'items_earned': items_earned,
        'stat_changes': stat_changes,
        'level_up': new_level > old_level,
        'new_level': new_level if new_level > old_level else None,
        'game_state': game_state.to_dict() if game_state else None,
        'adventure': session.to_dict(),
        'postcard_id': postcard_id,
        'postcard_message': '小橘稍后会给你寄明信片哦～' if is_success else None
    })


def trigger_postcard_generation(postcard_id, diary, scene_name, adventure_result=None):
    """触发后台生成明信片内容（异步）

    参数:
        postcard_id: 明信片ID
        diary: 日记对象
        scene_name: 场景名称
        adventure_result: 探险结果 {'defeated_count': N, 'total_monsters': M}
    """
    from concurrent.futures import ThreadPoolExecutor
    import sys

    def generate_task():
        from app import app
        with app.app_context():
            try:
                from services.postcard_service import generate_postcard_data, generate_postcard_image
                from models import Postcard, db

                postcard = Postcard.query.get(postcard_id)
                if not postcard:
                    return

                print(f"[明信片生成] 开始为明信片 #{postcard_id} 生成内容", file=sys.stderr)

                # 生成文本数据（传递探险结果）
                postcard_data = generate_postcard_data(
                    emotions=diary.emotion_tags or [],
                    intensity=diary.emotion_score.get('intensity', 5) if isinstance(diary.emotion_score, dict) else 5,
                    mental_health_score=postcard.mental_health_score or 50,
                    diary_content=diary.content,
                    trigger_event=diary.trigger_event,
                    adventure_result=adventure_result
                )

                # 更新明信片内容
                postcard.image_prompt = postcard_data['image_prompt']
                postcard.location_name = postcard_data.get('location_name', scene_name) or scene_name
                postcard.message = postcard_data['message']
                db.session.commit()

                # 生成图片
                image_url = generate_postcard_image(postcard_data['image_prompt'])
                if image_url:
                    postcard.image_url = image_url
                    postcard.status = 'completed'
                    postcard.generated_at = datetime.utcnow()
                else:
                    postcard.status = 'completed'  # 即使图片失败，文字内容也算完成

                db.session.commit()
                print(f"[明信片生成] 明信片 #{postcard_id} 生成完成", file=sys.stderr)

            except Exception as e:
                print(f"[明信片生成] 生成失败: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()

    # 提交后台任务
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(generate_task)


@adventure_bp.route('/<int:adventure_id>/retry', methods=['POST'])
@jwt_required()
def retry_adventure(adventure_id):
    """重试失败的探险"""
    user_id = get_jwt_identity()
    session = AdventureSession.query.filter_by(id=adventure_id, user_id=user_id).first()

    if not session:
        return jsonify({'error': '探险会话不存在'}), 404

    if session.status != 'failed':
        return jsonify({'error': '只有失败的探险才能重试'}), 400

    # 重置探险状态
    session.status = 'pending'
    session.current_challenge = 0
    session.completed_at = None
    session.coins_earned = 0
    session.items_earned = []
    session.stat_changes = {}

    # 重置挑战和怪物状态
    challenges = session.challenges or []
    for c in challenges:
        c['completed'] = False
        c['user_answers'] = []
        c['is_correct'] = False

    monsters = session.monsters or []
    for m in monsters:
        m['defeated'] = False

    session.challenges = challenges
    session.monsters = monsters

    db.session.commit()

    result = session.to_dict()
    result['success'] = True
    result['message'] = '探险已重置，可以重新开始'
    return jsonify(result)


@adventure_bp.route('/<int:adventure_id>/skip', methods=['POST'])
@jwt_required()
def skip_adventure(adventure_id):
    """跳过探险（不获得奖励）"""
    user_id = get_jwt_identity()
    session = AdventureSession.query.filter_by(id=adventure_id, user_id=user_id).first()

    if not session:
        return jsonify({'error': '探险会话不存在'}), 404

    if session.status in ['completed', 'skipped']:
        return jsonify({'error': '探险已完成或已跳过'}), 400

    session.status = 'skipped'
    session.completed_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'success': True,
        'message': '已跳过探险',
        'adventure': session.to_dict()
    })


@adventure_bp.route('/items', methods=['GET'])
@jwt_required()
def get_user_items():
    """获取用户道具列表"""
    user_id = get_jwt_identity()
    items = UserItem.query.filter_by(user_id=user_id).all()

    return jsonify({
        'success': True,
        'items': [item.to_dict() for item in items]
    })


# ==================== AI出题功能 ====================

def generate_ai_challenges(diary_content, emotion_tags, emotion_score, trigger_event):
    """
    使用AI生成挑战题目
    如果AI失败，使用本地模板作为后备
    """
    print(f"[探险] 开始生成挑战，情绪分数: {emotion_score}")

    try:
        # 调用AI生成挑战
        ai_result = call_ai_for_challenges(diary_content, emotion_tags, emotion_score, trigger_event)

        if ai_result:
            print(f"[探险] AI生成成功，场景: {ai_result.get('scene_name')}")
            monsters = ai_result.get('monsters', [])
            challenges = ai_result.get('challenges', [])

            # 确保数据格式正确
            formatted_monsters = []
            for m in monsters:
                monster_type = m.get('type', 'dark_cloud')
                formatted_monsters.append({
                    'type': monster_type,
                    'name_zh': m.get('name', MONSTER_CONFIG.get(monster_type, {}).get('name_zh', '迷雾怪')),
                    'description': m.get('description', ''),
                    'defeated': False
                })

            formatted_challenges = []
            for c in challenges:
                # 确保选项格式正确
                options = c.get('options', [])
                formatted_options = []
                for i, opt in enumerate(options):
                    formatted_options.append({
                        'id': opt.get('id', chr(97 + i)),  # a, b, c...
                        'text': opt.get('text', ''),
                        'is_correct': opt.get('is_correct', False)
                    })

                formatted_challenges.append({
                    'type': c.get('type', 'evidence'),
                    'monster_type': c.get('monster_type', 'dark_cloud'),
                    'distortion_thought': c.get('distortion_thought', ''),
                    'question': c.get('question', '请选择正确的选项'),
                    'instruction': c.get('instruction', '选择正确答案'),
                    'options': formatted_options,
                    'correct_ids': c.get('correct_ids', [opt['id'] for opt in formatted_options if opt.get('is_correct')]),
                    'correct_count': len([opt for opt in formatted_options if opt.get('is_correct')]),
                    'completed': False,
                    'explanation': c.get('explanation', '')
                })

            return formatted_monsters, formatted_challenges

    except Exception as e:
        print(f"[探险] AI生成失败: {e}")

    # AI失败，使用本地模板
    print("[探险] 使用本地模板生成挑战")
    return generate_fallback_challenges(emotion_score, emotion_tags, trigger_event)


def call_ai_for_challenges(diary_content, emotion_tags, emotion_score, trigger_event):
    """
    调用豆包AI生成挑战内容

    使用紧凑格式：AI只返回核心内容（约30字/题），后端组装完整题目
    速度：约15-18秒生成3道题（比原来34秒快一倍）
    """
    try:
        from services.doubao_service import generate_cbt_challenges

        print(f"[探险] 调用豆包AI生成挑战")
        print(f"[探险] 日记内容预览: {diary_content[:100] if diary_content else '空'}...")

        result = generate_cbt_challenges(
            diary_content=diary_content,
            emotion_tags=emotion_tags,
            emotion_score=emotion_score
        )

        print(f"[探险] 豆包AI生成成功，场景: {result.get('scene_name')}")
        return result

    except Exception as e:
        print(f"[探险] 豆包AI调用失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_fallback_challenges(emotion_score, emotion_tags, trigger_event):
    """本地模板生成挑战（后备方案）- 生成3-4道题"""
    is_positive = emotion_score >= 50

    if is_positive:
        # 正面情绪挑战 - 肯定自己（3道题）
        monsters = [
            {
                'type': 'gratitude_thief',
                'name_zh': '感恩小偷',
                'description': '想偷走你对美好事物的感恩',
                'defeated': False
            },
            {
                'type': 'achievement_eraser',
                'name_zh': '橡皮擦怪',
                'description': '想抹去你的成就感',
                'defeated': False
            },
            {
                'type': 'confidence_shadow',
                'name_zh': '自信阴影',
                'description': '想遮蔽你的自信光芒',
                'defeated': False
            }
        ]

        challenges = [
            {
                'type': 'evidence',
                'monster_type': 'gratitude_thief',
                'distortion_thought': '',
                'question': '今天有什么值得感恩的事情？选出能够体现感恩的想法：',
                'instruction': '选择正确的选项来击败感恩小偷',
                'options': [
                    {'id': 'a', 'text': '今天发生的好事只是运气，不值得感恩', 'is_correct': False},
                    {'id': 'b', 'text': '我应该珍惜今天的美好时刻', 'is_correct': True},
                    {'id': 'c', 'text': '感恩是矫情的表现', 'is_correct': False}
                ],
                'correct_ids': ['b'],
                'correct_count': 1,
                'completed': False,
                'explanation': '感恩能帮助我们关注生活中的积极面，提升幸福感。每天记录值得感恩的事情是培养积极心态的好方法。'
            },
            {
                'type': 'reframe',
                'monster_type': 'achievement_eraser',
                'distortion_thought': '这件事做得好只是因为运气',
                'question': '面对自己的成就，哪个想法更能肯定自己？',
                'instruction': '选择更积极的想法来击败橡皮擦怪',
                'options': [
                    {'id': 'a', 'text': '这次成功是我努力的结果，值得为自己骄傲', 'is_correct': True},
                    {'id': 'b', 'text': '可能下次就没这么幸运了', 'is_correct': False},
                    {'id': 'c', 'text': '别人做得比我更好', 'is_correct': False}
                ],
                'correct_ids': ['a'],
                'correct_count': 1,
                'completed': False,
                'explanation': '承认自己的成就并为之骄傲是健康的自我肯定。不要让"冒充者综合征"偷走你的成就感！'
            },
            {
                'type': 'evidence',
                'monster_type': 'confidence_shadow',
                'distortion_thought': '我没什么特别的优点',
                'question': '想想自己的优点，选出正确的自我认知：',
                'instruction': '选择能够肯定自己的想法来击败自信阴影',
                'options': [
                    {'id': 'a', 'text': '每个人都有独特的优点，包括我自己', 'is_correct': True},
                    {'id': 'b', 'text': '我的优点不值一提', 'is_correct': False},
                    {'id': 'c', 'text': '只有比别人强才算优点', 'is_correct': False}
                ],
                'correct_ids': ['a'],
                'correct_count': 1,
                'completed': False,
                'explanation': '自信来自于对自己的客观认知。你不需要完美，也不需要比任何人都强，你本身就有独特的价值。'
            }
        ]
    else:
        # 负面情绪挑战 - 不要否定自己（4道题）
        monsters = [
            {
                'type': 'dark_cloud',
                'name_zh': '黑云怪',
                'description': '把事情想象得比实际更糟糕',
                'defeated': False
            },
            {
                'type': 'checkerboard',
                'name_zh': '棋盘精',
                'description': '只看两个极端，忽视中间地带',
                'defeated': False
            },
            {
                'type': 'label_monster',
                'name_zh': '标签怪',
                'description': '给自己贴上负面的固定标签',
                'defeated': False
            },
            {
                'type': 'blame_magnet',
                'name_zh': '磁铁怪',
                'description': '把所有责任都揽到自己身上',
                'defeated': False
            }
        ]

        thought = trigger_event if trigger_event else "事情一定会变得很糟糕"

        challenges = [
            {
                'type': 'evidence',
                'monster_type': 'dark_cloud',
                'distortion_thought': thought,
                'question': f'面对「{thought}」这个想法，找出能够反驳它的证据：',
                'instruction': '选择能够反驳负面想法的证据（选3个）',
                'options': [
                    {'id': 'a', 'text': '过去类似的情况，结果并没有那么糟糕', 'is_correct': True},
                    {'id': 'b', 'text': '我的感觉一定是对的', 'is_correct': False},
                    {'id': 'c', 'text': '我有能力应对这种情况', 'is_correct': True},
                    {'id': 'd', 'text': '最坏的情况发生的概率其实很小', 'is_correct': True}
                ],
                'correct_ids': ['a', 'c', 'd'],
                'correct_count': 3,
                'completed': False,
                'explanation': '通过收集客观证据，我们可以打破灾难化思维。记住：感受不等于事实，大多数我们担心的事情其实不会发生。'
            },
            {
                'type': 'reframe',
                'monster_type': 'checkerboard',
                'distortion_thought': '如果不能做到完美，就是彻底的失败',
                'question': '面对这个非黑即白的想法，哪个替代想法更健康？',
                'instruction': '选择更平衡的想法来击败棋盘精',
                'options': [
                    {'id': 'a', 'text': '即使不完美，也有值得肯定的地方', 'is_correct': True},
                    {'id': 'b', 'text': '要么全力以赴，要么干脆放弃', 'is_correct': False},
                    {'id': 'c', 'text': '做不好就是我的问题', 'is_correct': False}
                ],
                'correct_ids': ['a'],
                'correct_count': 1,
                'completed': False,
                'explanation': '世界不是非黑即白的。承认中间地带，接受"足够好"，是减少焦虑和自我苛责的好方法。'
            },
            {
                'type': 'reframe',
                'monster_type': 'label_monster',
                'distortion_thought': '我就是一个失败者/笨蛋/没用的人',
                'question': '当你给自己贴负面标签时，哪个想法更客观？',
                'instruction': '选择更准确的自我认知来击败标签怪',
                'options': [
                    {'id': 'a', 'text': '一次失败不能定义我整个人，我有很多面', 'is_correct': True},
                    {'id': 'b', 'text': '事实证明我就是这样的人', 'is_correct': False},
                    {'id': 'c', 'text': '别人肯定也这么看我', 'is_correct': False}
                ],
                'correct_ids': ['a'],
                'correct_count': 1,
                'completed': False,
                'explanation': '给自己贴标签是一种过度简化。你是一个复杂的、多面的人，不能被任何单一标签所定义。'
            },
            {
                'type': 'evidence',
                'monster_type': 'blame_magnet',
                'distortion_thought': '这件事出了问题都是我的错',
                'question': '当你把所有责任都揽到自己身上时，请思考：',
                'instruction': '选择更客观的归因方式来击败磁铁怪',
                'options': [
                    {'id': 'a', 'text': '很多因素会影响结果，不都是我能控制的', 'is_correct': True},
                    {'id': 'b', 'text': '如果我做得更好，就不会这样', 'is_correct': False},
                    {'id': 'c', 'text': '我应该为所有事情负责', 'is_correct': False}
                ],
                'correct_ids': ['a'],
                'correct_count': 1,
                'completed': False,
                'explanation': '个人化思维让我们承担了不属于自己的责任。客观看待事情，区分什么是你能控制的，什么不是。'
            }
        ]

    return monsters, challenges
