# Multi-stage build for Smart-ToDo admin panel
FROM node:20-alpine as builder

WORKDIR /app

# Accept build arguments
ARG VITE_API_URL

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Set environment variable for build
ENV VITE_API_URL=$VITE_API_URL

# Build the application
RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

# Install serve to run the application
RUN npm install -g serve

# Create non-root user with a different UID
RUN adduser -D -u 1001 appuser

# Copy built application from builder (Vite outputs to dist)
COPY --from=builder --chown=appuser:appuser /app/dist ./dist

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 3000

# Serve the application
CMD ["serve", "-s", "dist", "-l", "3000"]