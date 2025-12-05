# -*- coding: utf-8 -*-
"""
明信片生成服务

功能：
1. 根据日记分析结果生成小狐狸回信明信片
2. 调用豆包AI生成明信片消息和图片prompt
3. 调用豆包Seedream生成明信片图片
4. 保存明信片到数据库
"""

import os
import sys
import json
import re
import uuid
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# 明信片图片保存目录 (使用static/uploads以便Flask静态文件服务)
POSTCARD_UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads', 'postcards')

# 豆包API配置
DOUBAO_API_KEY = os.environ.get('DOUBAO_API_KEY', 'a7ce8af1-5b59-467b-984e-4d0934976e80')
DOUBAO_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DOUBAO_POSTCARD_MODEL = os.environ.get('DOUBAO_POSTCARD_MODEL', 'doubao-seed-1-6-flash-250828')  # 用flash模型，速度更快

# 导入OpenAI SDK（用于豆包API）
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
    print("警告: 未安装 openai 包，豆包功能将不可用", file=sys.stderr)

# 导入Prompt模板
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from prompts.postcard_prompts import (
        get_full_postcard_prompt,
        get_fallback_postcard_data
    )
except ImportError as e:
    print(f"警告: 未找到postcard_prompts模块: {e}", file=sys.stderr)
    get_full_postcard_prompt = None
    get_fallback_postcard_data = None


def generate_postcard_data(
    emotions: list,
    intensity: int,
    mental_health_score: int,
    diary_content: str,
    trigger_event: str = None,
    adventure_result: dict = None
) -> dict:
    """
    调用豆包AI生成明信片数据（小狐狸的回信 + 场景图片）

    Args:
        emotions: 情绪标签列表
        intensity: 情绪强度 (1-10)
        mental_health_score: 心理健康值 (0-100)
        diary_content: 日记内容
        trigger_event: 触发事件
        adventure_result: 探险结果 {'defeated_count': N, 'total_monsters': M}

    Returns:
        {
            'scene_name': '场景名称',
            'location_name': '诗意地点名',
            'image_prompt': '图片生成prompt',
            'message': '小狐狸的回信'
        }
    """
    if not OpenAI:
        print("[明信片] OpenAI SDK未安装，使用本地生成", file=sys.stderr)
        return generate_postcard_local(emotions, intensity, mental_health_score, diary_content)

    try:
        # 获取prompt（传递探险结果）
        system_prompt, user_prompt = get_full_postcard_prompt(
            emotions=emotions,
            intensity=intensity,
            mental_health_score=mental_health_score,
            diary_content=diary_content,
            trigger_event=trigger_event,
            adventure_result=adventure_result
        )

        # 调用豆包Seed模型（质量更好）
        client = OpenAI(
            api_key=DOUBAO_API_KEY,
            base_url=DOUBAO_BASE_URL
        )

        print(f"[明信片] 调用豆包AI生成明信片数据，模型: {DOUBAO_POSTCARD_MODEL}", file=sys.stderr)

        response = client.chat.completions.create(
            model=DOUBAO_POSTCARD_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,  # 稍高温度以增加创意
            max_tokens=1024
        )

        raw_response = response.choices[0].message.content.strip()
        print(f"[明信片] 豆包响应长度: {len(raw_response)} 字符", file=sys.stderr)

        # 解析JSON
        postcard_data = parse_json_response(raw_response)

        if postcard_data:
            print(f"[明信片] 生成成功，场景: {postcard_data.get('scene_name')}", file=sys.stderr)
            return postcard_data
        else:
            print("[明信片] JSON解析失败，使用本地生成", file=sys.stderr)
            return generate_postcard_local(emotions, intensity, mental_health_score, diary_content)

    except Exception as e:
        print(f"[明信片] 豆包调用失败: {str(e)}，使用本地生成", file=sys.stderr)
        return generate_postcard_local(emotions, intensity, mental_health_score, diary_content)


def parse_json_response(raw_response: str) -> dict:
    """解析GLM返回的JSON响应"""
    try:
        # 尝试直接解析
        return json.loads(raw_response)
    except json.JSONDecodeError:
        pass

    # 尝试提取markdown代码块中的JSON
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试提取任意JSON对象
    json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def generate_postcard_local(
    emotions: list,
    intensity: int,
    mental_health_score: int,
    diary_content: str
) -> dict:
    """
    本地生成明信片数据（降级方案）
    当GLM不可用时使用预设的场景和消息模板
    """
    # 使用备用函数生成
    return get_fallback_postcard_data(emotions, mental_health_score)


def generate_local_message(emotions: list, mental_health_score: int, scene_name: str) -> str:
    """根据情绪和心理健康值生成本地消息模板"""

    if mental_health_score >= 70:
        # 积极状态
        messages = [
            f"亲爱的主人：\n\n今天小橘来到了{scene_name}！这里的风景真的好美呢，阳光暖暖的，就像主人今天的好心情一样～\n\n希望你每天都能这么开心哦！小橘会继续旅行，给你带来更多美好的风景～\n\n你的小橘 💕",
            f"亲爱的主人：\n\n{scene_name}的景色太棒啦！小橘在这里遇到了好多有趣的事情呢。感受到主人今天心情很好，小橘也超级开心的！\n\n继续保持好心情哦～\n\n你的小橘 💕"
        ]
    elif mental_health_score >= 50:
        # 平静状态
        messages = [
            f"亲爱的主人：\n\n小橘今天在{scene_name}散步呢。这里很安静，让小橘想起了主人平静的心情。\n\n有时候，就这样静静地待着也很好呢。小橘会一直陪着你的～\n\n你的小橘 💕",
            f"亲爱的主人：\n\n{scene_name}真是个让人放松的地方呢。小橘坐在这里，想着主人今天的一天。\n\n不管发生什么，小橘都会在你身边哦～\n\n你的小橘 💕"
        ]
    else:
        # 需要治愈的状态
        messages = [
            f"亲爱的主人：\n\n小橘今天特意来到{scene_name}，这里很安静，很治愈。小橘知道主人今天可能有点累，所以想把这份宁静分享给你。\n\n没关系的，小橘会一直陪着你。明天会更好的～\n\n你的小橘 💕",
            f"亲爱的主人：\n\n在{scene_name}，小橘看到了很美的风景。虽然主人今天可能心情不太好，但小橘相信你一定能挺过去的。\n\n要记得，不管什么时候，小橘都在这里陪你呢～\n\n你的小橘 💕"
        ]

    import random
    return random.choice(messages)


def generate_postcard_image(image_prompt: str) -> str:
    """
    调用豆包Seedream 4.5图片生成API创建明信片图片

    Args:
        image_prompt: 图片生成提示词

    Returns:
        生成的图片URL，失败返回None
    """
    # 获取豆包API配置（优先使用ARK_API_KEY，否则使用DOUBAO_API_KEY）
    ark_api_key = os.getenv('ARK_API_KEY') or DOUBAO_API_KEY
    image_model = os.getenv('DOUBAO_IMAGE_MODEL', 'doubao-seedream-4-5-251128')

    if not ark_api_key:
        print("[明信片图片] 未配置豆包API Key", file=sys.stderr)
        return None

    try:
        # 使用OpenAI SDK调用豆包API
        client = OpenAI(
            base_url=DOUBAO_BASE_URL,
            api_key=ark_api_key
        )

        print(f"[明信片图片] 调用豆包Seedream生成图片，模型: {image_model}", file=sys.stderr)
        print(f"[明信片图片] Prompt: {image_prompt[:100]}...", file=sys.stderr)

        # 生成2K 16:9的图片 (2560x1440)
        response = client.images.generate(
            model=image_model,
            prompt=image_prompt,
            size="2560x1440",  # 2K 16:9 比例
            response_format="url",
            extra_body={
                "watermark": False,  # 不添加水印
                "sequential_image_generation": "disabled"  # 只生成单图
            }
        )

        if response.data and len(response.data) > 0:
            image_url = response.data[0].url
            print(f"[明信片图片] 生成成功: {image_url[:80]}...", file=sys.stderr)
            return image_url
        else:
            print("[明信片图片] API返回空数据", file=sys.stderr)
            return None

    except ImportError:
        print("[明信片图片] 未安装openai包，请运行: pip install openai", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[明信片图片] 生成失败: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None


def download_and_save_image(image_url: str, user_id: int) -> str:
    """
    下载远程图片并保存到本地服务器

    Args:
        image_url: 远程图片URL
        user_id: 用户ID（用于组织目录）

    Returns:
        本地图片的相对路径（如 /uploads/postcards/9/abc123.jpg），失败返回None
    """
    if not image_url:
        return None

    try:
        # 确保目录存在
        user_folder = os.path.join(POSTCARD_UPLOAD_FOLDER, str(user_id))
        os.makedirs(user_folder, exist_ok=True)

        # 生成唯一文件名
        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(user_folder, filename)

        print(f"[明信片图片] 正在下载图片到: {filepath}", file=sys.stderr)

        # 下载图片
        response = requests.get(image_url, timeout=60, stream=True)
        response.raise_for_status()

        # 保存到本地
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # 返回相对路径（用于Web访问，通过Flask静态文件服务）
        relative_path = f"/static/uploads/postcards/{user_id}/{filename}"
        print(f"[明信片图片] 下载成功: {relative_path}", file=sys.stderr)

        return relative_path

    except Exception as e:
        print(f"[明信片图片] 下载保存失败: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None


def create_postcard(
    user_id: int,
    diary_id: int,
    emotions: list,
    intensity: int,
    mental_health_score: int,
    diary_content: str,
    trigger_event: str = None,
    generate_image: bool = True
) -> dict:
    """
    创建完整的明信片记录

    Args:
        user_id: 用户ID
        diary_id: 日记ID
        emotions: 情绪标签
        intensity: 情绪强度
        mental_health_score: 心理健康值
        diary_content: 日记内容
        trigger_event: 触发事件
        generate_image: 是否生成图片（可选择跳过以节省成本）

    Returns:
        创建的明信片数据字典
    """
    from models import Postcard, db

    try:
        print(f"[明信片] 开始创建，用户ID: {user_id}, 日记ID: {diary_id}", file=sys.stderr)

        # 1. 生成明信片文本数据
        postcard_data = generate_postcard_data(
            emotions=emotions,
            intensity=intensity,
            mental_health_score=mental_health_score,
            diary_content=diary_content,
            trigger_event=trigger_event
        )

        # 2. 生成图片（如果启用）
        image_url = None
        local_image_path = None
        if generate_image:
            # 先从豆包API获取临时URL
            temp_image_url = generate_postcard_image(postcard_data['image_prompt'])
            if temp_image_url:
                # 下载并保存到本地
                local_image_path = download_and_save_image(temp_image_url, user_id)
                # 优先使用本地路径，如果下载失败则使用临时URL
                image_url = local_image_path if local_image_path else temp_image_url

        # 3. 创建明信片记录
        postcard = Postcard(
            user_id=user_id,
            diary_id=diary_id,
            image_url=image_url,
            image_prompt=postcard_data['image_prompt'],
            location_name=postcard_data['location_name'],
            message=postcard_data['message'],
            status='completed' if image_url else 'text_only',
            emotion_tags=emotions,
            emotion_intensity=intensity,
            mental_health_score=mental_health_score,
            generated_at=datetime.utcnow() if image_url else None
        )

        db.session.add(postcard)
        db.session.commit()

        print(f"[明信片] 创建成功，ID: {postcard.id}", file=sys.stderr)

        return postcard.to_dict()

    except Exception as e:
        db.session.rollback()
        print(f"[明信片] 创建失败: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None


def create_postcard_async(
    user_id: int,
    diary_id: int,
    emotions: list,
    intensity: int,
    mental_health_score: int,
    diary_content: str,
    trigger_event: str = None
):
    """
    异步创建或更新明信片（用于后台任务）
    先创建pending状态的记录，然后异步生成图片
    如果明信片已存在（例如由探险先创建），则更新它

    Args:
        同 create_postcard
    """
    from models import Postcard, db

    try:
        # 1. 先生成文本数据
        postcard_data = generate_postcard_data(
            emotions=emotions,
            intensity=intensity,
            mental_health_score=mental_health_score,
            diary_content=diary_content,
            trigger_event=trigger_event
        )

        # 2. 检查是否已存在该日记的明信片（可能由探险先创建）
        postcard = Postcard.query.filter_by(diary_id=diary_id, user_id=user_id).first()

        if postcard:
            # 已存在，更新内容（保留探险的stat_changes和coins_earned）
            print(f"[明信片] 已存在记录 #{postcard.id}，更新内容", file=sys.stderr)
            postcard.image_prompt = postcard_data['image_prompt']
            postcard.location_name = postcard_data['location_name']
            postcard.message = postcard_data['message']
            postcard.emotion_tags = emotions
            postcard.emotion_intensity = intensity
            postcard.mental_health_score = mental_health_score
            if postcard.status == 'pending':
                # 只有pending状态才需要生成图片
                pass
        else:
            # 不存在，创建新记录
            postcard = Postcard(
                user_id=user_id,
                diary_id=diary_id,
                image_prompt=postcard_data['image_prompt'],
                location_name=postcard_data['location_name'],
                message=postcard_data['message'],
                status='pending',
                emotion_tags=emotions,
                emotion_intensity=intensity,
                mental_health_score=mental_health_score
            )
            db.session.add(postcard)

        db.session.commit()

        postcard_id = postcard.id
        print(f"[明信片] 创建/更新pending记录，ID: {postcard_id}", file=sys.stderr)

        # 3. 异步生成图片（这里可以用线程池或Celery）
        # 为了简单起见，这里直接在同一线程中生成
        from concurrent.futures import ThreadPoolExecutor

        def generate_image_task():
            from app import app
            with app.app_context():
                try:
                    postcard_record = Postcard.query.get(postcard_id)
                    if postcard_record:
                        postcard_record.status = 'generating'
                        db.session.commit()

                        image_url = generate_postcard_image(postcard_record.image_prompt)

                        if image_url:
                            postcard_record.image_url = image_url
                            postcard_record.status = 'completed'
                            postcard_record.generated_at = datetime.utcnow()
                        else:
                            postcard_record.status = 'text_only'

                        db.session.commit()
                        print(f"[明信片] 图片生成完成，ID: {postcard_id}", file=sys.stderr)
                except Exception as e:
                    print(f"[明信片] 异步图片生成失败: {str(e)}", file=sys.stderr)

        # 启动后台任务
        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(generate_image_task)

        return postcard.to_dict()

    except Exception as e:
        db.session.rollback()
        print(f"[明信片] 异步创建失败: {str(e)}", file=sys.stderr)
        return None


def get_user_postcards(user_id: int, limit: int = 20, offset: int = 0, unread_only: bool = False) -> list:
    """
    获取用户的明信片列表

    Args:
        user_id: 用户ID
        limit: 返回数量限制
        offset: 偏移量
        unread_only: 是否只返回未读的

    Returns:
        明信片列表
    """
    from models import Postcard

    query = Postcard.query.filter_by(user_id=user_id)

    if unread_only:
        query = query.filter_by(is_read=False)

    postcards = query.order_by(Postcard.created_at.desc()).offset(offset).limit(limit).all()

    return [p.to_dict() for p in postcards]


def mark_postcard_read(postcard_id: int, user_id: int) -> bool:
    """
    标记明信片为已读

    Args:
        postcard_id: 明信片ID
        user_id: 用户ID（验证所有权）

    Returns:
        是否成功
    """
    from models import Postcard, db

    try:
        postcard = Postcard.query.filter_by(id=postcard_id, user_id=user_id).first()
        if postcard:
            postcard.is_read = True
            postcard.read_at = datetime.utcnow()
            db.session.commit()
            return True
        return False
    except Exception as e:
        db.session.rollback()
        print(f"[明信片] 标记已读失败: {str(e)}", file=sys.stderr)
        return False


def get_unread_count(user_id: int) -> int:
    """获取用户未读明信片数量"""
    from models import Postcard
    return Postcard.query.filter_by(user_id=user_id, is_read=False).count()
