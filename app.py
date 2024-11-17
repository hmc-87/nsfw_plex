# app.py
from flask import Flask, request, jsonify, send_file, Response
import tempfile
import os
import shutil
from pathlib import Path
from PIL import Image
import io
import time
import logging
import magic
from config import MAX_FILE_SIZE, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from utils import ArchiveHandler, can_process_file, sort_files_by_priority
from processors import process_image, process_pdf_file, process_video_file, process_archive

# 配置日志
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Load index.html content
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(CURRENT_DIR, 'index.html'), 'r', encoding='utf-8') as f:
    INDEX_HTML = f.read()

@app.route('/')
def index():
    """Serve the index.html file"""
    return Response(INDEX_HTML, mimetype='text/html')

def detect_file_type(file_stream):
    """检测文件类型
    Returns: (mime_type, file_extension)
    """
    # 读取文件头部数据用于检测
    header = file_stream.read(2048)
    file_stream.seek(0)  # 重置文件指针
    
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
        'application/zip': '.zip',
        'application/x-7z-compressed': '.7z',
        'application/gzip': '.gz'
    }
    
    return mime_type, mime_to_ext.get(mime_type)

def process_file_by_type(file_stream, detected_type, original_filename):
    """根据文件类型选择处理方法"""
    mime_type, ext = detected_type
    
    # 如果有原始文件扩展名，优先使用
    if original_filename and '.' in original_filename:
        original_ext = os.path.splitext(original_filename)[1].lower()
        if original_ext in IMAGE_EXTENSIONS or original_ext == '.pdf' or original_ext in VIDEO_EXTENSIONS:
            ext = original_ext
    
    if not ext:
        return {
            'status': 'error',
            'message': 'Unsupported file type'
        }, 400
    
    try:
        if ext in IMAGE_EXTENSIONS:
            image = Image.open(file_stream)
            result = process_image(image)
            return {
                'status': 'success',
                'filename': original_filename,
                'result': result
            }
            
        elif ext == '.pdf':
            pdf_stream = file_stream.read()
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
            # 创建临时文件并正确写入内容
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            try:
                # 读取文件内容并写入临时文件
                file_content = file_stream.read()
                with open(temp_file.name, 'wb') as f:
                    f.write(file_content)
                
                result = process_video_file(temp_file.name)
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
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
                    
        elif ext in {'.zip', '.rar', '.7z', '.gz'}:
            return process_archive(file_stream, original_filename)
            
        else:
            return {
                'status': 'error',
                'message': 'Unsupported file type'
            }, 400
            
    except Exception as e:
        logger.error(f"处理文件时出错: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }, 500

@app.route('/check', methods=['POST'])
def check_file():
    """统一的文件检查入口点"""
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

        logger.info(f"接收到文件: {file.filename}")
        
        # 检测文件类型
        detected_type = detect_file_type(file.stream)
        logger.info(f"检测到文件类型: {detected_type}")
        
        # 处理文件
        result = process_file_by_type(file.stream, detected_type, file.filename)
        return jsonify(result) if isinstance(result, dict) else jsonify(result[0]), result[1] if isinstance(result, tuple) else 200

    except Exception as e:
        logger.error(f"处理过程发生错误: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3333)