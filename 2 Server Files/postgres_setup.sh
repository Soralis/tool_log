#!/bin/bash
set -e

DB_USER="tool_log_user"
DB_NAME="tool_log_db"
DB_PASSWORD="tool_log_password" # IMPORTANT: Change this to a strong, unique password in a production environment!

echo "Installing PostgreSQL..."
sudo apt-get update -y
sudo apt-get install -y postgresql postgresql-contrib

echo "Configuring PostgreSQL user and database..."
# Check if the user already exists
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
fi

# Check if the database already exists
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
fi

echo "PostgreSQL setup complete."
