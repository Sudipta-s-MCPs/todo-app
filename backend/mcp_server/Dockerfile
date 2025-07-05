# Ultra-minimal MCP Server Dockerfile - Optimized for size
FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Install build and runtime dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    linux-headers \
    curl && \
    rm -rf /var/cache/apk/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    rm requirements.txt

# Create non-root user
RUN adduser -D -u 1000 mcp

# Copy only MCP server code
COPY --chown=mcp:mcp ./ ./mcp_server/

# Switch to non-root user
USER mcp

# Health check using curl (much lighter than Python requests)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5485/mcp/ || exit 1

# Expose port
EXPOSE 5485

# Start MCP server
CMD ["python", "-m", "mcp_server.server"]