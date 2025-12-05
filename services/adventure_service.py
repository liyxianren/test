# -*- coding: utf-8 -*-
"""
探险服务模块

提供异步生成探险题目的功能
在日记提交时预生成，用户进入探险页面时直接使用
"""
import sys
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime


def create_adventure_async(
    user_id: int,
    diary_id: int,
    diary_content: str,
    emotion_tags: list,
    emotion_score: dict,
    trigger_event: str = None
):
    """
    异步创建探险会话（后台预生成题目）

    在日记提交时调用，后台生成AI题目
    用户进入探险页面时如果已生成则直接使用

    流程：
    1. 先创建 status='generating' 的占位会话
    2. 后台生成AI题目
    3. 更新会话内容，status='pending'
    """
    from app import app

    # 先在主线程创建占位会话（避免重复创建）
    with app.app_context():
        from models import AdventureSession, db
        from routes.adventure import SCENE_NAMES_POSITIVE, SCENE_NAMES_NEGATIVE

        # 检查是否已存在
        existing = AdventureSession.query.filter_by(
            diary_id=diary_id,
            user_id=user_id
        ).first()

        if existing:
            print(f"[探险预生成] 探险会话已存在，跳过", file=sys.stderr)
            return

        # 计算情绪分数
        score = 50
        if isinstance(emotion_score, dict):
            score = emotion_score.get('intensity', 5) * 10
        elif isinstance(emotion_score, (int, float)):
            score = emotion_score

        is_positive = score >= 50

        # 选择场景
        if is_positive:
            scene_name = random.choice(SCENE_NAMES_POSITIVE)
        else:
            scene_name = random.choice(SCENE_NAMES_NEGATIVE)

        # 创建占位会话（status='generating'表示正在生成中）
        session = AdventureSession(
            user_id=user_id,
            diary_id=diary_id,
            status='generating',  # 标记为生成中
            scene_name=scene_name,
            monsters=[],  # 空数组占位
            challenges=[],
            current_challenge=0
        )
        db.session.add(session)
        db.session.commit()

        session_id = session.id
        print(f"[探险预生成] 创建占位会话 #{session_id}，开始后台生成", file=sys.stderr)

    def generate_task():
        with app.app_context():
            try:
                from models import AdventureSession, db
                from routes.adventure import generate_ai_challenges

                # 重新获取会话
                session = AdventureSession.query.get(session_id)
                if not session:
                    print(f"[探险预生成] 会话 #{session_id} 不存在", file=sys.stderr)
                    return

                if session.status != 'generating':
                    print(f"[探险预生成] 会话 #{session_id} 状态已变更: {session.status}", file=sys.stderr)
                    return

                print(f"[探险预生成] 开始为会话 #{session_id} 生成AI题目", file=sys.stderr)

                # 调用AI生成
                monsters, challenges = generate_ai_challenges(
                    diary_content,
                    emotion_tags or [],
                    score,
                    trigger_event
                )

                # 更新会话
                session.monsters = monsters
                session.challenges = challenges
                session.status = 'pending'  # 标记为可用
                db.session.commit()

                print(f"[探险预生成] 会话 #{session_id} 生成完成，{len(challenges)} 道题目", file=sys.stderr)

            except Exception as e:
                print(f"[探险预生成] 生成失败: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()

                # 生成失败，删除占位会话，让用户可以重新触发
                try:
                    session = AdventureSession.query.get(session_id)
                    if session and session.status == 'generating':
                        db.session.delete(session)
                        db.session.commit()
                        print(f"[探险预生成] 已删除失败的占位会话 #{session_id}", file=sys.stderr)
                except:
                    pass

    # 提交后台任务
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(generate_task)
