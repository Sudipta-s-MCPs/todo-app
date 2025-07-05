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

# Create custom nginx configuration for SPA
RUN echo 'server { \
    listen 80; \
    server_name localhost; \
    root /usr/share/nginx/html; \
    index index.html; \
    \
    # Handle client-side routing \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
    \
    # Security headers \
    add_header X-Frame-Options DENY always; \
    add_header X-Content-Type-Options nosniff always; \
    add_header X-XSS-Protection "1; mode=block" always; \
    \
    # Gzip compression \
    gzip on; \
    gzip_types text/css application/javascript application/json image/svg+xml; \
    gzip_comp_level 9; \
    \
    # Cache static assets \
    location ~* \.(js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2)$ { \
        expires 1y; \
        add_header Cache-Control "public, immutable"; \
    } \
}' > /etc/nginx/conf.d/default.conf

# Create non-root user for security
RUN adduser -D -s /bin/false -u 1001 nginx-user && \
    chown -R nginx-user:nginx-user /usr/share/nginx/html && \
    chown -R nginx-user:nginx-user /var/cache/nginx && \
    chown -R nginx-user:nginx-user /var/log/nginx && \
    chown -R nginx-user:nginx-user /etc/nginx/conf.d && \
    touch /run/nginx.pid && \
    chown nginx-user:nginx-user /run/nginx.pid

# Switch to non-root user
USER nginx-user

# Expose port 80 (nginx default)
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]