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
        self._extracted_files = {}  # Stores a mapping of extracted files {original filename: temporary file path}
        
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
            logger.error(f"File type detection failed: {str(e)}")
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
            logger.error(f"7z file detection failed: {str(e)}")
            return False

    def _is_valid_gzip(self, filepath):
        try:
            with gzip.open(filepath, 'rb') as f:
                f.read(1)
            return True
        except Exception:
            return False

    def _generate_temp_filename(self, original_filename):
        """Generate a unique temporary filename."""
        ext = Path(original_filename).suffix
        return f"{str(uuid.uuid4())}{ext}"

    def _extract_rar_all(self):
        """Extract all RAR files using the unrar command-line tool."""
        if not self.temp_dir:
            self.temp_dir = tempfile.mkdtemp()

        try:
            extract_cmd = ['unrar', 'x', '-y', self.filepath, self.temp_dir + os.sep]
            result = subprocess.run(
                extract_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8'
            )

            if result.returncode != 0:
                raise Exception(f"RAR extraction failed: {result.stderr}")

            for root, _, files in os.walk(self.temp_dir):
                for filename in files:
                    original_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(original_path, self.temp_dir)
                    
                    new_filename = str(uuid.uuid4()) + os.path.splitext(filename)[1]
                    new_path = os.path.join(self.temp_dir, new_filename)
                    
                    os.rename(original_path, new_path)
                    self._extracted_files[relative_path] = new_path

            logger.info(f"Successfully extracted {len(self._extracted_files)} files to the temporary directory.")
            return True

        except Exception as e:
            logger.error(f"Complete RAR extraction failed: {str(e)}")
            return False
        
    def _extract_7z_files(self, files_to_extract):
        """Extract specific 7z files to a temporary directory."""
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
                    logger.warning(f"Failed to extract file {filename}: {result.stderr}")
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
            logger.error(f"7z file extraction failed: {str(e)}")
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            raise

    def __enter__(self):
        try:
            if self.type == 'zip':
                self.archive = zipfile.ZipFile(self.filepath)
                if self.archive.testzip() is not None:
                    raise zipfile.BadZipFile("ZIP file is corrupted.")
            elif self.type == 'rar':
                self.archive = rarfile.RarFile(self.filepath)
                if self.archive.needs_password():
                    raise Exception("RAR file is password protected.")
                if not self._extract_rar_all():
                    raise Exception("RAR extraction failed.")
            elif self.type == 'gz':
                self.archive = gzip.GzipFile(self.filepath)
            return self
        except (zipfile.BadZipFile, rarfile.BadRarFile) as e:
            raise Exception(f"Invalid archive file: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to open archive file: {str(e)}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.archive:
            self.archive.close()
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                logger.error(f"Failed to clean up temporary directory: {str(e)}")

    def list_files(self):
        try:
            if self.type == 'zip':
                files = [f for f in self.archive.namelist() if not f.endswith('/')]
            elif self.type == 'rar':
                files = list(self._extracted_files.keys())
            elif self.type == '7z':
                result = subprocess.run(
                    ['7z', 'l', '-slt', self.filepath], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    encoding='utf-8'
                )
                if result.returncode != 0:
                    raise Exception("Failed to list 7z file contents.")
                
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
                files = [base_name[:-3]] if base_name.endswith('.gz') else ['content']
            else:
                files = []

            logger.info(f"Found {len(files)} files that can be processed.")
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files: {str(e)}")
            return []

    def get_file_info(self, filename):
        try:
            if self.type == 'zip':
                return self.archive.getinfo(filename).file_size
            elif self.type == 'rar':
                if filename in self._extracted_files:
                    return os.path.getsize(self._extracted_files[filename])
                return 0
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
                            return int(line[7:])
                return 0
            elif self.type == 'gz':
                return self.archive.size
            return 0
        except Exception as e:
            logger.error(f"Failed to get file info: {str(e)}")
            return 0

    def extract_file(self, filename):
        try:
            base_name = os.path.basename(filename)
            logger.info(f"Checking file: {base_name}")
            
            if self.type == 'zip':
                return self.archive.read(filename)
            elif self.type == 'rar':
                if filename in self._extracted_files:
                    with open(self._extracted_files[filename], 'rb') as f:
                        return f.read()
                raise Exception(f"File {filename} not found in extraction list.")
            elif self.type == '7z':
                if filename in self._extracted_files:
                    with open(self._extracted_files[filename], 'rb') as f:
                        return f.read()
                if can_process_file(filename):
                    self._extract_7z_files([filename])
                    if filename in self._extracted_files:
                        with open(self._extracted_files[filename], 'rb') as f:
                            return f.read()
                raise Exception(f"File {filename} not found in extraction list.")
            elif self.type == 'gz':
                return self.archive.read()
            raise Exception("Unsupported archive format.")
        except Exception as e:
            raise Exception(f"Failed to extract file: {str(e)}")

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