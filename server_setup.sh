#!/bin/bash
set -e

# 1. Update and install packages
echo "Updating package lists and installing prerequisites..."
sudo apt-get update -y
sudo apt-get install -y nginx python3-venv wayfire chromium-browser

# Enable console autologin and launch Wayfire on tty1
sudo raspi-config nonint do_boot_behaviour B2
sudo -u pi bash -c 'cat >> /home/pi/.bash_profile << EOF
[[ -z \$WAYLAND_DISPLAY && \$XDG_VTNR -eq 1 ]] && exec wayfire
EOF'

# 2. Configure pi-user crontab for deploy and weekly reboot
echo "Configuring crontab for check_github and weekly reboot..."
(crontab -l 2>/dev/null | grep -v 'check_github.sh'; \
 echo "*/5 * * * * /bin/bash /home/pi/tool_log/check_github.sh >> /var/log/deploy.log 2>&1"; \
 echo "0 0 * * 0 /sbin/shutdown -r now") | crontab -

# 3. Create internet connection check script
echo "Creating internet_check.sh..."
cat > /home/pi/internet_check.sh << 'EOF'
#!/bin/bash
LOG=/var/log/internet_check.log
TARGET=8.8.8.8
if ! ping -c1 $TARGET > /dev/null; then
  echo "$(date): Ping failed, restarting dhcpcd" >> $LOG
  sudo systemctl restart dhcpcd
else
  echo "$(date): Ping OK" >> $LOG
fi
EOF
chmod +x /home/pi/internet_check.sh

# 4. Add internet_check to crontab
echo "Adding internet_check to crontab..."
(crontab -l 2>/dev/null | grep -v 'internet_check.sh'; \
 echo "* * * * * /bin/bash /home/pi/internet_check.sh >> /var/log/internet_check.log 2>&1") | crontab -

# Configure Wayfire autostart for Chromium kiosk
sudo -u pi mkdir -p /home/pi/.config
sudo -u pi bash -c 'cat > /home/pi/.config/wayfire.ini << EOF
[core]
exec = chromium-browser --noerrdialogs --disable-infobars --incognito --kiosk http://localhost/dashboard/requests
EOF'

# 6. Create nginx site configuration for blue-green deployment
echo "Writing nginx site config..."
sudo bash -c 'cat > /etc/nginx/sites-available/tool_log << EOF
server {
    listen 80;
    server_name _;
    location / {
        proxy_pass http://127.0.0.1:8000;
        include /etc/nginx/proxy_params;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    location /monitoring/ws {
        proxy_pass http://127.0.0.1:8000;
        include /etc/nginx/proxy_params;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    error_log /var/log/nginx/tool_log_error.log;
    access_log /var/log/nginx/tool_log_access.log;
}
EOF'
sudo ln -sf /etc/nginx/sites-available/tool_log /etc/nginx/sites-enabled/tool_log
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -s reload

echo "Server setup complete. Please reboot to start Weston and apply all changes."
