# utils.py 
import requests
import urllib.parse
from pathlib import Path
import zipfile
import py7zr
import rarfile
import gzip
import io
import os
import uuid
from PIL import Image
import logging
from config import HTTP_HEADERS, DOWNLOAD_TIMEOUT, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
logger = logging.getLogger(__name__)

class ArchiveHandler:
    def __init__(self, filepath):
        self.filepath = filepath
        self.archive = None
        self.type = self._determine_type()
        
    def _determine_type(self):
        """确定压缩包类型"""
        if zipfile.is_zipfile(self.filepath):
            return 'zip'
        elif rarfile.is_rarfile(self.filepath):
            return 'rar'
        elif py7zr.is_7zfile(self.filepath):
            return '7z'
        elif self.filepath.endswith('.gz'):
            return 'gz'
        return None

    def __enter__(self):
        """打开压缩包"""
        try:
            if self.type == 'zip':
                self.archive = zipfile.ZipFile(self.filepath)
            elif self.type == 'rar':
                self.archive = rarfile.RarFile(self.filepath)
                if self.archive.needs_password():
                    raise Exception("RAR文件有密码保护")
            elif self.type == '7z':
                self.archive = py7zr.SevenZipFile(self.filepath)
                if self.archive.needs_password():
                    raise Exception("7z文件有密码保护")
            elif self.type == 'gz':
                self.archive = gzip.open(self.filepath)
            else:
                raise Exception("不支持的压缩格式")
            return self
        except (zipfile.BadZipFile, rarfile.BadRarFile) as e:
            raise Exception(f"无效的压缩文件: {str(e)}")
        except Exception as e:
            raise Exception(f"打开压缩文件失败: {str(e)}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """关闭压缩包"""
        if self.archive:
            self.archive.close()

    def get_file_info(self, filename):
        """获取文件信息，返回文件大小（字节）"""
        try:
            if self.type == 'zip':
                info = self.archive.getinfo(filename)
                return info.file_size
            elif self.type == 'rar':
                info = self.archive.getinfo(filename)
                return info.file_size
            elif self.type == '7z':
                # 7z不直接提供文件大小，返回压缩后的大小
                file_info = self.archive.list()[self.archive.getnames().index(filename)]
                return file_info.uncompressed
            elif self.type == 'gz':
                # gz文件只包含一个文件，无法获取确切大小
                return 0
        except Exception as e:
            logger.error(f"获取文件{filename}信息时出错: {str(e)}")
            return 0
        return 0

    def list_files(self):
        """获取文件列表"""
        if self.type == 'zip':
            return self.archive.namelist()
        elif self.type == 'rar':
            return self.archive.namelist()
        elif self.type == '7z':
            return list(self.archive.getnames())
        elif self.type == 'gz':
            # gz文件只包含一个文件
            return ['content.bin']
        return []

    def extract_file(self, filename):
        """提取单个文件内容"""
        try:
            if self.type == 'zip':
                return self.archive.read(filename)
            elif self.type == 'rar':
                return self.archive.read(filename)
            elif self.type == '7z':
                return next(iter(self.archive.read([filename]).values())).read()
            elif self.type == 'gz':
                return self.archive.read()
        except Exception as e:
            raise Exception(f"提取文件失败: {str(e)}")

def get_file_extension(filename):
    """获取文件扩展名（小写）"""
    return Path(filename).suffix.lower()

def can_process_file(filename):
    """检查文件是否可以处理"""
    ext = get_file_extension(filename)
    return ext in IMAGE_EXTENSIONS or ext == '.pdf' or ext in VIDEO_EXTENSIONS

def sort_files_by_priority(handler, files):
    """按优先级对文件进行排序（同类型文件按大小排序）"""
    def get_priority_and_size(filename):
        ext = get_file_extension(filename)
        size = handler.get_file_info(filename)
        
        # 基础优先级：图片 > PDF > 视频
        if ext in IMAGE_EXTENSIONS:
            priority = 0
        elif ext == '.pdf':
            priority = 1
        elif ext in VIDEO_EXTENSIONS:
            priority = 2
        else:
            priority = 3
            
        return (priority, size)
    
    return sorted(files, key=get_priority_and_size)