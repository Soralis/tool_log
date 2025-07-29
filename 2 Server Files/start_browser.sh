#!/bin/bash

# Debug logging
LOG_FILE="/tmp/browser-launch.log"
exec > >(tee -a "$LOG_FILE") 2>&1

# Wait for X and environment
sleep 5
export XDG_RUNTIME_DIR=/run/user/1000
export WAYLAND_DISPLAY=DSI-1

# Set display and disable screen blanking
export DISPLAY=:0
xset s off
xset -dpms
xset s noblank

# Rotate screen
#/usr/local/bin/rotate-screen.sh # gay

# Launch Chromium
chromium-browser \
    --enable-features=UseOzonePlatform \
    --ozone-platform=wayland \
    --kiosk \
    --no-first-run \
    --no-sandbox \
    --disable-pinch \
    --disable-translate \
    --touch-events=enabled \
    --overscroll-history-navigation=0 \
    --app=http://localhost/dashboard/requests \
    --disable-text-selection \
    --blink-settings=disableScrollbars=true
