#!/bin/bash

# Set up environment variables
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export HOME=/home/pi

# Define deploy path
DEPLOY_PATH="/home/pi/tool_log/app_green/deploy.sh"

# Create and set permissions for pip cache directory
sudo mkdir -p /home/pi/.cache/pip
sudo chown -R pi:pi /home/pi/.cache

# Change to home directory to ensure consistent starting point
cd $HOME

if [ -f "$DEPLOY_PATH" ]; then
    echo "Running deploy script..."
    # Ensure deploy script is executable
    sudo chmod 755 "$DEPLOY_PATH"
    # Run as pi user
    sudo -H -u pi bash "$DEPLOY_PATH"
else
    echo "Error: Deploy script not found at $DEPLOY_PATH"
    exit 1