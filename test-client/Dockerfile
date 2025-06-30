# Test client Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd -m -u 1000 testuser && chown -R testuser:testuser /app

# Copy test code
COPY --chown=testuser:testuser . .

# Switch to non-root user
USER testuser

# Run tests
CMD ["python", "-m", "pytest", "-v", "--tb=short"]