# Ultra-minimal MCP Server Dockerfile - Optimized for size
FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Install minimal runtime dependencies only
RUN apk add --no-cache curl && \
    rm -rf /var/cache/apk/*

# Copy minimal requirements and install
COPY ../requirements-mcp.txt .
RUN pip install --no-cache-dir -r requirements-mcp.txt && \
    rm requirements-mcp.txt

# Create non-root user
RUN adduser -D -u 1000 mcp

# Copy only MCP server code (no full backend)
COPY --chown=mcp:mcp mcp_server/ ./mcp_server/
COPY --chown=mcp:mcp __init__.py .

# Switch to non-root user
USER mcp

# Health check using curl (much lighter than Python requests)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5485/mcp/ || exit 1

# Expose port
EXPOSE 5485

# Start MCP server
CMD ["python", "-m", "mcp_server.server"]