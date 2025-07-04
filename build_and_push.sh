#!/bin/bash

# Smart-ToDo - Build and Push Script
# Builds and pushes Docker images to GitHub Container Registry

set -e

# Set variables
IMAGE_BASE="ghcr.io/sudipta-s-mcps/smart-todo"
TAG="${1:-latest}"
PLATFORMS="linux/amd64,linux/arm64"

# Detect service based on first argument
if [[ "${1}" == "backend" ]]; then
    IMAGE_NAME="${IMAGE_BASE}-backend"
    BUILD_CONTEXT="./backend"
    SERVICE_NAME="Backend API"
    TAG="${2:-latest}"
elif [[ "${1}" == "frontend" ]]; then
    IMAGE_NAME="${IMAGE_BASE}-frontend"
    BUILD_CONTEXT="./frontend"
    SERVICE_NAME="Frontend PWA"
    TAG="${2:-latest}"
elif [[ "${1}" == "admin" || "${1}" == "admin-panel" ]]; then
    IMAGE_NAME="${IMAGE_BASE}-admin"
    BUILD_CONTEXT="./admin-panel"
    SERVICE_NAME="Admin Panel"
    TAG="${2:-latest}"
elif [[ "${1}" == "mcp" || "${1}" == "mcp-server" ]]; then
    IMAGE_NAME="${IMAGE_BASE}-mcp"
    BUILD_CONTEXT="./backend"
    DOCKERFILE_PATH="./backend/mcp_server/Dockerfile"
    SERVICE_NAME="MCP Server"
    TAG="${2:-latest}"
elif [[ "${1}" == "--all" ]]; then
    # Build all services mode
    BUILD_ALL=true
    TAG="${2:-latest}"
    SERVICE_NAME="All Services"
else
    # Default to backend if no service specified
    IMAGE_NAME="${IMAGE_BASE}-backend"
    BUILD_CONTEXT="./backend"
    SERVICE_NAME="Backend API"
    TAG="${1:-latest}"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo "🚀 $SERVICE_NAME - Docker Build & Push"
    echo "===================================================="
    if [[ "$BUILD_ALL" == "true" ]]; then
        echo "Building ALL services with tag: $TAG"
        echo "Services: Backend API, Frontend PWA, Admin Panel, MCP Server"
    else
        echo "Building: $IMAGE_NAME:$TAG"
    fi
    echo "Platforms: $PLATFORMS"
    echo ""
}

check_prerequisites() {
    info "Checking prerequisites..."
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        error "Docker is not running or not accessible"
        exit 1
    fi
    
    # Check if buildx is available
    if ! docker buildx version >/dev/null 2>&1; then
        error "Docker buildx is not available"
        exit 1
    fi
    
    # Check environment variables
    if [[ -z "$GITHUB_USERNAME" || -z "$GITHUB_PAT" ]]; then
        error "GITHUB_USERNAME or GITHUB_PAT environment variables are not set"
        echo ""
        echo "Please set them with:"
        echo "export GITHUB_USERNAME=your_github_username"
        echo "export GITHUB_PAT=your_personal_access_token"
        exit 1
    fi
    
    success "Prerequisites check passed"
}

authenticate_registry() {
    info "Authenticating to GitHub Container Registry..."
    
    echo "$GITHUB_PAT" | docker login ghcr.io -u "$GITHUB_USERNAME" --password-stdin
    if [ $? -ne 0 ]; then
        error "Docker login failed. Ensure your credentials are correct"
        exit 1
    fi
    
    success "Authentication successful"
}

create_builder() {
    info "Creating/using Docker buildx builder..."
    
    # Create builder if it doesn't exist
    if ! docker buildx inspect smart-todo-builder >/dev/null 2>&1; then
        docker buildx create --name smart-todo-builder --use
    else
        docker buildx use smart-todo-builder
    fi
    
    # Bootstrap the builder
    docker buildx inspect --bootstrap
    
    success "Builder ready"
}

build_single_service() {
    local service_name="$1"
    local image_name="$2"
    local build_context="$3"
    local dockerfile_path="$4"
    local tag="$5"
    
    info "Building $service_name..."
    
    # Add Dockerfile argument if custom path is specified
    DOCKERFILE_ARG=""
    if [ ! -z "$dockerfile_path" ]; then
        DOCKERFILE_ARG="-f $dockerfile_path"
    fi
    
    # Build for multiple platforms and push
    docker buildx build \
        --platform "$PLATFORMS" \
        $DOCKERFILE_ARG \
        --tag "$image_name:$tag" \
        --tag "$image_name:latest" \
        --push \
        --progress=plain \
        "$build_context"
    
    if [ $? -ne 0 ]; then
        error "$service_name build/push failed"
        return 1
    fi
    
    success "$service_name built and pushed successfully"
    return 0
}

build_and_push() {
    if [[ "$BUILD_ALL" == "true" ]]; then
        build_all_services
    else
        build_single_service_current
    fi
}

build_single_service_current() {
    info "Building and pushing Docker image..."
    
    # Add Dockerfile argument if custom path is specified
    DOCKERFILE_ARG=""
    if [ ! -z "$DOCKERFILE_PATH" ]; then
        DOCKERFILE_ARG="-f $DOCKERFILE_PATH"
    fi
    
    # Build for multiple platforms and push
    docker buildx build \
        --platform "$PLATFORMS" \
        $DOCKERFILE_ARG \
        --tag "$IMAGE_NAME:$TAG" \
        --tag "$IMAGE_NAME:latest" \
        --push \
        --progress=plain \
        "$BUILD_CONTEXT"
    
    if [ $? -ne 0 ]; then
        error "Docker image build/push failed"
        exit 1
    fi
    
    success "Image built and pushed successfully"
}

build_all_services() {
    info "Building all services..."
    
    local failed_services=()
    local total_services=4
    
    # Build Backend API
    echo ""
    echo "🔨 Building Backend API..."
    echo "────────────────────────────────────────"
    if ! build_single_service "Backend API" "${IMAGE_BASE}-backend" "./backend" "" "$TAG"; then
        failed_services+=("Backend API")
    fi
    
    # Build Frontend PWA
    echo ""
    echo "🔨 Building Frontend PWA..."
    echo "────────────────────────────────────────"
    if ! build_single_service "Frontend PWA" "${IMAGE_BASE}-frontend" "./frontend" "" "$TAG"; then
        failed_services+=("Frontend PWA")
    fi
    
    # Build Admin Panel
    echo ""
    echo "🔨 Building Admin Panel..."
    echo "────────────────────────────────────────"
    if ! build_single_service "Admin Panel" "${IMAGE_BASE}-admin" "./admin-panel" "" "$TAG"; then
        failed_services+=("Admin Panel")
    fi
    
    # Build MCP Server
    echo ""
    echo "🔨 Building MCP Server..."
    echo "────────────────────────────────────────"
    if ! build_single_service "MCP Server" "${IMAGE_BASE}-mcp" "./backend" "./backend/mcp_server/Dockerfile" "$TAG"; then
        failed_services+=("MCP Server")
    fi
    
    # Report results
    echo ""
    echo "📊 Build Summary"
    echo "════════════════"
    
    if [ ${#failed_services[@]} -eq 0 ]; then
        success "All services built successfully! 🎉"
    else
        error "Some services failed to build:"
        for service in "${failed_services[@]}"; do
            echo "   ❌ $service"
        done
        echo ""
        warning "Successfully built: $(($total_services - ${#failed_services[@]}))/$total_services services"
        exit 1
    fi
}

verify_image() {
    if [[ "$BUILD_ALL" == "true" ]]; then
        verify_all_images
    else
        verify_single_image
    fi
}

verify_single_image() {
    info "Verifying pushed image..."
    
    # Pull and inspect the image
    docker pull "$IMAGE_NAME:$TAG" >/dev/null
    
    # Get image info
    local image_size=$(docker images "$IMAGE_NAME:$TAG" --format "{{.Size}}")
    local image_id=$(docker images "$IMAGE_NAME:$TAG" --format "{{.ID}}")
    
    echo "Image ID: $image_id"
    echo "Image Size: $image_size"
    
    success "Image verification completed"
}

verify_all_images() {
    info "Verifying all pushed images..."
    
    local images=(
        "${IMAGE_BASE}-backend:$TAG"
        "${IMAGE_BASE}-frontend:$TAG"
        "${IMAGE_BASE}-admin:$TAG"
        "${IMAGE_BASE}-mcp:$TAG"
    )
    
    for image in "${images[@]}"; do
        echo "Verifying $image..."
        docker pull "$image" >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            local size=$(docker images "$image" --format "{{.Size}}")
            echo "  ✅ $image ($size)"
        else
            echo "  ❌ Failed to verify $image"
        fi
    done
    
    success "Image verification completed"
}

generate_deployment_instructions() {
    if [[ "$BUILD_ALL" == "true" ]]; then
        generate_all_deployment_instructions
    else
        generate_single_deployment_instructions
    fi
}

generate_single_deployment_instructions() {
    info "Generating deployment instructions..."
    
    cat > docker_deployment_info.md << EOF
# Docker Image Deployment Information

## Image Details
- **Image**: \`$IMAGE_NAME:$TAG\`
- **Platforms**: $PLATFORMS
- **Registry**: GitHub Container Registry (ghcr.io)
- **Build Date**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")

## Pull Command
\`\`\`bash
docker pull $IMAGE_NAME:$TAG
\`\`\`

## Portainer Stack Usage
Update your \`portainer-stack.yml\` to use this image:

\`\`\`yaml
services:
  smart-todo-service:
    image: $IMAGE_NAME:$TAG
    # ... rest of your configuration
\`\`\`

## Security Notes
- Image runs as non-root user (uid: 1000)
- Multi-stage build for minimal attack surface
- Only runtime dependencies included in final image
- Health checks configured for monitoring

## Verification
\`\`\`bash
# Check image layers
docker history $IMAGE_NAME:$TAG

# Test health endpoint (backend only)
curl http://localhost:8000/health
\`\`\`
EOF
    
    success "Deployment instructions created: docker_deployment_info.md"
}

generate_all_deployment_instructions() {
    info "Generating deployment instructions for all services..."
    
    cat > docker_deployment_info.md << EOF
# Smart-ToDo - Complete Docker Deployment Information

## Build Summary
- **Build Date**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
- **Tag**: $TAG
- **Platforms**: $PLATFORMS
- **Registry**: GitHub Container Registry (ghcr.io)

## Images Built

### Backend API
- **Image**: \`${IMAGE_BASE}-backend:$TAG\`
- **Port**: 8000
- **Purpose**: FastAPI backend with MCP integration

### Frontend PWA
- **Image**: \`${IMAGE_BASE}-frontend:$TAG\`
- **Port**: 80 (Nginx)
- **Purpose**: React PWA for users

### Admin Panel
- **Image**: \`${IMAGE_BASE}-admin:$TAG\`
- **Port**: 3000
- **Purpose**: Admin interface for system management

### MCP Server
- **Image**: \`${IMAGE_BASE}-mcp:$TAG\`
- **Port**: 5485
- **Purpose**: MCP server for Claude Desktop integration

## Pull All Images
\`\`\`bash
docker pull ${IMAGE_BASE}-backend:$TAG
docker pull ${IMAGE_BASE}-frontend:$TAG
docker pull ${IMAGE_BASE}-admin:$TAG
docker pull ${IMAGE_BASE}-mcp:$TAG
\`\`\`

## Complete Portainer Stack
\`\`\`yaml
version: '3.8'
services:
  backend:
    image: ${IMAGE_BASE}-backend:$TAG
    ports:
      - "5482:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://sd_todo_app_user:password@192.168.11.100:15432/sd_todo_app_db
      - REDIS_URL=redis://192.168.11.100:6379/0
      - SECRET_KEY=your_secret_key
    networks:
      - smart-todo-network
    
  frontend:
    image: ${IMAGE_BASE}-frontend:$TAG
    ports:
      - "5484:80"
    environment:
      - VITE_API_URL=http://192.168.11.100:5482/api/v1
    networks:
      - smart-todo-network
    depends_on:
      - backend
    
  admin-panel:
    image: ${IMAGE_BASE}-admin:$TAG
    ports:
      - "5483:3000"
    environment:
      - VITE_API_URL=http://192.168.11.100:5482/api/v1
    networks:
      - smart-todo-network
    depends_on:
      - backend
    
  mcp-server:
    image: ${IMAGE_BASE}-mcp:$TAG
    ports:
      - "5485:5485"
    environment:
      - TODO_API_ENDPOINT=http://192.168.11.100:5482/api/v1
      - MCP_SERVER_NAME=TodoApp
      - MCP_SERVER_VERSION=1.0.0
    networks:
      - smart-todo-network
    depends_on:
      - backend

networks:
  smart-todo-network:
    driver: bridge
\`\`\`

## Health Checks
\`\`\`bash
# Backend API
curl http://192.168.11.100:5482/health

# Frontend PWA
curl http://192.168.11.100:5484/

# Admin Panel
curl http://192.168.11.100:5483/

# MCP Server
curl http://192.168.11.100:5485/mcp/
\`\`\`

## Security Notes
- All images run as non-root user (uid: 1000)
- Multi-stage builds for minimal attack surface
- Only runtime dependencies included
- Health checks configured for monitoring
- External database and Redis for data persistence
EOF
    
    success "Complete deployment instructions created: docker_deployment_info.md"
}

cleanup() {
    info "Cleaning up local images..."
    
    # Remove local development images to save space
    docker image prune -f >/dev/null 2>&1 || true
    
    success "Cleanup completed"
}

print_summary() {
    echo ""
    if [[ "$BUILD_ALL" == "true" ]]; then
        print_all_summary
    else
        print_single_summary
    fi
}

print_single_summary() {
    echo "🎉 Build and Push Completed Successfully!"
    echo "========================================"
    echo ""
    echo "📦 Image Information:"
    echo "  Registry: GitHub Container Registry"
    echo "  Image: $IMAGE_NAME:$TAG"
    echo "  Platforms: $PLATFORMS"
    echo ""
    echo "🔗 Registry URL:"
    echo "  https://github.com/Sudipta-s-MCPs/todo-app/pkgs/container/smart-todo-*"
    echo ""
    echo "📋 Next Steps:"
    echo "  1. Update portainer-stack.yml to use: $IMAGE_NAME:$TAG"
    echo "  2. Deploy via Portainer on your Synology NAS"
    echo "  3. Verify deployment with health checks"
    echo ""
    echo "📄 Deployment guide: docker_deployment_info.md"
    echo ""
}

print_all_summary() {
    echo "🎉 All Services Build and Push Completed Successfully!"
    echo "===================================================="
    echo ""
    echo "📦 Images Built:"
    echo "  • ${IMAGE_BASE}-backend:$TAG"
    echo "  • ${IMAGE_BASE}-frontend:$TAG"
    echo "  • ${IMAGE_BASE}-admin:$TAG"
    echo "  • ${IMAGE_BASE}-mcp:$TAG"
    echo ""
    echo "🌐 Platforms: $PLATFORMS"
    echo ""
    echo "🔗 Registry URLs:"
    echo "  • https://github.com/Sudipta-s-MCPs/todo-app/pkgs/container/smart-todo-backend"
    echo "  • https://github.com/Sudipta-s-MCPs/todo-app/pkgs/container/smart-todo-frontend"
    echo "  • https://github.com/Sudipta-s-MCPs/todo-app/pkgs/container/smart-todo-admin"
    echo "  • https://github.com/Sudipta-s-MCPs/todo-app/pkgs/container/smart-todo-mcp"
    echo ""
    echo "📋 Next Steps:"
    echo "  1. Use the complete Portainer stack from docker_deployment_info.md"
    echo "  2. Deploy on your Synology NAS via Portainer"
    echo "  3. Verify all services are running with health checks"
    echo ""
    echo "📄 Complete deployment guide: docker_deployment_info.md"
    echo ""
}

# Main execution
main() {
    print_header
    check_prerequisites
    authenticate_registry
    create_builder
    build_and_push
    verify_image
    generate_deployment_instructions
    cleanup
    print_summary
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [SERVICE|TAG|--all] [TAG]"
        echo ""
        echo "Builds and pushes Docker images to GitHub Container Registry"
        echo ""
        echo "Arguments:"
        echo "  SERVICE    'backend' to build backend service"
        echo "             'frontend' to build frontend PWA"
        echo "             'admin' to build admin panel"
        echo "             'mcp' to build MCP server"
        echo "             '--all' to build all services"
        echo "  TAG        Image tag (default: latest)"
        echo ""
        echo "Environment Variables Required:"
        echo "  GITHUB_USERNAME    Your GitHub username"
        echo "  GITHUB_PAT         Your GitHub Personal Access Token"
        echo ""
        echo "Examples:"
        echo "  $0                       # Build backend with 'latest' tag"
        echo "  $0 v1.0.0               # Build backend with 'v1.0.0' tag"
        echo "  $0 frontend             # Build frontend with 'latest' tag"
        echo "  $0 admin v1.0.0         # Build admin panel with 'v1.0.0' tag"
        echo "  $0 mcp                  # Build MCP server with 'latest' tag"
        echo "  $0 --all                # Build ALL services with 'latest' tag"
        echo "  $0 --all v1.0.0         # Build ALL services with 'v1.0.0' tag"
        exit 0
        ;;
    --*|-*)
        if [[ "${1}" != "--all" ]]; then
            error "Unknown option: $1"
            echo "Use $0 --help for usage information"
            exit 1
        fi
        ;;
esac

# Run main function
main "$@"