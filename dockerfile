# Use Ubuntu as base image
FROM ubuntu:22.04

# Set working directory
WORKDIR /app

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system packages
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    unrar \
    p7zip-full \
    python3-opencv \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Install OpenCV
RUN pip3 install --no-cache-dir opencv-python-headless

# Install rarfile and py7zr
RUN pip3 install --no-cache-dir rarfile py7zr

# Install Flask and its dependencies
RUN pip3 install --no-cache-dir flask==2.0.1 werkzeug==2.0.3

# Install Pillow
RUN pip3 install --no-cache-dir Pillow

# Install transformers
RUN pip3 install --no-cache-dir transformers

# Install torch (CPU version)
RUN pip3 install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Pre-download the model
RUN python3 -c "from transformers import pipeline; pipe = pipeline('image-classification', model='Falconsai/nsfw_image_detection', device=-1)"

# Set cache directory permissions
RUN chmod -R 755 /root/.cache

# Copy local application file
COPY app.py /app/app.py

# Run the application
CMD ["python3", "app.py"]