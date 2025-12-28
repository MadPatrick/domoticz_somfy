# 🏠 Somfy Tahoma / Connexoon Plugin for Domoticz

![Status](https://img.shields.io/badge/Status-Stable-brightgreen)
![Domoticz](https://img.shields.io/badge/Domoticz-2022%2B-blue)
![Python](https://img.shields.io/badge/Python-3.7+-yellow)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

This plugin provides full integration between **Somfy Tahoma / Connexoon** devices and **Domoticz**, supporting both cloud (Web API) and Local API access.  
It enables reliable control of shutters, blinds, screens, awnings, and more — with full slat/orientation control where supported.

> Based on the original script by Nonolk  
> Fully rewritten and extended for modern Domoticz versions

---

## 🪟 Supported Somfy Devices

- Roller shutters  
- Blinds **including slat/orientation control**  
- Interior & exterior screens  
- Awnings  
- Pergolas  
- Garage doors  
- Windows  
- Luminance sensors  
- RTS devices *(Open/Close only — **no state feedback**)*

---

## 🚨 Important Notes

### 🔁 Version 3.x Upgrade
Before upgrading to **version 3.x**, you must remove **all Somfy devices** from Domoticz.  
The plugin will not update otherwise.

### 🌐 Version 4.x — Local API Support
From **version 4.x**, Somfy boxes can be controlled locally.  
This is faster, more reliable, and avoids Somfy cloud limitations.

### 🌐 Version 4.5 — Parameters changed
From **version 4.5** the parameters in the config has been changed 
You need to change your settings in the setup of the plugin

### ⚠ Somfy Web API Warning
Somfy discourages Web API usage.  
Cloud login or Web mode may fail without notice.  
**Local mode is strongly recommended.**

---

## 🌍 Local API Setup (Recommended)

### 1️⃣ Enable Developer Mode

Enable Developer Mode on your Somfy hub:

https://github.com/Somfy-Developer/Somfy-TaHoma-Developer-Mode

### 2️⃣ Map Hub PIN to Local Network

Add this line to `/etc/hosts` or your DNS server:

```bash
192.168.1.1 1234-1234-1234.local
```

Where:

- **192.168.1.1** → IP address of your Somfy hub  
- **1234-1234-1234** → Hub PIN *(append `.local`)*

---

## 📦 Installation

Clone the plugin into the Domoticz plugin directory:

```bash
cd domoticz/plugins
git clone https://github.com/MadPatrick/domoticz_somfy somfy
sudo systemctl restart domoticz
```

### 🧪 Optional: Beta Version

```bash
cd domoticz/plugins/somfy
git checkout beta
```

---

## ⚙️ Configuration

Open **Domoticz → Hardware** and add:

**Somfy Tahoma or Connexoon plugin**

| Field | Description |
|-------|-------------|
| Username | Somfy account login |
| Password | Somfy account password |
| Refresh Interval | Update frequency — Web: ≥5 min recommended, Local: lower intervals allowed |
| Connection | **Local** (recommended) or Web |
| Gateway PIN | PIN printed on the Somfy hub |
| Reset token | Enable only when token becomes invalid |
| Portnumber | Default: **8443** |
| Log file location | Optional log path |
| Debug logging | Enable for troubleshooting only |

✔️ After saving, Domoticz automatically creates Somfy devices.

---

## 🎚️ Slider Behavior

Prefer **0% = Open** and **100% = Closed** (or reversed)?

1. Open the device in Domoticz  
2. Check **Reverse Position**  
3. Move the device a few times to sync

---

## 🔄 Updating the Plugin

```bash
cd domoticz/plugins/somfy
git pull
sudo systemctl restart domoticz
```

You can also update via the Domoticz **Hardware** page.

---

## 📚 Documentation

- Somfy Web API docs:  
  https://tahomalink.com/enduser-mobile-web/enduserAPI/doc

- Somfy Local API docs:  
  https://github.com/Somfy-Developer/Somfy-TaHoma-Developer-Mode

---

## 📜 License

Released under the **MIT License**, unless specified otherwise.

---

🎉 **Your Domoticz installation is now Somfy-enabled!**
