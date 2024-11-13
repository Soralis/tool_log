#!/bin/bash

# Base URL (IP Address of the Server + First time register)
BASE_URL="http://10.0.36.52:8000/registerDevice"

# Prompt for device name
read -p "Enter the device name: " DEVICE_NAME

# Construct the KIOSK_URL
KIOSK_URL="${BASE_URL}?device_name=${DEVICE_NAME}"

# Enable autologin to command line
sudo raspi-config nonint do_boot_behaviour B2

# Update Raspberry OS
sudo apt-get update -y && sudo apt-get upgrade -y

# Install minimum GUI components
sudo apt-get install --no-install-recommends xserver-xorg x11-xserver-utils xinit openbox -y

# Install Chromium Web browser
sudo apt-get install --no-install-recommends chromium-browser -y

# # Rotate Touch
# sudo mkdir /etc/X11/xorg.conf.d
# sudo cp /usr/share/X11/xorg.conf.d/40-libinput.conf /etc/X11/xorg.conf.d/
# sudo sed -i '/MatchIsTouchscreen "on"/a\        Option "CalibrationMatrix" "0 -1 1 1 0 0 0 0 1"' /etc/X11/xorg.conf.d/40-libinput.conf  # 90 degrees left

# Edit Openbox config
sudo bash -c 'cat << EOF > /etc/xdg/openbox/autostart
# Disable screen blanking/power saving
xset -dpms
xset s off
xset s noblank

# # Rotate Display
# xrandr --output DSI-1 --rotate left

sed -i '"'"'s/"exited_cleanly":false/"exited_cleanly":true/'"'"' ~/.config/chromium/'"'"'Local State'"'"'
sed -i '"'"'s/"exited_cleanly":false/"exited_cleanly":true/; s/"exit_type":"["]+"/"exit_type":"Normal"/"'"'"' ~/.config/chromium/Default/Preferences
chromium-browser --noerrdialogs --disable-infobars --enable-features=OverlayScrollbar --kiosk \$KIOSK_URL --check-for-update-interval=31536000 &
EOF'

# Set Openbox environment
sudo bash -c `echo "export KIOSK_URL=\"${KIOSK_URL}\"" > /etc/xdg/openbox/environment`

# Check if bash_profile exists
if [ -f ~/.bash_profile ]; then
    echo "~/.bash_profile exists, editing it directly."
    sudo bash -c 'cat << EOF >> ~/.bash_profile
[[ -z \$DISPLAY && \$XDG_VTNR -eq 1 ]] && startx -- -nocursor
EOF'
else
    echo "~/.bash_profile does not exist, creating it."
    sudo bash -c 'cat << EOF > ~/.bash_profile
[[ -z \$DISPLAY && \$XDG_VTNR -eq 1 ]] && startx -- -nocursor
EOF'
fi

# Source the ~/.bash_profile
source ~/.bash_profile

# Reboot the Raspberry Pi
sudo reboot