#!/bin/bash

# Prompt for Base URL
read -p "Enter the Server IP Address: " SERVER_IP

# Get Raspberry Pi's CPU serial number for device name
DEVICE_NAME=$(cat /proc/cpuinfo | grep Serial | cut -d ' ' -f 2)
echo "Using Device Serial: $DEVICE_NAME"

# Construct the KIOSK_URL
KIOSK_URL="http://${SERVER_IP}/deviceRegistration?device_name=${DEVICE_NAME}"

# Enable autologin to command line
echo "Enabling Autologin"
sudo raspi-config nonint do_boot_behaviour B2

# Update Raspberry OS
echo "Updating and Upgrading Firmware"
sudo apt-get update -y && sudo apt-get full-upgrade -y

# Install minimum GUI components
echo "Installing Minimum GUI"
sudo apt-get install --no-install-recommends xserver-xorg x11-xserver-utils xinit openbox -y

# Install Chromium Web browser
echo "Installing chromium"
sudo apt-get install --no-install-recommends chromium-browser -y

# Rotate Touch
echo "Rotating Touch Input"
sudo cp /usr/share/X11/xorg.conf.d/40-libinput.conf /etc/X11/xorg.conf.d/
sudo sed -i '/MatchIsTouchscreen "on"/a\        Option "CalibrationMatrix" "0 -1 1 1 0 0 0 0 1"' /etc/X11/xorg.conf.d/40-libinput.conf  # 90 degrees left
# "0 1 0 -1 0 1 0 0 1" = 90 Dregree (right)
# "-1 0 1 0 -1 1 0 0 1" = 180 Dregree (inverted)
# "0 -1 1 1 0 0 0 0 1" = 270 Degree (left)

# Edit Openbox config
echo "Setting OpenBox Autostart"
sudo bash -c 'cat << EOF > /etc/xdg/openbox/autostart
# Enable screen power management
# Standby: 60 seconds, Suspend: never (0), Off: never (0)
xset +dpms
xset dpms 60 0 0

# Rotate Display
xrandr --output DSI-0 --rotate left
xrandr --output DSI-1 --rotate left
xrandr --output DSI-2 --rotate left

# Clear Chromium cache and data
rm -rf ~/.cache/chromium/
rm -rf ~/.config/chromium/Default/Cache/
rm -rf ~/.config/chromium/Default/Code\ Cache/
rm -rf ~/.config/chromium/Default/Service\ Worker/CacheStorage/

sed -i '"'"'s/"exited_cleanly":false/"exited_cleanly":true/'"'"' ~/.config/chromium/'"'"'Local State'"'"'
sed -i '"'"'s/"exited_cleanly":false/"exited_cleanly":true/; s/"exit_type":"[^"]*"/"exit_type":"Normal"/'"'"' ~/.config/chromium/Default/Preferences

# Start Chromium with cache-clearing flags
chromium-browser --noerrdialogs --disable-infobars --enable-features=OverlayScrollbar --incognito --kiosk \
  --disable-application-cache \
  --disable-cache \
  --disable \$KIOSK_URL
EOF'

# Set Openbox environment
echo "Setting Openbox Environment"
sudo bash -c "echo \"export KIOSK_URL=${KIOSK_URL}\" > /etc/xdg/openbox/environment"

# Insert Start conditions to bash_profile
echo "Setting Start Conditions"
touch /home/pi/.bash_profile
sudo bash -c 'echo "[[ -z \$DISPLAY && \$XDG_VTNR -eq 1 ]] && startx -- -nocursor" > /home/pi/.bash_profile'

# Reboot the Raspberry Pi
sudo reboot
