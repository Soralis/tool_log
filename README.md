<h1>HOW-TO AND SCRIPT FOR RASPBERRY PI KIOSK WITH ROTATED SCREEN</h1>

<h2>Install Raspberry Pi OS Lite (32-bit):</h2>
Download and flash the latest Raspberry Pi OS Lite 32-bit image to your SD card.

<h2>Enable SSH and configure Wi-Fi:</h2>
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

<h2>Run the setup script:</h2>
After booting and connecting via SSH, download and run the setup script:
```bash
wget -O setup_kiosk.sh https://raw.githubusercontent.com/Soralis/tool_log/master/log_device_setup.sh
chmod +x setup_kiosk.sh
sudo ./setup_kiosk.sh
```