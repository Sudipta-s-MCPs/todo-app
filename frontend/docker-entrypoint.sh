#!/bin/sh
# Frontend runtime configuration injection script

# Default values
DEFAULT_API_URL="http://localhost:5482/api/v1"

# Use environment variable or default
API_URL="${VITE_API_URL:-$DEFAULT_API_URL}"

# Extract base URL for CSP
API_BASE_URL=$(echo "$API_URL" | sed 's|/api/v1.*||')

# Determine WebSocket protocol
if echo "$API_BASE_URL" | grep -q "^https"; then
    WS_PROTOCOL="wss"
else
    WS_PROTOCOL="ws"
fi
WS_URL=$(echo "$API_BASE_URL" | sed "s|^https://|$WS_PROTOCOL://|" | sed "s|^http://|$WS_PROTOCOL://|")

# Create runtime config file
cat > /usr/share/nginx/html/config.js <<EOF
window.__RUNTIME_CONFIG__ = {
  API_URL: "$API_URL"
};
EOF

# Update nginx config with proper CSP
sed -i "s|connect-src 'self' http://localhost:\* ws://localhost:\*|connect-src 'self' $API_BASE_URL $WS_URL http://localhost:* ws://localhost:* https://todo-api.sudiptadhara.in wss://todo-api.sudiptadhara.in|g" /etc/nginx/conf.d/default.conf

echo "Runtime configuration generated:"
echo "API_URL: $API_URL"
echo "CSP updated for: $API_BASE_URL and $WS_URL"

# Start nginx
exec nginx -g "daemon off;"