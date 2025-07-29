#!/bin/bash

# Launch Chromium for Wayland
sleep 3
/usr/bin/chromium-browser --kiosk --ozone-platform=wayland --start-maximized http://10.0.36.130/dashboard/requests &