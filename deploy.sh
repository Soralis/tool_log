#!/bin/bash

# Define variables
BASE_DIR="/home/pi/tool_log"
BLUE_DIR="$BASE_DIR/app_blue"
GREEN_DIR="$BASE_DIR/app_green"
NGINX_CONFIG="/etc/nginx/sites-available/tool_log"
ACTIVE_PORT=""
NEW_PORT=""
ACTIVE_SERVICE=""
NEW_SERVICE=""
ACTIVE_DIR=""
NEW_DIR=""

# Function to send error message
send_error_message() {
    echo "Deployment failed: $1"
    # You can extend this function to send an email or alert
}

# Determine the active service by checking the Nginx configuration
if grep -q 'server 127.0.0.1:8000;' $NGINX_CONFIG; then
    ACTIVE_PORT="8000"
    NEW_PORT="8001"
    ACTIVE_SERVICE="tool_log_blue.service"
    NEW_SERVICE="tool_log_green.service"
    ACTIVE_DIR="$BLUE_DIR"
    NEW_DIR="$GREEN_DIR"
else
    ACTIVE_PORT="8001"
    NEW_PORT="8000"
    ACTIVE_SERVICE="tool_log_green.service"
    NEW_SERVICE="tool_log_blue.service"
    ACTIVE_DIR="$GREEN_DIR"
    NEW_DIR="$BLUE_DIR"
fi

echo "Active service: $ACTIVE_SERVICE on port $ACTIVE_PORT"
echo "Deploying to: $NEW_SERVICE on port $NEW_PORT"

# Update the non-active directory with the latest code
if [ ! -d "$NEW_DIR" ]; then
    # Clone the repository if the directory doesn't exist
    git clone https://your-git-repo-url.git "$NEW_DIR"
else
    # Pull the latest changes
    git -C "$NEW_DIR" pull
fi

# Navigate to the new directory
cd "$NEW_DIR"

# Activate the virtual environment or create it if it doesn't exist
if [ ! -d "venv" ]; then
    python3.13 -m venv venv
fi
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Deactivate the virtual environment
deactivate

# Start the new service
sudo systemctl start $NEW_SERVICE

# Wait for a few seconds to allow the service to start
sleep 5

# Check if the new service is running
if ! systemctl is-active --quiet $NEW_SERVICE; then
    send_error_message "New service $NEW_SERVICE failed to start."
    exit 1
fi

# Optionally perform a health check on the new service
HEALTH_CHECK_URL="http://127.0.0.1:$NEW_PORT/health"

if ! curl --silent --fail "$HEALTH_CHECK_URL" > /dev/null; then
    send_error_message "Health check failed for $NEW_SERVICE."
    sudo systemctl stop $NEW_SERVICE
    exit 1
fi

# Update Nginx configuration to point to the new service
sudo sed -i "s/server 127.0.0.1:$ACTIVE_PORT;/server 127.0.0.1:$NEW_PORT;/" $NGINX_CONFIG

# Reload Nginx to apply the changes
sudo nginx -s reload

# Stop the old service
sudo systemctl stop $ACTIVE_SERVICE

echo "Deployment to $NEW_SERVICE successful. Old service $ACTIVE_SERVICE stopped."

# Optionally, clean up old code or logs
