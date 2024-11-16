# app.py
from flask import Flask, request, jsonify
from transformers import pipeline
from PIL import Image
import os
import fitz
import io
import cv2
import numpy as np
import tempfile

app = Flask(__name__)

os.environ['TRANSFORMERS_CACHE'] = '/root/.cache/huggingface'
pipe = pipeline("image-classification", model="Falconsai/nsfw_image_detection")

@app.route('/check', methods=['POST'])
def check_image():
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file part'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400

        try:
            image = Image.open(file.stream)
            result = pipe(image)
            return jsonify({
                'status': 'success',
                'filename': file.filename,
                'result': result
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': 'Invalid image file'
            }), 400

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/pdf', methods=['POST'])
def check_pdf():
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file part'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400

        pdf_stream = file.read()
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        
        last_result = None
        images_found = False
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                images_found = True
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                image = Image.open(io.BytesIO(image_bytes))
                result = pipe(image)
                
                last_result = {
                    'status': 'success',
                    'filename': file.filename,
                    'result': result
                }
                
                nsfw_score = next((item['score'] for item in result if item['label'] == 'nsfw'), 0)
                normal_score = next((item['score'] for item in result if item['label'] == 'normal'), 1)
                
                if nsfw_score > 0.9 or normal_score < 0.6:
                    return jsonify(last_result)
        
        if not images_found:
            return jsonify({'status': 'false', 'message': 'No images found in PDF'})
            
        return jsonify(last_result)

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/video', methods=['POST'])
def check_video():
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file part'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        file.save(temp_file.name)
        
        cap = cv2.VideoCapture(temp_file.name)
        if not cap.isOpened():
            os.unlink(temp_file.name)
            return jsonify({
                'status': 'error',
                'message': 'Unable to read video file'
            }), 400

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0

        if duration < 1: 
            frame_positions = [0]
        elif duration <= 10:
            frame_positions = np.linspace(0, total_frames - 1, int(duration), dtype=int)
        else:
            frame_positions = np.linspace(0, total_frames - 1, 20, dtype=int)

        last_result = None
        frames_processed = 0

        for frame_pos in frame_positions:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
            ret, frame = cap.read()
            
            if not ret:
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            
            result = pipe(pil_image)
            frames_processed += 1
            
            last_result = {
                'status': 'success',
                'filename': file.filename,
                'frame_number': int(frame_pos),
                'timestamp': frame_pos / fps if fps > 0 else 0,
                'result': result
            }
            
            nsfw_score = next((item['score'] for item in result if item['label'] == 'nsfw'), 0)
            normal_score = next((item['score'] for item in result if item['label'] == 'normal'), 1)
            
            if nsfw_score > 0.9 or normal_score < 0.6:
                cap.release()
                os.unlink(temp_file.name)
                return jsonify(last_result)

        cap.release()
        os.unlink(temp_file.name)

        if frames_processed == 0:
            return jsonify({
                'status': 'error',
                'message': 'No frames could be processed from the video'
            }), 400

        return jsonify(last_result)

    except Exception as e:
        if 'temp_file' in locals():
            os.unlink(temp_file.name)
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3333)