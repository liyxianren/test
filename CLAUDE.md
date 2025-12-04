# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**CBT Emotion Diary Game** (CBT情绪日记游戏) - A web application combining Cognitive Behavioral Therapy (CBT) principles with gamification. Users record emotional diaries which are analyzed by AI (ChatGLM/COZE/QWEN) to generate personalized game parameters and CBT insights.

**Tech Stack**: Flask + SQLAlchemy + MySQL/SQLite, vanilla JavaScript frontend, deployed on Zeabur

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
# The app automatically runs db.create_all() on startup (see app.py:185-188)
# But you can also do it manually:
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Database migrations (Flask-Migrate)
# Note: Migrations may not work on Zeabur - use ensure_schema_updates() instead
flask db init           # First time only
flask db migrate -m "message"  # Generate migration
flask db upgrade        # Apply migration
```

### Testing
```bash
# Run test files
python test_auth.py              # Auth system tests
python test_chatglm.py           # ChatGLM integration tests
python test_integration.py       # Full integration tests
python test_deployment.py        # Deployment verification
```

## High-Level Architecture

### Application Structure

**Flask Application Factory Pattern**: The app uses a modular blueprint-based architecture. The main app ([app.py](app.py)) registers blueprints from [routes/](routes/) and initializes extensions via [extensions.py](extensions.py).

### Database Models ([models.py](models.py))

5 core models with cascade relationships:
- **User** → EmotionDiary (1:N), GameState (1:1), GameProgress (1:N)
- **EmotionDiary** → EmotionAnalysis (1:1), GameProgress (1:N)

Key design: All JSON fields use SQLAlchemy's `db.JSON` type with automatic fallback to `TEXT` for SQLite compatibility.

### Database Configuration Strategy

**Multi-environment database resolution** in [app.py:25-46](app.py#L25-L46):
1. Check `DATABASE_URL` (with postgres→postgresql conversion for Heroku/Zeabur)
2. Fall back to MySQL environment variables (`MYSQL_HOST`, `MYSQL_USER`, etc.)
3. Ultimate fallback to SQLite (`diary.db`) for local development

**Schema migration handling**: The `ensure_schema_updates()` function ([app.py:65-113](app.py#L65-L113)) automatically adds missing columns without migrations, critical for Zeabur deployments where `flask db` may not be available.

### AI Analysis Architecture

**Multi-provider strategy** with fallback chain in [routes/analysis.py](routes/analysis.py):

Primary: **ChatGLM (ZhipuAI)** with dual-prompt parallel execution:
- **Prompt 1**: User-friendly analysis (温暖的CBT分析) - [prompts/chatglm_prompts.py:7-58](prompts/chatglm_prompts.py#L7-L58)
- **Prompt 2**: Game data extraction (严格的JSON数值) - [prompts/chatglm_prompts.py:61-132](prompts/chatglm_prompts.py#L61-L132)

Fallback chain: ChatGLM → COZE API → QWEN API → Local rule-based analysis

**Key insight**: The dual-call pattern (`analyze_with_chatglm_dual` at [routes/analysis.py:383-449](routes/analysis.py#L383-L449)) uses `ThreadPoolExecutor` to parallelize the two API calls, reducing latency by ~50%.

### Emotion → Game Value Mapping

**CBT Theory Integration**: Emotions drive game mechanics via calculated modifiers:
- Negative emotions (sad, anxious, angry) → Higher game difficulty, lower income multiplier
- Positive emotions (happy, calm) → Lower difficulty, bonus multipliers
- See [routes/analysis.py:982-1023](routes/analysis.py#L982-L1023) for the valence mapping algorithm

**Game projection fields** (`game_values` object):
- `mental_health_score`: 0-100 (affects character stats)
- `stress_level`: 0-100 (affects energy regeneration)
- `income_multiplier`: 0.5-2.0 (economic impact)
- `daily_income_base`: Base currency generation

### Route Structure

Blueprints registered in [app.py:118-120](app.py#L118-L120):
- `/api/auth/*` - User authentication ([routes/auth.py](routes/auth.py))
- `/api/diary/*` - CRUD operations ([routes/diary.py](routes/diary.py))
- `/api/analysis/*` - AI emotion analysis ([routes/analysis.py](routes/analysis.py))
- `/api/upload/*` - File uploads ([routes/upload.py](routes/upload.py))

### Frontend JavaScript Architecture

**Main diary creation flow** ([static/js/diary_new.js](static/js/diary_new.js)):
1. Step-by-step guided form (emotions → trigger event → intensity → content → images)
2. On submission: POST `/api/diary/` → POST `/api/diary/{id}/ai-analyze`
3. Display dual analysis: user-friendly message + game values

**State management**: Uses plain JavaScript with a global `state` object tracking:
- `selectedEmotions`: Array of emotion tags
- `triggerEvent`: Event that triggered the emotion
- `intensity`: Emotion intensity (1-10 scale)
- `diaryContent`: Main diary text
- `uploadedImages`: Array of image URLs

### Complete Diary Workflow

**Creation flow**:
1. User fills out 4-step form in [diary_new.html](templates/diary_new.html)
2. Frontend POSTs to `/api/diary/` with: `{content, emotion_tags, emotion_score, trigger_event, images}`
3. Backend creates `EmotionDiary` record with `analysis_status='pending'`
4. Frontend immediately calls `/api/diary/{id}/ai-analyze`
5. Backend runs `analyze_with_chatglm_dual()` which:
   - Parallel calls ChatGLM twice (user-friendly + game data)
   - Fallback to COZE → QWEN → local rules if ChatGLM fails
   - Creates `EmotionAnalysis` record
   - Updates diary `analysis_status='completed'`
6. Frontend displays both analysis results in AI panel

### Environment Variables

**Critical for AI features** (see [.env.example](.env.example)):
- `ZHIPU_API_KEY` + `ZHIPU_MODEL_NAME` - Primary AI (ChatGLM, default: `glm-4-flash`)
- `COZE_API_KEY` + `COZE_BOT_ID` - Fallback #1
- `QWEN_API_KEY` + `QWEN_MODEL_NAME` - Fallback #2 (default: `qwen-turbo`)
- `DATABASE_URL` or `MYSQL_*` variables - Database connection

**JWT configuration**:
- `JWT_SECRET_KEY` - Token signing (must be strong in production)
- `JWT_ACCESS_TOKEN_EXPIRES_HOURS` - Default 24h

**File uploads**:
- `UPLOAD_FOLDER` - Directory for uploaded images (default: `uploads`)
- `MAX_CONTENT_LENGTH` - Max file size in bytes (default: 16MB)
- `ALLOWED_EXTENSIONS` - Comma-separated file extensions

### Deployment-Specific Patterns

**Zeabur compatibility**:
- Automatic MySQL environment variable injection handling
- Schema auto-patching to avoid migration failures
- URL password encoding via `urllib.parse.quote_plus()` ([app.py:41](app.py#L41))

**Windows batch scripts** for local development:
- [deploy.bat](deploy.bat) - Full setup automation
- [start.bat](start.bat) - Development server
- [start_prod.bat](start_prod.bat) - Production mode with Gunicorn

## Key Implementation Details

### Authentication Flow
- JWT tokens issued on login ([routes/auth.py](routes/auth.py))
- Tokens stored in `localStorage` by frontend
- All API routes use `@jwt_required()` decorator except public endpoints

### Password Reset Mechanism
- Token-based reset ([models.py:18-19](models.py#L18-L19))
- `reset_token` + `reset_token_expires` fields on User model
- No email integration yet - tokens returned in API response for testing

### Image Uploads
- Stored in `uploads/` directory
- URLs saved as JSON array in `EmotionDiary.images` field
- File validation via [routes/upload.py](routes/upload.py)

### CBT Four-Step Method (Planned)

The codebase includes references to CBT四步法 (4-step method):
1. Identify negative thoughts → `cognitive_distortions`
2. Gather evidence → `evidence_collected` (GameProgress model)
3. Generate alternatives → `alternative_thoughts`
4. Evaluate emotional change → Emotion tracking over time

Currently implemented in AI analysis prompts but not yet fully gamified in frontend.

## Common Gotchas

### SQLAlchemy JSON Type Issues
The `models.py` uses `db.JSON` which works on MySQL but may fail silently on SQLite. The schema auto-patch function ([app.py:65-113](app.py#L65-L113)) automatically converts JSON to TEXT for SQLite compatibility.

### ChatGLM Response Parsing
The AI may return incomplete JSON if `max_tokens` is too low. Current settings: 1500 for user message, 4000 for game data ([routes/analysis.py:410-421](routes/analysis.py#L410-L421)). Monitor the `finish_reason` in API responses. If you see truncated responses, the dual-call pattern will fall back to local rule-based analysis.

### Windows Path Issues
Use `os.path.join()` for all file paths. The codebase has Windows-specific batch files but Python code should remain cross-platform.

### Database Connection Pooling
The app uses `pool_pre_ping=True` ([app.py:58](app.py#L58)) to handle stale MySQL connections on Zeabur. This adds a small overhead but prevents "MySQL server has gone away" errors.

### Character Encoding on Windows
The batch files use `chcp 65001` to set UTF-8 encoding for proper display of Chinese characters in the Windows console.

## Code Style Conventions

- **Chinese comments**: Business logic and AI prompts use Chinese for clarity
- **English API**: All JSON keys and function names in English
- **Error handling**: Always rollback DB session on exceptions
- **Frontend**: No build step, vanilla JS with Bootstrap 5.3.0

## Troubleshooting & Debugging

### Common Issues

**Database connection fails on startup**:
- Check `.env` file exists and `DATABASE_URL` is set
- For MySQL: Verify `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`
- Test connection: `python -c "from app import app, db; app.app_context().push(); db.engine.connect()"`

**ChatGLM API errors**:
- Verify `ZHIPU_API_KEY` is valid
- Check model name matches available models (use `glm-4-flash` or `glm-4.6`)
- Monitor console output for `[调试]` messages showing API calls
- Check `finish_reason` in responses - if `length`, increase `max_tokens`

**JSON parsing errors in AI analysis**:
- The system has automatic fallbacks - check if COZE/QWEN keys are set
- Local rule-based analysis runs if all AI providers fail
- Check `routes/analysis.py` logs for fallback chain execution

**Image upload issues**:
- Ensure `uploads/` directory exists and is writable
- Check `MAX_CONTENT_LENGTH` setting (default 16MB)
- Verify `ALLOWED_EXTENSIONS` includes the file type

**Windows encoding issues**:
- Run `chcp 65001` before starting the app
- Batch files automatically set this, but manual Python commands may need it

## Testing Strategy

The project uses manual testing with test files rather than pytest:
- Test files include full Flask app context setup
- Use `with app.app_context():` for DB operations
- API tests use direct endpoint calls, not mocking

## Development Stages & Status

Per [README.md](README.md):

**Stage 1: Authentication & Database** ✅ **COMPLETED**
- User registration, login, password reset
- JWT-based authentication
- MySQL/SQLite dual-database support
- Zeabur deployment compatibility

**Stage 2: Diary Features** 🚧 **IN PROGRESS**
- Basic diary CRUD: ✅ Complete
- AI analysis integration: ✅ Complete (ChatGLM dual-prompt)
- Step-by-step diary creation UI: ✅ Complete
- Rich text editor: ⏳ Pending
- Search & filtering: ⏳ Pending

**Stage 3: Game Implementation** ⏳ **PLANNED**
- Canvas-based game UI
- CBT four-step method gamification
- Character stats & progression

**Stage 4: AI Optimization** ⏳ **PLANNED**
- Analysis accuracy improvements
- Response time optimization
- Caching layer

**Stage 5: Emotion-Game Loop** ⏳ **PLANNED**
- Real-time game parameter updates
- Achievement system
- Trend analysis dashboard

When implementing new features, maintain the dual-analysis pattern and ensure all game values are calculated consistently with the existing valence mapping algorithm.
