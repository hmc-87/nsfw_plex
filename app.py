# app.py
from flask import Flask, request, jsonify
from transformers import pipeline
from PIL import Image
import os

app = Flask(__name__)

os.environ['TRANSFORMERS_CACHE'] = '/root/.cache/huggingface'
pipe = pipeline("image-classification", model="Falconsai/nsfw_image_detection")

@app.route('/check', methods=['POST'])
def check_image():
    try:
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No file part in the request'
            }), 400
            
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No file selected'
            }), 400

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
                'message': 'Invalid image file or file format not supported'
            }), 400

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3333)