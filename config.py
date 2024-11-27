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

# MIME类型到文件扩展名的映射
MIME_TO_EXT = {
    # 图片格式
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif',
    'image/webp': '.webp',
    'image/bmp': '.bmp',
    'image/tiff': '.tiff',
    'image/x-tiff': '.tiff',
    'image/x-tga': '.tga',
    'image/x-portable-pixmap': '.ppm',
    'image/x-portable-graymap': '.pgm',
    'image/x-portable-bitmap': '.pbm',
    'image/x-portable-anymap': '.pnm',
    'image/svg+xml': '.svg',
    'image/x-pcx': '.pcx',
    'image/vnd.adobe.photoshop': '.psd',
    'image/vnd.microsoft.icon': '.ico',
    'image/heif': '.heif',
    'image/heic': '.heic',
    'image/avif': '.avif',
    'image/jxl': '.jxl',
    
    # PDF格式
    'application/pdf': '.pdf',
    
    # 视频和容器格式
    'video/mp4': '.mp4',
    'video/x-msvideo': '.avi',
    'video/x-matroska': '.mkv',
    'video/quicktime': '.mov',
    'video/x-ms-wmv': '.wmv',
    'video/webm': '.webm',
    'video/MP2T': '.ts',    
    'video/x-flv': '.flv',
    'video/3gpp': '.3gp',
    'video/3gpp2': '.3g2',
    'video/x-m4v': '.m4v',
    'video/mxf': '.mxf',
    'video/x-ogm': '.ogm',
    'video/vnd.rn-realvideo': '.rv',
    'video/dv': '.dv',
    'video/x-ms-asf': '.asf',
    'video/x-f4v': '.f4v',
    'video/vnd.dlna.mpeg-tts': '.m2ts',
    'video/x-raw': '.yuv',
    'video/mpeg': '.mpg',
    'video/x-mpeg': '.mpeg',
    'video/divx': '.divx',
    'video/x-vob': '.vob',
    'video/x-m2v': '.m2v',
    
    # 压缩格式
    'application/x-rar-compressed': '.rar',
    'application/x-rar': '.rar',
    'application/vnd.rar': '.rar',
    'application/zip': '.zip',
    'application/x-7z-compressed': '.7z',
    'application/gzip': '.gz',
    'application/x-tar': '.tar',
    'application/x-bzip2': '.bz2',
    'application/x-xz': '.xz',
    'application/x-lzma': '.lzma',
    'application/x-zstd': '.zst',
    'application/vnd.ms-cab-compressed': '.cab',
    
    # 额外的容器格式
    'application/vnd.apple.mpegurl': '.m3u8',
    'application/x-mpegURL': '.m3u8',
    'application/dash+xml': '.mpd',
    'application/x-shockwave-flash': '.swf'
}

# 文件扩展名配置
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tga', 
                   '.ppm', '.pgm', '.pbm', '.pnm', '.svg', '.pcx', '.psd', '.ico',
                   '.heif', '.heic', '.avif', '.jxl'}

VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.webm', '.ts', '.flv',
                   '.3gp', '.3g2', '.m4v', '.mxf', '.ogm', '.rv', '.dv', '.asf',
                   '.f4v', '.m2ts', '.yuv', '.mpg', '.mpeg', '.divx', '.vob', '.m2v'}

ARCHIVE_EXTENSIONS = {'.7z', '.rar', '.zip', '.gz', '.tar', '.bz2', '.xz', 
                     '.lzma', '.zst', '.cab'}

# MIME 类型集合
IMAGE_MIME_TYPES = {mime for mime, ext in MIME_TO_EXT.items() if mime.startswith('image/')}

VIDEO_MIME_TYPES = {mime for mime, ext in MIME_TO_EXT.items() if 
    mime.startswith('video/') or 
    mime in {'application/vnd.apple.mpegurl', 'application/x-mpegURL', 
             'application/dash+xml', 'application/x-shockwave-flash'}}

ARCHIVE_MIME_TYPES = {mime for mime, ext in MIME_TO_EXT.items() if 
    mime.startswith('application/') and 
    any(keyword in mime for keyword in ['zip', 'rar', '7z', 'gzip', 'tar', 
        'bzip2', 'xz', 'lzma', 'zstd', 'cab'])}

PDF_MIME_TYPES = {'application/pdf'}

# 所有支持的 MIME 类型集合
SUPPORTED_MIME_TYPES = IMAGE_MIME_TYPES | VIDEO_MIME_TYPES | ARCHIVE_MIME_TYPES | PDF_MIME_TYPES

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
FFMPEG_TIMEOUT = 1800          # FFmpeg 操作超时时间(秒)