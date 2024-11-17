FROM ubuntu:22.04

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

# 系统依赖安装放在最前面，因为这些很少改变
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
    libmagic1 \
    libxext6 \
    libxrender-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 合并 pip 安装命令，减少层数
RUN pip3 install --no-cache-dir \
    python-magic \
    opencv-python-headless \
    rarfile \
    py7zr \
    flask==2.0.1 \
    werkzeug==2.0.3 \
    Pillow \
    transformers \
    PyMuPDF \
    && pip3 install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 预下载模型
RUN python3 -c "from transformers import pipeline; pipe = pipeline('image-classification', model='Falconsai/nsfw_image_detection', device=-1)"

RUN chmod -R 755 /root/.cache

# 源代码复制放在最后，因为这些文件最容易变化
COPY app.py config.py processors.py utils.py index.html /app/

CMD ["python3", "app.py"]
