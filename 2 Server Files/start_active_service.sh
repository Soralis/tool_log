#!/bin/bash

# Define variables
NGINX_CONFIG="/etc/nginx/sites-available/tool_log"
ACTIVE_PORT=""
ACTIVE_SERVICE=""
INACTIVE_SERVICE=""
ACTIVE_APP_DIR=""

# Determine the active port from Nginx configuration
if grep -q 'proxy_pass http://127\.0\.0\.1:8000;' "$NGINX_CONFIG"; then
    ACTIVE_PORT="8000"
    ACTIVE_SERVICE="tool_log_blue.service"
    INACTIVE_SERVICE="tool_log_green.service"
    ACTIVE_APP_DIR="app_blue"
elif grep -q 'proxy_pass http://127\.0\.0\.1:8001;' "$NGINX_CONFIG"; then
    ACTIVE_PORT="8001"
    ACTIVE_SERVICE="tool_log_green.service"
    INACTIVE_SERVICE="tool_log_blue.service"
    ACTIVE_APP_DIR="app_green"
else
    echo "No active port found in Nginx configuration. Exiting."
    exit 1
fi

echo "Active service detected: $ACTIVE_SERVICE"

# Update static file location in Nginx to point to active deployment
sudo sed -i "s|alias /home/logdeviceserver/tool_log/app_[bg][lr][eu][ee]n/app/static/;|alias /home/logdeviceserver/tool_log/$ACTIVE_APP_DIR/app/static/;|" "$NGINX_CONFIG"

# Reload Nginx to apply changes
sudo nginx -t && sudo systemctl reload nginx

# Start the active service
sudo systemctl start "$ACTIVE_SERVICE"
sudo systemctl enable "$ACTIVE_SERVICE"

# Stop and disable the inactive service
sudo systemctl stop "$INACTIVE_SERVICE"
sudo systemctl disable "$INACTIVE_SERVICE"

echo "Started $ACTIVE_SERVICE and stopped $INACTIVE_SERVICE"
echo "Updated Nginx to serve static files from $ACTIVE_APP_DIR"
