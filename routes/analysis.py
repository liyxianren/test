from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import EmotionAnalysis, EmotionDiary, db
from datetime import datetime
import json
import os
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
from dotenv import load_dotenv

# 加载环境变量（确保在standalone测试时也能工作）
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
    from prompts.chatglm_prompts import (
        get_user_friendly_prompt,
        get_game_data_prompt,
        get_system_prompt
    )
except ImportError:
    print("警告: 未找到chatglm_prompts模块，使用默认Prompt", file=sys.stderr)
    get_user_friendly_prompt = None
    get_game_data_prompt = None
    get_system_prompt = None

bp = Blueprint('analysis', __name__)

class EmotionAnalysisService:
    """情绪分析服务类"""

    def __init__(self):
        self.coze_api_key = os.getenv('COZE_API_KEY')
        self.coze_bot_id = os.getenv('COZE_BOT_ID')
        self.coze_base_url = os.getenv('COZE_BASE_URL', 'https://api.coze.com')
        self.qwen_api_key = os.getenv('QWEN_API_KEY')
        self.qwen_model = os.getenv('QWEN_MODEL_NAME', 'qwen-turbo')

        # 智谱AI ChatGLM配置
        self.zhipu_api_key = os.getenv('ZHIPU_API_KEY')
        self.zhipu_model = os.getenv('ZHIPU_MODEL_NAME', 'glm-4-flash')  # 修正默认模型名
        self.zhipu_client = None

        if self.zhipu_api_key and ZhipuAI:
            try:
                self.zhipu_client = ZhipuAI(api_key=self.zhipu_api_key)
                print(f"[成功] 智谱AI客户端初始化成功，模型: {self.zhipu_model}", file=sys.stderr)
            except Exception as e:
                print(f"[失败] 智谱AI客户端初始化失败: {e}", file=sys.stderr)
                self.zhipu_client = None
        else:
            if not self.zhipu_api_key:
                print("[警告] 未设置 ZHIPU_API_KEY 环境变量", file=sys.stderr)
            if not ZhipuAI:
                print("[警告] 未安装 zhipuai 包，请运行: pip install zhipuai", file=sys.stderr)

    def analyze_with_coze(self, text):
        """使用COZE API进行情绪分析"""
        if not self.coze_api_key or not self.coze_bot_id:
            return None

        try:
            # 构建请求数据
            headers = {
                'Authorization': f'Bearer {self.coze_api_key}',
                'Content-Type': 'application/json'
            }

            payload = {
                'bot_id': self.coze_bot_id,
                'user_id': 'cbt_diary_user',
                'query': f"请分析以下文本的情绪：{text}",
                'stream': False
            }

            response = requests.post(
                f'{self.coze_base_url}/v1/chat/completions',
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return self.parse_coze_response(result)
            else:
                print(f"COZE API调用失败: {response.status_code}")
                return None

        except Exception as e:
            print(f"COZE API调用异常: {str(e)}")
            return None

    def analyze_with_qwen(self, text):
        """使用QWEN模型进行情绪分析"""
        if not self.qwen_api_key:
            return None

        try:
            headers = {
                'Authorization': f'Bearer {self.qwen_api_key}',
                'Content-Type': 'application/json'
            }

            # 构建情绪分析提示词
            prompt = f"""
            请对以下文本进行情绪分析，返回JSON格式的结果：

            文本内容："{text}"

            请分析以下内容并返回JSON格式：
            {{
                "overall_emotion": "主要情绪（happy, sad, angry, anxious, calm, neutral等）",
                "emotion_intensity": 情绪强度（0.0-1.0）,
                "emotion_dimensions": {{
                    "valence": 情绪效价（-1.0到1.0，负值表示负面情绪，正值表示正面情绪）,
                    "arousal": 唤醒度（0.0-1.0，表示情绪的激烈程度）,
                    "dominance": 控制度（0.0-1.0，表示对情绪的控制感）
                }},
                "key_words": ["关键词1", "关键词2", ...],
                "confidence_score": 置信度（0.0-1.0）
            }}
            """

            payload = {
                'model': self.qwen_model,
                'input': {
                    'messages': [
                        {
                            'role': 'system',
                            'content': '你是一个专业的情绪分析助手，请准确分析文本中的情绪状态。'
                        },
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ]
                },
                'parameters': {
                    'result_format': 'message'
                }
            }

            response = requests.post(
                'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generate',
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return self.parse_qwen_response(result)
            else:
                print(f"QWEN API调用失败: {response.status_code}")
                return None

        except Exception as e:
            print(f"QWEN API调用异常: {str(e)}")
            return None

    def parse_coze_response(self, response_data):
        """解析COZE API响应"""
        try:
            # 这里需要根据COZE API的实际响应格式进行解析
            # 假设返回的是文本格式的情绪分析结果
            content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')

            # 简单的情绪识别逻辑
            emotions = {
                'happy': ['开心', '快乐', '高兴', '愉快', '满足'],
                'sad': ['难过', '悲伤', '沮丧', '失落', '痛苦'],
                'angry': ['生气', '愤怒', '恼火', '气愤', '暴躁'],
                'anxious': ['焦虑', '担心', '紧张', '不安', '恐惧'],
                'calm': ['平静', '宁静', '安详', '放松', '舒适']
            }

            detected_emotion = 'neutral'
            confidence = 0.5

            for emotion, keywords in emotions.items():
                for keyword in keywords:
                    if keyword in content:
                        detected_emotion = emotion
                        confidence = 0.7
                        break

            return {
                'overall_emotion': detected_emotion,
                'emotion_intensity': 0.6,
                'emotion_dimensions': {
                    'valence': 0.0,
                    'arousal': 0.5,
                    'dominance': 0.5
                },
                'key_words': self.extract_keywords(content),
                'confidence_score': confidence
            }

        except Exception as e:
            print(f"COZE响应解析失败: {str(e)}")
            return None

    def parse_qwen_response(self, response_data):
        """解析QWEN API响应"""
        try:
            content = response_data.get('output', {}).get('choices', [{}])[0].get('message', {}).get('content', '')

            # 尝试解析JSON格式
            import json
            try:
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                # 如果无法解析JSON，使用备用解析方法
                return self.parse_text_emotion(content)

        except Exception as e:
            print(f"QWEN响应解析失败: {str(e)}")
            return None

    def parse_text_emotion(self, text):
        """从文本中解析情绪信息"""
        emotions = {
            'happy': ['开心', '快乐', '高兴', '愉快', '满足', '幸福'],
            'sad': ['难过', '悲伤', '沮丧', '失落', '痛苦', '伤心'],
            'angry': ['生气', '愤怒', '恼火', '气愤', '暴躁', '气愤'],
            'anxious': ['焦虑', '担心', '紧张', '不安', '恐惧', '害怕'],
            'calm': ['平静', '宁静', '安详', '放松', '舒适', '安心']
        }

        # 简单的情绪识别
        emotion_scores = {}
        for emotion, keywords in emotions.items():
            score = sum(1 for keyword in keywords if keyword in text)
            emotion_scores[emotion] = score

        # 找出得分最高的情绪
        max_emotion = max(emotion_scores.items(), key=lambda x: x[1])
        detected_emotion = max_emotion[0] if max_emotion[1] > 0 else 'neutral'

        return {
            'overall_emotion': detected_emotion,
            'emotion_intensity': min(0.9, max_emotion[1] * 0.3),
            'emotion_dimensions': {
                'valence': 0.0,
                'arousal': 0.5,
                'dominance': 0.5
            },
            'key_words': self.extract_keywords(text),
            'confidence_score': min(0.9, max_emotion[1] * 0.2 + 0.3)
        }

    def extract_keywords(self, text):
        """提取关键词"""
        # 简单的关键词提取
        common_words = ['的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这']

        import re
        words = re.findall(r'[\u4e00-\u9fff]+', text)
        word_freq = {}

        for word in words:
            if len(word) >= 2 and word not in common_words:
                word_freq[word] = word_freq.get(word, 0) + 1

        # 返回频率最高的前10个词
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:10]]

    def generate_emotion_mapping(self, emotion_data):
        """生成情绪-游戏映射配置"""
        emotion = emotion_data.get('overall_emotion', 'neutral')
        intensity = emotion_data.get('emotion_intensity', 0.5)

        # 游戏难度映射
        difficulty_mapping = {
            'happy': 0.7,
            'sad': 1.2,
            'angry': 1.4,
            'anxious': 1.3,
            'calm': 0.8,
            'neutral': 1.0
        }

        base_difficulty = difficulty_mapping.get(emotion, 1.0)
        final_difficulty = base_difficulty * (0.8 + intensity * 0.4)

        # 角色属性影响
        character_effects = {
            'speed': 1.0,
            'strength': 1.0,
            'intelligence': 1.0
        }

        if emotion == 'sad':
            character_effects['speed'] = 0.8
            character_effects['strength'] = 0.9
        elif emotion == 'angry':
            character_effects['strength'] = 1.2
            character_effects['intelligence'] = 0.9
        elif emotion == 'anxious':
            character_effects['speed'] = 1.1
            character_effects['intelligence'] = 0.8
        elif emotion == 'happy':
            character_effects['speed'] = 1.1
            character_effects['intelligence'] = 1.1

        economy_modifiers = self._calculate_game_projection({
            'overall_emotion': emotion,
            'emotion_intensity': intensity,
            'valence_score': self._emotion_to_valence(emotion),
            'trigger_summary': ''
        })

        return {
            'difficulty_modifier': final_difficulty,
            'character_effects': character_effects,
            'scenario_recommendations': self.get_scenario_recommendations(emotion),
            'cbt_challenges': self.generate_cbt_challenges(emotion),
            'economy_modifiers': economy_modifiers
        }

    def get_scenario_recommendations(self, emotion):
        """根据情绪推荐游戏场景"""
        scenarios = {
            'happy': ['阳光草原', '彩虹山谷', '欢乐城堡'],
            'sad': ['宁静湖泊', '月光森林', '温暖小屋'],
            'angry': ['平静海岸', '禅意花园', '冥想空间'],
            'anxious': ['轻松海滩', '舒缓温泉', '安静图书馆'],
            'calm': ['禅意庭院', '平静湖面', '和谐花园']
        }

        return scenarios.get(emotion, ['神秘岛屿'])

    def generate_cbt_challenges(self, emotion):
        """生成CBT挑战任务"""
        challenges = {
            'sad': [
                '识别负面思维模式',
                '寻找积极证据',
                '重构消极想法',
                '练习感恩日记'
            ],
            'angry': [
                '情绪识别练习',
                '愤怒管理技巧',
                '换位思考练习',
                '放松训练'
            ],
            'anxious': [
                '焦虑源识别',
                '现实性检验',
                '应对策略制定',
                '正念练习'
            ],
            'happy': [
                '维持积极状态',
                '分享快乐经验',
                '建立健康习惯',
                '目标设定'
            ],
            'calm': [
                '保持内心平静',
                '深度思考练习',
                '自我反思',
                '持续成长'
            ]
        }

        return challenges.get(emotion, ['基础认知训练'])

    def analyze_with_chatglm_dual(self, emotions, trigger_event, intensity, content):
        """
        使用ChatGLM双调用：并行获取用户友好版和游戏数值版
        返回: (user_message, game_data)
        """
        if not self.zhipu_client:
            print("[警告] ChatGLM客户端未初始化，使用降级方案", file=sys.stderr)
            return self._fallback_dual_analysis(emotions, trigger_event, intensity, content)

        # 准备两个Prompt
        if get_user_friendly_prompt and get_game_data_prompt:
            prompt_user = get_user_friendly_prompt(emotions, trigger_event, intensity, content)
            prompt_game = get_game_data_prompt(emotions, trigger_event, intensity, content)
        else:
            # 如果Prompt模块加载失败，使用内置Prompt
            prompt_user = self._get_default_user_prompt(emotions, trigger_event, intensity, content)
            prompt_game = self._get_default_game_prompt(emotions, trigger_event, intensity, content)

        # 使用线程池并行调用
        with ThreadPoolExecutor(max_workers=2) as executor:
            # 提交两个任务
            print(f"[调试] 准备调用用户友好版: max_tokens=1500, temp=0.8", file=sys.stderr)
            print(f"[调试] 用户友好版Prompt前50字符: {prompt_user[:50]}...", file=sys.stderr)

            future_user = executor.submit(
                self._call_chatglm_single,
                prompt_user,
                max_tokens=1500,
                temperature=0.8  # 用户版更温暖
            )

            print(f"[调试] 准备调用游戏数据版: max_tokens=4000, temp=0.3", file=sys.stderr)
            print(f"[调试] 游戏数据版Prompt前50字符: {prompt_game[:50]}...", file=sys.stderr)

            future_game = executor.submit(
                self._call_chatglm_single,
                prompt_game,
                max_tokens=4000,  # 增加到4000确保JSON完整
                temperature=0.3  # 数据版更精确
            )

            # 等待结果
            user_message = None
            game_data = None

            for future in as_completed([future_user, future_game]):
                if future == future_user:
                    try:
                        user_message = future.result()
                    except Exception as e:
                        print(f"[错误] 用户友好版调用失败: {e}", file=sys.stderr)
                        user_message = "抱歉，AI分析暂时不可用，但你的日记已经安全保存了。"

                elif future == future_game:
                    try:
                        game_data_raw = future.result()
                        # 解析JSON
                        game_data = self._parse_game_data_json(game_data_raw)
                    except Exception as e:
                        print(f"[错误] 游戏数据版调用失败: {e}", file=sys.stderr)
                        game_data = None

        # 如果游戏数据解析失败，使用降级方案
        if not game_data:
            game_data = self._fallback_game_data(emotions, trigger_event, intensity, content)

        return user_message, game_data

    def _call_chatglm_single(self, prompt, max_tokens=2000, temperature=0.7):
        """单次ChatGLM调用"""
        try:
            system_prompt = get_system_prompt() if get_system_prompt else "你是一位专业的CBT分析师。"

            # 判断调用类型（根据参数）
            call_type = "用户友好版" if max_tokens == 1500 else "游戏数据版" if max_tokens == 4000 else f"未知({max_tokens})"
            print(f"[调试] 开始{call_type}调用ChatGLM，模型: {self.zhipu_model}, max_tokens: {max_tokens}, temp: {temperature}", file=sys.stderr)

            response = self.zhipu_client.chat.completions.create(
                model=self.zhipu_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                stream=False,
                max_tokens=max_tokens,
                temperature=temperature
            )

            content = response.choices[0].message.content
            print(f"[调试] {call_type}响应长度: {len(content) if content else 0} 字符", file=sys.stderr)
            if content:
                print(f"[调试] {call_type}响应前100字符: {content[:100]}...", file=sys.stderr)

            return content

        except Exception as e:
            print(f"[错误] ChatGLM API调用失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            raise

    def _parse_game_data_json(self, json_string):
        """解析游戏数据JSON"""
        try:
            # 检查输入是否为空
            if not json_string or not json_string.strip():
                print(f"[错误] ChatGLM返回空响应", file=sys.stderr)
                return None

            # 移除可能的markdown代码块标记
            cleaned = re.sub(r'```json\s*|\s*```', '', json_string).strip()

            # 记录清理后的内容（用于调试）
            if len(cleaned) < 50:
                print(f"[调试] 清理后内容太短: {cleaned}", file=sys.stderr)
                return None

            # 尝试解析JSON
            data = json.loads(cleaned)

            # 验证必要字段
            required_keys = ['emotion_analysis', 'game_values']
            for key in required_keys:
                if key not in data:
                    print(f"[警告] 缺少必要字段: {key}，尝试使用降级方案", file=sys.stderr)
                    return None

            print(f"[成功] 游戏数据JSON解析成功", file=sys.stderr)
            return data

        except json.JSONDecodeError as e:
            print(f"[错误] JSON解析失败: {e}", file=sys.stderr)
            # 安全地打印原始内容
            if json_string:
                preview = json_string[:300] if len(json_string) > 300 else json_string
                print(f"原始内容前300字符: {preview}", file=sys.stderr)
            else:
                print(f"原始内容为空或None", file=sys.stderr)
            return None
        except Exception as e:
            print(f"[错误] 数据验证失败: {e}", file=sys.stderr)
            return None

    def _fallback_dual_analysis(self, emotions, trigger_event, intensity, content):
        """降级方案：当ChatGLM不可用时"""
        user_message = f"""感谢你记录今天的情绪。

我注意到你感受到了{', '.join(emotions)}，情绪强度达到了{intensity}/10。这种感受在经历"{trigger_event}"之后是完全正常的。

虽然AI分析暂时不可用，但请记住：
1. 记录情绪本身就是一个很好的开始
2. 认识到自己的感受是改变的第一步
3. 继续坚持记录，你会看到进步

加油！💪"""

        game_data = self._fallback_game_data(emotions, trigger_event, intensity, content)

        return user_message, game_data

    def _fallback_game_data(self, emotions, trigger_event, intensity, content):
        """降级方案：生成基础游戏数据"""
        # 简单分类正负面情绪
        positive_emotions = ['开心', '平静', '温暖', '兴奋', '满足']
        negative_emotions = ['焦虑', '愤怒', '悲伤', '沮丧', '害怕', '孤独']

        pos_count = sum(1 for e in emotions if e in positive_emotions)
        neg_count = sum(1 for e in emotions if e in negative_emotions)

        emotion_balance = (pos_count - neg_count) / max(len(emotions), 1)
        emotion_intensity_normalized = intensity / 10.0

        # 计算游戏数值
        mental_health = max(0, min(100, int(100 - (emotion_intensity_normalized * 100) + (emotion_balance * 20))))
        stress_level = int(emotion_intensity_normalized * 100)
        income_multiplier = max(0.5, min(2.0, 1.0 + (emotion_balance * 0.5)))

        return {
            "emotion_analysis": {
                "primary_emotion": emotions[0] if emotions else "平静",
                "emotion_intensity": emotion_intensity_normalized,
                "positive_emotions": [e for e in emotions if e in positive_emotions],
                "negative_emotions": [e for e in emotions if e in negative_emotions],
                "emotion_balance": emotion_balance
            },
            "cbt_insights": {
                "cognitive_distortions": [],
                "core_beliefs": [],
                "automatic_thoughts": []
            },
            "game_values": {
                "mental_health_score": mental_health,
                "stress_level": stress_level,
                "growth_potential": 50,
                "daily_income_base": 100,
                "income_multiplier": income_multiplier,
                "energy_level": max(0, 100 - stress_level),
                "mood_bonus": int((emotion_balance * 50))
            },
            "challenges": [],
            "recommendations": {
                "suggested_game": "基础情绪管理",
                "difficulty_level": max(1, min(5, int(emotion_intensity_normalized * 5))),
                "focus_areas": ["情绪识别", "自我关怀"]
            }
        }

    def _get_default_user_prompt(self, emotions, trigger_event, intensity, content):
        """默认的用户友好Prompt"""
        return f"""你是一位温暖的心理咨询师。用户记录了情绪日记，请给予温暖的回应和CBT分析。

情绪: {', '.join(emotions)}
触发事件: {trigger_event}
强度: {intensity}/10
内容: {content}

请用温暖、鼓励的语气回复，包括：
1. 肯定用户记录情绪的勇气
2. 识别主要情绪和可能的认知扭曲
3. 提供3-4条具体的CBT建议
4. 给予希望和支持"""

    def _get_default_game_prompt(self, emotions, trigger_event, intensity, content):
        """默认的游戏数据Prompt"""
        return f"""请分析以下情绪日记并返回JSON格式的游戏数值。

情绪: {', '.join(emotions)}
触发事件: {trigger_event}
强度: {intensity}/10
内容: {content}

返回JSON格式（不要markdown）：
{{
    "emotion_analysis": {{...}},
    "game_values": {{
        "mental_health_score": 0-100,
        "stress_level": 0-100,
        "daily_income_base": 整数,
        "income_multiplier": 小数
    }}
}}"""

    def analyze_cbt_content(self, diary_id, content, emotions, trigger_event, intensity):
        """
        使用ChatGLM双调用分析日记
        返回包含用户消息和游戏数值的完整分析结果
        """
        try:
            print(f"[开始] 分析日记 ID={diary_id}", file=sys.stderr)

            # 使用新的双调用方法
            user_message, game_data = self.analyze_with_chatglm_dual(
                emotions=emotions or [],
                trigger_event=trigger_event or '',
                intensity=intensity,
                content=content
            )

            # 构建返回结果（兼容前端期望的格式）
            analysis_result = {
                # Part 1: 给用户看的温暖消息
                "user_message": user_message,

                # Part 2: 游戏数值（从game_data提取）
                "overall_emotion": game_data['emotion_analysis']['primary_emotion'],
                "emotion_intensity": game_data['emotion_analysis']['emotion_intensity'],
                "cognitive_distortions": game_data.get('cbt_insights', {}).get('cognitive_distortions', []),
                "suggestions": self._extract_suggestions_from_user_message(user_message),
                "recommended_game": game_data.get('recommendations', {}).get('suggested_game', '基础情绪管理'),

                # Part 3: 游戏数值（新增）
                "game_values": game_data['game_values'],
                "emotion_analysis": game_data['emotion_analysis'],
                "challenges": game_data.get('challenges', []),
                "recommendations": game_data.get('recommendations', {}),

                # 元数据
                "ai_model_version": f"chatglm-{self.zhipu_model}",
                "analysis_timestamp": datetime.utcnow().isoformat()
            }

            # 保存到数据库
            self._save_analysis_result(diary_id, analysis_result)

            print(f"[成功] 日记分析完成 ID={diary_id}", file=sys.stderr)
            return analysis_result

        except Exception as e:
            print(f"[错误] CBT分析失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

            # 使用降级方案
            user_message, game_data = self._fallback_dual_analysis(emotions, trigger_event, intensity, content)

            return {
                "user_message": user_message,
                "overall_emotion": game_data['emotion_analysis']['primary_emotion'],
                "emotion_intensity": game_data['emotion_analysis']['emotion_intensity'],
                "cognitive_distortions": [],
                "suggestions": ["继续记录情绪", "关注积极的一面", "寻求支持"],
                "recommended_game": game_data.get('recommendations', {}).get('suggested_game'),
                "game_values": game_data['game_values'],
                "emotion_analysis": game_data['emotion_analysis'],
                "challenges": [],
                "recommendations": game_data.get('recommendations', {}),
                "ai_model_version": "fallback",
                "analysis_timestamp": datetime.utcnow().isoformat()
            }

    def _extract_suggestions_from_user_message(self, user_message):
        """从用户消息中提取建议列表"""
        # 简单的正则提取（假设消息中有编号列表）
        suggestions = []
        import re
        # 匹配 "1. xxx" 或 "- xxx" 格式的列表
        patterns = [
            r'\d+\.\s*(.+?)(?=\n|$)',  # 1. 建议
            r'-\s*(.+?)(?=\n|$)',       # - 建议
            r'•\s*(.+?)(?=\n|$)'        # • 建议
        ]

        for pattern in patterns:
            matches = re.findall(pattern, user_message)
            if matches:
                suggestions.extend([m.strip() for m in matches[:5]])  # 最多5条
                break

        # 如果没找到，返回默认建议
        if not suggestions:
            suggestions = [
                "继续记录你的情绪和想法",
                "尝试识别触发情绪的具体想法",
                "给自己一些关怀和时间"
            ]

        return suggestions[:5]  # 最多返回5条

    def _call_qwen_cbt_analysis(self, prompt):
        """调用QWEN进行CBT分析"""
        headers = {
            'Authorization': f'Bearer {self.qwen_api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            'model': self.qwen_model,
            'input': {
                'messages': [
                    {
                        'role': 'system',
                        'content': '你是一位专业的认知行为治疗(CBT)分析师，擅长识别认知扭曲并提供建设性建议。'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            },
            'parameters': {
                'result_format': 'message'
            }
        }

        response = requests.post(
            'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            content = result.get('output', {}).get('choices', [{}])[0].get('message', {}).get('content', '')

            # 解析JSON响应
            import json
            import re
            # 尝试提取JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

        return None

    def _call_coze_cbt_analysis(self, prompt):
        """调用COZE进行CBT分析"""
        headers = {
            'Authorization': f'Bearer {self.coze_api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            'bot_id': self.coze_bot_id,
            'user_id': 'cbt_diary_user',
            'query': prompt,
            'stream': False
        }

        response = requests.post(
            f'{self.coze_base_url}/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            # 解析COZE响应（根据实际API响应结构调整）
            import json
            import re
            content = str(result)
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

        return None

    def _build_traditional_cbt_prompt(self, payload):
        emotions = ', '.join(payload.get('emotions') or []) or '未指定'
        trigger_event = payload.get('trigger_event') or '未描述'
        intensity = payload.get('intensity') or 5
        content = payload.get('content') or ''
        return f"""
你是一名资深认知行为治疗(CBT)治疗师，请基于来访者的日记给出结构化分析。

**情绪标签**：{emotions}
**触发事件**：{trigger_event}
**情绪强度**：{intensity}/10
**日记正文**：
{content}

请使用JSON输出，字段包含：
{{
    "overall_emotion": "主要情绪",
    "emotion_intensity": 0-1之间的小数，
    "confidence_score": 0-1之间的小数，
    "cognitive_distortions": [
        {{"type": "歪曲类型", "description": "解释"}}
    ],
    "core_beliefs": ["潜在信念1", "潜在信念2"],
    "automatic_thoughts": ["自动思维1", "自动思维2"],
    "suggestions": ["认知重构建议1", "建议2"],
    "recommended_game": "结合情绪的游戏/任务建议",
    "emotion_panel": {{
        "valence_score": -1到1的数值,
        "trigger_summary": "用1-2句总结发生了什么",
        "key_findings": ["观察1", "观察2"]
    }},
    "game_projection": {{
        "income_modifier": -1到1,
        "customer_flow_modifier": -1到1,
        "staff_morale_modifier": -1到1,
        "event_suggestion": "可触发的经营事件"
    }},
    "ai_companion": {{
        "message": "用第一人称安抚语",
        "follow_up_question": "继续对话的问题",
        "affirmation": "鼓励语"
    }},
    "coping_tips": ["小贴士1", "小贴士2"]
}}
"""

    def _call_zhipu_cbt_analysis(self, payload):
        """调用智谱GLM分析日记，返回结构化JSON"""
        if not self.zhipu_client:
            return None

        user_prompt = self._build_traditional_cbt_prompt(payload)
        try:
            response = self.zhipu_client.chat.completions.create(
                model=self.zhipu_model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是资深CBT治疗师兼模拟经营游戏设计师，请输出结构化JSON，语言保持中文。"
                    },
                    {"role": "user", "content": user_prompt}
                ],
                thinking={"type": "enabled"},
                stream=False,
                temperature=0.6,
                max_tokens=2048
            )
        except Exception as exc:
            print(f"调用智谱GLM失败: {exc}")
            return None

        if not response or not getattr(response, 'choices', None):
            return None

        content = response.choices[0].message.content

        if isinstance(content, list):
            parsed_text = ''.join(
                part.get('text', '') if isinstance(part, dict) else str(part)
                for part in content
            )
        else:
            parsed_text = content

        return self._parse_json_response(parsed_text)

    def _parse_json_response(self, raw_text):
        if not raw_text:
            return None

        if isinstance(raw_text, (list, tuple)):
            raw_text = ''.join(str(item) for item in raw_text)

        try:
            return json.loads(raw_text)
        except (json.JSONDecodeError, TypeError):
            match = re.search(r'\{.*\}', str(raw_text), re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    return None
        return None

    def _ensure_panel_defaults(self, analysis_data, payload):
        analysis_data = analysis_data or {}
        fallback_emotion = payload.get('emotions', [None])[0] or 'neutral'
        analysis_data.setdefault('overall_emotion', fallback_emotion)
        raw_intensity = analysis_data.get('emotion_intensity')
        if raw_intensity is None:
            raw_intensity = max(1, min(int(payload.get('intensity') or 5), 10)) / 10.0
        analysis_data['emotion_intensity'] = float(raw_intensity)
        analysis_data.setdefault('confidence_score', 0.75)
        analysis_data.setdefault('cognitive_distortions', [])
        analysis_data.setdefault('core_beliefs', [])
        analysis_data.setdefault('automatic_thoughts', [])
        analysis_data.setdefault('suggestions', [])
        analysis_data.setdefault('recommended_game', '思维觉察训练')
        analysis_data.setdefault('coping_tips', analysis_data['suggestions'][:3])

        panel = analysis_data.get('emotion_panel') or {}
        panel.setdefault('overall_emotion', analysis_data['overall_emotion'])
        panel_intensity = panel.get('emotion_intensity')
        if panel_intensity is None:
            panel_intensity = analysis_data['emotion_intensity']
        panel['emotion_intensity'] = float(min(max(panel_intensity, 0.0), 1.0))
        base_valence = panel.get('valence_score')
        if base_valence is None:
            base_valence = self._emotion_to_valence(panel.get('overall_emotion'))
        panel['valence_score'] = round(base_valence, 3)
        panel['impact_score'] = round(panel['valence_score'] * panel['emotion_intensity'], 3)
        panel.setdefault('trigger_summary', payload.get('trigger_event') or '未描述具体触发事件')
        panel.setdefault('key_findings', [])
        analysis_data['emotion_panel'] = panel

        projection = analysis_data.get('game_projection')
        analysis_data['game_projection'] = self._normalize_projection(projection, panel)

        if not analysis_data.get('ai_companion'):
            analysis_data['ai_companion'] = {
                'message': f"我听见你正经历{panel.get('overall_emotion', '复杂情绪')}，谢谢你记录下来，我们一起想想可以怎么照顾自己。",
                'follow_up_question': '此刻最希望得到哪一种支持？',
                'affirmation': '每一次记录都在帮助自己前进。'
            }

        if not analysis_data.get('key_words'):
            analysis_data['key_words'] = self.extract_keywords(payload.get('content', ''))

        return analysis_data

    def _normalize_projection(self, projection, panel):
        projection = projection or {}
        valence = panel.get('valence_score', 0)
        intensity = panel.get('emotion_intensity', 0.5)

        def clamp(value):
            try:
                return max(-1.0, min(float(value), 1.0))
            except (TypeError, ValueError):
                return 0.0

        default_projection = self._calculate_game_projection(panel)

        return {
            'income_modifier': clamp(projection.get('income_modifier', default_projection['income_modifier'])),
            'customer_flow_modifier': clamp(projection.get('customer_flow_modifier', default_projection['customer_flow_modifier'])),
            'staff_morale_modifier': clamp(projection.get('staff_morale_modifier', default_projection['staff_morale_modifier'])),
            'event_suggestion': projection.get('event_suggestion') or self._event_from_valence(valence, intensity)
        }

    def _calculate_game_projection(self, panel):
        intensity = panel.get('emotion_intensity', 0.5)
        valence = panel.get('valence_score', 0.0)
        impact = valence * intensity

        return {
            'income_modifier': round(impact, 3),
            'customer_flow_modifier': round(impact * 0.7, 3),
            'staff_morale_modifier': round(impact * 0.5, 3),
            'event_suggestion': self._event_from_valence(valence, intensity)
        }

    def _emotion_to_valence(self, emotion):
        if not emotion:
            return 0.0
        mapping = {
            'happy': 0.8,
            'joy': 0.7,
            'calm': 0.4,
            'grateful': 0.6,
            'excited': 0.7,
            'neutral': 0.0,
            'anxious': -0.5,
            'sad': -0.7,
            'angry': -0.8,
            'frustrated': -0.6,
            'fear': -0.7,
            'lonely': -0.6
        }
        return mapping.get(str(emotion).lower(), 0.0)

    def _event_from_valence(self, valence, intensity):
        if valence >= 0.4:
            return '举办节日营销活动，放大积极情绪'
        if valence >= 0.1:
            return '推出小型限时优惠，巩固稳定状态'
        if valence <= -0.6:
            return '启动「情绪修复周」，调低营业强度'
        if valence <= -0.2:
            return '开放员工关怀日，鼓励慢下来'
        return '保持日常经营，关注微小波动'

    def _fallback_cbt_analysis(self, content, emotions, intensity, trigger_event=''):
        """本地兜底逻辑，当LLM不可用时提供基础CBT建议"""
        distortions = []

        if any(word in content for word in ['总是', '永远', '一定', '必须']):
            distortions.append({
                'type': '绝对化思维',
                'description': '容易把事件放大到“永远”或“一定”的程度'
            })

        if any(word in content for word in ['全都', '一无是处', '没救']):
            distortions.append({
                'type': '非黑即白',
                'description': '倾向用极端角度评价自己或他人'
            })

        if any(word in content for word in ['失败', '崩溃', '糟糕']):
            distortions.append({
                'type': '灾难化',
                'description': '习惯预期事情朝最坏方向发展'
            })

        suggestions = [
            '把情绪和事实拆开，把具体事件写清楚',
            '列出支持与反对这些自动想法的证据',
            '想象朋友遇到相同情况，你会给TA什么建议',
            '用3分钟做一次呼吸扫描，回到当下'
        ]

        main_emotion = emotions[0] if emotions else 'neutral'
        normalized_intensity = max(1, min(intensity or 5, 10)) / 10.0

        panel = {
            'overall_emotion': main_emotion,
            'emotion_intensity': normalized_intensity,
            'valence_score': self._emotion_to_valence(main_emotion),
            'trigger_summary': trigger_event or '未详细描述触发事件',
            'key_findings': suggestions[:2]
        }

        return {
            'overall_emotion': main_emotion,
            'emotion_intensity': normalized_intensity,
            'cognitive_distortions': distortions if distortions else [{
                'type': '需要进一步探索',
                'description': '当前文本尚无法定位具体的认知模式，建议继续记录'
            }],
            'core_beliefs': [],
            'automatic_thoughts': [],
            'suggestions': suggestions,
            'recommended_game': '思维重构练习',
            'emotion_panel': panel,
            'game_projection': self._calculate_game_projection(panel),
            'ai_companion': {
                'message': '我看到你已经勇敢地把感受写下来，我们就从这一步慢慢来。',
                'follow_up_question': '最想先调整的是情绪、行为还是思维？',
                'affirmation': '每一次记录都在训练你的自我觉察。'
            },
            'coping_tips': suggestions[:3]
        }

    def _save_analysis_result(self, diary_id, analysis_data):
        """保存情绪分析记录"""
        try:
            existing_analysis = EmotionAnalysis.query.filter_by(diary_id=diary_id).first()
            panel = analysis_data.get('emotion_panel', {})
            confidence = analysis_data.get('confidence_score', 0.8)
            keywords = analysis_data.get('key_words') or analysis_data.get('automatic_thoughts', [])
            model_version = analysis_data.get('ai_model_version', 'cbt-fallback')

            if existing_analysis:
                existing_analysis.overall_emotion = analysis_data.get('overall_emotion')
                existing_analysis.emotion_intensity = analysis_data.get('emotion_intensity')
                existing_analysis.emotion_dimensions = panel
                existing_analysis.key_words = keywords
                existing_analysis.confidence_score = confidence
                existing_analysis.analyzed_at = datetime.utcnow()
                existing_analysis.ai_model_version = model_version
                existing_analysis.analysis_payload = analysis_data
            else:
                new_analysis = EmotionAnalysis(
                    diary_id=diary_id,
                    overall_emotion=analysis_data.get('overall_emotion'),
                    emotion_intensity=analysis_data.get('emotion_intensity'),
                    emotion_dimensions=panel,
                    key_words=keywords,
                    confidence_score=confidence,
                    ai_model_version=model_version,
                    analysis_payload=analysis_data
                )
                db.session.add(new_analysis)

            db.session.commit()

        except Exception as e:
            print(f"保存分析结果失败: {str(e)}")
            db.session.rollback()

emotion_service = EmotionAnalysisService()

@bp.route('/<int:diary_id>', methods=['POST'])
@jwt_required()
def analyze_diary(diary_id):
    """分析单篇日记的情绪"""
    try:
        user_id = get_jwt_identity()

        # 验证日记所有权
        diary = EmotionDiary.query.filter_by(id=diary_id, user_id=user_id).first()
        if not diary:
            return jsonify({'error': 'Diary not found'}), 404

        # 检查是否已有分析结果
        existing_analysis = EmotionAnalysis.query.filter_by(diary_id=diary_id).first()
        if existing_analysis:
            return jsonify({
                'message': 'Analysis already exists',
                'analysis': existing_analysis.to_dict()
            }), 200

        # 进行情绪分析
        text_content = diary.content

        # 尝试使用COZE API
        coze_result = emotion_service.analyze_with_coze(text_content)

        # 如果COZE失败，使用QWEN
        if coze_result:
            analysis_result = coze_result
            ai_model_version = 'coze'
        else:
            qwen_result = emotion_service.analyze_with_qwen(text_content)
            if qwen_result:
                analysis_result = qwen_result
                ai_model_version = 'qwen'
            else:
                # 如果都失败，使用备用分析
                analysis_result = emotion_service.parse_text_emotion(text_content)
                ai_model_version = 'fallback'

        if not analysis_result:
            return jsonify({'error': 'Failed to analyze emotion'}), 500

        # 创建分析记录
        analysis = EmotionAnalysis(
            diary_id=diary_id,
            overall_emotion=analysis_result.get('overall_emotion', 'neutral'),
            emotion_intensity=analysis_result.get('emotion_intensity', 0.5),
            emotion_dimensions=analysis_result.get('emotion_dimensions', {}),
            key_words=analysis_result.get('key_words', []),
            confidence_score=analysis_result.get('confidence_score', 0.5),
            ai_model_version=ai_model_version
        )

        db.session.add(analysis)

        # 更新日记的分析状态
        diary.analysis_status = 'completed'
        diary.emotion_score = {
            'overall_emotion': analysis_result.get('overall_emotion', 'neutral'),
            'emotion_intensity': analysis_result.get('emotion_intensity', 0.5),
            'confidence_score': analysis_result.get('confidence_score', 0.5)
        }

        db.session.commit()

        # 生成游戏映射配置
        game_mapping = emotion_service.generate_emotion_mapping(analysis_result)

        return jsonify({
            'message': 'Emotion analysis completed',
            'analysis': analysis.to_dict(),
            'game_mapping': game_mapping
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@bp.route('/batch', methods=['POST'])
@jwt_required()
def batch_analyze():
    """批量分析日记"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        diary_ids = data.get('diary_ids', [])
        if not diary_ids:
            return jsonify({'error': 'No diary IDs provided'}), 400

        results = []
        for diary_id in diary_ids:
            # 验证日记所有权
            diary = EmotionDiary.query.filter_by(id=diary_id, user_id=user_id).first()
            if not diary:
                results.append({'diary_id': diary_id, 'status': 'not_found'})
                continue

            # 检查是否已有分析结果
            existing_analysis = EmotionAnalysis.query.filter_by(diary_id=diary_id).first()
            if existing_analysis:
                results.append({
                    'diary_id': diary_id,
                    'status': 'already_analyzed',
                    'analysis': existing_analysis.to_dict()
                })
                continue

            # 进行情绪分析（简化版，实际项目中可以优化为异步处理）
            text_content = diary.content
            analysis_result = emotion_service.analyze_with_coze(text_content)

            if not analysis_result:
                analysis_result = emotion_service.analyze_with_qwen(text_content)

            if not analysis_result:
                analysis_result = emotion_service.parse_text_emotion(text_content)

            if analysis_result:
                # 创建分析记录
                analysis = EmotionAnalysis(
                    diary_id=diary_id,
                    overall_emotion=analysis_result.get('overall_emotion', 'neutral'),
                    emotion_intensity=analysis_result.get('emotion_intensity', 0.5),
                    emotion_dimensions=analysis_result.get('emotion_dimensions', {}),
                    key_words=analysis_result.get('key_words', []),
                    confidence_score=analysis_result.get('confidence_score', 0.5),
                    ai_model_version='batch_analysis'
                )

                db.session.add(analysis)

                # 更新日记状态
                diary.analysis_status = 'completed'
                diary.emotion_score = {
                    'overall_emotion': analysis_result.get('overall_emotion', 'neutral'),
                    'emotion_intensity': analysis_result.get('emotion_intensity', 0.5),
                    'confidence_score': analysis_result.get('confidence_score', 0.5)
                }

                results.append({
                    'diary_id': diary_id,
                    'status': 'analyzed',
                    'analysis': analysis.to_dict()
                })
            else:
                results.append({'diary_id': diary_id, 'status': 'analysis_failed'})

        db.session.commit()

        return jsonify({
            'message': 'Batch analysis completed',
            'results': results
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Batch analysis failed: {str(e)}'}), 500

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



