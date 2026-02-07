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

# 明信片图片保存目录 (Zeabur部署使用/image/持久化存储)
# 优先使用环境变量配置的路径，否则使用默认的/image/postcards
POSTCARD_UPLOAD_FOLDER = os.environ.get('POSTCARD_UPLOAD_FOLDER', '/image/postcards')

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
    adventure_result: dict = None,
    use_fallback: bool = False
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
        use_fallback: 是否允许使用备用模板（默认False，必须使用AI）

    Returns:
        {
            'scene_name': '场景名称',
            'location_name': '诗意地点名',
            'image_prompt': '图片生成prompt',
            'message': '小狐狸的回信'
        }

    Raises:
        Exception: 当AI调用失败且use_fallback=False时抛出异常
    """
    if not OpenAI:
        error_msg = "OpenAI SDK未安装，无法调用豆包AI"
        print(f"[明信片] {error_msg}", file=sys.stderr)
        if use_fallback:
            return generate_postcard_local(emotions, intensity, mental_health_score, diary_content)
        raise Exception(error_msg)

    last_error = None

    # 最多重试3次
    for attempt in range(3):
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

            # 调用豆包Seed模型
            client = OpenAI(
                api_key=DOUBAO_API_KEY,
                base_url=DOUBAO_BASE_URL
            )

            print(f"[明信片] 调用豆包AI生成明信片数据，模型: {DOUBAO_POSTCARD_MODEL}，第{attempt+1}次尝试", file=sys.stderr)

            response = client.chat.completions.create(
                model=DOUBAO_POSTCARD_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,
                max_tokens=1024
            )

            raw_response = response.choices[0].message.content.strip()
            print(f"[明信片] 豆包响应长度: {len(raw_response)} 字符", file=sys.stderr)

            # 解析JSON
            postcard_data = parse_json_response(raw_response)

            if postcard_data and postcard_data.get('message'):
                print(f"[明信片] 生成成功，场景: {postcard_data.get('scene_name')}", file=sys.stderr)
                return postcard_data
            else:
                last_error = f"JSON解析失败或消息为空，响应内容: {raw_response[:200]}..."
                print(f"[明信片] {last_error}", file=sys.stderr)

        except Exception as e:
            last_error = str(e)
            print(f"[明信片] 第{attempt+1}次尝试失败: {last_error}", file=sys.stderr)

        # 等待1秒后重试
        import time
        time.sleep(1)

    # 所有重试都失败了
    error_msg = f"豆包AI调用失败（重试3次）: {last_error}"
    print(f"[明信片] {error_msg}", file=sys.stderr)

    if use_fallback:
        print("[明信片] 使用备用模板生成", file=sys.stderr)
        return generate_postcard_local(emotions, intensity, mental_health_score, diary_content)

    raise Exception(error_msg)


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
    """根据情绪和心理健康值生成本地消息模板（使用小狐狸讲故事的模式）"""

    if mental_health_score >= 70:
        # 积极状态 - 小狐狸分享开心的小故事
        messages = [
            f"亲爱的主人：\n\n今天在{scene_name}，我遇到了小兔子棉棉！她正在草地上打滚，开心得耳朵都在抖。\n\n\"小橘小橘，今天的阳光好温暖呀！\"她一边说一边笑。\n\n看着她那么开心，我也忍不住跟着一起在草地上打滚了。原来快乐真的是会传染的呢！\n\n主人今天一定也有让你开心的事情吧？把这份快乐好好收藏起来～\n\n你的小橘 🧡",
            f"亲爱的主人：\n\n今天在{scene_name}发现了一件特别棒的事！我找到了一块超级大的蘑菇，足够我和小熊蜜蜜、松鼠果果一起分享。\n\n\"哇，你运气真好！\"果果眼睛亮亮的。\n\n其实我知道，好运气不是凭空来的，是因为我每天都认真寻找呀。就像主人一样，认真生活的人，总会遇到美好的事情～\n\n你的小橘 🧡"
        ]
    elif mental_health_score >= 50:
        # 平静状态 - 小狐狸讲日常小故事
        messages = [
            f"亲爱的主人：\n\n今天在{scene_name}遇到了猫头鹰博士。他正坐在树枝上发呆，我问他在想什么。\n\n\"没想什么特别的，就是看看天空，听听风声。\"他说。\n\n原来安安静静地待着也是一种享受呢。我就陪他坐了一会儿，看云慢慢飘过。\n\n主人今天过得怎么样？不管是热闹还是安静，我都陪着你哦～\n\n你的小橘 💕",
            f"亲爱的主人：\n\n今天在{scene_name}散步的时候，遇到了小鹿斑斑。她在河边喝水，水面倒映着蓝天白云。\n\n\"小橘，你有没有发现，每天的天空都不一样？\"她轻声说。\n\n我抬头看了看，真的呢，今天的云是棉花糖的形状。日子平平淡淡的，但每天都有小小的不同。\n\n你的小橘 💕"
        ]
    else:
        # 需要治愈的状态 - 小狐狸讲安慰的小故事
        messages = [
            f"亲爱的主人：\n\n今天在{scene_name}遇到了松鼠果果，她看起来有点沮丧。\n\n\"我藏的橡果找不到了......\"她小声说。\n\n我陪她找了很久，最后在一棵老树下找到了。原来是她太着急，忘记了藏在哪里。\n\n有时候事情看起来很糟糕，但只要慢慢来，总会找到出路的。主人也是一样哦，小橘一直在你身边呢～\n\n你的小橘 🧡",
            f"亲爱的主人：\n\n今天在{scene_name}，小刺猬球球悄悄告诉我他的烦恼：\"大家都觉得我很扎人，不敢靠近我......\"\n\n我轻轻拍了拍他的背（小心避开刺），说：\"但我知道你内心很柔软呀。\"\n\n他的眼睛一下子亮了起来。有时候，只需要有一个人理解，就够了。\n\n主人，不管你今天遇到了什么，小橘都理解你、陪着你哦～\n\n你的小橘 🧡"
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


def download_and_save_image(image_url: str, user_id: int, diary_id: int = None) -> str:
    """
    下载远程图片并保存到本地服务器

    Args:
        image_url: 远程图片URL
        user_id: 用户ID（用于组织目录）
        diary_id: 日记ID（用于文件命名，便于关联删除）

    Returns:
        本地图片的相对路径（如 /image/postcards/9/diary_123_abc.jpg），失败返回None
    """
    if not image_url:
        return None

    try:
        # 确保目录存在
        user_folder = os.path.join(POSTCARD_UPLOAD_FOLDER, str(user_id))
        os.makedirs(user_folder, exist_ok=True)

        # 生成唯一文件名（包含diary_id便于追踪）
        unique_id = uuid.uuid4().hex[:8]
        if diary_id:
            filename = f"diary_{diary_id}_{unique_id}.jpg"
        else:
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

        # 返回相对路径（用于Web访问，通过Flask路由服务）
        relative_path = f"/image/postcards/{user_id}/{filename}"
        print(f"[明信片图片] 下载成功: {relative_path}", file=sys.stderr)

        return relative_path

    except Exception as e:
        print(f"[明信片图片] 下载保存失败: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None


def delete_postcard_image(image_url: str) -> bool:
    """
    删除明信片图片文件

    Args:
        image_url: 图片的相对路径（如 /image/postcards/9/diary_123_abc.jpg）

    Returns:
        是否删除成功
    """
    if not image_url or not image_url.startswith('/image/postcards/'):
        return False

    try:
        # 从URL路径构建实际文件路径
        # /image/postcards/9/filename.jpg -> /image/postcards/9/filename.jpg
        filepath = image_url  # Zeabur上直接使用/image/作为根目录

        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"[明信片图片] 删除成功: {filepath}", file=sys.stderr)
            return True
        else:
            print(f"[明信片图片] 文件不存在: {filepath}", file=sys.stderr)
            return False

    except Exception as e:
        print(f"[明信片图片] 删除失败: {str(e)}", file=sys.stderr)
        return False


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
                # 下载并保存到本地（传入diary_id便于关联删除）
                local_image_path = download_and_save_image(temp_image_url, user_id, diary_id)
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
    完全异步创建明信片（用于后台任务）

    流程：
    1. 立即创建 status='generating' 的占位记录
    2. 后台线程调用豆包AI生成文本
    3. 后台线程调用豆包生成图片
    4. 更新记录为 completed

    这样不会阻塞日记创建的响应
    """
    from app import app
    from concurrent.futures import ThreadPoolExecutor

    # 先在主线程创建占位记录（避免重复创建）
    with app.app_context():
        from models import Postcard, db

        # 检查是否已存在
        existing = Postcard.query.filter_by(diary_id=diary_id, user_id=user_id).first()
        if existing:
            print(f"[明信片] 已存在记录 #{existing.id}，跳过创建", file=sys.stderr)
            postcard_id = existing.id
        else:
            # 创建占位记录
            postcard = Postcard(
                user_id=user_id,
                diary_id=diary_id,
                image_prompt='',  # 占位
                location_name='生成中...',
                message='小橘正在写信给你...',  # 占位消息
                status='generating',  # 标记为生成中
                emotion_tags=emotions,
                emotion_intensity=intensity,
                mental_health_score=mental_health_score
            )
            db.session.add(postcard)
            db.session.commit()
            postcard_id = postcard.id
            print(f"[明信片] 创建占位记录 #{postcard_id}，开始后台生成", file=sys.stderr)

    def generate_task():
        """后台生成任务：文本 + 图片"""
        with app.app_context():
            from models import Postcard, db

            try:
                postcard = Postcard.query.get(postcard_id)
                if not postcard:
                    print(f"[明信片] 记录 #{postcard_id} 不存在", file=sys.stderr)
                    return

                # 如果已经完成，跳过
                if postcard.status == 'completed':
                    print(f"[明信片] 记录 #{postcard_id} 已完成，跳过", file=sys.stderr)
                    return

                print(f"[明信片] 开始为 #{postcard_id} 生成内容（豆包AI）", file=sys.stderr)

                # 1. 调用豆包AI生成文本（必须成功，不用备用模板）
                postcard_data = generate_postcard_data(
                    emotions=emotions,
                    intensity=intensity,
                    mental_health_score=mental_health_score,
                    diary_content=diary_content,
                    trigger_event=trigger_event
                )

                # 更新文本内容
                postcard.image_prompt = postcard_data.get('image_prompt', '')
                postcard.location_name = postcard_data.get('location_name', '温暖森林')
                postcard.message = postcard_data.get('message', '')
                db.session.commit()

                print(f"[明信片] #{postcard_id} 文本生成完成，场景: {postcard.location_name}", file=sys.stderr)

                # 2. 生成图片
                if postcard.image_prompt:
                    temp_image_url = generate_postcard_image(postcard.image_prompt)
                    if temp_image_url:
                        # 下载并保存到本地持久化存储
                        local_image_path = download_and_save_image(temp_image_url, user_id, diary_id)
                        # 优先使用本地路径，失败则使用临时URL
                        postcard.image_url = local_image_path if local_image_path else temp_image_url
                        postcard.status = 'completed'
                        postcard.generated_at = datetime.utcnow()
                        print(f"[明信片] #{postcard_id} 图片生成完成，路径: {postcard.image_url}", file=sys.stderr)
                    else:
                        postcard.status = 'text_only'
                        print(f"[明信片] #{postcard_id} 图片生成失败，仅保留文本", file=sys.stderr)
                else:
                    postcard.status = 'text_only'

                db.session.commit()

            except Exception as e:
                print(f"[明信片] #{postcard_id} 生成失败: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()

                # 即使失败，也更新状态
                try:
                    postcard = Postcard.query.get(postcard_id)
                    if postcard and postcard.status == 'generating':
                        postcard.status = 'failed'
                        postcard.message = '生成失败，请稍后重试'
                        db.session.commit()
                except:
                    pass

    # 启动后台任务
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(generate_task)

    return {'id': postcard_id, 'status': 'generating'}


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
