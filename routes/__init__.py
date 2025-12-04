# 路由模块初始化
# 导入路由处理器和蓝图
from . import auth, diary, upload, analysis, game, postcard

# 导出蓝图
auth_bp = auth.bp
diary_bp = diary.bp
upload_bp = upload.bp
analysis_bp = analysis.bp
game_bp = game.bp
postcard_bp = postcard.bp