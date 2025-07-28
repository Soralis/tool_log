#!/bin/bash
set -e

LOG_USER="logdeviceserver"
REPO_URL="https://github.com/Soralis/tool_log.git"
BLUE_DIR="/home/$LOG_USER/tool_log/app_blue"
GREEN_DIR="/home/$LOG_USER/tool_log/app_green"

# 1. Install prerequisites
echo "Updating package lists and installing prerequisites..."
sudo apt-get update -y
sudo apt-get install -y git nginx python3-venv wayfire chromium-browser

# 2. Clone tool_log repository twice (blue/green)
echo "Cloning tool_log repository into blue and green directories..."
sudo rm -rf "$BLUE_DIR" "$GREEN_DIR"
sudo -u $LOG_USER git clone "$REPO_URL" "$BLUE_DIR"
sudo -u $LOG_USER git clone "$REPO_URL" "$GREEN_DIR"

# 3. Install server scripts and configs
echo "Installing server scripts and configuration files..."
sudo mkdir -p /home/$LOG_USER/.config

# Copy core scripts
sudo cp "$BLUE_DIR/2 Server Files/check_github.sh" /home/$LOG_USER/tool_log/check_github.sh
sudo cp "$BLUE_DIR/2 Server Files/rotate_screen.sh" /usr/local/bin/rotate_screen.sh
sudo cp "$BLUE_DIR/2 Server Files/start_active_service.sh" /home/$LOG_USER/tool_log/start_active_service.sh
sudo cp "$BLUE_DIR/2 Server Files/start_browser.sh" /usr/local/bin/start_browser.sh
sudo cp "$BLUE_DIR/2 Server Files/wayfire.ini" /home/$LOG_USER/.config/wayfire.ini

# Copy new modular scripts
sudo cp "$BLUE_DIR/2 Server Files/internet_check.sh" /home/$LOG_USER/internet_check.sh
sudo cp "$BLUE_DIR/2 Server Files/nginx_setup.sh" /home/$LOG_USER/tool_log/nginx_setup.sh

# Set permissions and ownership
sudo chmod +x /usr/local/bin/rotate_screen.sh /usr/local/bin/start_browser.sh
sudo chmod +x /home/$LOG_USER/tool_log/check_github.sh \
                 /home/$LOG_USER/tool_log/start_active_service.sh \
                 /home/$LOG_USER/internet_check.sh \
                 /home/$LOG_USER/tool_log/nginx_setup.sh
sudo chown -R $LOG_USER:$LOG_USER /home/$LOG_USER/tool_log
sudo chown root:root /usr/local/bin/rotate_screen.sh /usr/local/bin/start_browser.sh

# 4. Enable console autologin and launch Wayfire on tty1
echo "Configuring autologin and Wayfire startup..."
sudo raspi-config nonint do_boot_behaviour B2
sudo -u $LOG_USER touch /home/$LOG_USER/.bash_profile
sudo -u $LOG_USER chmod 644 /home/$LOG_USER/.bash_profile
sudo -u $LOG_USER bash -c 'grep -qxF "[[ -z \$WAYLAND_DISPLAY && \$XDG_VTNR -eq 1 ]] && exec wayfire" ~/.bash_profile || \
    echo "[[ -z \$WAYLAND_DISPLAY && \$XDG_VTNR -eq 1 ]] && exec wayfire" >> ~/.bash_profile'

# 5. Configure pi-user crontab
echo "Configuring crontab for periodic tasks..."
(crontab -l 2>/dev/null | grep -v 'check_github.sh' | grep -v 'internet_check.sh'; \
 echo "*/5 * * * * /bin/bash /home/$LOG_USER/tool_log/check_github.sh >> /var/log/deploy.log 2>&1"; \
 echo "* * * * * /bin/bash /home/$LOG_USER/internet_check.sh >> /var/log/internet_check.log 2>&1"; \
 echo "0 0 * * 0 /sbin/shutdown -r now") | crontab -

# 6. Configure Nginx via modular script
echo "Configuring Nginx via nginx_setup.sh..."
sudo bash /home/$LOG_USER/tool_log/nginx_setup.sh

# 7. Activate blue-green deployment
echo "Activating service via start_active_service.sh..."
sudo bash /home/$LOG_USER/tool_log/start_active_service.sh

echo "Server setup complete. Add .env Files with environment Keys to both app_blue and app_green, then reboot to start Wayfire and apply all changes."
