#!/bin/bash

# Script to update all connected log devices by running log_device_setup.sh on each device

# Database connection details
DB_USER="pi"
DB_NAME="tool_log"
DB_HOST="localhost"

# Path to log_device_setup.sh on the remote devices
REMOTE_SCRIPT_PATH="/home/pi/log_device_setup.sh"

# SSH username for the Raspberry Pi devices
SSH_USER="pi"

# SSH key path (if using key-based authentication)
SSH_KEY_PATH="/home/pi/.ssh/id_rsa"

# SSH options
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=5"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Get list of active log devices with IP addresses
log "Retrieving list of active log devices..."

# Use Python to query the database and get the list of active devices
DEVICES=$(python3 - <<EOF
import os, sys
cwd = os.getcwd()
print("Current working directory:", cwd)
sys.path.insert(0, cwd)
from sqlmodel import Session, select, create_engine
from app.models import LogDevice

# Create database engine
engine = create_engine(f"postgresql://${DB_USER}@${DB_HOST}/${DB_NAME}")

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
cp log_device_setup.sh $TMP_SCRIPT
chmod +x $TMP_SCRIPT

# Process each device
echo "$DEVICES" | while IFS='|' read -r DEVICE_NAME IP_ADDRESS; do
    log "Processing device: $DEVICE_NAME ($IP_ADDRESS)"
    
    # Check if the device is reachable
    if ping -c 1 -W 2 $IP_ADDRESS > /dev/null 2>&1; then
        log "Device $DEVICE_NAME is reachable. Attempting to update..."
        
        # Copy the script to the device
        scp $SSH_OPTS -i $SSH_KEY_PATH $TMP_SCRIPT ${SSH_USER}@${IP_ADDRESS}:$REMOTE_SCRIPT_PATH
        
        if [ $? -eq 0 ]; then
            log "Script copied successfully to $DEVICE_NAME."
            
            # Execute the script on the remote device
            ssh $SSH_OPTS -i $SSH_KEY_PATH ${SSH_USER}@${IP_ADDRESS} "chmod +x $REMOTE_SCRIPT_PATH && $REMOTE_SCRIPT_PATH"
            
            if [ $? -eq 0 ]; then
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
done

# Clean up
rm $TMP_SCRIPT

log "Update process completed."
