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
    """游戏状态模型"""
    __tablename__ = 'game_states'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    current_level = db.Column(db.Integer, default=1)
    game_difficulty = db.Column(db.Float, default=1.0)
    character_stats = db.Column(db.JSON, default={})
    unlocked_features = db.Column(db.JSON, default={})
    total_play_time = db.Column(db.Integer, default=0)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'current_level': self.current_level,
            'game_difficulty': self.game_difficulty,
            'character_stats': self.character_stats,
            'unlocked_features': self.unlocked_features,
            'total_play_time': self.total_play_time,
            'last_active': self.last_active.isoformat()
        }

class GameProgress(db.Model):
    """游戏进度模型"""
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