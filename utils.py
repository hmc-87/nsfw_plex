# utils.py
import zipfile
import py7zr
import rarfile
import gzip
import io
import os
import logging
import tempfile
from pathlib import Path
from config import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS

logger = logging.getLogger(__name__)

class ArchiveHandler:
    """统一的压缩文件处理类"""
    
    def __init__(self, filepath):
        """
        初始化压缩文件处理器
        Args:
            filepath: 压缩文件路径
        """
        self.filepath = filepath
        self.archive = None
        self.type = self._determine_type()
        
    def _determine_type(self):
        """
        确定压缩包类型
        Returns:
            str: 压缩文件类型 ('zip', 'rar', '7z', 'gz' 或 None)
        """
        try:
            if zipfile.is_zipfile(self.filepath):
                return 'zip'
            elif rarfile.is_rarfile(self.filepath):
                return 'rar'
            elif py7zr.is_7zfile(self.filepath):
                return '7z'
            elif self._is_valid_gzip(self.filepath):
                return 'gz'
            return None
        except Exception as e:
            logger.error(f"文件类型检测失败: {str(e)}")
            return None

    def _is_valid_gzip(self, filepath):
        """
        验证是否为有效的gzip文件
        Args:
            filepath: 文件路径
        Returns:
            bool: 是否为有效的gzip文件
        """
        try:
            with gzip.open(filepath, 'rb') as f:
                f.read(1)
            return True
        except Exception:
            return False

    def __enter__(self):
        """
        打开压缩文件
        Returns:
            ArchiveHandler: 自身实例
        Raises:
            Exception: 打开文件失败时抛出异常
        """
        try:
            if self.type == 'zip':
                self.archive = zipfile.ZipFile(self.filepath)
                if self.archive.testzip() is not None:
                    raise zipfile.BadZipFile("ZIP文件损坏")
                    
            elif self.type == 'rar':
                self.archive = rarfile.RarFile(self.filepath)
                if self.archive.needs_password():
                    raise Exception("RAR文件有密码保护")
                    
            elif self.type == '7z':
                self.archive = py7zr.SevenZipFile(self.filepath)
                if self.archive.needs_password():
                    raise Exception("7z文件有密码保护")
                    
            elif self.type == 'gz':
                self.archive = gzip.GzipFile(self.filepath)
            else:
                raise Exception("不支持的压缩格式")
            
            return self
            
        except (zipfile.BadZipFile, rarfile.BadRarFile) as e:
            raise Exception(f"无效的压缩文件: {str(e)}")
        except Exception as e:
            raise Exception(f"打开压缩文件失败: {str(e)}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """关闭压缩文件"""
        if self.archive:
            self.archive.close()

    def list_files(self):
        """
        获取压缩包中的文件列表
        Returns:
            list: 文件名列表
        """
        try:
            if self.type == 'zip':
                # 过滤掉目录项
                return [f for f in self.archive.namelist() if not f.endswith('/')]
                
            elif self.type == 'rar':
                # 过滤掉目录项
                return [f.filename for f in self.archive.infolist() if not f.is_dir()]
                
            elif self.type == '7z':
                # 获取所有文件信息并过滤目录
                file_list = []
                for filename, info in self.archive.files.items():
                    if not info.is_directory:
                        file_list.append(filename)
                return file_list
                
            elif self.type == 'gz':
                # gz文件只包含一个文件，使用原始文件名（去掉.gz后缀）
                base_name = os.path.basename(self.filepath)
                if base_name.endswith('.gz'):
                    return [base_name[:-3]]
                return ['content']
                
            return []
            
        except Exception as e:
            logger.error(f"获取文件列表失败: {str(e)}")
            return []

    def get_file_info(self, filename):
        """
        获取文件信息
        Args:
            filename: 文件名
        Returns:
            int: 文件大小（字节）
        """
        try:
            if self.type == 'zip':
                return self.archive.getinfo(filename).file_size
                
            elif self.type == 'rar':
                return self.archive.getinfo(filename).file_size
                
            elif self.type == '7z':
                return self.archive.files[filename].uncompressed
                
            elif self.type == 'gz':
                # 对于gz文件，返回解压后的大小
                return self.archive.size
                
            return 0
            
        except Exception as e:
            logger.error(f"获取文件 {filename} 信息失败: {str(e)}")
            return 0

    def extract_file(self, filename):
        """
        提取单个文件
        Args:
            filename: 要提取的文件名
        Returns:
            bytes: 文件内容的字节数据
        Raises:
            Exception: 提取失败时抛出异常
        """
        try:
            if self.type == 'zip':
                return self.archive.read(filename)
                
            elif self.type == 'rar':
                return self.archive.read(filename)
                
            elif self.type == '7z':
                # 专门处理7z文件的提取
                file_data = None
                target_file = self.archive.files[filename]
                
                # 如果是单个文件，直接提取
                if len(self.archive.files) == 1:
                    file_data = next(iter(self.archive.read([filename]).values())).read()
                else:
                    # 如果是多个文件，使用临时目录提取单个文件
                    with tempfile.TemporaryDirectory() as temp_dir:
                        self.archive.extract(temp_dir, [filename])
                        file_path = os.path.join(temp_dir, filename)
                        with open(file_path, 'rb') as f:
                            file_data = f.read()
                            
                if file_data is None:
                    raise Exception(f"无法提取文件: {filename}")
                return file_data
                
            elif self.type == 'gz':
                # 对于gz文件，读取全部内容
                return self.archive.read()
                
            raise Exception("不支持的压缩格式")
            
        except KeyError:
            raise Exception(f"文件不存在: {filename}")
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
    """
    按优先级对文件进行排序
    Args:
        handler: ArchiveHandler实例
        files: 文件名列表
    Returns:
        list: 排序后的文件列表
    """
    def get_priority_and_size(filename):
        ext = get_file_extension(filename)
        size = handler.get_file_info(filename)
        
        # 设置优先级：图片 > PDF > 视频
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