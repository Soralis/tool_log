#!/bin/bash

LOG="$HOME/internet_check.log"
TARGET=8.8.8.8

if ! ping -c1 "$TARGET" > /dev/null; then
  echo "$(date): Ping failed, restarting dhcpcd" >> "$LOG"
  sudo systemctl restart dhcpcd
else
  echo "$(date): Ping OK" >> "$LOG"
fi
