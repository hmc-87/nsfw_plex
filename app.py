# app.py
from flask import Flask, request, jsonify, send_file, Response
import tempfile
import os
import shutil
import logging
import magic
from pathlib import Path
from werkzeug.utils import secure_filename
from config import MAX_FILE_SIZE, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from utils import ArchiveHandler, can_process_file, sort_files_by_priority
from processors import process_image, process_pdf_file, process_video_file, process_archive

# 配置日志
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 文件上传配置
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE  # 从config导入的最大文件大小
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()  # 使用系统临时目录
app.request_class.max_form_memory_size = 128 * 1024 * 1024  # 强制所有上传写入磁盘

# Load index.html content
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(CURRENT_DIR, 'index.html'), 'r', encoding='utf-8') as f:
    INDEX_HTML = f.read()

class TempFileHandler:
    """临时文件管理器"""
    def __init__(self):
        self.temp_files = []
        
    def create_temp_file(self, suffix=None):
        """创建临时文件"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        self.temp_files.append(temp_file.name)
        return temp_file
        
    def cleanup(self):
        """清理所有临时文件"""
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logger.error(f"清理临时文件失败 {file_path}: {str(e)}")
        self.temp_files.clear()

def detect_file_type(file_path):
    """检测文件类型，使用文件的前2048字节"""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(2048)
        
        mime = magic.Magic(mime=True)
        mime_type = mime.from_buffer(header)
        
        # 基于 MIME 类型映射文件扩展名
        mime_to_ext = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'image/bmp': '.bmp',
            'application/pdf': '.pdf',
            'video/mp4': '.mp4',
            'video/x-msvideo': '.avi',
            'video/x-matroska': '.mkv',
            'video/quicktime': '.mov',
            'video/x-ms-wmv': '.wmv',
            'video/webm': '.webm',
            'application/x-rar-compressed': '.rar',
            'application/x-rar': '.rar',
            'application/vnd.rar': '.rar',
            'application/zip': '.zip',
            'application/x-7z-compressed': '.7z',
            'application/gzip': '.gz'
        }
        
        # 对于RAR文件的特殊处理
        if mime_type not in mime_to_ext:
            with open(file_path, 'rb') as f:
                if f.read(7).startswith(b'Rar!\x1a\x07'):
                    return 'application/x-rar', '.rar'
        
        return mime_type, mime_to_ext.get(mime_type)
        
    except Exception as e:
        logger.error(f"文件类型检测失败: {str(e)}")
        raise

def process_file_by_type(file_path, detected_type, original_filename, temp_handler):
    """根据文件类型选择处理方法"""
    mime_type, ext = detected_type
    
    # 如果有原始文件扩展名，优先使用
    if original_filename and '.' in original_filename:
        original_ext = os.path.splitext(original_filename)[1].lower()
        if original_ext in IMAGE_EXTENSIONS or original_ext == '.pdf' or \
           original_ext in VIDEO_EXTENSIONS or original_ext in {'.rar', '.zip', '.7z', '.gz'}:
            ext = original_ext
    
    if not ext:
        logger.error(f"不支持的文件类型: {mime_type}")
        return {
            'status': 'error',
            'message': f'Unsupported file type: {mime_type}'
        }, 400
    
    try:
        if ext in IMAGE_EXTENSIONS:
            with open(file_path, 'rb') as f:
                from PIL import Image
                image = Image.open(f)
                result = process_image(image)
                return {
                    'status': 'success',
                    'filename': original_filename,
                    'result': result
                }
                
        elif ext == '.pdf':
            with open(file_path, 'rb') as f:
                pdf_stream = f.read()
                result = process_pdf_file(pdf_stream)
                if result:
                    return {
                        'status': 'success',
                        'filename': original_filename,
                        'result': result
                    }
                return {
                    'status': 'error',
                    'message': 'No processable content found in PDF'
                }, 400
                
        elif ext in VIDEO_EXTENSIONS:
            result = process_video_file(file_path)
            if result:
                return {
                    'status': 'success',
                    'filename': original_filename,
                    'result': result
                }
            return {
                'status': 'error',
                'message': 'No processable content found in video'
            }, 400
                
        elif ext in {'.zip', '.rar', '.7z', '.gz'}:
            return process_archive(file_path, original_filename)
            
        else:
            logger.error(f"不支持的文件扩展名: {ext}")
            return {
                'status': 'error',
                'message': f'Unsupported file extension: {ext}'
            }, 400
            
    except Exception as e:
        logger.error(f"处理文件时出错: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }, 500

@app.route('/')
def index():
    """Serve the index.html file"""
    return Response(INDEX_HTML, mimetype='text/html')

@app.route('/check', methods=['POST'])
def check_file():
    """统一的文件检查入口点"""
    temp_handler = TempFileHandler()
    try:
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No file found'
            }), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No file selected'
            }), 400

        # 获取安全的文件名
        filename = secure_filename(file.filename)
        logger.info(f"接收到文件: {filename}")
        
        # 创建临时文件
        temp_file = temp_handler.create_temp_file()
        file.save(temp_file.name)
        
        # 检查文件大小
        file_size = os.path.getsize(temp_file.name)
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'status': 'error',
                'message': 'File too large'
            }), 400
        
        # 检测文件类型
        detected_type = detect_file_type(temp_file.name)
        logger.info(f"检测到文件类型: {detected_type}")
        
        # 处理文件
        result = process_file_by_type(temp_file.name, detected_type, filename, temp_handler)
        return jsonify(result) if isinstance(result, dict) else jsonify(result[0]), result[1] if isinstance(result, tuple) else 200

    except Exception as e:
        logger.error(f"处理过程发生错误: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
        
    finally:
        # 清理所有临时文件
        temp_handler.cleanup()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3333)