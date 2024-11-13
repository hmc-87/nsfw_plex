# NSFW Detector

[中文指南](README_cn.md) | [日本語ガイド](README_jp.md)

## Introduction

This is an NSFW content detector based on [Falconsai/nsfw_image_detection](https://huggingface.co/Falconsai/nsfw_image_detection).  
Model: google/vit-base-patch16-224-in21k

Compared to other common NSFW detectors, this detector has the following advantages:

* AI-based, providing better accuracy.
* Supports CPU-only inference, can run on most servers.
* Automatically utilizes multiple CPUs to accelerate inference.
* Simple classification with only two categories: nsfw and normal.
* Provides service via API, making it easier to integrate with other applications.
* Docker-based deployment, suitable for distributed deployment.

### Performance Requirements

Running this model requires up to 2GB of memory. No GPU support is needed.

### Supported File Types

This detector supports checking the following file types:

* 🆗 Images (Supported)
* 📅 Videos (Planned)
* 📅 PDF Files (Planned)
* 📅 Files in Archives (Planned)

## Quick Start

### Start the API Server

```bash
docker run -d -p 3333:3333 --name nsfw-detector vxlink/nsfw_detector:latest
```

### Use the API for Content Checking

```bash
curl -X POST -F "image=@/path/to/image.jpg" http://localhost:3333/check
```

## Public API

If you just want to try it out or don't want to deploy it yourself, you can use the public API service provided by vx.link.

```bash
curl -X POST -F "image=@/path/to/image.jpg" http://vx.link/public/nsfw
```

Please note that this API has a rate limit of 30 requests per minute.

## License

This project is open-source under the Apache 2.0 license.
