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
(OPTIONAL - FOR REMOTE SETUP.)
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

### Update Log Devices Remotely
## Setup
1. __Check for existing SSH keys or generate a new one:__

   - Open a terminal on this control machine.

   - Check if you already have keys: `ls -al ~/.ssh/id_rsa*`

     - If you see `id_rsa` (private key) and `id_rsa.pub` (public key), you have a default key pair.

     - If not, or if you want a new one specifically for this purpose, generate a new key pair. A common command is:

       ```bash
       ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa_log_devices -C "log_devices_key"
       ```

       - `-t rsa`: Specifies RSA key type.

       - `-b 4096`: Specifies a key length of 4096 bits (strong).

       - `-f ~/.ssh/id_rsa_log_devices`: __This is important.__ This specifies the filename for the new key. I've used `id_rsa_log_devices` as an example. You can choose a different name or use the default `~/.ssh/id_rsa` if you prefer.

       - `-C "log_devices_key"`: Adds a comment to the key, which can be helpful for identification.

       - When prompted for a passphrase:

         - For fully automated scripts where you don't want to be prompted, you can press Enter to leave the passphrase empty. __Be aware of the security implications:__ anyone who gets access to this private key file can log in to your devices.
         - If you do set a passphrase, you'll need to use an `ssh-agent` to manage it so you're not prompted every time the script runs.

2. __Update `SSH_KEY_PATH` in `update_log_devices.sh` (if needed):__

   - If you generated a key with a name other than `id_rsa` or in a location other than `/home/pi/.ssh/`, you __must__ update the `SSH_KEY_PATH` variable in your `update_log_devices.sh` script to point to the correct private key file.

   - For example, if you used the `ssh-keygen` command above with `-f ~/.ssh/id_rsa_log_devices`, you would change line 11 in your script to:

     ```bash
     SSH_KEY_PATH="/home/pi/.ssh/id_rsa_log_devices"
     ```

     (Assuming the user running the script is `pi`. If it's a different user, adjust `/home/pi/` accordingly, or use `~/.ssh/your_key_name` which usually resolves to the current user's home directory).

__On EACH of your remote Raspberry Pi devices (the ones you want to update):__

3. __Copy the public key to the remote devices:__

   - You need to get the content of the __public key__ file (e.g., `~/.ssh/id_rsa_log_devices.pub` or `~/.ssh/id_rsa.pub` from the control machine) and add it to the `~/.ssh/authorized_keys` file on each remote Raspberry Pi.

   - __Easiest way (if you can temporarily log in with a password to the remote Pis):__ From the control machine, use the `ssh-copy-id` command for each Pi:

     ```bash
     ssh-copy-id -i ~/.ssh/id_rsa_log_devices.pub pi@<IP_ADDRESS_OF_REMOTE_PI>
     ```

     - Replace `~/.ssh/id_rsa_log_devices.pub` with the actual path to your public key file.
     - Replace `pi@<IP_ADDRESS_OF_REMOTE_PI>` with the username and IP address of the target Pi.
     - You'll be prompted for the password for the remote Pi *this one time* to copy the key.

## Run Collective Update
Now to run the Update connect to the Server via SSH and run the following code (replace {running_deployment} with the actually running deployment app_blue or app_green)
```bash
/bin/bash /home/pi/tool_log/{running_deployment}/update_log_devices.sh
```