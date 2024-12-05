# HOW-TO AND SCRIPT FOR RASPBERRY PI KIOSK WITH ROTATED SCREEN


## How to use

### Install Raspberry Pi OS Lite (32-bit):
Download and flash the latest Raspberry Pi OS Lite 32-bit image to your SD card.

### Enable SSH and configure Wi-Fi:
In the OS Customization edit the default settings
- Set username and password:
    - Username: pi
    - Password: 1234
- Configure Wireless LAN
    - SSID: IRNA_WIFI
    - Password: you gotta know your password, man
    - Country: US
- Set locale Settings:
    - Time zone: America/New_York
-	Services:
    - Enable SSH
        - Use Password Authentication

### Identify IP Address
(OPTIONAL - FOR REMOTE SETUP)
After Installation, log in and identify the Devices IP Address with 
```bash
ifconfig
```
The Ip Address should look like '10.0.36.xxx'

Then Connect to the Device remotely (with another PC) with 
```bash
ssh pi@{ip address of device}
```

### Run the setup script:
After booting and connecting via SSH, download and run the setup script:
```bash
wget -O setup_kiosk.sh https://raw.githubusercontent.com/Soralis/tool_log/master/log_device_setup.sh
chmod +x setup_kiosk.sh
sudo ./setup_kiosk.sh
```