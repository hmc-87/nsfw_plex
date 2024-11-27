#!/bin/bash
set -e

# 默认配置值
IMAGE_NAME="vxlink/nsfw_detector"
VERSION="v1.4"
PUSH="false"
CACHE_DIR="${HOME}/.docker/nsfw_detector_cache"
CACHE_FROM=""

# 检测本机平台
NATIVE_PLATFORM=$(docker version -f '{{.Server.Os}}/{{.Server.Arch}}' | sed 's/x86_64/amd64/')

# 设置目标平台（默认包含所有支持的平台）
ALL_PLATFORMS="linux/amd64,linux/arm64"
PLATFORM="$NATIVE_PLATFORM"  # 默认仅构建本机平台

# 帮助信息显示函数
show_help() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -p, --push        Push images to registry after building (default: false)"
    echo "  -v, --version     Specify version tag (default: v0.3)"
    echo "  -h, --help        Show this help message"
    echo "  --no-cache        Disable build cache"
    echo "  --platform        Specify target platforms (default: native platform)"
    echo "  --all-platforms   Build for all supported platforms"
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--push)
            PUSH="true"
            PLATFORM="$ALL_PLATFORMS"  # 推送时默认构建所有平台
            shift
            ;;
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        --no-cache)
            CACHE_FROM="--no-cache"
            shift
            ;;
        --platform)
            PLATFORM="$2"
            shift 2
            ;;
        --all-platforms)
            PLATFORM="$ALL_PLATFORMS"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

echo "Building with configuration:"
echo "- Version: ${VERSION}"
echo "- Push to registry: ${PUSH}"
echo "- Native platform: ${NATIVE_PLATFORM}"
echo "- Target platforms: ${PLATFORM}"
echo "- Cache enabled: $([ -z "$CACHE_FROM" ] && echo "yes" || echo "no")"

# 创建缓存目录（如果不存在）
mkdir -p "${CACHE_DIR}"

# 配置 buildx 构建器
BUILDER="nsfw-detector-builder"
if ! docker buildx inspect "${BUILDER}" > /dev/null 2>&1; then
    docker buildx create --name "${BUILDER}" \
        --driver docker-container \
        --driver-opt network=host \
        --buildkitd-flags '--allow-insecure-entitlement security.insecure' \
        --use
else
    docker buildx use "${BUILDER}"
fi

# 设置缓存配置参数
if [ -z "$CACHE_FROM" ]; then
    CACHE_CONFIG="--cache-from=type=local,src=${CACHE_DIR} --cache-to=type=local,dest=${CACHE_DIR},mode=max"
else
    CACHE_CONFIG="$CACHE_FROM"
fi

# 构建基础命令
BUILD_CMD="docker buildx build \
  --platform ${PLATFORM} \
  --tag ${IMAGE_NAME}:${VERSION} \
  --tag ${IMAGE_NAME}:latest \
  --file dockerfile \
  ${CACHE_CONFIG} \
  --build-arg BUILDKIT_INLINE_CACHE=1"

if [ "$PUSH" = "true" ]; then
    # 远程构建模式：推送到仓库
    BUILD_CMD="${BUILD_CMD} --push"
elif [ "$PLATFORM" = "$NATIVE_PLATFORM" ]; then
    # 本地构建模式（单一本机平台）：使用 --load
    BUILD_CMD="${BUILD_CMD} --load"
else
    # 本地构建模式（多平台或非本机平台）：输出到本地 docker 镜像
    echo "Warning: Building for non-native platform(s). Images will be available through docker buildx, but not in regular docker images list."
fi

BUILD_CMD="${BUILD_CMD} ."

# 执行构建
echo "Executing build command..."
eval ${BUILD_CMD}

# 验证构建结果（仅在推送模式下）
if [ "$PUSH" = "true" ]; then
    echo "Verifying manifest for version ${VERSION}..."
    docker manifest inspect ${IMAGE_NAME}:${VERSION}

    echo "Verifying manifest for latest..."
    docker manifest inspect ${IMAGE_NAME}:latest
fi

# 清理和切换构建器
if [ "$PUSH" = "true" ]; then
    docker buildx use default
else
    echo "Build completed for platform(s): ${PLATFORM}"
fi

echo "Build complete!"
echo "Built images:"
echo "- ${IMAGE_NAME}:${VERSION}"
echo "- ${IMAGE_NAME}:latest"

if [ "$PUSH" = "true" ]; then
    echo "Images have been pushed to registry"
elif [ "$PLATFORM" = "$NATIVE_PLATFORM" ]; then
    echo "Images are available locally via 'docker images'"
else
    echo "Images are available through buildx"
fi