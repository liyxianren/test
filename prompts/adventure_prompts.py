# -*- coding: utf-8 -*-
"""
探险游戏AI出题Prompt

根据用户日记内容和情绪类型，动态生成CBT挑战题目
"""


def get_adventure_challenge_prompt(diary_content: str, emotion_tags: list, emotion_score: int, trigger_event: str = None) -> str:
    """
    生成探险挑战的Prompt

    根据情绪类型生成不同的挑战：
    - 负面情绪（分数<50）：消除认知扭曲，帮助用户不要否定自己
    - 正面情绪（分数>=50）：巩固积极思维，帮助用户肯定自己
    """

    # 判断情绪类型
    is_positive = emotion_score >= 50

    emotion_tags_str = "、".join(emotion_tags) if emotion_tags else "未知"
    trigger_str = trigger_event if trigger_event else "未提及"

    if is_positive:
        # 正面情绪 - 肯定自己
        return f'''你是一个CBT（认知行为疗法）游戏设计师，需要根据用户的日记内容生成探险游戏的挑战题目。

## 用户日记信息
- 情绪标签：{emotion_tags_str}
- 情绪强度：{emotion_score}/100（正面情绪）
- 触发事件：{trigger_str}
- 日记内容：{diary_content}

## 你的任务
用户今天心情不错！请生成**正向强化**类型的挑战，帮助用户：
1. 回顾和肯定自己的成就
2. 感恩生活中的美好
3. 强化积极的思维模式
4. 建立自信心

## 怪物类型（选择1-2个最相关的）
- gratitude_thief（感恩小偷）：试图偷走用户的感恩之心，需要用户找回值得感恩的事
- achievement_eraser（成就橡皮擦）：想抹去用户的成就感，需要用户回顾自己的成功
- joy_fog（快乐迷雾）：模糊快乐的记忆，需要用户清晰描述快乐时刻
- confidence_shadow（自信阴影）：遮蔽用户的自信，需要用户发现自己的优点

## 输出格式（严格JSON，不要添加任何注释）
生成3只怪物和3道挑战题目。

```json
{{
    "scene_name": "阳光草地",
    "monsters": [
        {{"type": "gratitude_thief", "name": "感恩小偷", "description": "想偷走你的感恩"}},
        {{"type": "achievement_eraser", "name": "橡皮擦怪", "description": "想抹去你的成就"}},
        {{"type": "confidence_shadow", "name": "自信阴影", "description": "想遮蔽你的自信"}}
    ],
    "challenges": [
        {{
            "type": "evidence",
            "monster_type": "gratitude_thief",
            "distortion_thought": "",
            "question": "基于日记内容的问题",
            "instruction": "选择正确答案",
            "options": [
                {{"id": "a", "text": "正确选项", "is_correct": true}},
                {{"id": "b", "text": "错误选项", "is_correct": false}},
                {{"id": "c", "text": "错误选项", "is_correct": false}}
            ],
            "explanation": "CBT洞见"
        }},
        {{
            "type": "reframe",
            "monster_type": "achievement_eraser",
            "distortion_thought": "这可能只是运气",
            "question": "哪个想法更能肯定自己？",
            "instruction": "选择更积极的想法",
            "options": [
                {{"id": "a", "text": "正确选项", "is_correct": true}},
                {{"id": "b", "text": "错误选项", "is_correct": false}},
                {{"id": "c", "text": "错误选项", "is_correct": false}}
            ],
            "explanation": "CBT洞见"
        }},
        {{
            "type": "evidence",
            "monster_type": "confidence_shadow",
            "distortion_thought": "",
            "question": "第三道题目",
            "instruction": "选择正确答案",
            "options": [
                {{"id": "a", "text": "选项A", "is_correct": true}},
                {{"id": "b", "text": "选项B", "is_correct": false}},
                {{"id": "c", "text": "选项C", "is_correct": false}}
            ],
            "explanation": "CBT洞见"
        }}
    ]
}}
```

## 重要提示
1. 题目必须基于用户的日记内容，体现个性化
2. 正确选项应该帮助用户**肯定自己、感恩生活、建立自信**
3. 错误选项应该是**否定自己、淡化成就、消极思维**的表述
4. explanation要温暖鼓励，强化正面体验
5. 只输出JSON，不要其他内容
'''
    else:
        # 负面情绪 - 不要否定自己
        return f'''你是一个CBT（认知行为疗法）游戏设计师，需要根据用户的日记内容生成探险游戏的挑战题目。

## 用户日记信息
- 情绪标签：{emotion_tags_str}
- 情绪强度：{emotion_score}/100（负面情绪）
- 触发事件：{trigger_str}
- 日记内容：{diary_content}

## 你的任务
用户今天情绪低落，请生成**消除认知扭曲**类型的挑战，帮助用户：
1. 识别和质疑负面的自动化思维
2. 不要过度否定自己
3. 用更平衡的视角看待事情
4. 学会自我关怀

## 怪物类型（选择1-2个最相关的认知扭曲）
- dark_cloud（灾难化黑云）：把事情想得太糟糕，需要找到反驳证据
- checkerboard（非黑即白棋盘精）：只看极端，需要发现中间地带
- crystal_ball（读心水晶球）：臆测他人想法，需要区分事实和猜测
- rule_stone（应该思维规则石）：用"应该"束缚自己，需要更灵活的想法
- label_monster（贴标签怪）：给自己贴负面标签，需要看到完整的自己
- magnifier（过度概括放大镜）：一次失败=永远失败，需要具体化
- blame_magnet（个人化磁铁怪）：把所有责任揽到自己身上，需要客观归因
- emotion_heart（情绪推理心形怪）：因为感觉糟糕就认为事实糟糕，需要区分感受和事实

## 输出格式（严格JSON，不要添加任何注释）
生成3只怪物和3道挑战题目。

```json
{{
    "scene_name": "迷雾森林",
    "monsters": [
        {{"type": "dark_cloud", "name": "灾难化黑云", "description": "把事情想得太糟糕"}},
        {{"type": "checkerboard", "name": "棋盘精", "description": "非黑即白的思维"}},
        {{"type": "crystal_ball", "name": "水晶球怪", "description": "总是猜测别人在想什么"}}
    ],
    "challenges": [
        {{
            "type": "evidence",
            "monster_type": "dark_cloud",
            "distortion_thought": "日记中的负面想法",
            "question": "基于日记内容的问题",
            "instruction": "选择能反驳负面想法的证据",
            "options": [
                {{"id": "a", "text": "正确选项", "is_correct": true}},
                {{"id": "b", "text": "错误选项", "is_correct": false}},
                {{"id": "c", "text": "错误选项", "is_correct": false}}
            ],
            "explanation": "CBT洞见"
        }},
        {{
            "type": "reframe",
            "monster_type": "checkerboard",
            "distortion_thought": "日记中的认知扭曲",
            "question": "哪个想法更平衡？",
            "instruction": "选择更客观的想法",
            "options": [
                {{"id": "a", "text": "正确选项", "is_correct": true}},
                {{"id": "b", "text": "错误选项", "is_correct": false}},
                {{"id": "c", "text": "错误选项", "is_correct": false}}
            ],
            "explanation": "CBT洞见"
        }},
        {{
            "type": "evidence",
            "monster_type": "crystal_ball",
            "distortion_thought": "",
            "question": "第三道题目",
            "instruction": "选择正确答案",
            "options": [
                {{"id": "a", "text": "选项A", "is_correct": true}},
                {{"id": "b", "text": "选项B", "is_correct": false}},
                {{"id": "c", "text": "选项C", "is_correct": false}}
            ],
            "explanation": "CBT洞见"
        }}
    ]
}}
```

## 重要提示
1. 题目必须基于用户的日记内容，体现个性化
2. 识别日记中的认知扭曲，并设计相应的挑战
3. 正确选项应该帮助用户**客观看待事情、不否定自己**
4. 错误选项应该是**认知扭曲、自我否定**的表述
5. explanation要温暖支持，像一个理解你的朋友
6. 只输出JSON，不要其他内容
'''


# 怪物配置 - 扩展版本
MONSTER_CONFIG = {
    # === 负面情绪怪物（帮助用户不要否定自己）===
    'dark_cloud': {
        'name': '灾难化黑云',
        'name_zh': '黑云怪',
        'description': '把事情想象得比实际更糟糕',
        'color': '#2d3436',
        'challenge_type': 'evidence',
        'svg': 'monster_dark_cloud.svg',
        'defeat_message': '乌云散去，阳光照进来了！',
        'reward': {'type': 'stress_reduce', 'value': 5}
    },
    'checkerboard': {
        'name': '非黑即白棋盘精',
        'name_zh': '棋盘精',
        'description': '只看两个极端，忽视中间地带',
        'color': '#636e72',
        'challenge_type': 'reframe',
        'svg': 'monster_checkerboard.svg',
        'defeat_message': '世界不只是黑白，还有彩色！',
        'reward': {'type': 'mental_boost', 'value': 3}
    },
    'crystal_ball': {
        'name': '读心水晶球',
        'name_zh': '水晶球怪',
        'description': '臆测他人的想法和动机',
        'color': '#6c5ce7',
        'challenge_type': 'evidence',
        'svg': 'monster_crystal_ball.svg',
        'defeat_message': '别猜了，事实往往比想象的好！',
        'reward': {'type': 'stress_reduce', 'value': 4}
    },
    'rule_stone': {
        'name': '应该思维规则石',
        'name_zh': '规则石',
        'description': '用"应该"、"必须"束缚自己',
        'color': '#b2bec3',
        'challenge_type': 'reframe',
        'svg': 'monster_rule_stone.svg',
        'defeat_message': '打破束缚，你可以选择！',
        'reward': {'type': 'mental_boost', 'value': 4}
    },
    'label_monster': {
        'name': '贴标签怪',
        'name_zh': '标签怪',
        'description': '给自己贴上负面的固定标签',
        'color': '#e17055',
        'challenge_type': 'reframe',
        'svg': 'monster_label.svg',
        'defeat_message': '撕掉标签，你比标签更丰富！',
        'reward': {'type': 'growth_boost', 'value': 5}
    },
    'magnifier': {
        'name': '过度概括放大镜',
        'name_zh': '放大镜怪',
        'description': '把一次事件扩大为永远的规律',
        'color': '#fdcb6e',
        'challenge_type': 'evidence',
        'svg': 'monster_magnifier.svg',
        'defeat_message': '一次不代表永远！',
        'reward': {'type': 'stress_reduce', 'value': 4}
    },
    'blame_magnet': {
        'name': '个人化磁铁怪',
        'name_zh': '磁铁怪',
        'description': '把所有责任都揽到自己身上',
        'color': '#e84393',
        'challenge_type': 'evidence',
        'svg': 'monster_magnet.svg',
        'defeat_message': '不是所有事都是你的错！',
        'reward': {'type': 'mental_boost', 'value': 4}
    },
    'emotion_heart': {
        'name': '情绪推理心形怪',
        'name_zh': '心形怪',
        'description': '因为感觉糟糕就认为事实糟糕',
        'color': '#fd79a8',
        'challenge_type': 'reframe',
        'svg': 'monster_heart.svg',
        'defeat_message': '感受不等于事实！',
        'reward': {'type': 'stress_reduce', 'value': 5}
    },

    # === 正面情绪怪物（帮助用户肯定自己）===
    'gratitude_thief': {
        'name': '感恩小偷',
        'name_zh': '感恩小偷',
        'description': '想偷走你对美好事物的感恩',
        'color': '#00b894',
        'challenge_type': 'evidence',
        'svg': 'monster_thief.svg',
        'defeat_message': '感恩之心永远属于你！',
        'reward': {'type': 'mental_boost', 'value': 5}
    },
    'achievement_eraser': {
        'name': '成就橡皮擦',
        'name_zh': '橡皮擦怪',
        'description': '想抹去你的成就和进步',
        'color': '#0984e3',
        'challenge_type': 'evidence',
        'svg': 'monster_eraser.svg',
        'defeat_message': '你的成就谁也抹不掉！',
        'reward': {'type': 'growth_boost', 'value': 6}
    },
    'joy_fog': {
        'name': '快乐迷雾',
        'name_zh': '迷雾怪',
        'description': '想模糊你快乐的记忆',
        'color': '#74b9ff',
        'challenge_type': 'reframe',
        'svg': 'monster_fog.svg',
        'defeat_message': '快乐的记忆清晰如初！',
        'reward': {'type': 'stress_reduce', 'value': 5}
    },
    'confidence_shadow': {
        'name': '自信阴影',
        'name_zh': '阴影怪',
        'description': '想遮蔽你的自信光芒',
        'color': '#a29bfe',
        'challenge_type': 'reframe',
        'svg': 'monster_shadow.svg',
        'defeat_message': '你的光芒无法被遮蔽！',
        'reward': {'type': 'mental_boost', 'value': 5}
    }
}

# 认知扭曲到怪物的映射
DISTORTION_TO_MONSTER = {
    # 负面情绪相关
    '灾难化': 'dark_cloud',
    '灾难化思维': 'dark_cloud',
    '非黑即白': 'checkerboard',
    '极端思维': 'checkerboard',
    '读心术': 'crystal_ball',
    '臆测': 'crystal_ball',
    '应该思维': 'rule_stone',
    '必须思维': 'rule_stone',
    '贴标签': 'label_monster',
    '自我标签': 'label_monster',
    '过度概括': 'magnifier',
    '以偏概全': 'magnifier',
    '个人化': 'blame_magnet',
    '自我归因': 'blame_magnet',
    '情绪推理': 'emotion_heart',
    '感觉等于事实': 'emotion_heart',

    # 正面情绪相关 - 用于巩固
    '忽视积极': 'gratitude_thief',
    '淡化成就': 'achievement_eraser',
    '遗忘快乐': 'joy_fog',
    '自我怀疑': 'confidence_shadow'
}


def get_default_monsters_for_emotion(is_positive: bool) -> list:
    """
    根据情绪类型返回默认怪物列表
    用于AI生成失败时的后备方案
    """
    if is_positive:
        return ['gratitude_thief', 'achievement_eraser']
    else:
        return ['dark_cloud', 'checkerboard']
