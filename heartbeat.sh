#!/bin/bash

# Get Raspberry Pi's MAC address for device name
DEVICE_NAME=$(ifconfig wlan0 | grep ether | awk '{print $2}')

# Prompt for Base URL from environment variable
SERVER_IP=${SERVER_IP}

# Heartbeat function
heartbeat() {
  ping -c 1 -W 5 http://${SERVER_IP}/unprotected/heartbeat?device_name=${DEVICE_NAME} > /dev/null
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
