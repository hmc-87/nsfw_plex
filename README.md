# NSFW Plex (Or any media)

## Introduction

This is an NSFW content detector based on [Falconsai/nsfw_image_detection](https://huggingface.co/Falconsai/nsfw_image_detection).  
Model: google/vit-base-patch16-224-in21k

This tool detects NSFW content in various file formats using AI. It runs locally on your server, ensuring data security.

It will currently scan files to deteremine NFSW.  Future builds will include automatic media library scanning, notifcaitons and quarantining for review. 

## Key Features

- **AI-powered** for high accuracy.
- Works on **CPU-only systems**.
- **Efficient**—utilizes multiple CPUs for faster processing.
- Simple classification: **NSFW** or **Normal**.
- API-based, easy to integrate into applications.
- Fully **local**, no data is sent to external servers.
- Docker-based for quick and consistent deployment.

## System Requirements

- **Memory**: Requires up to 2GB RAM.
- **Architecture**: Supports `x86_64` and `ARM64`.
- **File Types Supported**:
  - Images
  - PDFs
  - Videos
  - Compressed files (ZIP, RAR, etc.)

---

## Quick Start Guide

### Step 1: Run the Detector

To run the NSFW detector, use Docker. The following command starts the API server:

```bash
docker run -d -p 3333:3333 --name nsfw-detector vxlink/nsfw_detector:latest

Step 2: Optional - Mount Local Files

If you need to analyze local files on the server, mount the desired directory into the Docker container:

docker run -d -p 3333:3333 -v /path/to/files:/path/to/files --name nsfw-detector hmc-87/nsfw_plex:latest

Replace /path/to/files with the path of the directory containing your files.

How to Use

1. Using the API

You can send files for detection using curl:
	•	Detect NSFW in an uploaded file:

curl -X POST -F "file=@/path/to/image.jpg" http://localhost:3333/check


	•	Analyze a file by its path on the server:

curl -X POST -F "path=/path/to/image.jpg" http://localhost:3333/check



2. Web Interface

Access the built-in web interface by visiting http://localhost:3333 in your browser.
Here, you can upload files directly to check for NSFW content.

Configuration

You can customize the detector by creating a config file and mounting it in the /tmp directory of the container.

Example Configuration Options:
	•	NSFW Threshold: Adjust sensitivity (nsfw_threshold).
	•	Video Frame Limit: Set maximum frames to process (ffmpeg_max_frames).
	•	Video Timeout: Set timeout for video processing (ffmpeg_max_timeout).

To use a custom configuration, mount the /tmp directory:

docker run -d -p 3333:3333 -v /tmp/config:/tmp/config --name nsfw-detector hmc-87/nsfw_plex:latest


License

This project is open-source under the Apache 2.0 License.

