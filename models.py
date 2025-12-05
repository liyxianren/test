from datetime import datetime
from extensions import db

class User(db.Model):
    """用户模型"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    profile_data = db.Column(db.JSON, default={})

    # 密码重置字段
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)

    # 关联
    diaries = db.relationship('EmotionDiary', backref='user', lazy=True, cascade='all, delete-orphan')
    game_state = db.relationship('GameState', backref='user', lazy=True, uselist=False, cascade='all, delete-orphan')
    game_progress = db.relationship('GameProgress', backref='user', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active,
            'profile_data': self.profile_data
        }

class EmotionDiary(db.Model):
    """情绪日记模型"""
    __tablename__ = 'emotion_diaries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    emotion_tags = db.Column(db.JSON, default=list)
    emotion_score = db.Column(db.JSON, default={})
    trigger_event = db.Column(db.Text, nullable=True)  # 触发情绪的事件或想法
    images = db.Column(db.JSON, default=list)  # 图片URL列表
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    analysis_status = db.Column(db.String(20), default='pending')
    # 计分是否已应用，旧日记缺省时视为已应用，避免重复改分
    score_applied = db.Column(db.Boolean, default=False)

    # 关联
    analysis = db.relationship('EmotionAnalysis', backref='diary', lazy=True, uselist=False, cascade='all, delete-orphan')
    game_progress = db.relationship('GameProgress', backref='diary', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'content': self.content,
            'emotion_tags': self.emotion_tags,
            'emotion_score': self.emotion_score,
            'trigger_event': self.trigger_event,
            'images': self.images if self.images else [],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'analysis_status': self.analysis_status
        }

class EmotionAnalysis(db.Model):
    """情绪分析结果模型"""
    __tablename__ = 'emotion_analysis'

    id = db.Column(db.Integer, primary_key=True)
    diary_id = db.Column(db.Integer, db.ForeignKey('emotion_diaries.id'), nullable=False)
    overall_emotion = db.Column(db.String(50))
    emotion_intensity = db.Column(db.Float)
    emotion_dimensions = db.Column(db.JSON, default={})
    key_words = db.Column(db.JSON, default=list)
    confidence_score = db.Column(db.Float)
    analyzed_at = db.Column(db.DateTime, default=datetime.utcnow)
    ai_model_version = db.Column(db.String(50))
    analysis_payload = db.Column(db.JSON, default={})

    def to_dict(self):
        return {
            'id': self.id,
            'diary_id': self.diary_id,
            'overall_emotion': self.overall_emotion,
            'emotion_intensity': self.emotion_intensity,
            'emotion_dimensions': self.emotion_dimensions,
            'key_words': self.key_words,
            'confidence_score': self.confidence_score,
            'analyzed_at': self.analyzed_at.isoformat(),
            'ai_model_version': self.ai_model_version,
            'analysis_payload': self.analysis_payload or {}
        }

class GameState(db.Model):
    """
    游戏状态模型 - 增量模式

    核心属性从50起始，每篇日记可调整±5
    用于店铺经营游戏的角色属性和资源管理
    """
    __tablename__ = 'game_states'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # ===== 核心属性（增量模式，起始50，范围0-100）=====
    mental_health_score = db.Column(db.Integer, default=50)  # 心理健康值：影响店铺员工效率
    stress_level = db.Column(db.Integer, default=50)         # 压力水平：影响随机事件概率
    growth_potential = db.Column(db.Integer, default=50)     # 成长潜力：影响经验获取倍率

    # ===== 游戏资源（累积）=====
    coins = db.Column(db.Integer, default=0)                 # 金币：游戏货币
    level = db.Column(db.Integer, default=1)                 # 等级：每10篇日记升1级
    total_diaries = db.Column(db.Integer, default=0)         # 日记总数：记录写作数量

    # ===== 时间戳 =====
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """返回完整的游戏状态字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            # 核心属性
            'mental_health_score': self.mental_health_score,
            'stress_level': self.stress_level,
            'growth_potential': self.growth_potential,
            # 游戏资源
            'coins': self.coins,
            'level': self.level,
            'total_diaries': self.total_diaries,
            # 时间戳
            'last_active': self.last_active.isoformat() if self.last_active else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            # 计算属性
            'diaries_to_next_level': 10 - (self.total_diaries % 10) if self.total_diaries % 10 != 0 else 10
        }

class Postcard(db.Model):
    """
    明信片模型 - 小狐狸旅行明信片

    每次用户写完日记并分析后，小狐狸会根据情绪状态
    去不同的地方旅行，并寄回明信片（图片+文字）
    """
    __tablename__ = 'postcards'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    diary_id = db.Column(db.Integer, db.ForeignKey('emotion_diaries.id'), nullable=False)

    # 明信片内容
    image_url = db.Column(db.String(500))           # AI生成的图片URL
    image_prompt = db.Column(db.Text)               # 生成图片使用的prompt
    location_name = db.Column(db.String(100))       # 地点名称，如"心灵森林·宁静小径"
    message = db.Column(db.Text)                    # 小狐狸写给用户的话

    # 生成状态
    status = db.Column(db.String(20), default='pending')  # pending, generating, completed, failed

    # 关联的情绪数据（冗余存储，方便查询）
    emotion_tags = db.Column(db.JSON, default=list)
    emotion_intensity = db.Column(db.Integer)
    mental_health_score = db.Column(db.Integer)     # 生成时的心理健康值

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    generated_at = db.Column(db.DateTime)           # 图片生成完成时间

    # 用户是否已查看
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)

    # 探险获得的数值变化（JSON格式）
    stat_changes = db.Column(db.JSON, default=dict)  # {"mental_health": +5, "stress": -3, "growth": +2}
    coins_earned = db.Column(db.Integer, default=0)  # 探险获得的金币

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'diary_id': self.diary_id,
            'image_url': self.image_url,
            'image_prompt': self.image_prompt,
            'location_name': self.location_name,
            'message': self.message,
            'status': self.status,
            'emotion_tags': self.emotion_tags or [],
            'emotion_intensity': self.emotion_intensity,
            'mental_health_score': self.mental_health_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'is_read': self.is_read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'stat_changes': self.stat_changes or {},
            'coins_earned': self.coins_earned or 0
        }


class GameProgress(db.Model):
    """
    游戏进度模型 - [已废弃]

    注意：此表目前未使用，保留供未来CBT四步法游戏化功能使用
    所有游戏状态现在通过 GameState 模型管理
    """
    __tablename__ = 'game_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    diary_id = db.Column(db.Integer, db.ForeignKey('emotion_diaries.id'), nullable=False)
    cbt_step = db.Column(db.String(50))  # CBT四步法当前步骤
    challenge_completed = db.Column(db.Boolean, default=False)
    evidence_collected = db.Column(db.JSON, default={})
    alternative_thoughts = db.Column(db.Text)
    game_rewards = db.Column(db.JSON, default={})
    completed_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'diary_id': self.diary_id,
            'cbt_step': self.cbt_step,
            'challenge_completed': self.challenge_completed,
            'evidence_collected': self.evidence_collected,
            'alternative_thoughts': self.alternative_thoughts,
            'game_rewards': self.game_rewards,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class AdventureSession(db.Model):
    """
    探险会话模型 - CBT交互式探险游戏

    每次用户写完日记后，可以开始一次探险
    探险中需要帮助小橘击败"迷雾怪物"（认知扭曲的具象化）
    """
    __tablename__ = 'adventure_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    diary_id = db.Column(db.Integer, db.ForeignKey('emotion_diaries.id'), nullable=False)

    # 探险状态
    status = db.Column(db.String(20), default='pending')  # pending/in_progress/completed/skipped
    scene_name = db.Column(db.String(100))                # 场景名称，如"迷雾森林"

    # 怪物和挑战配置（JSON）
    monsters = db.Column(db.JSON, default=list)           # [{type, name_zh, severity, defeated}]
    challenges = db.Column(db.JSON, default=list)         # [{type, question, options, correct_ids, completed}]
    current_challenge = db.Column(db.Integer, default=0)  # 当前挑战索引

    # 奖励
    coins_earned = db.Column(db.Integer, default=0)
    items_earned = db.Column(db.JSON, default=list)       # [{name, name_zh, effect_type, effect_value}]
    stat_changes = db.Column(db.JSON, default=dict)       # {mental_health: +3, stress: -5}

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'diary_id': self.diary_id,
            'status': self.status,
            'scene_name': self.scene_name,
            'monsters': self.monsters or [],
            'challenges': self.challenges or [],
            'current_challenge': self.current_challenge,
            'coins_earned': self.coins_earned,
            'items_earned': self.items_earned or [],
            'stat_changes': self.stat_changes or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class UserItem(db.Model):
    """
    用户道具模型 - 探险获得的道具

    道具类型:
    - healing: 治愈道具，可消除负面效果（如阳光露水、平衡羽毛）
    - adventure: 探险道具，帮助挑战（如迷雾灯笼、智慧眼镜）
    - cosmetic: 装饰道具，装扮小橘（MVP暂不实现）
    """
    __tablename__ = 'user_items'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # 道具信息
    item_name = db.Column(db.String(50), nullable=False)      # 道具英文名
    item_name_zh = db.Column(db.String(50), nullable=False)   # 道具中文名
    item_type = db.Column(db.String(20), default='healing')   # healing/adventure/cosmetic
    quantity = db.Column(db.Integer, default=1)

    # 道具效果
    effect_type = db.Column(db.String(30))    # stress_reduce/mental_boost/growth_boost/difficulty_reduce
    effect_value = db.Column(db.Integer, default=0)

    # 时间戳
    acquired_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'item_name': self.item_name,
            'item_name_zh': self.item_name_zh,
            'item_type': self.item_type,
            'quantity': self.quantity,
            'effect_type': self.effect_type,
            'effect_value': self.effect_value,
            'acquired_at': self.acquired_at.isoformat() if self.acquired_at else None
        }
