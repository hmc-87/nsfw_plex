variable "DOCKER_USERNAME" {
  default = "vxlink"
}

variable "IMAGE_NAME" {
  default = "nsfw_detector"
}

variable "VERSION" {
  default = "v0.3"
}

group "default" {
  targets = ["app"]
}

target "app" {
  context = "."
  dockerfile = "Dockerfile"
  tags = [
    "${DOCKER_USERNAME}/${IMAGE_NAME}:${VERSION}",
    "${DOCKER_USERNAME}/${IMAGE_NAME}:latest"
  ]
  cache-from = ["type=registry,ref=${DOCKER_USERNAME}/${IMAGE_NAME}:cache"]
  cache-to = ["type=registry,ref=${DOCKER_USERNAME}/${IMAGE_NAME}:cache,mode=max"]
  push = true
  platforms = [
    "linux/amd64",    // x86_64
    "linux/arm64",    // ARM64
  ]
}