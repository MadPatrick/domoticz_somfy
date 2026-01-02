# Somfy plugin for Domoticz
Original script was written by Nonolk : https://github.com/nonolk/domoticz_tahoma_blind.git

**Special thanks to Jan-Jaap who did the rewritting of the plugin**


Domoticz plugin writen in Python to first support Somfy IO roller shutters using Tahoma/Connexoon. 
Basic support of RTS (Open/Close) is also included without return state (limitation due to RTS), it means for RTS the state of the device won't be updated if the device state is modified outside of domoticz.
The plugin currently support the following device types: roller shutters, screens (interior/exterior), awning, pergolas, garage door, windows, luminance sensor and blinds (postions and slats control).

## Important note
### Version 3.x
When upgrading to version 3.x, it is required to first remove all devices attached to the Somfy hardware. This has to do with the upgrade to the Domoticz Extended Framework, which enabled the slats/orientation control for the blinds.
 The plugin will not upgrade when there are still devices attached to the Somfy hardware.
### version 4.x
As of version 4.x the plugin supports local access to the Somfy box for both Tahoma and Connexoon. Addtional installation steps mentioned below.

----------------------------------------------------------------------------------------------------------------------

**Somfy currently discourages the use of the Web function**
**So the connection to Somfy Web may not work properly in the plugin**
**It is therefore recommended to use local mode. Refer to Somfy instructions to put your box in development mode.**

----------------------------------------------------------------------------------------------------------------------

## Somfy login

Before installation, you need to register you Somfy products and add them to your Tahoma or Connexoon box
https://www.somfy.nl/nieuw-account-aanmaken
https://www.tahomalink.com/enduser-mobile-web/steer-html5-client/tahoma/



## Installation

### Prerequisites
The following steps need to be taken before plugin installation (generic for any plugin)
1. Python version 3.7 or higher required & Domoticz version 2022.1 (due to extended plugin framework) or greater. 
2. follow the Domoticz guide on [Using Python Plugins](https://www.domoticz.com/wiki/Using_Python_plugins).
3. install the required libraries:
```
sudo apt-get update
sudo apt-get install python3 libpython3-dev libpython3.7-dev
sudo apt-get install python3-requests
```
### Setup local API access
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


### install the plugin
1. Go in your Domoticz directory using a command line and open the plugins directory:
 ```cd domoticz/plugins```
2. clone the plugin:
 ```git clone https://github.com/MadPatrick/somfy```
2. Restart Domoticz:
 ```sudo systemctl restart domoticz```

### Configure the plugin
In the Domoticz UI, navigate to the Hardware page. 
In the hardware dropdown list there will be an entry called "Somfy Tahoma or Connexoon plugin".
Add the hardware to your Domoticz system and fill in the required fields

![Domoticz - Hardware](https://user-images.githubusercontent.com/81873830/206902090-8d6cc4cb-a945-4779-87ab-a5ccadacc919.png)

|Field          | Input         |
| :------------ | :------------ |
|Username | Your login name for your Somfy account|
|Password | Your password for your Somfy account|
|Refresh Interval | Select the time of updating the devices. <br/>For Web login don't refresh too frequently the avoid login errors from Somfy webserver, 5 minutes interval adviced <br/> For local login lower interval can be used|
|Connection | Select Local or Web <br/>Local needs the developer mode on your Somfy box <br/>Web is the API website of Somfy |
|Gateway PIN| PIN code of your box (see the box)|
|Reset token| Set as default to False If you have error with the token your request a new token|
|Portnumber | The connection port of your Somby box. <br />By default this is set to 8443|
|Log file location | You can set a custom log location if you like|
|Debug logging| Default is False <br />If you need some extra information in the log you can set this to True|

![Domoticz - Hardware2](https://user-images.githubusercontent.com/81873830/206902138-29d95de5-de75-46e3-a908-856421bf5133.png)

After completing the field the devices will be created in your Devices section.

## Slider status in Domoticz
The slider status of the created devices can be changed if this does not meet your requirements
Some people like to heve slider with status **Open** at 0% and **Close** at 100%
You can change this per devies if you edit the device and click the box "Reverse Position" 
(To set the position correctly move your devices a few time)

![Domoticz - Devices_613_LightEdit](https://user-images.githubusercontent.com/81873830/206902008-46de4127-313e-4c0a-ba2a-3c729762734a.png)

## Update the plugin:
When there an update of the plugin you can easlily do an update by:
```
cd domoticz/plugins/somfy
git pull
```
And then either restart Domoticz or update the plugin on the Hardware page.

# used information:
- Web API description Tahoma: https://tahomalink.com/enduser-mobile-web/enduserAPI/doc
- local API description somfy box: https://github.com/Somfy-Developer/Somfy-TaHoma-Developer-Mode
