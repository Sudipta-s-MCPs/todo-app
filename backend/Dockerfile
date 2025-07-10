# Multi-stage build for Smart-ToDo backend - Full features with Debian
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    build-essential \
    && pip install --upgrade pip \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy consolidated requirements
COPY requirements.txt .
# Create a filtered requirements file for production
RUN grep -v -E "^(pytest|black|flake8|mypy|faker|rich|asyncio-mqtt)" requirements.txt | grep -v "^#" | grep -v "^$" > requirements-filtered.txt && \
    pip install --no-cache-dir -r requirements-filtered.txt

# Production stage - Debian slim for full compatibility
FROM python:3.11-slim

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN adduser --disabled-password --uid 1001 --gecos "" appuser

# Copy only necessary application code (exclude dev files)
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser scripts/ ./scripts/
COPY --chown=appuser:appuser mcp_server/ ./mcp_server/
COPY --chown=appuser:appuser alembic.ini .

# Make startup script executable
RUN chmod +x scripts/start.sh

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["sh", "./scripts/start.sh"]