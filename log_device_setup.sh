#!/bin/bash

# Base URL (edit this if the base URL changes)
BASE_URL="http://10.0.36.52:8000/registerDevice"

# Prompt for device name
read -p "Enter the device name: " DEVICE_NAME

# Construct the KIOSK_URL
KIOSK_URL="${BASE_URL}?device_name=${DEVICE_NAME}"


# Update and upgrade
sudo apt update -y && sudo apt upgrade -y

# Install necessary packages
sudo apt install --no-install-recommends xserver-xorg x11-xserver-utils xinit openbox chromium-browser xserver-xorg-input-libinput -y

# Fix Chromium "exited_cleanly" flag (if needed)
# sed -i 's/"exited_cleanly":false/"exited_cleanly":true/' ~/.config/chromium/'Local State'
# sed -i 's/"exited_cleanly":false/"exited_cleanly":true/; s/"exit_type":"["]+"/"exit_type":"Normal"/' ~/.config/chromium/Default/Preferences


# Configure libinput for touch rotation
sudo mkdir -p /etc/X11/xorg.conf.d  # -p creates the directory if it doesn't exist
sudo cp /usr/share/X11/xorg.conf.d/40-libinput.conf /etc/X11/xorg.conf.d/
sudo sed -i '/MatchIsTouchscreen "on"/a\        Option "CalibrationMatrix" "0 -1 1 1 0 0 0 0 1"' /etc/X11/xorg.conf.d/40-libinput.conf   # 90 degrees left rotation. Change as needed.


# Configure .xinitrc (using the dynamically created KIOSK_URL)
cat << EOF > ~/.xinitrc
# Disable screen blanking and power saving
xset -dpms
xset s off
xset s noblank

xrandr --output DSI-1 --rotate left  # Replace DSI-1 if necessary

chromium-browser --noerrdialogs --disable-infobars --enable-features=OverlayScrollbar --kiosk "\$KIOSK_URL" --check-for-update-interval=31536000 & # Note the escaped \$

openbox
exec openbox
EOF

# Enable autologin to command line
sudo raspi-config nonint do_boot_behaviour B2

# Configure .bash_profile to start X
cat << EOF > ~/.bash_profile
[[ -z \$DISPLAY && \$XDG_VTNR -eq 1 ]] && startx -- -nocursor
EOF


# Reboot
sudo reboot