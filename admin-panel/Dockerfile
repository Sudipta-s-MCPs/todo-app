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

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Remove default nginx content
RUN rm -rf /usr/share/nginx/html/*

# Copy built application to nginx html directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Create non-root user and necessary directories
RUN adduser -D -s /bin/false -u 1001 nginx-user && \
    # Create temp directories that nginx needs
    mkdir -p /tmp/client_body_temp /tmp/proxy_temp /tmp/fastcgi_temp /tmp/uwsgi_temp /tmp/scgi_temp && \
    # Set ownership
    chown -R nginx-user:nginx-user /usr/share/nginx/html && \
    chown -R nginx-user:nginx-user /var/cache/nginx && \
    chown -R nginx-user:nginx-user /tmp/client_body_temp && \
    chown -R nginx-user:nginx-user /tmp/proxy_temp && \
    chown -R nginx-user:nginx-user /tmp/fastcgi_temp && \
    chown -R nginx-user:nginx-user /tmp/uwsgi_temp && \
    chown -R nginx-user:nginx-user /tmp/scgi_temp && \
    # Make sure nginx can write logs
    touch /var/run/nginx.pid && \
    chown nginx-user:nginx-user /var/run/nginx.pid

# Switch to non-root user
USER nginx-user

# Expose port 3000 (as configured in nginx.conf)
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Override entrypoint to skip default scripts
ENTRYPOINT ["nginx"]

# Start nginx
CMD ["-g", "daemon off;"]