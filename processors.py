# processors.py
from transformers import pipeline
import cv2
import numpy as np
from PIL import Image
import fitz
import io
import logging
import tempfile
import os
import shutil
from pathlib import Path
from config import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from utils import ArchiveHandler, can_process_file, sort_files_by_priority
from config import MAX_FILE_SIZE

# 配置日志
logger = logging.getLogger(__name__)

# 设置 OpenCV 日志级别，抑制警告信息
cv2.setLogLevel(0)

# 初始化模型
pipe = pipeline("image-classification", model="Falconsai/nsfw_image_detection", device=-1)

def process_image(image):
    """处理单张图片并返回检测结果"""
    try:
        logger.info("开始处理图片")
        result = pipe(image)
        nsfw_score = next((item['score'] for item in result if item['label'] == 'nsfw'), 0)
        normal_score = next((item['score'] for item in result if item['label'] == 'normal'), 1)
        logger.info(f"图片处理完成: NSFW={nsfw_score:.3f}, Normal={normal_score:.3f}")
        return {
            'nsfw': nsfw_score,
            'normal': normal_score
        }
    except Exception as e:
        logger.error(f"图片处理失败: {str(e)}")
        raise Exception(f"Image processing failed: {str(e)}")

def process_pdf_file(pdf_stream):
    """处理PDF文件并检查内容"""
    try:
        logger.info("开始处理PDF文件")
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        total_pages = len(doc)
        logger.info(f"PDF共有 {total_pages} 页")
        
        last_result = None  # 保存最后一次处理结果
        
        for page_num in range(total_pages):
            logger.info(f"正在处理第 {page_num + 1} 页")
            page = doc[page_num]
            image_list = page.get_images()
            
            if len(image_list) > 0:
                logger.info(f"第 {page_num + 1} 页发现 {len(image_list)} 张图片")
            
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    image = Image.open(io.BytesIO(image_bytes))
                    result = process_image(image)
                    last_result = result  # 保存每次的处理结果
                    
                    if result['nsfw'] > 0.8:
                        logger.info(f"在第 {page_num + 1} 页发现匹配内容")
                        return result

                except Exception as e:
                    logger.error(f"处理PDF中的图片失败: {str(e)}")
                    continue
        
        logger.info("PDF处理完成，返回最后一次处理结果")
        return last_result  # 返回最后一次处理结果，如果没有处理过任何图片则为None
    except Exception as e:
        logger.error(f"PDF处理失败: {str(e)}")
        raise Exception(f"PDF processing failed: {str(e)}")

def process_video_file(video_path):
    """处理视频文件并检查内容"""
    try:
        logger.info("开始处理视频文件")
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error("无法打开视频文件")
            return None

        # 获取视频信息
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        logger.info(f"视频信息: {total_frames} 帧, {fps} FPS, 时长 {duration:.2f} 秒")

        # 根据视频时长确定采样帧数
        if duration < 1:
            frame_positions = [0]
        elif duration <= 10:
            frame_positions = np.linspace(0, total_frames - 1, int(duration), dtype=int)
        else:
            frame_positions = np.linspace(0, total_frames - 1, 20, dtype=int)
        
        logger.info(f"计划检查 {len(frame_positions)} 个关键帧")

        last_result = None  # 保存最后一次处理结果
        
        for frame_pos in frame_positions:
            try:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
                ret, frame = cap.read()
                
                if not ret:
                    logger.warning(f"无法读取帧 {frame_pos}")
                    continue

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)
                
                result = process_image(pil_image)
                last_result = result  # 保存每次的处理结果
                
                if result['nsfw'] > 0.8:
                    timestamp = frame_pos / fps if fps > 0 else 0
                    logger.info(f"在时间点 {timestamp:.2f} 秒发现匹配内容")
                    cap.release()
                    return result

            except Exception as e:
                logger.error(f"处理视频帧 {frame_pos} 失败: {str(e)}")
                continue

        logger.info("视频处理完成，返回最后一次处理结果")
        cap.release()
        return last_result  # 返回最后一次处理结果，如果没有处理过任何帧则为None
    except Exception as e:
        logger.error(f"视频处理失败: {str(e)}")
        raise Exception(f"Video processing failed: {str(e)}")

def process_archive(file_stream, filename):
    """处理压缩文件"""
    temp_dir = None
    try:
        # 创建临时目录和文件
        temp_dir = tempfile.mkdtemp()
        archive_path = os.path.join(temp_dir, 'archive_file')
        
        # 正确的文件保存方式
        with open(archive_path, 'wb') as f:
            f.write(file_stream.read())
        
        # 检查文件大小
        file_size = os.path.getsize(archive_path)
        if file_size > MAX_FILE_SIZE:
            return {
                'status': 'error',
                'message': 'File too large'
            }, 400

        with ArchiveHandler(archive_path) as handler:
            # 获取文件列表
            files = handler.list_files()
            processable_files = [f for f in files if can_process_file(f)]
            
            if not processable_files:
                return {
                    'status': 'error',
                    'message': 'No processable files found in archive'
                }, 400

            # 按优先级和大小排序
            sorted_files = sort_files_by_priority(handler, processable_files)
            
            # 逐个处理文件
            last_result = None
            matched_content = None
            for inner_filename in sorted_files:
                try:
                    content = handler.extract_file(inner_filename)
                    ext = os.path.splitext(inner_filename)[1].lower()
                    
                    if ext in IMAGE_EXTENSIONS:
                        img = Image.open(io.BytesIO(content))
                        result = process_image(img)
                        last_result = {
                            'matched_file': inner_filename,
                            'result': result
                        }
                        
                        if result['nsfw'] > 0.8:
                            matched_content = last_result
                            break
                    
                    elif ext == '.pdf':
                        result = process_pdf_file(content)
                        if result:  # 只在有结果时更新
                            last_result = {
                                'matched_file': inner_filename,
                                'result': result
                            }
                            if result['nsfw'] > 0.8:
                                matched_content = last_result
                                break
                    
                    elif ext in VIDEO_EXTENSIONS:
                        temp_video = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                        try:
                            with open(temp_video.name, 'wb') as f:
                                f.write(content)
                            
                            result = process_video_file(temp_video.name)
                            if result:  # 只在有结果时更新
                                last_result = {
                                    'matched_file': inner_filename,
                                    'result': result
                                }
                                if result['nsfw'] > 0.8:
                                    matched_content = last_result
                                    break
                        finally:
                            if os.path.exists(temp_video.name):
                                os.unlink(temp_video.name)
                                
                except Exception as e:
                    logger.error(f"处理文件 {inner_filename} 时出错: {str(e)}")
                    continue

            # 返回结果
            if matched_content:
                logger.info(f"在压缩包 {filename} 中发现匹配内容: {matched_content['matched_file']}")
                return {
                    'status': 'success',
                    'filename': filename,
                    'result': matched_content['result']
                }
            elif last_result:
                logger.info(f"处理压缩包 {filename} 完成,最后处理的文件: {last_result['matched_file']}")
                return {
                    'status': 'success',
                    'filename': filename,
                    'result': last_result['result']
                }
            else:
                return {
                    'status': 'error',
                    'message': 'No files could be processed successfully'
                }, 400

    except Exception as e:
        logger.error(f"处理压缩包时出错: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }, 500
        
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.error(f"清理临时目录时出错: {str(e)}")