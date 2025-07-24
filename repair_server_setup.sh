#!/bin/bash
set -e

# 1. Remove any touchscreen calibration matrix lines
if [ -f /etc/X11/xorg.conf.d/40-libinput.conf ]; then
  echo "Removing touch calibration entries..."
  sudo sed -i '/CalibrationMatrix/d' /etc/X11/xorg.conf.d/40-libinput.conf
fi

# 2. Remove any xrandr rotation commands from Openbox autostart
if [ -f /etc/xdg/openbox/autostart ]; then
  echo "Removing xrandr rotation commands..."
  sudo sed -i '/xrandr --output .* --rotate/d' /etc/xdg/openbox/autostart
fi

# 3. Overwrite Openbox autostart to launch Chromium in kiosk mode
echo "Writing new Openbox autostart..."
sudo bash -c 'cat > /etc/xdg/openbox/autostart << EOF
# Start Chromium in kiosk mode on local dashboard
chromium-browser --noerrdialogs --disable-infobars --incognito --kiosk http://localhost/dashboard/requests
EOF'

# 4. Update Openbox environment with local kiosk URL
echo "Setting KIOSK_URL in Openbox environment..."
sudo bash -c 'echo "export KIOSK_URL=http://localhost/dashboard/requests" > /etc/xdg/openbox/environment'

# 5. Ensure SERVER_IP is set to localhost in /etc/environment
echo "Updating SERVER_IP in /etc/environment..."
sudo sed -i '/^export SERVER_IP/d' /etc/environment
sudo bash -c 'echo "export SERVER_IP=localhost" >> /etc/environment'

# 6. Remove heartbeat cron job for server
echo "Removing heartbeat cron job from crontab..."
(crontab -l 2>/dev/null | grep -v 'heartbeat.sh') | crontab -


echo "Repair script completed. Please reboot the server to apply all changes."
