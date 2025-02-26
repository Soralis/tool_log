#!/bin/bash

# Get Raspberry Pi's MAC address for device name
# Try ip command first, fall back to ifconfig if ip is not available
if command -v ip > /dev/null; then
  DEVICE_NAME=$(ip link show wlan0 | grep -o "ether [^ ]*" | cut -d' ' -f2)
elif command -v ifconfig > /dev/null; then
  DEVICE_NAME=$(ifconfig wlan0 | grep ether | awk '{print $2}')
else
  # Last resort: use hostname as device identifier
  DEVICE_NAME=$(hostname)
fi

echo "Using device identifier: $DEVICE_NAME"

# Set server IP address
# SERVER_IP="10.0.36.192"
SERVER_IP="10.0.0.148" # for home office, without port

# Heartbeat function
heartbeat() {
  echo "Sending heartbeat to http://${SERVER_IP}/unprotected/heartbeat"
  
  # Use POST method with device_token parameter
  RESPONSE=$(curl -s -X POST "http://${SERVER_IP}/unprotected/heartbeat" \
    -H "Content-Type: application/json" \
    -d "{\"device_token\": \"${DEVICE_NAME}\"}")
  
  echo "Response: $RESPONSE"
  
  if echo "$RESPONSE" | grep -q "success"; then
    echo "Heartbeat successful"
    FAILED_PINGS=0
  else
    echo "Heartbeat failed"
    FAILED_PINGS=$((FAILED_PINGS + 1))
    if [ "$FAILED_PINGS" -ge 15 ]; then
      echo "No heartbeat for 15 minutes. Rebooting..."
      sudo reboot
    fi
  fi
}

# Initialize failed pings counter
FAILED_PINGS=0

# Heartbeat
heartbeat
