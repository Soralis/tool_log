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
# Detect network IP address (from wlan0)
if command -v ip > /dev/null; then
  DEVICE_IP=$(ip -4 addr show wlan0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
elif command -v ifconfig > /dev/null; then
  DEVICE_IP=$(ifconfig wlan0 | grep 'inet ' | awk '{print $2}')
else
  DEVICE_IP=""
fi
if [ -n "$DEVICE_IP" ]; then
  echo "Detected device IP: $DEVICE_IP"
else
  echo "Device IP not detected."
fi

# Set server IP address
SERVER_IP="10.0.36.192"
# SERVER_IP="10.0.0.38:8000" # for home office

# Heartbeat function
heartbeat() {
  echo "Sending heartbeat to http://${SERVER_IP}/unprotected/heartbeat"
  COUNTER_FILE="/tmp/failed_pings.txt"
  if [ -f "$COUNTER_FILE" ]; then
      FAILED_PINGS=$(cat "$COUNTER_FILE")
  else
      FAILED_PINGS=0
  fi

  curl_data()
  {
    cat<<EOF
  {
    "device_token": "$DEVICE_NAME"
  }
EOF
  }
  
  # Use POST method with device_token parameter
  EXTRA_HEADER=""
  if [ -n "$DEVICE_IP" ]; then
      EXTRA_HEADER="-H \"X-Real-IP: $DEVICE_IP\""
  fi
  RESPONSE=$(curl -s --connect-timeout 30 --max-time 60 -X POST "http://${SERVER_IP}/unprotected/heartbeat" \
    -H "Content-Type: application/json" $EXTRA_HEADER \
    -d "$(curl_data)" )
  
  echo "Response: $RESPONSE"
  
  if echo "$RESPONSE" | grep -q "success"; then
    FAILED_PINGS=0
    echo "0" > "$COUNTER_FILE"
    echo "$(date): Heartbeat successful. Failed pings reset to 0." >> /tmp/heartbeat_status.log
    echo "Heartbeat successful"
  else
    FAILED_PINGS=$((FAILED_PINGS + 1))
    echo "$FAILED_PINGS" > "$COUNTER_FILE"
    echo "$(date): Heartbeat failed. Failed pings: $FAILED_PINGS" >> /tmp/heartbeat_status.log
    echo "Heartbeat failed"
    if [ "$FAILED_PINGS" -ge 5 ]; then
      echo "0" > "$COUNTER_FILE"
      echo "$(date): No heartbeat for 5 minutes. Rebooting..." >> /tmp/heartbeat_status.log
      echo "No heartbeat for 5 minutes. Rebooting..."
      sudo reboot
    fi
    if [ "$FAILED_PINGS" -ge 3 ]; then
      echo "0" > "$COUNTER_FILE"
      echo "$(date): No heartbeat for 3 minutes. Restarting WIFI Service..." >> /tmp/heartbeat_status.log
      echo "No heartbeat for 3 minutes. Restarting WIFI Service..."
      sudo ip link set wlan0 down && sleep 2 && sudo ip link set wlan0 up
    fi
    
  fi
}

# Run Heartbeat
heartbeat
