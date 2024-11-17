# config.py
import os
import rarfile
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 配置 rarfile
rarfile.UNRAR_TOOL = "unrar"
rarfile.PATH_SEP = '/'

# 使用新的环境变量名称 HF_HOME 替代 TRANSFORMERS_CACHE
os.environ['HF_HOME'] = '/root/.cache/huggingface'

# 文件扩展名配置
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.ts', '.flv', '.webm'}
ARCHIVE_EXTENSIONS = {'.7z', '.rar', '.zip', '.gz'}

# HTTP 配置
HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 文件大小限制 (20480MB)
MAX_FILE_SIZE = 20 * 1024 * 1024 * 1024

# 超时设置
DOWNLOAD_TIMEOUT = 30

# NSFW 配置
NSFW_THRESHOLD = 0.8  # 统一的 NSFW 检测阈值

# FFmpeg 配置
FFMPEG_MAX_FRAMES = 20          # 最大提取帧数
MAX_INTERVAL_SECONDS = 30       # 最大采样间隔(秒)
FFMPEG_TIMEOUT = 300           # FFmpeg 操作超时时间(秒)