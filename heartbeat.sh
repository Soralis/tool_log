#!/bin/bash

# Get Raspberry Pi's MAC address for device name
DEVICE_NAME=$(ifconfig wlan0 | grep ether | awk '{print $2}')

# Set server IP address
SERVER_IP="10.0.36.192"
# SERVER_IP="10.0.0.38:8000" # for home office

# Heartbeat function
heartbeat() {
  curl -s -o /dev/null -w "%{http_code}" "http://${SERVER_IP}/unprotected/heartbeat?device_name=${DEVICE_NAME}" | grep -q "200"
  if [ $? -eq 0 ]; then
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
