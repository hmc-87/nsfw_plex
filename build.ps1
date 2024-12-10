# build.ps1

# Default configuration values
$script:ImageName = "vxlink/nsfw_detector"
$script:Version = "v1.8"  # Default version if build.version file is not found
$script:Push = $false
$script:CacheDir = "$env:USERPROFILE\.docker\nsfw_detector_cache"
$script:CacheFrom = ""

# Read build.version file
$VersionFile = Join-Path $PSScriptRoot "build.version"
if (Test-Path $VersionFile) {
    $script:Version = (Get-Content $VersionFile).Trim()
    Write-Host "Using version from build.version: $Version"
} else {
    Write-Host "Warning: version file not found at $VersionFile, using default version $Version"
}

# Get native platform
$script:NativePlatform = $(docker version --format '{{.Server.Os}}/{{.Server.Arch}}').Replace('x86_64', 'amd64')

# Set target platform
$script:AllPlatforms = "linux/amd64,linux/arm64"
$script:Platform = $NativePlatform  # Default to building only for the native platform

function Show-Help {
    Write-Host "Usage: .\build.ps1 [options]"
    Write-Host "Options:"
    Write-Host "  -Push         Push images to registry after building (default: false)"
    Write-Host "  -Version      Specify version tag (default: v1.8)"
    Write-Host "  -NoCache      Disable build cache"
    Write-Host "  -Platform     Specify target platforms (default: native platform)"
    Write-Host "  -AllPlatforms Build for all supported platforms"
    Write-Host "  -Help         Show this help message"
}

# Parameter definitions
param(
    [switch]$Push,
    [string]$Version,
    [switch]$NoCache,
    [string]$Platform,
    [switch]$AllPlatforms,
    [switch]$Help
)

# Handle help parameter
if ($Help) {
    Show-Help
    exit 0
}

# Process parameters
if ($Push) {
    $script:Push = $true
    $script:Platform = $AllPlatforms  # Pushing implies building for all platforms
}

if ($Version) {
    $script:Version = $Version
}

if ($NoCache) {
    $script:CacheFrom = "--no-cache"
}

if ($Platform) {
    $script:Platform = $Platform
}

if ($AllPlatforms) {
    $script:Platform = $AllPlatforms
}

# Display configuration information
Write-Host "Building with configuration:"
Write-Host "- Version: $Version"
Write-Host "- Push to registry: $Push"
Write-Host "- Native platform: $NativePlatform"
Write-Host "- Target platforms: $Platform"
Write-Host "- Cache enabled: $(if ($CacheFrom -eq "") { 'yes' } else { 'no' })"

# Create cache directory if it does not exist
if (-not (Test-Path $CacheDir)) {
    New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null
}

# Configure buildx builder
$BuilderName = "nsfw-detector-builder"
$builderExists = $null
try {
    $builderExists = docker buildx inspect $BuilderName 2>$null
} catch {
    $builderExists = $null
}

if (-not $builderExists) {
    docker buildx create --name $BuilderName `
        --driver docker-container `
        --driver-opt network=host `
        --buildkitd-flags '--allow-insecure-entitlement security.insecure' `
        --use
} else {
    docker buildx use $BuilderName
}

# Set cache configuration parameters
if ($CacheFrom -eq "") {
    $CacheConfig = "--cache-from=type=local,src=$CacheDir --cache-to=type=local,dest=$CacheDir,mode=max"
} else {
    $CacheConfig = $CacheFrom
}

# Build base command
$BuildCmd = "docker buildx build " +
    "--platform $Platform " +
    "--tag ${ImageName}:${Version} " +
    "--tag ${ImageName}:latest " +
    "--file dockerfile " +
    "$CacheConfig " +
    "--build-arg BUILDKIT_INLINE_CACHE=1"

if ($Push) {
    # Remote build mode: Push images to the registry
    $BuildCmd += " --push"
} elseif ($Platform -eq $NativePlatform) {
    # Local build mode (single native platform): Use --load
    $BuildCmd += " --load"
} else {
    # Local build mode (multi-platform or non-native platforms)
    Write-Host "Warning: Building for non-native platform(s). Images will be available through docker buildx, but not in the regular docker images list."
}

$BuildCmd += " ."

# Execute build
Write-Host "Executing build command..."
Invoke-Expression $BuildCmd

# Verify build results (only in push mode)
if ($Push) {
    Write-Host "Verifying manifest for version $Version..."
    docker manifest inspect "${ImageName}:${Version}"

    Write-Host "Verifying manifest for latest..."
    docker manifest inspect "${ImageName}:latest"
}

# Cleanup and builder switching
if ($Push) {
    docker buildx use default
} else {
    Write-Host "Build completed for platform(s): $Platform"
}

Write-Host "Build complete!"
Write-Host "Built images:"
Write-Host "- ${ImageName}:${Version}"
Write-Host "- ${ImageName}:latest"

if ($Push) {
    Write-Host "Images have been pushed to registry"
} elseif ($Platform -eq $NativePlatform) {
    Write-Host "Images are available locally via 'docker images'"
} else {
    Write-Host "Images are available through docker buildx"
}