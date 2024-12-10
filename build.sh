#!/bin/bash
set -e

# Default configuration values
IMAGE_NAME="vxlink/nsfw_detector"
VERSION="v1.8"  # Default version if build.version file is not found
PUSH="false"
CACHE_DIR="${HOME}/.docker/nsfw_detector_cache"
CACHE_FROM=""

# Read build.version file
VERSION_FILE="./build.version"
if [ -f "$VERSION_FILE" ]; then
    VERSION=$(cat "$VERSION_FILE" | tr -d '[:space:]')
    echo "Using version from build.version: $VERSION"
else
    echo "Warning: version file not found at $VERSION_FILE, using default version $VERSION"
fi

# Detect native platform
NATIVE_PLATFORM=$(docker version -f '{{.Server.Os}}/{{.Server.Arch}}' | sed 's/x86_64/amd64/')

# Set target platform (default to native platform only)
ALL_PLATFORMS="linux/amd64,linux/arm64"
PLATFORM="$NATIVE_PLATFORM"  # Default to build only for the native platform

# Help message function
show_help() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -p, --push        Push images to registry after building (default: false)"
    echo "  -v, --version     Specify version tag (default: v1.8)"
    echo "  -h, --help        Show this help message"
    echo "  --no-cache        Disable build cache"
    echo "  --platform        Specify target platforms (default: native platform)"
    echo "  --all-platforms   Build for all supported platforms"
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--push)
            PUSH="true"
            PLATFORM="$ALL_PLATFORMS"  # Push implies building for all platforms
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

# Create cache directory if it doesn't exist
mkdir -p "${CACHE_DIR}"

# Configure buildx builder
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

# Set cache configuration parameters
if [ -z "$CACHE_FROM" ]; then
    CACHE_CONFIG="--cache-from=type=local,src=${CACHE_DIR} --cache-to=type=local,dest=${CACHE_DIR},mode=max"
else
    CACHE_CONFIG="$CACHE_FROM"
fi

# Build command
BUILD_CMD="docker buildx build \
  --platform ${PLATFORM} \
  --tag ${IMAGE_NAME}:${VERSION} \
  --tag ${IMAGE_NAME}:latest \
  --file dockerfile \
  ${CACHE_CONFIG} \
  --build-arg BUILDKIT_INLINE_CACHE=1"

if [ "$PUSH" = "true" ]; then
    # Remote build mode: Push images to the registry
    BUILD_CMD="${BUILD_CMD} --push"
elif [ "$PLATFORM" = "$NATIVE_PLATFORM" ]; then
    # Local build mode (single native platform): Use --load
    BUILD_CMD="${BUILD_CMD} --load"
else
    # Local build mode (multi-platform or non-native): Output to buildx
    echo "Warning: Building for non-native platform(s). Images will be available through docker buildx, but not in the regular docker images list."
fi

BUILD_CMD="${BUILD_CMD} ."

# Execute build
echo "Executing build command..."
eval ${BUILD_CMD}

# Verify build results (only in push mode)
if [ "$PUSH" = "true" ]; then
    echo "Verifying manifest for version ${VERSION}..."
    docker manifest inspect ${IMAGE_NAME}:${VERSION}

    echo "Verifying manifest for latest..."
    docker manifest inspect ${IMAGE_NAME}:latest
fi

# Cleanup and builder switching
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
    echo "Images have been pushed to the registry."
elif [ "$PLATFORM" = "$NATIVE_PLATFORM" ]; then
    echo "Images are available locally via 'docker images'."
else
    echo "Images are available through docker buildx."
fi