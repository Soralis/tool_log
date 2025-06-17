#!/bin/bash
set -euo pipefail

# Script to update all connected log devices by running log_device_setup.sh on each device

# Path to log_device_setup.sh on the remote devices
REMOTE_SCRIPT_PATH="/home/pi/log_device_setup.sh"

# SSH username for the Raspberry Pi devices
SSH_USER="pi"

# SSH key path (if using key-based authentication)
SSH_KEY_PATH="/home/pi/.ssh/id_rsa"

# SSH options
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=5"
DEPLOY_ROOT="$( cd "$(dirname "$0")" && pwd )"
export DEPLOY_ROOT

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}
# Activate virtual environment if it exists
VENV_PATH="$DEPLOY_ROOT/venv/bin/activate"
if [ -f "$VENV_PATH" ]; then
    # shellcheck disable=SC1091
    source "$VENV_PATH"
    log "Activated virtual environment at $VENV_PATH"
else
    log "Virtual environment not found at $VENV_PATH. Continuing without it."
fi


# Get list of active log devices with IP addresses
log "Retrieving list of active log devices..."

# Use Python to query the database and get the list of active devices
DEVICES=$(python3 - <<EOF
import os, sys
deploy_root = os.environ.get("DEPLOY_ROOT")
if not deploy_root:
    deploy_root = os.getcwd()
print("Deploy root:", deploy_root)
sys.path.insert(0, deploy_root)
from sqlmodel import Session, select, create_engine
from app.models.log_device import LogDevice
import os
from dotenv import dotenv_values

DB_URL = dotenv_values('.env').get('DATABASE_URL')
if not DB_URL:
    raise ValueError(f"DATABASE_URL not set. Possible values: {dotenv_values('.env')}")

# Create database engine
engine = create_engine(DB_URL)

# Query active devices with IP addresses
with Session(engine) as session:
    query = select(LogDevice).where(LogDevice.active == True, LogDevice.ip_address != None)
    devices = session.exec(query).all()
    
    # Print device info in a format that can be parsed by bash
    for device in devices:
        if device.name == "Server":
            continue
        print(f"{device.name}|{device.ip_address}")
EOF
)

if [ -z "$DEVICES" ]; then
    log "No active devices found with IP addresses."
    exit 1
fi

# Count of devices
DEVICE_COUNT=$(echo "$DEVICES" | wc -l)
log "Found $DEVICE_COUNT active devices with IP addresses."

# Copy log_device_setup.sh to a temporary location
TMP_SCRIPT="/tmp/log_device_setup.sh"
cp "$DEPLOY_ROOT/log_device_setup.sh" "$TMP_SCRIPT"
chmod +x $TMP_SCRIPT

# Process each device
while IFS='|' read -r DEVICE_NAME IP_ADDRESS; do
    log "Processing device: $DEVICE_NAME ($IP_ADDRESS)"
    
    # Check if the device is reachable
    if ping -c 1 -W 2 "$IP_ADDRESS" > /dev/null 2>&1; then
        log "Device $DEVICE_NAME is reachable. Attempting to update..."
        
        # Copy the script to the device
        if scp $SSH_OPTS -i "$SSH_KEY_PATH" "$TMP_SCRIPT" "${SSH_USER}@${IP_ADDRESS}:$REMOTE_SCRIPT_PATH"; then
            log "Script copied successfully to $DEVICE_NAME."
            
            # Execute the script on the remote device
            if ssh $SSH_OPTS -i "$SSH_KEY_PATH" "${SSH_USER}@${IP_ADDRESS}" "chmod +x $REMOTE_SCRIPT_PATH && $REMOTE_SCRIPT_PATH"; then
                log "Update successful for device $DEVICE_NAME."
            else
                log "Failed to execute script on device $DEVICE_NAME."
            fi
        else
            log "Failed to copy script to device $DEVICE_NAME."
        fi
    else
        log "Device $DEVICE_NAME is not reachable at $IP_ADDRESS."
    fi
done <<< "$DEVICES"

# Clean up
rm "$TMP_SCRIPT"

log "Update process completed."
