# Docker Image Deployment Information

## Image Details
- **Image**: `ghcr.io/sudipta-s-mcps/smart-todo-mcp:latest`
- **Platforms**: linux/amd64,linux/arm64
- **Registry**: GitHub Container Registry (ghcr.io)
- **Build Date**: 2025-07-05 07:21:05 UTC

## Pull Command
```bash
docker pull ghcr.io/sudipta-s-mcps/smart-todo-mcp:latest
```

## Portainer Stack Usage
Update your `portainer-stack.yml` to use this image:

```yaml
services:
  smart-todo-service:
    image: ghcr.io/sudipta-s-mcps/smart-todo-mcp:latest
    # ... rest of your configuration
```

## Security Notes
- Image runs as non-root user (uid: 1000)
- Multi-stage build for minimal attack surface
- Only runtime dependencies included in final image
- Health checks configured for monitoring

## Verification
```bash
# Check image layers
docker history ghcr.io/sudipta-s-mcps/smart-todo-mcp:latest

# Test health endpoint (backend only)
curl http://localhost:8000/health
```
