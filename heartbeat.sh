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
SERVER_IP="10.0.0.148:8000" # for home office, with port (no nginx)

# Heartbeat function
heartbeat() {
  echo "Sending heartbeat to http://${SERVER_IP}/unprotected/heartbeat"

  curl_data()
  {
    cat<<EOF
  {
    "device_token": "$DEVICE_NAME"
  }
EOF
  }
  
  # Use POST method with device_token parameter
  RESPONSE=$(curl -s -X POST "http://${SERVER_IP}/unprotected/heartbeat" \
    -H "Content-Type: application/json" \
    -d "$(curl_data)" )
  
  echo "Response: $RESPONSE"
  
  if echo "$RESPONSE" | grep -q "success"; then
    FAILED_PINGS=0
    echo "$(date): Heartbeat successful. Failed pings reset to 0." >> /tmp/heartbeat_status.log
    echo "Heartbeat successful"
  else
    FAILED_PINGS=$((FAILED_PINGS + 1))
    echo "$(date): Heartbeat failed. Failed pings: $FAILED_PINGS" >> /tmp/heartbeat_status.log
    echo "Heartbeat failed"
    if [ "$FAILED_PINGS" -ge 5 ]; then
      echo "$(date): No heartbeat for 5 minutes. Rebooting..." >> /tmp/heartbeat_status.log
      echo "No heartbeat for 5 minutes. Rebooting..."
      sudo reboot
    fi
  fi
}

# Initialize failed pings counter
FAILED_PINGS=0

# Run Heartbeat
heartbeat
