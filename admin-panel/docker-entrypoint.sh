#!/bin/sh
# Admin panel runtime configuration injection script

# Default values
DEFAULT_API_URL="http://localhost:5482/api/v1"

# Use environment variable or default
API_URL="${VITE_API_URL:-$DEFAULT_API_URL}"

# Create runtime config file
cat > /usr/share/nginx/html/config.js <<EOF
window.__RUNTIME_CONFIG__ = {
  API_URL: "$API_URL"
};
EOF

echo "Runtime configuration generated for admin panel:"
echo "API_URL: $API_URL"

# Start nginx
exec nginx -g "daemon off;"