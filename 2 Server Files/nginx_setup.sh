#!/bin/bash
# nginx_setup.sh: Configure Nginx for blue-green deployment and reload

SITE_CONF="/etc/nginx/sites-available/tool_log"

# Write site configuration
sudo tee "$SITE_CONF" > /dev/null << 'ENDOFFILE'
server {
    listen 80;
    server_name _;
    
    client_body_buffer_size 128k;
    client_max_body_size 20M;
    
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/javascript application/xml+rss application/json image/svg+xml;
    
    location /static/ {
        alias /home/logdeviceserver/tool_log/app_green/app/static/;
        try_files $uri @static_blue;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
    
    location @static_blue {
        alias /home/logdeviceserver/tool_log/app_blue/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
    
    location /monitoring/ws {
        proxy_pass http://127.0.0.1:8000;
        include /etc/nginx/proxy_params;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        include /etc/nginx/proxy_params;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_buffering off;
    }
    
    error_log /var/log/nginx/tool_log_error.log;
    access_log /var/log/nginx/tool_log_access.log;
}
ENDOFFILE

# Enable site and reload
sudo ln -sf "$SITE_CONF" /etc/nginx/sites-enabled/tool_log
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
