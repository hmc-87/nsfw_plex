import zipfile
import rarfile
import gzip
import io
import os
import logging
import tempfile
import subprocess
import shutil
import uuid
from pathlib import Path
from config import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS

logger = logging.getLogger(__name__)

class ArchiveHandler:
    def __init__(self, filepath):
        self.filepath = filepath
        self.archive = None
        self.type = self._determine_type()
        self.temp_dir = None
        self._extracted_files = {}  # 存储解压文件的映射 {原始文件名: 临时文件路径}
        
    def _determine_type(self):
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
        try:
            with gzip.open(filepath, 'rb') as f:
                f.read(1)
            return True
        except Exception:
            return False

    def _generate_temp_filename(self, original_filename):
        """生成唯一的临时文件名"""
        ext = Path(original_filename).suffix
        return f"{str(uuid.uuid4())}{ext}"

    def __encode_filename(self, filename):
        """文件名编码处理"""
        if isinstance(filename, str):
            return filename
            
        try:
            decoded = filename.decode('utf-8')
            return decoded
        except UnicodeDecodeError as e:
            return filename.decode('utf-8', errors='replace')

    def _extract_rar_files(self, files_to_extract):
        """只解压需要处理的RAR文件到临时目录"""
        if not self.temp_dir:
            self.temp_dir = tempfile.mkdtemp()

        try:
            for filename in files_to_extract:
                # 使用unrar命令行工具解压特定文件
                extract_cmd = ['unrar', 'e', '-y', self.filepath, filename, self.temp_dir]
                
                result = subprocess.run(
                    extract_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding='utf-8'
                )
                
                if result.returncode != 0:
                    logger.warning(f"解压RAR文件 {filename} 失败: {result.stderr}")
                    continue

                # 获取解压后的文件路径
                original_path = os.path.join(self.temp_dir, os.path.basename(filename))
                if os.path.exists(original_path):
                    new_filename = self._generate_temp_filename(filename)
                    new_path = os.path.join(self.temp_dir, new_filename)
                    try:
                        os.link(original_path, new_path)
                    except OSError:
                        shutil.copy2(original_path, new_path)
                    self._extracted_files[filename] = new_path
                    os.unlink(original_path)

        except Exception as e:
            logger.error(f"RAR文件解压失败: {str(e)}")
            raise

    def _extract_7z_files(self, files_to_extract):
        """只解压需要处理的7z文件到临时目录"""
        if not self.temp_dir:
            self.temp_dir = tempfile.mkdtemp()

        try:
            for filename in files_to_extract:
                extract_cmd = ['7z', 'e', self.filepath, '-o' + self.temp_dir, filename, '-y']
                
                result = subprocess.run(
                    extract_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding='utf-8'
                )
                
                if result.returncode != 0:
                    logger.warning(f"解压文件 {filename} 失败: {result.stderr}")
                    continue

                original_path = os.path.join(self.temp_dir, os.path.basename(filename))
                if os.path.exists(original_path):
                    new_filename = self._generate_temp_filename(filename)
                    new_path = os.path.join(self.temp_dir, new_filename)
                    try:
                        os.link(original_path, new_path)
                    except OSError:
                        shutil.copy2(original_path, new_path)
                    self._extracted_files[filename] = new_path
                    os.unlink(original_path)

        except Exception as e:
            logger.error(f"7z文件解压失败: {str(e)}")
            raise

    def __enter__(self):
        try:
            if self.type == 'zip':
                self.archive = zipfile.ZipFile(self.filepath)
                if self.archive.testzip() is not None:
                    raise zipfile.BadZipFile("ZIP文件损坏")
            elif self.type == 'rar':
                # 只打开文件以获取文件列表，不进行解压
                self.archive = rarfile.RarFile(self.filepath)
                if self.archive.needs_password():
                    raise Exception("RAR文件有密码保护")
            elif self.type == 'gz':
                self.archive = gzip.GzipFile(self.filepath)
            return self
        except (zipfile.BadZipFile, rarfile.BadRarFile) as e:
            raise Exception(f"无效的压缩文件: {str(e)}")
        except Exception as e:
            raise Exception(f"打开压缩文件失败: {str(e)}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.archive:
            self.archive.close()
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                logger.error(f"清理临时目录失败: {str(e)}")

    def list_files(self):
        try:
            files = []
            if self.type == 'zip':
                files = [self.__encode_filename(f) for f in self.archive.namelist() 
                        if not f.endswith('/')]
            elif self.type == 'rar':
                files = [self.__encode_filename(f.filename) for f in self.archive.infolist() 
                        if not f.is_dir()]
                processable_files = [f for f in files if can_process_file(f)]
                if processable_files:
                    self._extract_rar_files(processable_files)
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
                        current_file = line[7:]
                    elif line.startswith('Attributes = D'):
                        is_directory = True
                    elif line == '':
                        if current_file and not is_directory:
                            files.append(current_file)
                        current_file = None
                        is_directory = False
                
                processable_files = [f for f in files if can_process_file(f)]
                if processable_files:
                    self._extract_7z_files(processable_files)
                    
            elif self.type == 'gz':
                base_name = os.path.basename(self.filepath)
                if base_name.endswith('.gz'):
                    files = [base_name[:-3]]
                else:
                    files = ['content']

            processable = [f for f in files if can_process_file(f)]
            logger.info(f"找到 {len(processable)} 个可处理文件")
            return files
            
        except Exception as e:
            logger.error(f"获取文件列表失败: {str(e)}")
            return []

    def get_file_info(self, filename):
        try:
            if self.type == 'zip':
                return self.archive.getinfo(filename).file_size
            elif self.type == 'rar':
                if filename in self._extracted_files:
                    return os.path.getsize(self._extracted_files[filename])
                return self.archive.getinfo(filename).file_size
            elif self.type == '7z':
                if filename in self._extracted_files:
                    return os.path.getsize(self._extracted_files[filename])
                result = subprocess.run(
                    ['7z', 'l', '-slt', self.filepath, filename],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding='utf-8'
                )
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if line.startswith('Size = '):
                            try:
                                return int(line[7:])
                            except ValueError:
                                pass
                return 0
            elif self.type == 'gz':
                return self.archive.size
            return 0
        except Exception as e:
            logger.error(f"获取文件信息失败: {str(e)}")
            return 0

    def extract_file(self, filename):
        try:
            encoded_filename = self.__encode_filename(filename)
            logger.info(f"正在检测文件: {encoded_filename}")
            
            if self.type == 'zip':
                return self.archive.read(filename)  # 使用原始 filename
            elif self.type == 'rar':
                if encoded_filename in self._extracted_files:
                    with open(self._extracted_files[encoded_filename], 'rb') as f:
                        return f.read()
                if can_process_file(encoded_filename):
                    self._extract_rar_files([filename])  # 使用原始 filename
                    if encoded_filename in self._extracted_files:
                        with open(self._extracted_files[encoded_filename], 'rb') as f:
                            return f.read()
                return self.archive.read(filename)  # 使用原始 filename
            elif self.type == '7z':
                if encoded_filename in self._extracted_files:
                    with open(self._extracted_files[encoded_filename], 'rb') as f:
                        return f.read()
                if can_process_file(encoded_filename):
                    self._extract_7z_files([filename])  # 使用原始 filename
                    if encoded_filename in self._extracted_files:
                        with open(self._extracted_files[encoded_filename], 'rb') as f:
                            return f.read()
                raise Exception(f"文件 {encoded_filename} 未找到在提取列表中")
            elif self.type == 'gz':
                return self.archive.read()
            raise Exception("不支持的压缩格式")
        except Exception as e:
            raise Exception(f"提取文件失败: {str(e)}")

def get_file_extension(filename):
    return Path(filename).suffix.lower()

def can_process_file(filename):
    ext = get_file_extension(filename)
    return ext in IMAGE_EXTENSIONS or ext == '.pdf' or ext in VIDEO_EXTENSIONS

def sort_files_by_priority(handler, files):
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