# 🏠 Somfy Tahoma/Connexoon Plugin for Domoticz
![Status](https://img.shields.io/badge/Status-Stable-brightgreen)
![Domoticz](https://img.shields.io/badge/Domoticz-2022%2B-blue)
![Python](https://img.shields.io/badge/Python-3.7+-yellow)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

Original script by [Nonolk](https://github.com/nonolk/domoticz_tahoma_blind).  
Special thanks to Jan-Jaap for supporting the conversion of plugin to local access.  

Domoticz plugin written in Python to support Somfy Tahoma/Connexoon devices.  
Supports both **Web (cloud)** and **Local API** access. Local API is recommended for reliability.

The plugin currently supports the following device types: roller shutters, blinds (with slat/orientation control), interior/exterior screens, awnings, pergolas, garage doors, windows, luminance sensors, and RTS devices (Open/Close only, no state feedback due to RTS limitations).
Supported devices:

- Roller shutters
- Screens (interior/exterior)
- Awning
- Pergolas
- Garage door
- Windows
- Venetian blinds (positions + slats control)
- Luminance sensor

## ⚠️ Important Notes
### Version 3.x
When upgrading to version 3.x, it is required to first remove all devices attached to the Somfy hardware. This has to do with the upgrade to the Domoticz Extended Framework, which enabled the slats/orientation control for the blinds.
 The plugin will not upgrade when there are still devices attached to the Somfy hardware.
### version 4.x
As of version 4.x the plugin supports local access to the Somfy box for both Tahoma and Connexoon. Addtional installation steps mentioned below.

### Version 5.x
The latest plugin version **5.1.1** introduces:

- **Extended device support**  
  - Full venetian blinds: separate units for up/down and orientation.  
  - Awning devices handled correctly (no inverted percentages).  
  - Luminance sensors supported.

- **Day/Night polling**  
  - Separate intervals for day and night (`Mode2`).  
  - Temporary fast polling (10s) after commands for faster updates.  

- **Sunrise/Sunset awareness**  
  - Sunrise/sunset delays configurable via `Mode3`.  
  - Polling interval automatically adjusts based on daylight hours.

- **Local API & token management**  
  - Automatic token generation & storage for Local API.  
  - Web API still available but deprecated.  

- **Configuration via `config.txt`**  
  - Domoticz host/port, refresh intervals, sunrise/sunset delays, TEMP_DELAY/TIME.  
  - Can reload without restarting Domoticz.

- **Improved logging & error handling**  
  - Separate log file (`Mode5`) + debug logging (`Mode6`).  
  - Only logs meaningful changes.  
  - Better handling of API and command errors.

- **Versioning & upgrades**  
  - MAJOR/MINOR/PATCH version check (`checkVersion`).  
  - Automatic update to extended plugin framework (`updateToEx`).  

----------------------------------------------------------------------------------------------------------------------
⚠ **Somfy currently discourages the use of the Web API**  
The connection to Somfy Web may not work properly in the plugin.  
**It is therefore recommended to use Local API mode.** Refer to Somfy instructions to put your box in Developer Mode.

----------------------------------------------------------------------------------------------------------------------

## 🔑 Somfy Login
Before installation, register your Somfy products and add them to your Tahoma or Connexoon box:  
- [Create Somfy account](https://www.somfy.nl/nieuw-account-aanmaken)  
- [Tahoma login](https://www.tahomalink.com/enduser-mobile-web/steer-html5-client/tahoma/)

Activating this mode will enable a local API on your TaHoma and Connexoon box. Be aware that Somfy will not be able to provide support for usage of this API.

## 💻 Installation

### Prerequisites
1. Python 3.7+ and Domoticz 2022.1+ (required for Extended Plugin Framework)  
2. Follow the Domoticz guide on [Using Python Plugins](https://www.domoticz.com/wiki/Using_Python_plugins)  
3. Install required libraries:
4. 
```
sudo apt-get update
sudo apt-get install python3 libpython3-dev libpython3.7-dev
sudo apt-get install python3-requests
```
### 🖧 Setup Local API Access (Recommended)
1. First you need to enable developer mode on your box:
- connect to the [Somfy website](https://www.somfy.nl/inloggen) and navigate to the **My Account menu.**
- Find the different available options for your TaHoma box and activate **Developer Mode**.
- Follow instructions as provided by [Somfy](https://github.com/Somfy-Developer/Somfy-TaHoma-Developer-Mode)


Activating this mode will enable a local API on your TaHoma and Connexoon box. Be aware that Somfy will not be able to provide support for usage of this API.

2. Your Somfy box needs the traceable in your network.
To do this, you need to link your Somfy Box PIN to the Somfy Box IP address.
Add your Somfy Box PIN number to the IP in your local network in etc/hosts or in your DNS Server
```
192.168.1.1 1234-1234-1234.local
```
192.168.1.1 is the IP of your Somfy box<br/>
1234-1234-1234 is the PIN number of your Somfy box and don't forget to add .local to the PIN number


### 📦 Install the plugin
1. Go in your Domoticz directory using a command line and open the plugins directory:
 ```cd domoticz/plugins```
2. clone the plugin:
 ```git clone https://github.com/MadPatrick/somfy```
2. Restart Domoticz:
 ```sudo systemctl restart domoticz```

### ⚙️ Configure the Plugin
In the Domoticz UI, navigate to the Hardware page. 
In the hardware dropdown list there will be an entry called "Somfy Tahoma or Connexoon plugin".
Add the hardware to your Domoticz system and fill in the required fields

<img width="654" height="420" alt="image" src="https://github.com/user-attachments/assets/c04dec01-eefa-46b1-88ab-561f915b8e13" />


👉 **Somfy Tahoma or Connexoon plugin**

| 🏷️ **Field** | 📋 **Input** |
|--------------|--------------|
| 👤 Username | Somfy account login |
| 🔑 Password | Somfy account password |
| 🌅 Sunrise/Sunset Delay (`Mode3`) | Delay in minutes for sunrise/sunset calculations. in minutes bedore sunrise and after sunset |
| 🔄 Refresh Interval (`Mode2`) | `day;night` polling interval (in seconds) |
| ⌛ Temp polling interval (`Mode5`) |  refresh time and duration |
| 🌐 Connection (`Mode4`) | Local (recommended) or Web |
| 📍 Gateway PIN | Your Somfy box PIN |
| 🔁 Reset token (`Mode1`) | `False` by default; set `True` if token errors occur |
| 🔢 Portnumber | Default `8443` |
| 🐞 Debug logging (`Mode6`) | `False` by default; `True` for verbose logs |


🔧 After saving the configuration, devices are automatically created in **Devices**.

## 🧾 config.txt (Advanced configuration)

The plugin supports an optional `config.txt` file for advanced configuration.  
This allows you to change settings **without restarting Domoticz**.

📁 **Location:**
```
domoticz/plugins/somfy/config.txt
```
Remove the # for the setting you want to use in config.txt

🔄 **Reloading config.txt**

The plugin automatically reloads config.txt during runtime
No Domoticz restart required.
Invalid or missing values will fall back to default settings

📌 Values from config.txt override UI settings when defined.

```
DOMOTICZ_HOST=127.0.0.1
DOMOTICZ_PORT=8080

```
Remove the # for the setting you want to use in config.txt

---
### 🔄 Slider Status in Domoticz
If the slider positions do not match your preferences (Open = 0%, Close = 100%), you can reverse the slider for each device:

1. Edit the device in Domoticz  
2. Check **Reverse Position**  
3. Move the device a few times to calibrate
(To set the position correctly move your devices a few time)

![Domoticz - Devices_613_LightEdit](https://user-images.githubusercontent.com/81873830/206902008-46de4127-313e-4c0a-ba2a-3c729762734a.png)

## 🔄 Update the plugin:
When there an update of the plugin you can easlily do an update by:
```
cd domoticz/plugins/somfy
git pull
```
And then either restart Domoticz or update the plugin on the Hardware page.

# 📚 References:
- Web API description Tahoma: https://tahomalink.com/enduser-mobile-web/enduserAPI/doc
- local API description somfy box: https://github.com/Somfy-Developer/Somfy-TaHoma-Developer-Mode
