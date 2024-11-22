#!/bin/bash

# Define variables
BASE_DIR="/home/pi/tool_log"
BLUE_DIR="$BASE_DIR/app_blue"
GREEN_DIR="$BASE_DIR/app_green"
NGINX_CONFIG="/etc/nginx/sites-available/tool_log"
REPO_URL="https://github.com/Soralis/tool_log.git"
BRANCH="master"
ACTIVE_PORT=""
NEW_PORT=""
ACTIVE_SERVICE=""
NEW_SERVICE=""
ACTIVE_DIR=""
NEW_DIR=""

REMOTE_COMMIT=""

# Function to check for updates
check_for_updates() {
    cd "$1" || return 1
    LOCAL_COMMIT=$(git rev-parse HEAD)
    if [ -z "$REMOTE_COMMIT" ]; then
	echo "CATCHING GIT"
        git fetch origin "$BRANCH"
        REMOTE_COMMIT=$(git rev-parse origin/$BRANCH)
    fi
    [ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]  # Return 0 if updates are available
}


# Function to send error message
send_error_message() {
    echo "Deployment failed: $1"
    # You can extend this function to send an email or alert
}

echo "Determining the active Service..."

# Determine the active service by checking the Nginx configuration
if grep -q 'proxy_pass http://127\.0\.0\.1:8000;' "$NGINX_CONFIG"; then
    echo "Detected active service on Port 8000" 
    ACTIVE_PORT="8000"
    NEW_PORT="8001"
    ACTIVE_SERVICE="tool_log_blue.service"
    NEW_SERVICE="tool_log_green.service"
    ACTIVE_DIR="$BLUE_DIR"
    NEW_DIR="$GREEN_DIR"
elif grep -q 'proxy_pass http://127\.0\.0\.1:8001;' "$NGINX_CONFIG"; then
    echo "Detected active service on Port 8001"
    ACTIVE_PORT="8001"
    NEW_PORT="8000"
    ACTIVE_SERVICE="tool_log_green.service"
    NEW_SERVICE="tool_log_blue.service"
    ACTIVE_DIR="$GREEN_DIR"
    NEW_DIR="$BLUE_DIR"
else
    send_error_message "Could not determine the active Service from Nginx Configuration."
    exit 1
fi

# Update the non-active directory with the latest code
if [ ! -d "$NEW_DIR" ]; then
    # Clone the repository if the directory doesn't exist
    git clone "$REPO_URL" "$NEW_DIR"
else
    if check_for_updates "$ACTIVE_DIR"; then
	echo "Newer than currently deployed version found, checking innovativity..."
        if ! check_for_updates "$NEW_DIR"; then
	    echo "Not innovative, still broken. Exiting."
	    exit 0
	fi
	echo "Innovative! Commence Deploy of new Version."
    else
    echo "Nothing newer than the current Version. Exiting."
	exit 0
    fi
    cd "$NEW_DIR"
    # Pull the latest changes
    git pull origin $BRANCH
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

# Run database migrations
alembic upgrade head

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
sudo sed -i "s|proxy_pass http://127\.0\.0\.1:$ACTIVE_PORT;|proxy_pass http://127.0.0.1:$NEW_PORT;|" $NGINX_CONFIG
# Also update the WebSocket proxy_pass
sudo sed -i "s|location /monitoring/ws.*{.*proxy_pass http://127\.0\.0\.1:$ACTIVE_PORT;|location /monitoring/ws {\n        proxy_pass http://127.0.0.1:$NEW_PORT;|g" $NGINX_CONFIG
sudo cat /etc/nginx/sites-available/tool_log | grep 'proxy_pass'


# Reload Nginx to apply the changes
sudo nginx -s reload

# Activate New Service
sudo systemctl enable "$NEW_SERVICE"

# Stop the old service
sudo systemctl stop $ACTIVE_SERVICE
sudo systemctl disable "$ACTIVE_SERVICE"


echo "Deployment to $NEW_SERVICE successful. Old service $ACTIVE_SERVICE stopped."

# Optionally, clean up old code or logs
