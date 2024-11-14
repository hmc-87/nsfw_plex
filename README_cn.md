# NSFW Detector

## 简介

这是一个 NSFW 内容检测器，它基于 [Falconsai/nsfw_image_detection](https://huggingface.co/Falconsai/nsfw_image_detection) 。  
模型: google/vit-base-patch16-224-in21k

相比其它常见的 NSFW 检测器，这个检测器的优势在于：

* 基于 AI ，准确度更好。
* 支持纯 CPU 推理，可以运行在大部分服务器上。
* 自动调度多个 CPU 加速推理。
* 简单判断，只有两个类别：nsfw 和 normal。
* 以 API 的方式提供服务，更方便集成到其它应用中。
* 基于 Docker 部署，便于分布式部署。

### 性能需求

运行这个模型最多需要 2GB 的内存。不需要显卡的支持。

### 支持的文件类型

这个检测器支持检查的文件类型：

* 🆗 图片（已支持）
* 📅 视频（计划）
* 📅 PDF 文件（计划）
* 📅 压缩包中的文件（计划）

## 快速开始

### 启动 API 服务器

```bash
docker run -d -p 3333:3333 --name nsfw-detector vxlink/nsfw_detector:latest
```

### 使用 API 进行内容检查

```bash
curl -X POST -F "file=@/path/to/image.jpg" http://localhost:3333/check
```

## 公共 API

如果你只是想试试效果，或者不想自己部署，可以使用 vx.link 提供的公共 API 服务。

```bash
curl -X POST -F "file=@/path/to/image.jpg" https://vx.link/public/nsfw
```

* 不会保存你提交的图片。
* 请注意，该 API 速率限制为每分钟 30 次请求。

## 许可证

本项目基于 Apache 2.0 许可证开源。
