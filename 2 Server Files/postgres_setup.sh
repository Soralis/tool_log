#!/bin/bash
set -e

echo "DEBUG: Running postgres_setup.sh"

DB_USER="tool_log_user"
DB_NAME="tool_log_db"
DB_PASSWORD="tool_log_password" # IMPORTANT: Change this to a strong, unique password in a production environment!

echo "Installing PostgreSQL..."
sudo apt-get update -y
sudo apt-get install -y postgresql postgresql-contrib

echo "Configuring PostgreSQL user and database..."
# Check if the user already exists
if ! sudo -u postgres HOME=/tmp psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
    sudo -u postgres HOME=/tmp psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
fi

# Check if the database already exists
if ! sudo -u postgres HOME=/tmp psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
    sudo -u postgres HOME=/tmp psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
fi

echo "PostgreSQL setup complete."

# Find the postgresql.conf file dynamically
PG_CONF="/etc/postgresql/$(pg_lsclusters | head -n 1 | awk '{print $1}')/main/postgresql.conf"

# Configure listen_addresses
if [ -f "$PG_CONF" ]; then
    echo "Configuring listen_addresses in $PG_CONF..."
    sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF"
    sudo sed -i "s/listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF" # In case it's uncommented but still 'localhost'
else
    echo "WARNING: postgresql.conf not found at expected path. Please configure listen_addresses manually."
fi

echo "Restarting PostgreSQL service..."
sudo systemctl restart postgresql@15-main.service
sudo systemctl status postgresql@15-main.service
