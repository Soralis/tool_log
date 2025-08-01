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

# Hardcode the postgresql.conf file path
PG_CONF="/etc/postgresql/15/main/postgresql.conf"

# Configure listen_addresses
if [ -f "$PG_CONF" ]; then
    echo "Configuring listen_addresses in $PG_CONF..."
    # Ensure the line is uncommented and set to '*'
    sudo grep -q "^#\s*listen_addresses" "$PG_CONF" && sudo sed -i "s/^#\s*listen_addresses.*/listen_addresses = '*'/" "$PG_CONF" || sudo sed -i "s/^listen_addresses.*/listen_addresses = '*'/" "$PG_CONF"
else
    echo "WARNING: postgresql.conf not found at expected path. Please configure listen_addresses manually."
fi

# Hardcode the pg_hba.conf file path
PG_HBA_CONF="/etc/postgresql/15/main/pg_hba.conf"
if [ -f "$PG_HBA_CONF" ]; then
    echo "Configuring pg_hba.conf in $PG_HBA_CONF..."
    # Check if the entry already exists to avoid duplicates
    if ! grep -q "host    all             all             0.0.0.0/0" "$PG_HBA_CONF"; then
        echo "host    all             all             0.0.0.0/0               scram-sha-256" | sudo tee -a "$PG_HBA_CONF" > /dev/null
    fi
else
    echo "WARNING: pg_hba.conf not found at expected path. Please configure pg_hba.conf manually."
fi

echo "Restarting PostgreSQL service..."
sudo systemctl restart postgresql@15-main.service
# sudo systemctl status postgresql@15-main.service
