# Multi-stage build for Smart-ToDo admin panel
FROM node:20-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

# Install serve to run the application
RUN npm install -g serve

# Create non-root user
RUN adduser -D -u 1000 appuser

# Copy built application from builder
COPY --from=builder --chown=appuser:appuser /app/build ./build

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 3000

# Serve the application
CMD ["serve", "-s", "build", "-l", "3000"]