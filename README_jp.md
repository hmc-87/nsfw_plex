# NSFW 検出器

## はじめに

これは [Falconsai/nsfw_image_detection](https://huggingface.co/Falconsai/nsfw_image_detection) に基づいた NSFW コンテンツ検出器です。  
モデル：google/vit-base-patch16-224-in21k

精度の確認は以下のリンクで行えます：[NSFW 検出器](https://www.vx.link/nsfw_detector.html)

他の一般的な NSFW 検出器と比較して、本検出器には以下の利点がございます：

* AI ベースで、より高い精度を実現しています。
* CPU のみでの推論に対応し、ほとんどのサーバーで実行可能です。
* 複数の CPU を自動的に活用し、推論を高速化します。
* nsfw と normal の2カテゴリーのみの簡潔な判定を行います。
* API として提供されるため、他のアプリケーションとの統合が容易です。
* Docker ベースの展開により、分散配置が容易です。
* 完全にローカルで動作し、データの安全性を保護します。

### パフォーマンス要件

本モデルの実行には最大 2GB のメモリが必要です。GPU は不要です。

### 対応ファイル形式

本検出器は以下のファイル形式の確認に対応しております：

* ✅ 画像（対応済み）
* ✅ PDF（対応済み）
* ✅ 動画（対応済み）
* ✅ 圧縮ファイル内のファイル（対応済み）

## クイックスタート

### API サーバーの起動

```bash
docker run -d -p 3333:3333 --name nsfw-detector vxlink/nsfw_detector:latest
```

サーバーのローカルパスにあるファイルを直接チェックする場合は、パスをコンテナにマウントしてください。
混乱を避けるため、通常はマウントパスをコンテナ内のパスと同じにすることをお勧めします。

```bash
docker run -d -p 3333:3333 -v /path/to/files:/path/to/files --name nsfw-detector vxlink/nsfw_detector:latest
```



対応システムアーキテクチャ：`x86_64`、`ARM64`。

### API を使用したコンテンツ確認

```bash
# 検出
curl -X POST -F "file=@/path/to/image.jpg" http://localhost:3333/check


# ファイルパスを指定して検出
curl -X POST -F "path=/path/to/image.jpg" http://localhost:3333/check
```

### Web インターフェースを使用した検出

アクセス先：[http://localhost:3333](http://localhost:3333)

## パブリック API

vx.link が提供する公開 API サービスをご利用いただけます。

```bash
# 検出
curl -X POST -F "file=@/path/to/image.jpg" https://vx.link/public/nsfw
```

* 提出された画像は保存されません。
* この API のリクエストレートは1分あたり30回に制限されていますのでご注意ください。

## ライセンス

本プロジェクトは Apache 2.0 ライセンスのもとでオープンソース化されております。
