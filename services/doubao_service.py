# -*- coding: utf-8 -*-
"""
豆包AI服务模块

使用豆包Flash模型快速生成CBT题目
采用紧凑输出格式，后端组装完整题目
"""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 豆包配置
DOUBAO_API_KEY = os.environ.get('DOUBAO_API_KEY', 'a7ce8af1-5b59-467b-984e-4d0934976e80')
DOUBAO_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DOUBAO_MODEL = os.environ.get('DOUBAO_MODEL', 'doubao-seed-1-6-flash-250828')

# 创建客户端
_client = None

def get_client():
    """获取豆包客户端（单例）"""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=DOUBAO_API_KEY,
            base_url=DOUBAO_BASE_URL
        )
    return _client


def generate_cbt_challenges(diary_content: str, emotion_tags: list, emotion_score: int) -> dict:
    """
    生成CBT挑战题目

    采用紧凑格式：AI只返回核心内容，后端组装完整题目

    Returns:
        {
            "scene_name": "迷雾森林",
            "monsters": [...],
            "challenges": [...]
        }
    """
    is_positive = emotion_score >= 50
    emotion_str = "、".join(emotion_tags) if emotion_tags else "复杂情绪"

    # 根据情绪类型选择怪物池
    if is_positive:
        monster_pool = "感恩小偷|成就橡皮擦|快乐迷雾|自信阴影"
        task_desc = "帮助用户肯定自己、感恩生活"
    else:
        monster_pool = "灾难化|贴标签|过度概括|读心术|应该思维|个人化"
        task_desc = "帮助用户识别认知扭曲，不要否定自己"

    # 紧凑Prompt - 让AI只返回核心内容
    prompt = f'''日记:{diary_content[:200]}
情绪:{emotion_str}({emotion_score}/100)

生成3道CBT题目，{task_desc}。
每行格式: 怪物类型|错误想法|正确想法
怪物类型从[{monster_pool}]选择。

只返回3行，不要其他内容。'''

    try:
        client = get_client()
        response = client.chat.completions.create(
            model=DOUBAO_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7
        )

        content = response.choices[0].message.content.strip()

        # 解析AI返回的紧凑内容
        lines = [l.strip() for l in content.split('\n') if '|' in l]

        # 组装完整题目
        challenges = []
        monsters = []

        for i, line in enumerate(lines[:3]):
            parts = line.split('|')
            if len(parts) >= 3:
                monster_type = parts[0].strip()
                wrong_thought = parts[1].strip()
                right_thought = parts[2].strip()

                # 映射怪物类型
                monster_key = map_monster_type(monster_type, is_positive)
                monster_info = get_monster_info(monster_key)

                if monster_key not in [m['type'] for m in monsters]:
                    monsters.append({
                        "type": monster_key,
                        "name": monster_info['name'],
                        "description": monster_info['description']
                    })

                # 组装题目
                challenge = assemble_challenge(
                    monster_type=monster_key,
                    wrong_thought=wrong_thought,
                    right_thought=right_thought,
                    index=i
                )
                challenges.append(challenge)

        # 如果解析失败，使用备用题目
        if len(challenges) < 3:
            challenges = get_fallback_challenges(is_positive, diary_content)
            monsters = get_fallback_monsters(is_positive)

        return {
            "scene_name": "阳光草地" if is_positive else "迷雾森林",
            "monsters": monsters[:3],
            "challenges": challenges[:3]
        }

    except Exception as e:
        print(f"[豆包AI] 生成失败: {e}")
        # 返回备用题目
        return {
            "scene_name": "迷雾森林",
            "monsters": get_fallback_monsters(is_positive),
            "challenges": get_fallback_challenges(is_positive, diary_content)
        }


def map_monster_type(chinese_name: str, is_positive: bool) -> str:
    """将中文怪物名映射到英文key"""
    mapping = {
        # 负面情绪怪物
        '灾难化': 'dark_cloud',
        '灾难化黑云': 'dark_cloud',
        '贴标签': 'label_monster',
        '标签': 'label_monster',
        '过度概括': 'magnifier',
        '以偏概全': 'magnifier',
        '读心术': 'crystal_ball',
        '读心': 'crystal_ball',
        '应该思维': 'rule_stone',
        '应该': 'rule_stone',
        '个人化': 'blame_magnet',
        '自责': 'blame_magnet',
        '非黑即白': 'checkerboard',
        '情绪推理': 'emotion_heart',

        # 正面情绪怪物
        '感恩小偷': 'gratitude_thief',
        '感恩': 'gratitude_thief',
        '成就橡皮擦': 'achievement_eraser',
        '成就': 'achievement_eraser',
        '橡皮擦': 'achievement_eraser',
        '快乐迷雾': 'joy_fog',
        '迷雾': 'joy_fog',
        '自信阴影': 'confidence_shadow',
        '阴影': 'confidence_shadow',
    }

    # 尝试匹配
    for key, value in mapping.items():
        if key in chinese_name:
            return value

    # 默认返回
    return 'dark_cloud' if not is_positive else 'gratitude_thief'


def get_monster_info(monster_type: str) -> dict:
    """获取怪物信息"""
    monsters = {
        'dark_cloud': {'name': '灾难化黑云', 'description': '把事情想得太糟糕'},
        'label_monster': {'name': '贴标签怪', 'description': '给自己贴负面标签'},
        'magnifier': {'name': '放大镜怪', 'description': '把一次失败扩大为永远'},
        'crystal_ball': {'name': '水晶球怪', 'description': '臆测他人的想法'},
        'rule_stone': {'name': '规则石', 'description': '用"应该"束缚自己'},
        'blame_magnet': {'name': '磁铁怪', 'description': '把责任都揽到自己身上'},
        'checkerboard': {'name': '棋盘精', 'description': '非黑即白的思维'},
        'emotion_heart': {'name': '心形怪', 'description': '感觉糟糕就认为事实糟糕'},
        'gratitude_thief': {'name': '感恩小偷', 'description': '想偷走你的感恩之心'},
        'achievement_eraser': {'name': '橡皮擦怪', 'description': '想抹去你的成就'},
        'joy_fog': {'name': '快乐迷雾', 'description': '想模糊快乐的记忆'},
        'confidence_shadow': {'name': '自信阴影', 'description': '想遮蔽你的自信'},
    }
    return monsters.get(monster_type, {'name': '迷雾怪', 'description': '认知扭曲'})


def assemble_challenge(monster_type: str, wrong_thought: str, right_thought: str, index: int) -> dict:
    """组装完整的挑战题目"""

    # 题目模板
    question_templates = [
        f"当你想「{wrong_thought}」时，哪个想法更合理？",
        f"面对「{wrong_thought}」这个想法，哪个回应更健康？",
        f"关于「{wrong_thought}」，哪个看法更客观？",
    ]

    instruction_templates = [
        "选择更平衡的想法",
        "选择对自己更友善的回应",
        "选择更客观的看法",
    ]

    # 生成错误选项
    wrong_options = [
        wrong_thought,
        "这就是事实，没什么好争辩的",
        "我就是这样的人，改不了",
        "别人肯定也这么看我",
        "我应该更努力才对",
    ]

    # 选择题目模板
    template_idx = index % len(question_templates)

    # 组装选项（随机排列正确答案位置）
    import random
    correct_pos = random.randint(0, 2)
    options = []
    wrong_idx = 0

    for i in range(3):
        if i == correct_pos:
            options.append({
                "id": chr(97 + i),  # a, b, c
                "text": right_thought,
                "is_correct": True
            })
        else:
            options.append({
                "id": chr(97 + i),
                "text": wrong_options[wrong_idx % len(wrong_options)],
                "is_correct": False
            })
            wrong_idx += 1

    return {
        "type": "reframe",
        "monster_type": monster_type,
        "distortion_thought": wrong_thought,
        "question": question_templates[template_idx],
        "instruction": instruction_templates[template_idx],
        "options": options,
        "explanation": f"「{wrong_thought}」是一种认知扭曲。更合理的想法是：{right_thought}。对自己温柔一点，你值得被善待。"
    }


def get_fallback_monsters(is_positive: bool) -> list:
    """获取备用怪物列表"""
    if is_positive:
        return [
            {"type": "gratitude_thief", "name": "感恩小偷", "description": "想偷走你的感恩之心"},
            {"type": "achievement_eraser", "name": "橡皮擦怪", "description": "想抹去你的成就"},
            {"type": "confidence_shadow", "name": "自信阴影", "description": "想遮蔽你的自信"},
        ]
    else:
        return [
            {"type": "dark_cloud", "name": "灾难化黑云", "description": "把事情想得太糟糕"},
            {"type": "label_monster", "name": "贴标签怪", "description": "给自己贴负面标签"},
            {"type": "magnifier", "name": "放大镜怪", "description": "把一次失败扩大为永远"},
        ]


def get_fallback_challenges(is_positive: bool, diary_content: str) -> list:
    """获取备用题目"""
    if is_positive:
        return [
            {
                "type": "evidence",
                "monster_type": "gratitude_thief",
                "distortion_thought": "",
                "question": "回想一下，今天有什么值得感恩的小事？",
                "instruction": "选择一个答案",
                "options": [
                    {"id": "a", "text": "有很多值得感恩的，比如健康、朋友、美食", "is_correct": True},
                    {"id": "b", "text": "没什么特别的", "is_correct": False},
                    {"id": "c", "text": "生活太普通了", "is_correct": False}
                ],
                "explanation": "每天都有值得感恩的小事，培养感恩之心能提升幸福感。"
            },
            {
                "type": "reframe",
                "monster_type": "achievement_eraser",
                "distortion_thought": "这没什么大不了",
                "question": "当你完成一件事却觉得「这没什么大不了」时，怎么想更好？",
                "instruction": "选择更积极的想法",
                "options": [
                    {"id": "a", "text": "每一个小进步都值得肯定", "is_correct": True},
                    {"id": "b", "text": "确实没什么值得骄傲的", "is_correct": False},
                    {"id": "c", "text": "别人做得更好", "is_correct": False}
                ],
                "explanation": "肯定自己的每一点进步，是建立自信的重要方式。"
            },
            {
                "type": "reframe",
                "monster_type": "confidence_shadow",
                "distortion_thought": "我不够好",
                "question": "当你觉得「我不够好」时，哪个想法更健康？",
                "instruction": "选择对自己更友善的回应",
                "options": [
                    {"id": "a", "text": "我在不断成长，已经很棒了", "is_correct": True},
                    {"id": "b", "text": "我确实不如别人", "is_correct": False},
                    {"id": "c", "text": "我应该更完美", "is_correct": False}
                ],
                "explanation": "你不需要完美，你只需要做真实的自己。"
            }
        ]
    else:
        return [
            {
                "type": "reframe",
                "monster_type": "dark_cloud",
                "distortion_thought": "一切都完了",
                "question": "当你觉得「一切都完了」时，哪个想法更合理？",
                "instruction": "选择更平衡的想法",
                "options": [
                    {"id": "a", "text": "这只是暂时的困难，会过去的", "is_correct": True},
                    {"id": "b", "text": "确实没救了", "is_correct": False},
                    {"id": "c", "text": "我总是这么倒霉", "is_correct": False}
                ],
                "explanation": "困难是暂时的，把一次挫折当成永久的灾难是灾难化思维。"
            },
            {
                "type": "reframe",
                "monster_type": "label_monster",
                "distortion_thought": "我很没用",
                "question": "当你给自己贴上「没用」的标签时，哪个想法更客观？",
                "instruction": "选择更客观的看法",
                "options": [
                    {"id": "a", "text": "一次失败不代表我这个人没用", "is_correct": True},
                    {"id": "b", "text": "我就是个失败者", "is_correct": False},
                    {"id": "c", "text": "我什么都做不好", "is_correct": False}
                ],
                "explanation": "给自己贴标签是一种认知扭曲，你比任何标签都丰富得多。"
            },
            {
                "type": "evidence",
                "monster_type": "magnifier",
                "distortion_thought": "我总是失败",
                "question": "「我总是失败」这个想法准确吗？",
                "instruction": "选择能反驳这个想法的证据",
                "options": [
                    {"id": "a", "text": "不准确，我有过成功的经历", "is_correct": True},
                    {"id": "b", "text": "是的，我从来没成功过", "is_correct": False},
                    {"id": "c", "text": "成功只是运气", "is_correct": False}
                ],
                "explanation": "「总是」和「从不」往往是过度概括，回想一下你的成功经历。"
            }
        ]
