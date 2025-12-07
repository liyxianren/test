# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**CBT Emotion Diary Game** (CBT情绪日记游戏) - A web application combining Cognitive Behavioral Therapy (CBT) principles with gamification. Users record emotional diaries which are analyzed by AI to generate personalized game parameters, CBT insights, adventure challenges, and postcards from a traveling fox mascot (小橘).

**Tech Stack**: Flask + SQLAlchemy + MySQL/SQLite, vanilla JavaScript frontend, deployed on Zeabur

**AI Providers**:
- **ChatGLM (ZhipuAI)** - Primary diary analysis (`glm-4.5-x` default)
- **Doubao (豆包)** - CBT challenge generation (`doubao-seed-1-6-flash-250828`)
- **Doubao Seedream** - Postcard image generation (`doubao-seedream-4-5-251128`)

## Development Commands

### Initial Setup
```bash
# Windows
deploy.bat              # Complete deployment: creates venv, installs deps, sets up DB

# Manual setup
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### Running the Application
```bash
# Development mode (auto-reload enabled)
start.bat               # Windows
python app.py           # Any platform

# Production mode
start_prod.bat          # Windows (uses Gunicorn on Linux)
gunicorn -w 4 -b 0.0.0.0:5000 app:app  # Linux/Mac
```

### Database Operations
```bash
# Initialize database (creates all tables)
# The app automatically runs db.create_all() on startup (see app.py:275-277)
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Schema auto-patching happens via ensure_schema_updates() - no manual migrations needed on Zeabur
```

## High-Level Architecture

### Application Structure

**Flask Blueprint Architecture**: The main app ([app.py](app.py)) registers 8 blueprints from [routes/](routes/) and initializes extensions via [extensions.py](extensions.py).

### Database Models ([models.py](models.py))

8 core models with cascade relationships:
- **User** → EmotionDiary (1:N), GameState (1:1), GameProgress (1:N)
- **EmotionDiary** → EmotionAnalysis (1:1), Postcard (1:1), AdventureSession (1:1)
- **User** → UserItem (1:N) - Items earned from adventures
- **AccessLog** - Request logging for admin analytics

Key models:
- `GameState`: Incremental stats (mental_health_score, stress_level, growth_potential) starting at 50, adjusted ±5 per diary
- `Postcard`: AI-generated travel postcards from 小橘 (the fox mascot)
- `AdventureSession`: CBT challenge game sessions with monsters and rewards
- `UserItem`: Collectible items with healing/adventure effects
- `AccessLog`: HTTP request logs for traffic analysis in admin panel

### Database Configuration Strategy

**Multi-environment database resolution** in `resolve_database_url()` ([app.py:40-61](app.py#L40-L61)):
1. Check `DATABASE_URL` (with postgres→postgresql conversion)
2. Fall back to MySQL environment variables (`MYSQL_HOST`, `MYSQL_USER`, etc.)
3. Ultimate fallback to SQLite (`diary.db`) for local development

**Schema migration handling**: The `ensure_schema_updates()` function ([app.py:80-195](app.py#L80-L195)) automatically adds missing columns without migrations, supporting 8 tables with comprehensive field definitions.

### AI Service Architecture

**Three-tier AI integration**:

1. **ChatGLM (ZhipuAI)** - Primary diary analysis ([routes/analysis.py](routes/analysis.py))
   - Unified prompt returns: user_message + score_changes + coins + CBT insights
   - Fallback to local rule-based calculation if API fails

2. **Doubao (豆包)** - CBT challenge generation ([services/doubao_service.py](services/doubao_service.py))
   - Fast Flash model for generating 3 CBT challenges per adventure
   - Compact prompt format: `怪物类型|错误想法|正确想法`

3. **Doubao Seedream** - Postcard image generation ([services/postcard_service.py](services/postcard_service.py))
   - Generates travel scene images based on emotion state via `doubao-seedream-4-5-251128`
   - Requires `ARK_API_KEY` environment variable

### Route Structure

Blueprints registered in [app.py:200-207](app.py#L200-L207):
- `/api/auth/*` - User authentication ([routes/auth.py](routes/auth.py))
- `/api/diary/*` - CRUD + AI analysis ([routes/diary.py](routes/diary.py))
- `/api/analysis/*` - Emotion analysis endpoints ([routes/analysis.py](routes/analysis.py))
- `/api/upload/*` - File uploads ([routes/upload.py](routes/upload.py))
- `/api/game/*` - Game state management ([routes/game.py](routes/game.py))
- `/api/postcard/*` - Postcard generation/retrieval ([routes/postcard.py](routes/postcard.py))
- `/api/adventure/*` - CBT adventure game ([routes/adventure.py](routes/adventure.py))
- `/api/admin/*` - Admin panel API ([routes/admin.py](routes/admin.py))

### Prompt Templates ([prompts/](prompts/))

- `chatglm_prompts.py` - Unified diary analysis prompt with CBT framework
- `adventure_prompts.py` - Monster types and challenge templates
- `postcard_prompts.py` - Location/scene generation for postcard images

### Service Layer ([services/](services/))

- `doubao_service.py` - Doubao API client for CBT challenge generation
- `postcard_service.py` - Async postcard creation with image generation
- `adventure_service.py` - Adventure session management

### Complete Diary Workflow

**Creation → Analysis → Adventure → Postcard**:
1. User submits diary via step-by-step form ([templates/diary_new.html](templates/diary_new.html))
2. Backend creates `EmotionDiary` with `analysis_status='pending'`
3. AI analysis via ChatGLM returns warm CBT feedback + game stat changes
4. `GameState` updated with incremental changes (±5 range)
5. `AdventureSession` created with Doubao-generated CBT challenges
6. `Postcard` queued for async image generation
7. User can play adventure game and view postcard after generation completes

### Environment Variables

**AI Services** (see [.env.example](.env.example)):
- `ZHIPU_API_KEY` + `ZHIPU_MODEL_NAME` - Primary AI (default: `glm-4.5-x`)
- `DOUBAO_API_KEY` + `DOUBAO_MODEL` - CBT challenge generation (default: `doubao-seed-1-6-flash-250828`)
- `ARK_API_KEY` + `DOUBAO_IMAGE_MODEL` - Postcard image generation (default: `doubao-seedream-4-5-251128`)

**Database**:
- `DATABASE_URL` or `MYSQL_*` variables for production
- Falls back to SQLite for local development

**JWT**: `JWT_SECRET_KEY` - Token signing (24h expiry default)

### Admin Panel

**Default admin credentials**: `admin` / `kongbai123` (created on first startup)

**Admin routes** ([templates/admin/](templates/admin/)):
- `/admin/login` - Admin login page
- `/admin/dashboard` - Overview with user stats, traffic analytics
- `/admin/users` - User management (view, edit, delete)
- `/admin/diaries` - Browse all user diaries
- `/admin/postcards` - View generated postcards

### Deployment-Specific Patterns

**Zeabur compatibility**:
- Automatic MySQL environment variable injection handling
- Schema auto-patching via `ensure_schema_updates()` - no Flask-Migrate needed
- URL password encoding via `urllib.parse.quote_plus()` ([app.py:56](app.py#L56))
- ProxyFix middleware for HTTPS behind reverse proxy ([app.py:28-34](app.py#L28-L34))

**Windows batch scripts**:
- `deploy.bat` - Full setup automation
- `start.bat` - Development server
- `start_prod.bat` - Production mode

## Key Implementation Details

### Game State Incremental Model

`GameState` uses incremental scoring ([models.py:129-173](models.py#L129-L173)):
- **mental_health_score**: 0-100, starts at 50, affects shop efficiency
- **stress_level**: 0-100, starts at 50, affects random event probability
- **growth_potential**: 0-100, starts at 50, affects XP multiplier
- **coins**: Accumulated currency from diaries and adventures
- **level**: Increases every 10 diaries

Each diary adjusts these by ±5 based on emotion analysis.

### CBT Adventure System

Adventures ([routes/adventure.py](routes/adventure.py)) gamify CBT concepts:
- **Monsters**: Represent cognitive distortions (灾难化, 贴标签, 过度概括, etc.)
- **Challenges**: Multiple-choice questions identifying correct vs. distorted thinking
- **Rewards**: Coins, stat boosts, collectible items

### Postcard System

Postcards ([routes/postcard.py](routes/postcard.py)) provide emotional rewards:
- 小橘 (fox mascot) "travels" to locations matching user's emotional state
- AI generates scene images via CogView
- Includes stat changes and coins earned from the "adventure"

## Common Gotchas

### SQLAlchemy JSON Type
Uses `db.JSON` with automatic TEXT fallback for SQLite. The schema auto-patch in [app.py:80-195](app.py#L80-L195) handles this.

### AI Response Parsing
All AI calls have fallback handlers. ChatGLM may return incomplete JSON - the `fallback_calculate()` function ([routes/analysis.py:56-114](routes/analysis.py#L56-L114)) provides rule-based defaults.

### Database Connection Pooling
Uses `pool_pre_ping=True` ([app.py:73](app.py#L73)) to handle stale MySQL connections on Zeabur.

### Windows Encoding
Batch files use `chcp 65001` for UTF-8. Python scripts should work cross-platform.

### Deprecated Endpoints
- `/api/analysis/<diary_id>/unified-analyze` - Returns 410 Gone. Game scores now calculated during adventure completion.
- Use `/api/analysis/<diary_id>/unified-analyze-legacy` for emergency fallback only.

## Code Style

- **Chinese comments**: Business logic and AI prompts use Chinese
- **English API**: All JSON keys and function names in English
- **Error handling**: Rollback DB session on exceptions
- **Frontend**: Vanilla JS with Bootstrap 5.3.0, no build step
