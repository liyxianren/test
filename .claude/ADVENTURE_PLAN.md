# CBT探险游戏开发计划 (MVP版本)

## 项目背景

领导反馈：CBT治疗需要有**交互性**，不能只是被动看明信片。用户有负面情绪时，需要在游戏中通过收集道具、完成挑战来主动消除负面效果。

## 用户确认

- ✅ 探险可跳过，但必须完成探险才能看明信片（选项A）
- ✅ 优先实现"证据收集"和"思维重构"两种挑战
- ✅ 美术素材用AI生成（豆包等）
- ✅ 先做最小可玩版本（MVP）

---

## 核心设计理念

将日记分析识别出的**认知扭曲**转化为游戏中的**迷雾怪物**，用户帮助小橘克服挑战，通过CBT技巧消除负面效果。

---

## MVP范围（第一版）

### 包含功能
1. **2种挑战类型**：证据收集 + 思维重构
2. **4种怪物**：黑云怪、棋盘精、水晶球怪、规则石
3. **基础奖励**：金币 + 属性变化
4. **简单道具**：挑战完成获得治愈道具

### 不包含（后续版本）
- 呼吸练习、迷雾消除、朋友对话挑战
- 装饰道具系统
- 怪物图鉴
- 成就系统

---

## 一、游戏核心玩法

### 游戏流程
```
写日记 → AI分析识别认知扭曲 → 生成探险场景
                              ↓
           用户选择：[开始探险] 或 [跳过]
                              ↓
              ┌───────────────┴───────────────┐
              ↓                               ↓
        完成CBT挑战                      跳过（无奖励）
              ↓                               ↓
        消除怪物 + 获得奖励              直接看明信片
              ↓
        生成明信片（带探险故事）
```

### MVP挑战类型

| 挑战类型 | CBT技巧 | 玩法 | 对应怪物 |
|---------|--------|------|---------|
| 证据收集 | 寻找证据 | 从6个选项中选出3个正确证据 | 黑云怪、水晶球怪 |
| 思维重构 | 认知重建 | 从3个想法中选择最平衡的 | 棋盘精、规则石 |

---

## 二、认知扭曲 → 怪物映射（MVP）

| 认知扭曲 | 怪物名称 | 挑战类型 | 击败奖励 |
|---------|---------|---------|---------|
| 灾难化思维 | 黑云怪 | 证据收集 | 阳光露水(stress-5) |
| 非黑即白 | 棋盘精 | 思维重构 | 平衡羽毛(mental+3) |
| 读心术 | 水晶球怪 | 证据收集 | 清明水滴(stress-3) |
| 应该思维 | 规则石 | 思维重构 | 自由羽毛(growth+3) |

**难度映射**（基于severity 1-10）：
- 1-4: 简单，选3个正确答案，1.0x奖励
- 5-7: 中等，选3个正确答案+干扰项，1.5x奖励
- 8-10: 困难，需要选4个正确答案，2.0x奖励

---

## 三、数据库模型（MVP）

### 新增模型

```python
# models.py 新增

class AdventureSession(db.Model):
    """探险会话"""
    __tablename__ = 'adventure_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    diary_id = db.Column(db.Integer, db.ForeignKey('emotion_diaries.id'), nullable=False)

    status = db.Column(db.String(20), default='pending')  # pending/in_progress/completed/skipped
    scene_name = db.Column(db.String(100))

    # 怪物和挑战（JSON）
    monsters = db.Column(db.JSON, default=[])      # [{type, name_zh, severity, defeated}]
    challenges = db.Column(db.JSON, default=[])    # [{type, options, correct_answers, completed}]
    current_challenge = db.Column(db.Integer, default=0)

    # 奖励
    coins_earned = db.Column(db.Integer, default=0)
    items_earned = db.Column(db.JSON, default=[])  # [{name, effect}]
    stat_changes = db.Column(db.JSON, default={})  # {mental: +3, stress: -5}

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)


class UserItem(db.Model):
    """用户道具"""
    __tablename__ = 'user_items'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    item_name = db.Column(db.String(50), nullable=False)
    item_name_zh = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    effect_type = db.Column(db.String(30))  # stress_reduce/mental_boost/growth_boost
    effect_value = db.Column(db.Integer, default=0)
    acquired_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### GameState扩展
```python
# 在现有GameState模型中添加
total_adventures = db.Column(db.Integer, default=0)
monsters_defeated = db.Column(db.Integer, default=0)
```

---

## 四、API设计（MVP）

### 探险API (`routes/adventure.py`)

```python
# 1. 获取/创建探险会话
GET/POST /api/adventure/session/<diary_id>
返回: {adventure_id, status, monsters, challenges, scene_name}

# 2. 提交挑战答案
POST /api/adventure/<id>/submit
请求: {challenge_index, selected_answers: [0, 2, 4]}
返回: {correct, score, monster_defeated, next_challenge}

# 3. 完成探险
POST /api/adventure/<id>/complete
返回: {rewards: {coins, items, stat_changes}, postcard_id}

# 4. 跳过探险
POST /api/adventure/<id>/skip
返回: {postcard_id}  # 无奖励，直接看明信片
```

---

## 五、前端页面（MVP）

### 新增文件
```
templates/
└── adventure.html          # 探险主页面（单页应用）

static/js/
└── adventure.js            # 探险游戏逻辑
```

### 页面结构
```html
<!-- adventure.html -->
<div class="adventure-container">
    <!-- 场景背景 -->
    <div class="scene-bg" id="sceneBg"></div>

    <!-- 怪物显示区 -->
    <div class="monster-area" id="monsterArea">
        <div class="monster-sprite"></div>
        <div class="monster-name">黑云怪</div>
        <div class="monster-hp-bar"></div>
    </div>

    <!-- 小橘 -->
    <div class="xiaoju" id="xiaoju">
        <img src="/game/xiaoju.png" alt="小橘">
    </div>

    <!-- 挑战区域 -->
    <div class="challenge-panel" id="challengePanel">
        <h3 class="challenge-title">找出反驳这个想法的证据</h3>
        <div class="challenge-question">我觉得明天的演讲一定会失败</div>
        <div class="options-grid" id="optionsGrid">
            <!-- 6个选项 -->
        </div>
        <button class="btn-submit" id="btnSubmit">确认选择</button>
    </div>

    <!-- 顶部UI -->
    <div class="top-ui">
        <div class="progress">挑战 1/2</div>
        <button class="btn-skip">跳过探险</button>
    </div>

    <!-- 结算弹窗 -->
    <div class="victory-modal" id="victoryModal" style="display:none;">
        <h2>探险完成！</h2>
        <div class="rewards-list"></div>
        <button class="btn-view-postcard">查看明信片</button>
    </div>
</div>
```

---

## 六、AI Prompt（探险生成）

### 新增 `prompts/adventure_prompts.py`

```python
def get_adventure_prompt(cognitive_distortions, diary_content, emotions):
    """生成探险挑战内容的Prompt"""

    system = """你是CBT探险游戏的挑战设计师。根据用户日记中识别的认知扭曲，生成对应的CBT挑战。

## 挑战类型
1. 证据收集（evidence）：给出6个选项，其中3个是反驳该认知扭曲的有效证据
2. 思维重构（reframe）：给出3个替代想法，其中1个是最平衡健康的

## 输出JSON格式
{
    "scene_name": "迷雾森林",
    "challenges": [
        {
            "monster_type": "dark_cloud",
            "monster_name_zh": "黑云怪",
            "challenge_type": "evidence",
            "distortion_thought": "用户的具体负面想法",
            "question": "找出能反驳这个想法的证据",
            "options": [
                {"id": 0, "text": "选项1", "is_correct": true, "explanation": "这是有效证据因为..."},
                {"id": 1, "text": "选项2", "is_correct": false, "explanation": "这不是有效证据因为..."},
                ...
            ],
            "correct_count": 3,
            "cbt_insight": "完成后显示的CBT洞察"
        }
    ]
}"""

    return system, user_prompt
```

---

## 七、关键文件清单

| 文件 | 操作 | 内容 |
|------|------|------|
| `models.py` | 修改 | 添加AdventureSession, UserItem模型 |
| `app.py` | 修改 | 注册adventure蓝图 + 新页面路由 |
| `routes/__init__.py` | 修改 | 导出adventure_bp |
| `routes/adventure.py` | **新建** | 探险API |
| `routes/analysis.py` | 修改 | 分析完成后创建探险会话 |
| `services/adventure_service.py` | **新建** | 探险业务逻辑 |
| `prompts/adventure_prompts.py` | **新建** | 探险Prompt |
| `templates/adventure.html` | **新建** | 探险页面 |
| `static/js/adventure.js` | **新建** | 探险前端逻辑 |
| `templates/diary_result.html` | 修改 | 添加"开始探险"按钮 |

---

## 八、实施步骤

### 步骤1：数据库模型
1. 在models.py添加AdventureSession和UserItem
2. 扩展GameState添加统计字段
3. 更新ensure_schema_updates()

### 步骤2：探险API
1. 创建routes/adventure.py
2. 实现session创建/获取
3. 实现挑战提交逻辑
4. 实现完成/跳过逻辑

### 步骤3：AI生成
1. 创建prompts/adventure_prompts.py
2. 创建services/adventure_service.py
3. 实现挑战内容生成

### 步骤4：前端页面
1. 创建templates/adventure.html
2. 创建static/js/adventure.js
3. 实现挑战交互逻辑
4. 实现奖励结算动画

### 步骤5：集成
1. 修改analysis.py，分析完成后创建探险
2. 修改diary_result.html，添加探险入口
3. 整合明信片生成流程

### 步骤6：测试
1. 端到端测试完整流程
2. 测试各种认知扭曲的挑战生成
3. 测试奖励计算

---

## 九、素材需求（AI生成）

| 素材 | 用途 | 生成方式 |
|------|------|---------|
| 场景背景 | 探险场景 | 豆包生成像素风背景 |
| 怪物图片 | 4种怪物 | 豆包生成像素风怪物 |
| 小橘动画 | 角色状态 | 复用现有或AI生成 |
| 道具图标 | 奖励展示 | 简单图标或emoji |

---

## 十、后续扩展（V2+）

1. 更多挑战类型（呼吸练习、迷雾消除、朋友对话）
2. 更多怪物类型
3. 装饰道具系统（装扮小橘）
4. 怪物图鉴
5. 成就系统
6. 探险故事线

---

## 十一、MVP实施任务清单

### 阶段1：数据库模型 ⬜
- [ ] 1.1 在models.py添加AdventureSession模型
- [ ] 1.2 在models.py添加UserItem模型
- [ ] 1.3 在app.py的ensure_schema_updates()添加新表字段

### 阶段2：探险API基础框架 ⬜
- [ ] 2.1 创建routes/adventure.py
- [ ] 2.2 实现GET/POST /api/adventure/session/<diary_id>
- [ ] 2.3 实现POST /api/adventure/<id>/submit
- [ ] 2.4 实现POST /api/adventure/<id>/complete
- [ ] 2.5 实现POST /api/adventure/<id>/skip
- [ ] 2.6 在routes/__init__.py导出adventure_bp
- [ ] 2.7 在app.py注册蓝图

### 阶段3：探险Prompt和服务层 ⬜
- [ ] 3.1 创建prompts/adventure_prompts.py
- [ ] 3.2 创建services/adventure_service.py
- [ ] 3.3 实现generate_adventure_challenges()函数
- [ ] 3.4 实现calculate_rewards()函数

### 阶段4：探险前端页面 ⬜
- [ ] 4.1 创建templates/adventure.html
- [ ] 4.2 创建static/js/adventure.js
- [ ] 4.3 实现挑战交互逻辑（证据收集）
- [ ] 4.4 实现挑战交互逻辑（思维重构）
- [ ] 4.5 实现奖励结算动画
- [ ] 4.6 在app.py添加/adventure/<diary_id>路由

### 阶段5：素材准备 ⬜
- [ ] 5.1 准备4种怪物图片（黑云怪、棋盘精、水晶球怪、规则石）
- [ ] 5.2 准备2-3个场景背景图
- [ ] 5.3 准备小橘角色图片
- [ ] 5.4 准备道具图标（可用emoji代替）

### 阶段6：集成测试 ⬜
- [ ] 6.1 修改diary_result.html添加"开始探险"按钮
- [ ] 6.2 修改routes/analysis.py，分析完成后创建探险会话
- [ ] 6.3 测试完整流程：日记→分析→探险→明信片
- [ ] 6.4 调试和修复bug

---

## 当前进度

**状态**: ✅ MVP基本完成
**最后更新**: 2025-12-05

### 已完成功能

#### 1. 数据库模型 ✅
- AdventureSession 模型已添加
- UserItem 模型已添加
- Postcard 模型已完善

#### 2. 探险API ✅
- `routes/adventure.py` - 完整的探险API
  - GET/POST `/api/adventure/session/<diary_id>` - 获取/创建探险
  - POST `/api/adventure/<id>/submit` - 提交答案
  - POST `/api/adventure/<id>/complete` - 完成探险
  - POST `/api/adventure/<id>/skip` - 跳过探险

#### 3. AI服务（豆包） ✅
- **探险题目生成**: `services/doubao_service.py`
  - 使用 `doubao-seed-1-6-flash-250828` 模型
  - 紧凑格式：AI返回 `怪物类型|错误想法|正确想法`（~30字/题）
  - 后端组装完整题目
  - 速度：**~12秒/3道题**（原34秒）

- **明信片生成**: `services/postcard_service.py`
  - 使用 `doubao-seed-1-6-flash-250828` 模型
  - 小狐狸讲述森林故事来呼应用户情绪
  - 速度：**~20秒**（原56秒）

#### 4. Prompt设计 ✅
- `prompts/adventure_prompts.py` - 探险题目Prompt
- `prompts/postcard_prompts.py` - 小狐狸回信Prompt（故事模式）
  - 8个森林朋友（小乌龟慢慢、小兔子棉棉、小熊蜜蜜等）
  - 通过故事呼应用户情绪，不是直接说教

#### 5. 前端页面 ✅
- `templates/adventure.html` - 探险页面
- `static/js/adventure.js` - 探险交互逻辑
- `templates/diary_result.html` - 日记结果页（含探险入口）

#### 6. 素材 ✅
- `game/` 目录下的SVG素材
  - 森林背景、小橘角色、12种怪物图片

### 性能优化成果

| 功能 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 探险题目生成 | 34秒 | 12秒 | 2.8x |
| 明信片生成 | 56秒 | 20秒 | 2.8x |

### 完整用户流程

```
写日记 → 提交 → 进入探险（或跳过）
                    ↓
         完成CBT挑战（3道题）
                    ↓
         击败怪物 + 获得奖励
                    ↓
         生成小狐狸明信片（故事模式）
                    ↓
         查看明信片
```

### 下一步计划

- [ ] 端到端测试完整流程
- [ ] 添加更多怪物类型
- [ ] 优化明信片图片生成
- [ ] 添加成就系统
