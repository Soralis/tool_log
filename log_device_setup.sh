#!/bin/bash

# Set server IP address
SERVER_IP="10.0.36.130"
# SERVER_IP="10.0.0.38:8000" # for home office
# read -p "Enter the Server IP Address: " SERVER_IP

# WLAN configuration - Edit these values to change network settings
WLAN_SSID="Non_IoT"
WLAN_PASSWORD="M@croBlank479"
CONFIGURE_WLAN=false  # Set to true to apply WLAN configuration

# Configure WLAN if enabled
if [ "$CONFIGURE_WLAN" = true ]; then
  echo "Configuring WLAN with SSID: $WLAN_SSID"
  
  # Create wpa_supplicant configuration
  sudo bash -c "cat > /etc/wpa_supplicant/wpa_supplicant.conf << EOF
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=DE

network={
    ssid=\"$WLAN_SSID\"
    psk=\"$WLAN_PASSWORD\"
    key_mgmt=WPA-PSK
}
EOF"

  # Restart networking to apply changes
  echo "Restarting networking services..."
  sudo systemctl restart dhcpcd
  sudo wpa_cli -i wlan0 reconfigure
  
  echo "WLAN configuration updated. New settings will be applied."
fi

# Get Raspberry Pi's MAC address for device name
# Using /sys/class/net/wlan0/address is more reliable than parsing ifconfig output
# and avoids issues with ifconfig not being in PATH for non-interactive SSH sessions.
DEVICE_NAME=$(cat /sys/class/net/wlan0/address)

echo "Using Device MAC Address: $DEVICE_NAME"

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

# Delete uneccessary installs
echo "Cleaning up"
sudo apt autoremove -y

# Setup SSH access for the control machine
echo "Setting up SSH authorized key for logdeviceserver user..."
SSH_PUBLIC_KEY="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCpuGOFaL3W1YAc5bQVVg68zlUKAwL6mLqaVgVNOrRgEkjH+rHuk+1wzGUWgosBenwGBbnl3aWcDGj6XNavJ4EsUbFIdj7JqwieRiuMcOvIeTB+nVvG4vT982MFoXzf0oqXCGMDB5zRkG3QjgcpIvOyTDRvm3sWCs8NE7ALJCAnIcvAjaC2AvrlJG9wHj6Lf5iIpA+3YoIEbWZx2XGbAZ9j7fHa9BLHz3xWTo8VkPdIiqJkSz/5mR4mLIn0cHuKZMqBcft5rckFNU4+NLkw/5vV+j5AMFRZZplmlNQJG/7lHOANgtZGguZz4wOHY2rFqCCB/vBr3UmiVOqOfFGbmwdMV4PDYHkvuBlh7/ZXxjAT93R97n1eis4rUBQMZNTxozuP0YlOkDx9sKqi270EiY4flurGaxd4p06VwfSM/7xIrm0hFF057ywPVm19+c3yC7QjV06ke8hHgNvbXFJSVW5ZJHMmLTla7HgfvWqfT4lcFJsZ3sbV3v7HAjjydfQaX/KtAwUE0FARoHz1pw7ol2CQ4xLQGI+QloUmMn5vfkavhiTtSuGHIe0GWCx9vdE3akH8iSBpwOIxmyK3PWBN8+TQWJjMfLdNcPdl3Vtfw0sOq8Oc0YsHfVy3Tr/dH4HPKQanAoVPA66I52Vq6YyD/zyPc3bTuBY5YMd/boIIacHuuQ== log_devices_key"

# Ensure .ssh directory exists and has correct permissions
# This script is run as the 'pi' user, so ~ will resolve to /home/pi
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Add the public key to authorized_keys if it's not already there
# and ensure authorized_keys has correct permissions
touch ~/.ssh/authorized_keys # Ensure the file exists before grep/tee
if ! grep -qF "$SSH_PUBLIC_KEY" ~/.ssh/authorized_keys; then
    echo "$SSH_PUBLIC_KEY" >> ~/.ssh/authorized_keys
    echo "Public key added to ~/.ssh/authorized_keys"
else
    echo "Public key already exists in ~/.ssh/authorized_keys"
fi
chmod 600 ~/.ssh/authorized_keys
echo "SSH key setup completed."

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
  --disable-pinch \
  --touch-events=enabled \
  --overscroll-history-navigation=0 \
  --disable \$KIOSK_URL
EOF'

# Retrieve heartbeat.sh from GitHub and make it executable
# Ensure pi user can create/own the file, remove if it exists and is root-owned from a previous run
sudo rm -f /home/pi/heartbeat.sh
wget -O /home/pi/heartbeat.sh https://raw.githubusercontent.com/Soralis/tool_log/master/heartbeat.sh
# The file /home/pi/heartbeat.sh should now be owned by the user running this script (assumed to be 'pi').
chmod +x /home/pi/heartbeat.sh # This should now work if run as 'pi'

# Set Openbox environment
echo "Setting Openbox Environment"
sudo bash -c "echo \"export KIOSK_URL=${KIOSK_URL}\" > /etc/xdg/openbox/environment"

# Set SERVER_IP environment variable
echo "Setting SERVER_IP Environment"
sudo bash -c "echo \"export SERVER_IP=${SERVER_IP}\" > /etc/environment"

# Add cron job to run heartbeat.sh every minute
echo "Adding cron job for heartbeat"
# Remove any existing heartbeat.sh entries first
(crontab -l 2>/dev/null | grep -v "heartbeat.sh") | crontab -
# Add the new entry
(crontab -l 2>/dev/null; echo "* * * * * /home/pi/heartbeat.sh") | crontab -
echo "Heartbeat.sh installed and cron job added"

# Insert Start conditions to bash_profile
echo "Setting Start Conditions"
touch /home/pi/.bash_profile
sudo bash -c 'echo "[[ -z \$DISPLAY && \$XDG_VTNR -eq 1 ]] && startx -- -nocursor" > /home/pi/.bash_profile'

# Reboot the Raspberry Pi
sudo reboot
