#!/bin/bash

# Script to debug heartbeat issues on a headless Raspberry Pi
# Run this script via SSH to diagnose problems

echo "===== HEARTBEAT DEBUGGING SCRIPT ====="
echo "Date and time: $(date)"
echo

# Check if heartbeat.sh exists and is executable
echo "1. Checking heartbeat.sh file:"
if [ -f /heartbeat.sh ]; then
    echo "   - heartbeat.sh exists at /heartbeat.sh"
    if [ -x /heartbeat.sh ]; then
        echo "   - heartbeat.sh is executable"
    else
        echo "   - ERROR: heartbeat.sh is NOT executable"
        echo "   - Fixing permissions..."
        sudo chmod +x /heartbeat.sh
    fi
else
    echo "   - ERROR: heartbeat.sh does NOT exist at /heartbeat.sh"
    echo "   - Checking other locations..."
    find / -name "heartbeat.sh" 2>/dev/null
fi

# Check crontab entry
echo
echo "2. Checking crontab entries:"
CRONTAB=$(crontab -l 2>/dev/null)
if echo "$CRONTAB" | grep -q "heartbeat.sh"; then
    echo "   - Crontab entry found:"
    echo "$CRONTAB" | grep "heartbeat.sh"
else
    echo "   - ERROR: No crontab entry for heartbeat.sh found"
    echo "   - Current crontab entries:"
    echo "$CRONTAB"
fi

# Check if curl is installed
echo
echo "3. Checking if curl is installed:"
if command -v curl &> /dev/null; then
    echo "   - curl is installed: $(curl --version | head -n 1)"
else
    echo "   - ERROR: curl is NOT installed"
    echo "   - Installing curl..."
    sudo apt-get update && sudo apt-get install -y curl
fi

# Check network connectivity
echo
echo "4. Checking network connectivity:"
echo "   - IP configuration:"
ifconfig wlan0 | grep -E "inet|ether"
echo
echo "   - Testing connection to server (10.0.0.148):"
ping -c 3 10.0.0.148

# Check server reachability
echo
echo "5. Testing server endpoint:"
SERVER_IP="10.0.0.148:8000"
DEVICE_NAME=$(ifconfig wlan0 | grep ether | awk '{print $2}')
echo "   - Device MAC: $DEVICE_NAME"
echo "   - Testing heartbeat endpoint with curl:"
curl -v "http://${SERVER_IP}/unprotected/heartbeat?device_name=${DEVICE_NAME}" 2>&1

# Check for device token
echo
echo "6. Checking for device token:"
if grep -q "device_token" /heartbeat.sh; then
    echo "   - heartbeat.sh uses device_token"
    TOKEN=$(grep -o 'device_token="[^"]*"' /heartbeat.sh | cut -d'"' -f2)
    if [ -n "$TOKEN" ]; then
        echo "   - Token found: $TOKEN"
    else
        echo "   - ERROR: Token variable exists but no value set"
    fi
else
    echo "   - ERROR: heartbeat.sh doesn't use device_token parameter"
    echo "   - The API endpoint requires a device_token parameter"
fi

# Test manual execution of heartbeat.sh
echo
echo "7. Testing manual execution of heartbeat.sh:"
echo "   - Output from heartbeat.sh:"
bash -x /heartbeat.sh

# Check system logs for cron execution
echo
echo "8. Checking system logs for cron execution:"
echo "   - Last 10 cron-related log entries:"
grep CRON /var/log/syslog | tail -10

echo
echo "===== DEBUGGING COMPLETE ====="
echo "Copy this output and share it for further assistance"
