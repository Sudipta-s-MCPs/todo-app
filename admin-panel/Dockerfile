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

# Production stage - Static file serving with nginx
FROM nginx:alpine

# Remove default nginx config and website
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/*

# Copy built application to nginx html directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create non-root user for security
RUN adduser -D -u 1001 appuser && \
    chown -R appuser:appuser /usr/share/nginx/html && \
    chown -R appuser:appuser /var/cache/nginx && \
    chown -R appuser:appuser /var/log/nginx && \
    chown -R appuser:appuser /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R appuser:appuser /var/run/nginx.pid

# Switch to non-root user
USER appuser

# Expose port 80 (nginx default)
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]