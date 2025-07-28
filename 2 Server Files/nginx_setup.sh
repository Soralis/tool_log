#!/bin/bash
# nginx_setup.sh: Configure Nginx for blue-green deployment and reload

SITE_CONF="/etc/nginx/sites-available/tool_log"
REPO_DIR="/home/logdeviceserver/tool_log"

# Write site configuration
sudo bash -c "cat > $SITE_CONF << 'EOF'
server {
    listen 80;
    server_name _;
    location / {
        proxy_pass http://127.0.0.1:8000;
        include /etc/nginx/proxy_params;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \"upgrade\";
    }
    location /monitoring/ws {
        proxy_pass http://127.0.0.1:8000;
        include /etc/nginx/proxy_params;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \"upgrade\";
    }
    error_log /var/log/nginx/tool_log_error.log;
    access_log /var/log/nginx/tool_log_access.log;
}
EOF"

# Enable site and reload
sudo ln -sf "$SITE_CONF" /etc/nginx/sites-enabled/tool_log
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -s reload
