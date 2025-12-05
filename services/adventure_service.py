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
    """

    def generate_task():
        from app import app
        with app.app_context():
            try:
                from models import AdventureSession, EmotionDiary, db
                from routes.adventure import generate_ai_challenges, SCENE_NAMES_POSITIVE, SCENE_NAMES_NEGATIVE

                # 检查是否已存在
                existing = AdventureSession.query.filter_by(
                    diary_id=diary_id,
                    user_id=user_id
                ).first()

                if existing:
                    print(f"[探险预生成] 探险会话已存在，跳过", file=sys.stderr)
                    return

                print(f"[探险预生成] 开始为日记 #{diary_id} 生成探险题目", file=sys.stderr)

                # 计算情绪分数
                score = 50
                if isinstance(emotion_score, dict):
                    score = emotion_score.get('intensity', 5) * 10
                elif isinstance(emotion_score, (int, float)):
                    score = emotion_score

                is_positive = score >= 50

                # 调用AI生成
                monsters, challenges = generate_ai_challenges(
                    diary_content,
                    emotion_tags or [],
                    score,
                    trigger_event
                )

                # 选择场景
                if is_positive:
                    scene_name = random.choice(SCENE_NAMES_POSITIVE)
                else:
                    scene_name = random.choice(SCENE_NAMES_NEGATIVE)

                # 创建探险会话
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

                print(f"[探险预生成] 探险会话创建成功，ID: {session.id}", file=sys.stderr)

            except Exception as e:
                print(f"[探险预生成] 生成失败: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()

    # 提交后台任务
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(generate_task)
