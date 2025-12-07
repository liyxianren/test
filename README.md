# CBT情绪日记游戏

<div align="center">

![CBT情绪日记游戏](https://img.shields.io/badge/CBT-情绪日记游戏-blue?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Flask](https://img.shields.io/badge/Flask-2.3.3-red?style=for-the-badge&logo=flask)
![MySQL](https://img.shields.io/badge/MySQL-8.0-blue?style=for-the-badge&logo=mysql)
![AI](https://img.shields.io/badge/AI-Powered-purple?style=for-the-badge)

**融合认知行为疗法(CBT)与游戏化的情绪日记Web应用**

</div>

## 项目简介

CBT情绪日记游戏是一个将**认知行为疗法(CBT)**理论与**游戏化交互**结合的Web应用。用户通过记录情绪日记，AI分析后生成个性化的游戏参数、CBT洞察、探险挑战，以及来自旅行狐狸吉祥物"小橘"的明信片。

### 核心理念

> **影响我们情绪的不是事件本身，而是我们对事件的解读和认知。**

基于CBT理论的认知三角模型，通过AI技术分析用户的情绪日记，在游戏中帮助用户进行认知重构练习。

## 技术栈

### 后端
- **框架**: Flask 2.3.3 + SQLAlchemy 2.0
- **数据库**: MySQL 8.0 / SQLite（开发）
- **认证**: Flask-JWT-Extended
- **部署**: Zeabur

### 前端
- **基础**: HTML5 + CSS3 + JavaScript ES6+
- **UI框架**: Bootstrap 5.3.0
- **图标**: Font Awesome 6.4.0

### AI服务
- **ChatGLM (智谱AI)**: 日记分析，模型 `glm-4.5-x`
- **豆包 (Doubao)**: CBT挑战生成，模型 `doubao-seed-1-6-flash-250828`
- **豆包 Seedream**: 明信片图片生成，模型 `doubao-seedream-4-5-251128`

## 功能特色

### 情绪日记系统
- 步骤式引导写日记（事件→想法→情绪→内容）
- AI自动分析情绪并生成CBT洞察
- 情绪标签和强度记录

### 游戏化CBT体验
- **探险系统**: 击败"迷雾怪物"（认知扭曲的具象化）
- **CBT挑战**: 识别正确思维 vs 扭曲思维的选择题
- **奖励系统**: 金币、道具、属性提升

### 明信片系统
- 小橘根据情绪状态去不同地点"旅行"
- AI生成旅行场景图片
- 温暖的文字陪伴

### 管理后台
- 用户管理、日记浏览、流量分析
- 默认管理员: `admin` / `kongbai123`

## 快速开始

### 环境要求
- Python 3.9+
- MySQL 8.0+（或使用SQLite进行本地开发）

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/your-username/cbt-emotion-diary-game.git
cd cbt-emotion-diary-game

# 2. 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入API密钥等配置

# 5. 启动应用（自动创建数据库表）
python app.py
```

### Windows快捷方式
```bash
deploy.bat    # 完整部署（创建venv、安装依赖、初始化DB）
start.bat     # 开发模式启动
```

### 环境变量配置

```bash
# 必需 - AI服务
ZHIPU_API_KEY=your-zhipu-api-key
ZHIPU_MODEL_NAME=glm-4.5-x
ARK_API_KEY=your-ark-api-key
DOUBAO_IMAGE_MODEL=doubao-seedream-4-5-251128

# 数据库（云端使用MySQL，本地可用SQLite）
DATABASE_URL=mysql+pymysql://user:password@host:port/database?charset=utf8mb4
# 或回退到SQLite
# SQLITE_PATH=diary.db

# JWT认证
JWT_SECRET_KEY=your-jwt-secret-key
```

## 项目架构

### 目录结构

```
diary/
├── app.py                 # 主应用入口
├── models.py              # 数据库模型（8个核心模型）
├── extensions.py          # Flask扩展初始化
├── routes/                # API路由蓝图
│   ├── auth.py           # 用户认证
│   ├── diary.py          # 日记CRUD
│   ├── analysis.py       # AI情绪分析
│   ├── game.py           # 游戏状态
│   ├── adventure.py      # CBT探险游戏
│   ├── postcard.py       # 明信片系统
│   └── admin.py          # 管理后台API
├── services/              # 业务服务层
│   ├── doubao_service.py # 豆包API客户端
│   ├── postcard_service.py # 明信片生成
│   └── adventure_service.py # 探险会话管理
├── prompts/               # AI提示词模板
│   ├── chatglm_prompts.py
│   ├── adventure_prompts.py
│   └── postcard_prompts.py
├── templates/             # HTML模板
│   ├── admin/            # 管理后台页面
│   └── ...               # 用户页面
└── static/               # 静态资源
```

### 数据库模型

| 模型 | 说明 |
|------|------|
| User | 用户账户，含管理员标识 |
| EmotionDiary | 情绪日记 |
| EmotionAnalysis | AI分析结果 |
| GameState | 游戏状态（心理健康值、压力、成长潜力、金币等） |
| AdventureSession | CBT探险会话 |
| Postcard | 小橘明信片 |
| UserItem | 用户道具 |
| AccessLog | 访问日志 |

### API路由

| 路径 | 说明 |
|------|------|
| `/api/auth/*` | 用户认证（注册、登录、重置密码） |
| `/api/diary/*` | 日记CRUD |
| `/api/analysis/*` | 情绪分析 |
| `/api/game/*` | 游戏状态 |
| `/api/adventure/*` | CBT探险 |
| `/api/postcard/*` | 明信片 |
| `/api/admin/*` | 管理后台 |

## 核心工作流

1. **用户写日记** → 步骤式表单引导
2. **AI分析** → ChatGLM返回CBT洞察 + 属性变化
3. **游戏状态更新** → 心理健康值、压力、成长潜力 ±5
4. **探险挑战生成** → 豆包生成3道CBT选择题
5. **明信片生成** → 豆包Seedream生成旅行场景图

## 部署

### Zeabur部署
- 自动注入MySQL环境变量
- 通过`ensure_schema_updates()`自动迁移数据库
- ProxyFix中间件处理HTTPS

### 生产模式
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 许可证

MIT License

---

<div align="center">

**用科学与爱，帮助每个人重获内心平衡**

</div>
