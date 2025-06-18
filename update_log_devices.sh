#!/bin/bash
set -euo pipefail

# Script to update all connected log devices by running log_device_setup.sh on each device

# Path to log_device_setup.sh on the remote devices
REMOTE_SCRIPT_PATH="/home/pi/log_device_setup.sh"

# SSH username for the Raspberry Pi devices
SSH_USER="pi"

# SSH key path (if using key-based authentication)
SSH_KEY_PATH="/home/pi/.ssh/id_rsa_log_devices"

# SSH options
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=5"
DEPLOY_ROOT="$( cd "$(dirname "$0")" && pwd )"
export DEPLOY_ROOT

# Arrays to store update status
successful_updates=()
failed_updates=()

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Temporary directory for status files from parallel jobs
STATUS_DIR=$(mktemp -d)
# Ensure cleanup of the status directory on exit
trap 'rm -rf -- "$STATUS_DIR"' EXIT

# Function to process a single device update
# This function will be run in the background for each device
process_device_update() {
    local DEVICE_NAME="$1"
    local IP_ADDRESS="$2"
    local DEVICE_INFO="$DEVICE_NAME ($IP_ADDRESS)"
    # Using a subshell for log prefixing to avoid conflicts if log function is complex
    # and to ensure output is associated with this specific job.
    # Alternatively, pass PID to log function or prefix echo directly.
    local LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')] [Job for $DEVICE_NAME]"

    echo "$LOG_PREFIX Processing device..."

    if ping -c 1 -W 2 "$IP_ADDRESS" > /dev/null 2>&1; then
        echo "$LOG_PREFIX Device is reachable. Attempting to update..."
        
        # Ensure TMP_SCRIPT is accessible; it's defined in the main script
        if scp $SSH_OPTS -i "$SSH_KEY_PATH" "$TMP_SCRIPT" "${SSH_USER}@${IP_ADDRESS}:$REMOTE_SCRIPT_PATH"; then
            echo "$LOG_PREFIX Script copied successfully."
            
            if ssh $SSH_OPTS -i "$SSH_KEY_PATH" "${SSH_USER}@${IP_ADDRESS}" "chmod +x $REMOTE_SCRIPT_PATH && $REMOTE_SCRIPT_PATH"; then
                echo "$LOG_PREFIX Update successful."
                echo "SUCCESS:$DEVICE_INFO" > "$STATUS_DIR/status_${DEVICE_NAME}_${IP_ADDRESS//./_}.txt" # Sanitize IP for filename
            else
                echo "$LOG_PREFIX Failed to execute script on device."
                echo "FAILURE:$DEVICE_INFO - Reason: Script execution failed" > "$STATUS_DIR/status_${DEVICE_NAME}_${IP_ADDRESS//./_}.txt"
            fi
        else
            echo "$LOG_PREFIX Failed to copy script to device."
            echo "FAILURE:$DEVICE_INFO - Reason: SCP failed" > "$STATUS_DIR/status_${DEVICE_NAME}_${IP_ADDRESS//./_}.txt"
        fi
    else
        echo "$LOG_PREFIX Device is not reachable (ping failed)."
        echo "FAILURE:$DEVICE_INFO - Reason: Not reachable (ping failed)" > "$STATUS_DIR/status_${DEVICE_NAME}_${IP_ADDRESS//./_}.txt"
    fi
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

env_path = os.path.join(deploy_root, '.env')
config = dotenv_values(env_path)
DB_URL = config.get('DATABASE_URL')
if not DB_URL:
    raise ValueError(f"DATABASE_URL not set in {env_path}. Possible values: {config.keys()}")

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
log "Devices:\n$DEVICES"

# Copy log_device_setup.sh to a temporary location
TMP_SCRIPT="/tmp/log_device_setup.sh"
cp "$DEPLOY_ROOT/log_device_setup.sh" "$TMP_SCRIPT"
chmod +x $TMP_SCRIPT

log "Starting parallel updates for all devices..."
# Process each device in parallel
while IFS='|' read -r DEVICE_NAME IP_ADDRESS; do
    # Export variables needed by the background function
    export SSH_OPTS SSH_KEY_PATH TMP_SCRIPT SSH_USER REMOTE_SCRIPT_PATH STATUS_DIR
    process_device_update "$DEVICE_NAME" "$IP_ADDRESS" &
done <<< "$DEVICES"

log "All update jobs launched. Waiting for completion..."
wait # Wait for all background jobs to finish

log "All update jobs completed. Aggregating results..."

# Aggregate results from status files
for status_file in "$STATUS_DIR"/status_*.txt; do
    if [ -f "$status_file" ]; then # Check if file exists (in case no devices or other issues)
        read -r line < "$status_file"
        if [[ "$line" == SUCCESS:* ]]; then
            successful_updates+=("${line#SUCCESS:}")
        elif [[ "$line" == FAILURE:* ]]; then
            failed_updates+=("${line#FAILURE:}")
        fi
    fi
done

# Clean up temporary script file (status dir is cleaned by trap)
rm "$TMP_SCRIPT"

log "----------------------------------------"
log "Update process completed."
log "SUMMARY OF UPDATES:"
log "----------------------------------------"

if [ ${#successful_updates[@]} -gt 0 ]; then
    log "Successful Updates:"
    # Sort the arrays for consistent output
    IFS=$'\n' sorted_successful=($(sort <<<"${successful_updates[*]}"))
    unset IFS
    for device in "${sorted_successful[@]}"; do
        log "  - $device"
    done
else
    log "No devices were updated successfully."
fi

log "" # Empty line for spacing

if [ ${#failed_updates[@]} -gt 0 ]; then
    log "Failed Updates:"
    # Sort the arrays for consistent output
    IFS=$'\n' sorted_failed=($(sort <<<"${failed_updates[*]}"))
    unset IFS
    for device in "${sorted_failed[@]}"; do
        log "  - $device"
    done
else
    log "No devices failed to update."
fi
log "----------------------------------------"
