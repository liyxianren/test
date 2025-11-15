"""
图片上传路由
"""
from flask import Blueprint, request, jsonify, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime

bp = Blueprint('upload', __name__)

# 配置
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_size(file):
    """获取文件大小"""
    file.seek(0, 2)  # 移动到文件末尾
    size = file.tell()
    file.seek(0)  # 重置到开始
    return size

@bp.route('/upload/image', methods=['POST'])
@jwt_required()
def upload_image():
    """
    上传图片

    请求：
    - multipart/form-data
    - file: 图片文件

    响应：
    - image_url: 图片URL
    """
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({'error': '没有文件'}), 400

        file = request.files['file']

        # 检查文件名
        if file.filename == '':
            return jsonify({'error': '文件名为空'}), 400

        # 检查文件类型
        if not allowed_file(file.filename):
            return jsonify({'error': f'不支持的文件类型，仅支持: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

        # 检查文件大小
        file_size = get_file_size(file)
        if file_size > MAX_FILE_SIZE:
            return jsonify({'error': f'文件过大，最大支持 {MAX_FILE_SIZE // (1024 * 1024)}MB'}), 400

        # 生成安全的文件名
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower()

        # 使用UUID和时间戳生成唯一文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        new_filename = f"{timestamp}_{unique_id}.{file_ext}"

        # 确保上传目录存在
        upload_path = os.path.join(os.getcwd(), UPLOAD_FOLDER)
        os.makedirs(upload_path, exist_ok=True)

        # 保存文件
        file_path = os.path.join(upload_path, new_filename)
        file.save(file_path)

        # 生成URL
        image_url = url_for('static', filename=f'uploads/{new_filename}', _external=False)

        return jsonify({
            'message': '上传成功',
            'image_url': image_url,
            'filename': new_filename,
            'size': file_size
        }), 200

    except Exception as e:
        return jsonify({'error': f'上传失败: {str(e)}'}), 500

@bp.route('/upload/delete', methods=['POST'])
@jwt_required()
def delete_image():
    """
    删除图片

    请求：
    - filename: 文件名

    响应：
    - message: 删除结果
    """
    try:
        data = request.get_json()
        filename = data.get('filename')

        if not filename:
            return jsonify({'error': '文件名不能为空'}), 400

        # 安全检查：确保文件名不包含路径遍历
        filename = secure_filename(filename)

        # 构建完整路径
        file_path = os.path.join(os.getcwd(), UPLOAD_FOLDER, filename)

        # 检查文件是否存在
        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404

        # 删除文件
        os.remove(file_path)

        return jsonify({'message': '删除成功'}), 200

    except Exception as e:
        return jsonify({'error': f'删除失败: {str(e)}'}), 500
