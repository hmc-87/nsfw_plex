from flask import Flask, request, jsonify, Response
import tempfile
import os
import logging
import magic
from pathlib import Path
from werkzeug.utils import secure_filename
from config import get_config, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, MIME_TO_EXT
from processors import process_image, process_pdf_file, process_video_file, process_archive

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Retrieve MAX_FILE_SIZE dynamically
MAX_FILE_SIZE = get_config("MAX_FILE_SIZE", 20 * 1024 * 1024 * 1024)

# Set maximum upload size
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Load `index.html` content once
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML_PATH = os.path.join(CURRENT_DIR, 'index.html')
if os.path.exists(INDEX_HTML_PATH):
    with open(INDEX_HTML_PATH, 'r', encoding='utf-8') as f:
        INDEX_HTML = f.read()
else:
    raise FileNotFoundError("index.html file is missing in the application directory.")

def detect_file_type(file_path):
    """Detect file MIME type and extension using magic library."""
    try:
        mime = magic.Magic(mime=True)
        mime_type = mime.from_file(file_path)
        ext = MIME_TO_EXT.get(mime_type)
        return mime_type, ext
    except Exception as e:
        logger.error(f"Failed to detect file type: {str(e)}")
        raise

@app.route('/')
def index():
    """Serve the HTML interface."""
    return Response(INDEX_HTML, mimetype='text/html')

@app.route('/check', methods=['POST'])
def check_file():
    """Handle file upload or local path for analysis."""
    try:
        if 'file' in request.files:
            # File upload via POST
            uploaded_file = request.files['file']
            if not uploaded_file.filename:
                return jsonify({'status': 'error', 'message': 'No file selected'}), 400

            filename = secure_filename(uploaded_file.filename)
            logger.info(f"Received uploaded file: {filename}")

            # Save to a temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            uploaded_file.save(temp_file.name)

            # Check file size
            file_size = os.path.getsize(temp_file.name)
            if file_size > MAX_FILE_SIZE:
                os.unlink(temp_file.name)
                return jsonify({'status': 'error', 'message': 'File too large'}), 400

            # Detect file type and process
            mime_type, ext = detect_file_type(temp_file.name)
            logger.info(f"Detected file type: {mime_type}, extension: {ext}")

            return process_file(temp_file.name, ext, filename)

        elif 'path' in request.form:
            # Local path provided via form data
            file_path = request.form['path']
            abs_path = os.path.abspath(file_path)

            # Check if file exists
            if not os.path.exists(abs_path):
                return jsonify({'status': 'error', 'message': 'File not found'}), 404

            # Check if it's a file
            if not os.path.isfile(abs_path):
                return jsonify({'status': 'error', 'message': 'Path is not a file'}), 400

            # Check file size
            file_size = os.path.getsize(abs_path)
            if file_size > MAX_FILE_SIZE:
                return jsonify({'status': 'error', 'message': 'File too large'}), 400

            # Detect file type and process
            mime_type, ext = detect_file_type(abs_path)
            logger.info(f"Detected file type: {mime_type}, extension: {ext}")

            return process_file(abs_path, ext, os.path.basename(abs_path))

        else:
            return jsonify({'status': 'error', 'message': 'No file or path provided'}), 400

    except Exception as e:
        logger.error(f"Error during file processing: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def process_file(file_path, ext, original_filename):
    """Process the file based on its type."""
    try:
        if ext in IMAGE_EXTENSIONS:
            from PIL import Image
            with Image.open(file_path) as img:
                result = process_image(img)
            return jsonify({
                'status': 'success',
                'filename': original_filename,
                'result': result
            })

        elif ext == '.pdf':
            with open(file_path, 'rb') as f:
                pdf_stream = f.read()
            result = process_pdf_file(pdf_stream)
            if result:
                return jsonify({
                    'status': 'success',
                    'filename': original_filename,
                    'result': result
                })
            return jsonify({'status': 'error', 'message': 'No processable content found in PDF'}), 400

        elif ext in VIDEO_EXTENSIONS:
            result = process_video_file(file_path)
            if result:
                # Include NSFW detection scores in the response
                return jsonify({
                    'status': 'success',
                    'filename': original_filename,
                    'result': {
                        'nsfw': result.get('nsfw', 0),
                        'normal': result.get('normal', 1)
                    },
                    'message': result.get('message', 'Processed video successfully.')
                }), 200
            else:
                # No NSFW content was found
                return jsonify({
                    'status': 'success',
                    'filename': original_filename,
                    'result': {
                        'nsfw': 0,
                        'normal': 1
                    },
                    'message': 'No NSFW content detected in video.'
                }), 200

        elif ext in {'.zip', '.rar', '.7z', '.gz'}:
            result = process_archive(file_path, original_filename)
            return jsonify(result) if isinstance(result, dict) else jsonify(result[0]), result[1]

        else:
            logger.error(f"Unsupported file extension: {ext}")
            return jsonify({'status': 'error', 'message': f'Unsupported file type: {ext}'}), 400

    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if os.path.exists(file_path):
            os.unlink(file_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3333)