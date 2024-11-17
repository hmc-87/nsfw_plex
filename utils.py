# utils.py
import zipfile
import rarfile
import gzip
import io
import os
import logging
import tempfile
import subprocess
import shutil
from pathlib import Path
from config import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS

logger = logging.getLogger(__name__)

class ArchiveHandler:
    def __init__(self, filepath):
        """
        初始化归档文件处理器
        Args:
            filepath: 归档文件路径
        """
        self.filepath = filepath
        self.archive = None
        self.type = self._determine_type()
        
    def _determine_type(self):
        """
        确定归档文件类型
        Returns:
            str: 文件类型 ('zip', 'rar', '7z', 'gz' 或 None)
        """
        try:
            if zipfile.is_zipfile(self.filepath):
                return 'zip'
            elif rarfile.is_rarfile(self.filepath):
                return 'rar'
            elif self._is_7z_file(self.filepath):
                return '7z'
            elif self._is_valid_gzip(self.filepath):
                return 'gz'
            return None
        except Exception as e:
            logger.error(f"文件类型检测失败: {str(e)}")
            return None

    def _is_7z_file(self, filepath):
        """
        检查是否为7z文件
        Args:
            filepath: 文件路径
        Returns:
            bool: 是否为7z文件
        """
        try:
            result = subprocess.run(
                ['7z', 'l', filepath], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                encoding='utf-8'
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"7z文件检测失败: {str(e)}")
            return False

    def _is_valid_gzip(self, filepath):
        """
        检查是否为有效的gzip文件
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
        上下文管理器入口
        Returns:
            ArchiveHandler: 处理器实例
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
                # 7z文件不需要持续打开
                pass
                    
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
        """上下文管理器退出"""
        if self.archive:
            self.archive.close()

    def list_files(self):
        """
        列出归档中的所有文件
        Returns:
            list: 文件名列表
        """
        try:
            if self.type == 'zip':
                return [f for f in self.archive.namelist() if not f.endswith('/')]
                
            elif self.type == 'rar':
                return [f.filename for f in self.archive.infolist() if not f.is_dir()]
                
            elif self.type == '7z':
                result = subprocess.run(
                    ['7z', 'l', '-slt', self.filepath], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    encoding='utf-8'
                )
                
                if result.returncode != 0:
                    raise Exception("无法列出7z文件内容")
                
                files = []
                current_file = None
                is_directory = False
                
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line.startswith('Path = '):
                        current_file = line[7:]  # 去掉 "Path = "
                    elif line.startswith('Attributes = D'):
                        is_directory = True
                    elif line == '':  # 空行表示一个文件信息块的结束
                        if current_file and not is_directory:
                            files.append(current_file)
                        current_file = None
                        is_directory = False
                
                logger.info(f"找到以下文件: {files}")
                return files
                
            elif self.type == 'gz':
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
                result = subprocess.run(
                    ['7z', 'l', '-slt', self.filepath, filename], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    encoding='utf-8'
                )
                
                if result.returncode != 0:
                    return 0
                
                size = 0
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line.startswith('Size = '):
                        try:
                            size = int(line[7:])  # 去掉 "Size = "
                            break
                        except ValueError:
                            continue
                
                return size
                
            elif self.type == 'gz':
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
            bytes: 文件内容
        """
        try:
            if self.type == 'zip':
                return self.archive.read(filename)
                
            elif self.type == 'rar':
                return self.archive.read(filename)
                
            elif self.type == '7z':
                # 创建临时文件以存储提取的文件
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_path = temp_file.name
                
                try:
                    # 提取文件到临时文件
                    cmd = ['7z', 'e', self.filepath, filename, f'-so']
                    result = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=True
                    )
                    
                    # 返回文件内容
                    return result.stdout
                    
                except subprocess.CalledProcessError as e:
                    logger.error(f"7z命令执行失败: {e.stderr.decode('utf-8', errors='ignore')}")
                    raise Exception("文件提取失败")
                finally:
                    # 清理临时文件
                    try:
                        os.unlink(temp_path)
                    except Exception as e:
                        logger.error(f"清理临时文件失败: {str(e)}")
                
            elif self.type == 'gz':
                return self.archive.read()
                
            raise Exception("不支持的压缩格式")
            
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
    """按优先级对文件进行排序"""
    def get_priority_and_size(filename):
        ext = get_file_extension(filename)
        size = handler.get_file_info(filename)
        
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