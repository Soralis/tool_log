HOW-TO AND SCRIPT FOR RASPBERRY PI KIOSK WITH ROTATED SCREEN

Install Raspberry Pi OS Lite (32-bit):
Download and flash the latest Raspberry Pi OS Lite 32-bit image to your SD card.
Enable SSH and configure Wi-Fi:
In the OS Customization edit the default settings
-	Set username and password:
o	Username: pi
o	Password: 1234
-	Configure Wireless LAN
o	SSID: IRNA_WIFI
o	Password: #$uperW1F1
o	Country: US
-	Set locale Settings:
o	Time zone: America/New_York
-	Services:
o	Enable SSH
	Use Password Authentication

Run the setup script:
After booting and connecting via SSH, download and run the setup script:
```bash
wget -O setup_kiosk.sh https://raw.githubusercontent.com/Soralis/tool_log/master/log_device_setup.sh
chmod +x setup_kiosk.sh
sudo ./setup_kiosk.sh
```