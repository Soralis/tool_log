#!/bin/bash

# Base URL
BASE_URL="http://10.0.36.52:8000/registerDevice"

# Prompt for device name
read -p "Enter the device name: " DEVICE_NAME

# Construct the KIOSK_URL
KIOSK_URL="${BASE_URL}?device_name=${DEVICE_NAME}"

# Set KIOSK_URL in the environment
echo "export KIOSK_URL=\"${KIOSK_URL}\"" >> ~/.bashrc

# Enable autologin to command line
sudo raspi-config nonint do_boot_behaviour B2

# Update and upgrade
sudo apt update -y && sudo apt upgrade -y

# Install necessary packages
sudo apt install --no-install-recommends xserver-xorg x11-xserver-utils xinit openbox chromium-browser xserver-xorg-input-libinput -y

# Configure libinput for touch rotation
sudo mkdir -p /etc/X11/xorg.conf.d
sudo cp /usr/share/X11/xorg.conf.d/40-libinput.conf /etc/X11/xorg.conf.d/
sudo sed -i '/MatchIsTouchscreen "on"/a\        Option "CalibrationMatrix" "0 -1 1 1 0 0 0 0 1"' /etc/X11/xorg.conf.d/40-libinput.conf  # 90 degrees left

# Configure .xinitrc
cat << EOF > ~/.xinitrc
# Source .bashrc to get environment variables
. ~/.bashrc

# Disable screen blanking and power saving
xset -dpms
xset s off
xset s noblank

# Rotate display
xrandr --output DSI-1 --rotate left   # Replace DSI-1 if needed

# Launch Chromium in kiosk mode
chromium-browser --noerrdialogs --disable-infobars --enable-features=OverlayScrollbar --kiosk "\$KIOSK_URL" --check-for-update-interval=31536000 &

# Start and make openbox persist
openbox
exec openbox
EOF

# Start x server on boot
echo "[[ -z \$DISPLAY && \$XDG_VTNR -eq 1 ]] && startx --" >> ~/.bashrc

# Reboot
sudo reboot
