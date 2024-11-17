FROM ubuntu:22.04

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

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
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install python-magic
RUN pip3 install --no-cache-dir opencv-python-headless
RUN pip3 install --no-cache-dir rarfile py7zr
RUN pip3 install --no-cache-dir flask==2.0.1 werkzeug==2.0.3
RUN pip3 install --no-cache-dir Pillow
RUN pip3 install --no-cache-dir transformers
RUN pip3 install --no-cache-dir PyMuPDF
RUN pip3 install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

RUN python3 -c "from transformers import pipeline; pipe = pipeline('image-classification', model='Falconsai/nsfw_image_detection', device=-1)"

RUN chmod -R 755 /root/.cache

COPY app.py /app/app.py
COPY config.py /app/config.py
COPY processors.py /app/processors.py
COPY utils.py /app/utils.py
COPY index.html /app/index.html

CMD ["python3", "app.py"]
