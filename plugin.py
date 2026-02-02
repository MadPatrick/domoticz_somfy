# Tahoma/Connexoon IO blind plugin
#
#
# 
# All credits for the plugin are for Nonolk, who is the origin plugin creator
"""
<plugin key="tahomaIO" name="Somfy Tahoma or Connexoon plugin" author="MadPatrick" version="5.2.0" externallink="https://github.com/MadPatrick/somfy">
    <description>
        <br/><h2>Somfy Tahoma/Connexoon plugin</h2><br/>
        Version: 5.2.0
        <br/>This plugin connects to the Tahoma or Connexoon box either via the web API or via local access.
        <br/>Various devices are supported (RollerShutter, LightSensor, Screen, Awning, Window, VenetianBlind, etc.).
        <br/>For new devices, please raise a ticket at the Github link above.
        <h2><br/>Configuration</h2><br/>
        The configuration contains the following sections:
        <ol>
            <li>General: enter here your credentials and select the connection method</li>
            <li>Local: when connection method local is selected, fill this section as well</li>
            <li>Debug: allows to set log level and specify log file location</li>
        </ol>
        <br/><font color="yellow">Please put in the additional parameters in the config.txt file in the plugin folder</font>
        <br/>
        <br/>
<table border="1" cellpadding="4" cellspacing="0" width="50%">
    <tr>
        <th align="left" style="background-color: red;">Parameter</th>
        <th align="left" style="background-color: red;">Description</th>
    </tr>
    <tr>
        <td><b>Username</b></td>
        <td>Enter your Somfy login name </td>
    </tr>
    <tr>
        <td><b>Password</b></td>
        <td>Enter your Somfy Password</td>
    </tr>
    <tr>
        <td><b>Refresh interval</b></td>
        <td>How often must the devices be polled?
        <br/>Enter two numbers separated by a semicolon (;)
        <br/>The first number is for day refresh polling (in seconds), the second is for night refresh polling (in seconds).</td>
    </tr>
    <tr>
        <td><b>Night Mode</b></td>
        <td>When should the night mode start?
        <br/>Enter two numbers separated by a semicolon (;).
        <br/>The first number is the time (in minutes) before sunrise, and the second number is the time after sunset.</td>
    </tr>
        <tr>
        <td><b>Temp polling interval</b></td>
        <td>How often must the devices be polled?
        <br/>Enter two numbers separated by a semicolon (;)</td>
    </tr>
    <tr>
        <td><b>Connection</b></td>
        <td>Choose how to interact with the Somfy/Tahoma/Connexoon box:
        <br/>Web API: via Somfy web server (requires continuous internet access)
        <br/>Local API: connect directly to the box (default)
        <br/>Somfy is depreciating the Web access, so it is better to use the local API</td>
    </tr>
    <tr>
        <td><b>Address</b></td>
        <td>Gateway PIN of the Portnumber Tahoma box
        <br/>Don't forget to set your DNS setting with you IP linked to the PIN number </td>
    </tr>
    <tr>
        <td><b>Port</b></td>
        <td>Portnumber of the Tahoma box (8443)</td>
    </tr>
    <tr>
        <td><b>Reset token</b></td>
        <td>Set to True to request a new token. Can be used when you get access denied</td>
    </tr>
    <tr>
        <td><b>Debug logging</b></td>
        <td>Set to True to enable debug logging for troubleshooting</td>
    </tr>
    </table>
    <br/>
</description>
    <params>
        <param field="Username" label="Username" width="200px" required="true" default=""/>
        <param field="Password" label="Password" width="200px" required="true" default="" password="true"/>
        <param field="Mode2" label="Refresh interval" width="100px" default="30;900"/>
        <param field="Mode3" label="Night Mode" width="100px" default="30;60"/>
        <param field="Mode5" label="Temp refresh interval" width="200px" default="15;120"/>
        <param field="Mode4" label="Connection" width="100px">
            <description><br/>Somfy is depreciating the Web access, so it is better to use the local API</description>
            <options>
                <option label="Web" value="Web"/>
                <option label="Local" value="Local" default="true"/>
            </options>
        </param>
        <param field="Address" label="Gateway PIN" width="150px" required="true" default="1234-1234-1234"/>
        <param field="Port" label="Portnumber Tahoma box" width="100px" required="true" default="8443"/>
        <param field="Mode1" label="Reset token" width="100px">            
            <options>
                <option label="false" value="false" default="true"/>
                <option label="true" value="true" />
            </options>
        </param>
        <param field="Mode6" label="Debug logging" width="100px">
            <options>
                <option label="true" value="Debug"/>
                <option label="false" value="Normal"  default="true" />
            </options>
        </param>
    </params>
</plugin>
"""

# Tahoma/Connexoon IO blind plugin
import DomoticzEx as Domoticz
import json
import logging
import exceptions
import time
import datetime
import tahoma
import os
import math
from tahoma_local import SomfyBox
import utils
import urllib.request

class BasePlugin:
    def __init__(self):
        self.enabled = False
        self.heartbeat = False
        self.runCounter = 0
        self.command_data = None
        self.command = False
        self.actions_serialized = []

        self.log_filename = "somfy.log"
        self.local = False

        # Device / mode tracking
        self._last_mode = None

        # Sunrise/sunset / daily refresh
        self.last_sunrise = None
        self.last_sunset = None
        self.sun_refresh_time = "02:00"  # vaste tijd
        self.last_sun_refresh_ts = datetime.datetime.min  # timestamp van laatste refresh

        # Domoticz / polling defaults
        self.domoticz_host = "127.0.0.1"
        self.domoticz_port = "8080"
        self.dayInterval = 30
        self.nightInterval = 900
        self.sunriseDelay = 30
        self.sunsetDelay = 60
        self.temp_delay = 10
        self.temp_time = 60
        self.temp_interval_end = 0
        self.temp_delay = 10     # fallback defaults
        self.temp_time  = 60     # fallback defaults
        self.temp_interval_end = 0
    
    def onStart(self):
        """
        Plugin initialization.
        Sets up logging, polling intervals, sunrise/sunset delays,
        and TEMP_DELAY / TEMP_TIME from Mode5.
        """
        # --- Logfile in standaard Domoticz-map ---
        log_dir = ""
        log_fullname = os.path.join(log_dir, self.log_filename)
        Domoticz.Log(f"Starting Tahoma blind plugin, logging to file {log_fullname}")

        # --- Logging setup ---
        if Parameters.get("Mode6") == "Debug":
            Domoticz.Debugging(2)
            logging.basicConfig(
                format='%(asctime)s - %(levelname)-8s - %(filename)-18s - %(message)s',
                filename=log_fullname,
                level=logging.DEBUG
            )
            DumpConfigToLog()
        else:
            logging.basicConfig(
                format='%(asctime)s - %(levelname)-8s - %(filename)-18s - %(message)s',
                filename=log_fullname,
                level=logging.INFO
            )

        logging.info("Starting plugin version " + Parameters.get("Version", "Unknown"))

        # --- Polling intervals (Mode2) ---
        try:
            day_str, night_str = Parameters.get("Mode2", "30;900").split(";")
            self.dayInterval   = int(day_str.strip())
            self.nightInterval = int(night_str.strip())
            Domoticz.Log(f"Somfy: Polling intervals Day / Night: {self.dayInterval}s and {self.nightInterval}s")
        except Exception as e:
            self.dayInterval   = 30
            self.nightInterval = 900
            Domoticz.Error(f"Somfy: Failed to parse Mode2 for intervals, using defaults: {e}")

        # --- Sunrise / Sunset delays (Mode3) ---
        try:
            sr_delay_str, ss_delay_str = Parameters.get("Mode3", "30;60").split(";")
            self.sunriseDelay = int(sr_delay_str.strip())
            self.sunsetDelay  = int(ss_delay_str.strip())
            Domoticz.Log(f"Somfy: Sunrise / Sunset delays : {self.sunriseDelay}m and {self.sunsetDelay}m")
        except Exception as e:
            self.sunriseDelay = 30
            self.sunsetDelay  = 60
            Domoticz.Error(f"Somfy: Failed to parse Mode3 for sunrise/sunset delays, using defaults: {e}")

        # --- TEMP_DELAY / TEMP_TIME uit Mode5 ---
        try:
            delay_str, time_str = Parameters.get("Mode5", "10;60").split(";")
            self.temp_delay = int(delay_str.strip())
            self.temp_time  = int(time_str.strip())
            Domoticz.Log(f"Somfy: Temp delay settings : {self.temp_delay}s delay for {self.temp_time}s")
        except Exception as e:
            self.temp_delay = 10
            self.temp_time  = 60
            Domoticz.Error(f"Somfy: Failed to parse Mode5 for TEMP settings, using defaults: {e}")

        # --- Set initial runCounter for heartbeat ---
        self.runCounter = self.dayInterval

        # --- Enable heartbeat ---
        Domoticz.Heartbeat(1)

        # --- Load remaining settings from config.txt if needed ---
        self.load_config_txt(log=True)

        # --- Mark last config day ---
        self.last_config_day = datetime.datetime.now().day
        self.enabled = True

        # --- Connect to Tahoma/Connexoon box ---
        pin  = Parameters.get("Address")
        port = int(Parameters.get("Port", 8443))

        if Parameters.get("Mode4") == "Local":
            self.tahoma = SomfyBox(pin, port)
            self.local  = True
        else:
            self.tahoma = tahoma.Tahoma()
            self.local  = False

        try:
            self.tahoma.tahoma_login(str(Parameters.get("Username")), str(Parameters.get("Password")))
        except Exception as exp:
            Domoticz.Error("Failed to login: " + str(exp))
            return False

        self.setup_and_sync_devices(pin)


    def setup_and_sync_devices(self, pin):
        if not self.tahoma.logged_in:
            Domoticz.Error("TaHoma not logged in")
            return False

        # --- TOKEN / LISTENER ---
        if self.local:
            logging.debug("check if token stored in configuration")
            confToken = getConfigItem('token', '0')

            if confToken == '0' or Parameters["Mode1"] == "True":
                logging.debug("no token found, generate a new one")
                self.tahoma.generate_token(pin)
                self.tahoma.activate_token(pin, self.tahoma.token)
                setConfigItem('token', self.tahoma.token)
                Parameters["Mode1"] = "False"
            else:
                logging.debug("found token in configuration: " + str(confToken))
                self.tahoma.token = confToken

        self.tahoma.register_listener()

        # --- DEVICES OPHALEN ---
        filtered_devices = self.tahoma.get_devices()

        # --- DEVICES AANMAKEN (alleen als nodig) ---
        if len(Devices) == 0:
            unit = firstFree()
            if unit is None or unit >= 249:
                Domoticz.Error("No free Domoticz units available, cannot create devices")
                return False

            self.create_devices(filtered_devices)

        # --- STATUS UPDATEN ---
        self.update_devices_status(utils.filter_states(filtered_devices))

        return True

    def onStop(self):
        logging.info("stopping plugin")
        Domoticz.Log("stopping plugin")
        self.heartbeat = False

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug("onConnect: Connection: '"+str(Connection)+"', Status: '"+str(Status)+"', Description: '"+str(Description)+"' self.tahoma.logged_in: '"+str(self.tahoma.logged_in)+"'")
        if (Status == 0 and not self.tahoma.logged_in):
          self.tahoma.tahoma_login(str(Parameters["Username"]), str(Parameters["Password"]))
        elif (self.tahoma.logged_in and (not self.command)):
          event_list = self.tahoma.get_events()
          self.update_devices_status(event_list)

        elif (self.command):
          event_list = self.tahoma.tahoma_command(self.command_data)
          self.update_devices_status(event_list)
          self.command = False
          self.heartbeat = False
          self.actions_serialized = []
        else:
          logging.info("Failed to connect to tahoma api")

    def refresh_daily_data(self):
        """
        Refresh sunrise/sunset daily from Domoticz JSON API at a fixed time.
        Forces update at first plugin start.
        """
        now = datetime.datetime.now()

        # Split HH:MM
        refresh_hour, refresh_min = map(int, self.sun_refresh_time.split(":"))
        refresh_today = now.replace(hour=refresh_hour, minute=refresh_min, second=0, microsecond=0)

        # Forceer eerste refresh bij opstart
        first_refresh = self.last_sun_refresh_ts is None or self.last_sun_refresh_ts <= datetime.datetime.min

        # Controleer of refresh nodig is
        if first_refresh or (now >= refresh_today and self.last_sun_refresh_ts < refresh_today):
            try:
                api_url = f"http://{self.domoticz_host}:{self.domoticz_port}/json.htm?type=command&param=getSunRiseSet"
                with urllib.request.urlopen(api_url, timeout=10) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    sunrise_full = data.get("Sunrise", "06:00:00")
                    sunset_full  = data.get("Sunset", "22:00:00")

                    # Bewaar ook de datetime voor interne logica
                    self.last_sunrise = sunrise_full[:5]
                    self.last_sunset  = sunset_full[:5]

                    self.last_sunrise_ts = now.replace(hour=int(self.last_sunrise.split(":")[0]),
                                                    minute=int(self.last_sunrise.split(":")[1]),
                                                    second=0, microsecond=0)
                    self.last_sunset_ts = now.replace(hour=int(self.last_sunset.split(":")[0]),
                                                    minute=int(self.last_sunset.split(":")[1]),
                                                    second=0, microsecond=0)

                    self.log_day_night_times()
                Domoticz.Log(f"Sunrise/sunset refreshed @ {now.strftime('%H:%M')}: sunrise={self.last_sunrise} sunset={self.last_sunset}")

            except Exception as e:
                Domoticz.Error(f"Sunrise/sunset couldn't be loaded: {e}")
                if not self.last_sunrise:
                    self.last_sunrise = "06:00"
                if not self.last_sunset:
                    self.last_sunset = "22:00"

            # Update timestamp naar nu, zodat we niet meteen opnieuw refreshen
            self.last_sun_refresh_ts = now

    def log_day_night_times(self):
        if not self.last_sunrise or not self.last_sunset:
            Domoticz.Debug("Sunrise/sunset nog niet beschikbaar, kan dag/nacht tijden niet loggen")
            return

        # Convert sunrise and sunset strings to hours and minutes
        sr_hour, sr_min = map(int, self.last_sunrise.split(':'))
        ss_hour, ss_min = map(int, self.last_sunset.split(':'))

        # Day mode start = sunrise - sunriseDelay
        day_start_minutes = sr_hour * 60 + sr_min - self.sunriseDelay
        day_start_hour = day_start_minutes // 60
        day_start_min = day_start_minutes % 60

        # Night mode start = sunset + sunsetDelay
        night_start_minutes = ss_hour * 60 + ss_min + self.sunsetDelay
        night_start_hour = night_start_minutes // 60
        night_start_min = night_start_minutes % 60

        # Format time as HH:MM
        day_start_str = f"{day_start_hour:02d}:{day_start_min:02d}"
        night_start_str = f"{night_start_hour:02d}:{night_start_min:02d}"

        Domoticz.Log(f"Day mode starts at {day_start_str} | Night mode starts at {night_start_str}")

    def onMessage(self, Connection, Data):
        Domoticz.Error("onMessage called but not implemented")
        Domoticz.Debug("onMessage data: "+str(Data))

    def onCommand(self, DeviceId, Unit, Command, Level, Hue):
        Domoticz.Debug(f"onCommand: DeviceId: {DeviceId}, Unit: {Unit}, Command: {Command}, Level: {Level}, Hue: {Hue}")
        self.actions_serialized = []
        commands_serialized = []
        action = {}
        commands = {}
        params = []

        # Determine command based on unit
        if Unit == 1:
            if Command in ("Off", "Close"):
                commands["name"] = "close"
            elif Command in ("On", "Open"):
                commands["name"] = "open"
            elif Command == "Stop":
                commands["name"] = "stop"
            elif "Set Level" in Command:
                commands["name"] = "setClosure"
                tmp = max(100 - int(Level), 0)  # invert open/close
                params.append(tmp)
                commands["parameters"] = params
        elif Unit == 2:
            if "Set Level" in Command:
                commands["name"] = "setOrientation"
                tmp = max(100 - int(Level), 1)  # orientation does not accept 0
                params.append(tmp)
                commands["parameters"] = params
            else:
                Domoticz.Error(f"Command {Command} not supported for unit 2")
                return False
        else:
            Domoticz.Error(f"Unit {Unit} not supported")
            return False

        # Prepare action
        commands_serialized.append(commands)
        action["deviceURL"] = DeviceId
        action["commands"] = commands_serialized
        self.actions_serialized.append(action)

        data = {
            "label": f"Domoticz - {Devices[DeviceId].Units[Unit].Name} - {commands['name']}",
            "actions": self.actions_serialized
        }
        if self.local:
            self.command_data = data
        else:
            self.command_data = json.dumps(data, indent=None, sort_keys=True)

        # Log in if necessary
        if not self.tahoma.logged_in:
            Domoticz.Log("Not logged in, trying to login")
            self.command = True
            self.tahoma.tahoma_login(str(Parameters["Username"]), str(Parameters["Password"]))
            if self.tahoma.logged_in:
                self.tahoma.register_listener()

        # Send command
        try:
            self.tahoma.send_command(self.command_data)
            self.temp_interval_end = time.time() + self.temp_time
            self.runCounter = 0

        except (exceptions.TooManyRetries,
                exceptions.FailureWithErrorCode,
                exceptions.FailureWithoutErrorCode,
                Exception) as exp:
            Domoticz.Error(f"Somfy: Failed to send command: {exp}")
            if not self.local:
                self.actions_serialized = []
            return False

        return True

    def onDisconnect(self, Connection):
        return

    def onHeartbeat(self):
        self.runCounter -= 1

        if not self.enabled:
            return False

        # --- Daily refresh (sunrise/sunset) ---
        self.refresh_daily_data()  # checkt zelf of update nodig is

        now = datetime.datetime.now()
        now_minutes = now.hour * 60 + now.minute

        # Gebruik de strings voor logging en berekeningen
        sunrise_str = self.last_sunrise or "06:00"
        sunset_str  = self.last_sunset or "22:00"

        sr_hour, sr_min = map(int, sunrise_str.split(":"))
        ss_hour, ss_min = map(int, sunset_str.split(":"))

        sunrise_minutes = sr_hour * 60 + sr_min
        sunset_minutes  = ss_hour * 60 + ss_min

        # Check day/night mode
        if sunrise_minutes - self.sunriseDelay <= now_minutes < sunset_minutes + self.sunsetDelay:
            standard_interval = self.dayInterval
            status_label = "DAY-MODE"
        else:
            standard_interval = self.nightInterval
            status_label = "NIGHT-MODE"

        # Log bij modus-overgang
        if self._last_mode != status_label:
            Domoticz.Status(f"Mode switched to {status_label}. Polling interval is now {standard_interval}s")
            logging.info(f"Mode switched to {status_label}. Polling interval is now {standard_interval}s")
            self._last_mode = status_label

        self.log_changes(standard_interval, self.last_sunrise, self.last_sunset, status_label)

        # Temporary fast polling after command
        if time.time() < self.temp_interval_end:
            interval = self.temp_delay
            if not getattr(self, "_temp_log_active", False):
                remaining = math.ceil(self.temp_interval_end - time.time())
                Domoticz.Status(f"Action detected! Fast polling ({self.temp_delay}s) active for {remaining}s")
                self._temp_log_active = True
        else:
            interval = standard_interval
            if getattr(self, "_temp_log_active", False):
                Domoticz.Status(f"Fast polling ended. Returning to standard interval ({interval}s)")
                self._temp_log_active = False

        # Poll devices only when needed
        if self.runCounter <= 0 or self.heartbeat:
            if self.local or (self.tahoma.logged_in and not self.tahoma.startup):
                try:
                    filtered_devices = self.tahoma.get_devices()
                    self.update_devices_status(utils.filter_states(filtered_devices))
                except Exception as exp:
                    Domoticz.Error(f"Connection error: {exp}")

            self.runCounter = interval
            self.heartbeat = False

        return True

    def update_devices_status(self, Updated_devices):
        Domoticz.Debug("updating device status self.tahoma.startup = "+str(self.tahoma.startup)+" on num datasets: "+str(len(Updated_devices)))
        Domoticz.Debug("updating device status on data: "+str(Updated_devices))
        if self.local:
            eventList = utils.filter_events(Updated_devices)
        else:
            eventList = Updated_devices
        num_updates = 0
        Domoticz.Debug("checking device updates for "+str(len(eventList))+" filtered events")
        for dataset in eventList:
            Domoticz.Debug("checking dataset: "+str(dataset))

            if dataset["deviceURL"] not in Devices:
                Domoticz.Error("device not found for URL: "+str(dataset["deviceURL"]))
                logging.error("device not found for URL: "+str(dataset["deviceURL"])+" while updating states")
                continue #no deviceURL found that matches to domoticz Devices, skip to next dataset

            if (dataset["deviceURL"].startswith("io://")):
                dev = dataset["deviceURL"]
                deviceClassTrig = dataset.get("deviceClass")
                level = 0
                status_num = 0
                status = None
                nValue = 0
                sValue = "0"

                states = dataset["deviceStates"]
                if not (dataset["name"] == "DeviceStateChangedEvent" or dataset["name"] == "DeviceState"):
                    Domoticz.Debug("update_devices_status: dataset['name'] != DeviceStateChangedEvent: "+str(dataset["name"])+": breaking out")
                    continue #dataset does not contain correct event, skip to next dataset

                lumstatus_l = False
                level = None

                for state in states:

                    if ((state["name"] == "core:ClosureState") or (state["name"] == "core:DeploymentState")):
                        if (deviceClassTrig == "Awning"):
                            level = int(state["value"]) #Don't invert open/close percentage for an Awning
                            status_num = 1
                        else:
                            level = int(state["value"])
                            level = 100 - level #invert open/close percentage
                            status_num = 1

                    elif state["name"] == "core:SlateOrientationState":
                        level = int(state["value"])
                        status_num = 2

                    elif state["name"] == "core:LuminanceState":
                        lumlevel = state["value"]
                        lumstatus_l = True
              
                    Domoticz.Debug("checking for update on state[name]: '" +state["name"]+"' with status_num = '"+str(status_num)+ "' for device: '"+dev+"'")
                    if status_num > 0:
                        if (Devices[dev].Units[status_num].sValue):
                            int_level = int(Devices[dev].Units[status_num].sValue)
                        else:
                            int_level = 0
                        if (level != int_level):
                            Domoticz.Status("Updating device : "+Devices[dev].Units[status_num].Name)
                            logging.info("Updating device : "+Devices[dev].Units[status_num].Name)
                            if (level == 0):
                                nValue = 0
                                sValue = "0"
                            if (level == 100):
                                nValue = 1
                                sValue = "100"
                            if (level != 0 and level != 100):
                                nValue = 2
                                sValue = str(level)
                            UpdateDevice(dev, status_num, nValue,sValue)
                    if lumstatus_l: #assuming for now that the luminance sensor is always a single unit in a device
                        if (Devices[dev].Units[1].sValue):
                            int_lumlevel = Devices[dev].Units[1].sValue
                        else:
                            int_lumlevel = 0
                        if (lumlevel != int_lumlevel):
                            Domoticz.Status("Updating device : "+Devices[dev].Units[1].Name)
                            logging.info("Updating device : "+Devices[dev].Units[1].Name)
                            if (lumlevel != 0 and lumlevel != 120000):
                                nValue = 3
                                sValue = str(lumlevel)
                                UpdateDevice(dev, 1, nValue,sValue)
                    num_updates += 1

        return num_updates

    def onDeviceAdded(self, DeviceID, Unit):
        logging.debug("onDeviceAdded called for DeviceID {0} and Unit {1}".format(DeviceID, Unit))

    def onDeviceModified(self, DeviceID, Unit):
        logging.debug("onDeviceModified called for DeviceID {0} and Unit {1}".format(DeviceID, Unit))

    def onDeviceRemoved(self, DeviceID, Unit):
        logging.debug("onDeviceRemoved called for DeviceID {0} and Unit {1}".format(DeviceID, Unit))

    def create_devices(self, filtered_devices):
        logging.debug("create_devices: devices found, domoticz: "+str(len(Devices))+" API: "+str(len(filtered_devices)))
        created_devices = 0
        
        if (len(Devices) <= len(filtered_devices)):
            #Domoticz devices already present but less than from API or starting up
            logging.debug("New device(s) detected")

            for device in filtered_devices:
                found = False
                if type(device) is str:
                    logging.debug("create_device: device in filter_list is of type string, need to convert")
                    device = json.loads(device)
                logging.debug("create_devices: check if need to create device: "+device["label"])
                if device["deviceURL"] in Devices:
                    logging.debug("create_devices: step 1, do not create new device: "+device["label"]+", device already exists")
                    found = True
                    #break
                for domo_dev in Devices:
                    if domo_dev == device["deviceURL"]:
                        logging.debug("create_devices: step 2, do not create new device: "+device["label"]+", device already exists")
                        found = True
                        break
                if (found==False):
                    #DeviceID not found, create new one
                    swtype = None

                    logging.debug("create_devices: Must create new device: "+device["label"])

                    if (device["deviceURL"].startswith("io://") or (device["deviceURL"].startswith("rts://"))):
                        deviceType = 244
                        swtype = 13
                        subtype2 = 73
                        used = 1 # 1 = True
                        if (device["definition"]["uiClass"] == "Awning"):
                            swtype = 13
                        elif (device["definition"]["uiClass"] == "RollerShutter"):
                            deviceType = 244
                            swtype = 21
                            subtype2 = 73                    
                        elif (device["definition"]["uiClass"] == "LightSensor"):
                            deviceType = 246
                            swtype = 12
                            subtype2 = 1
                    elif (device["definition"]["uiClass"] == "Pod"):
                        deviceType = 244
                        subtype2 = 73
                        swtype = 9
                        used = 0 #0 = False

                    # extended framework: create first device then unit? or create device+unit in one go?
                    created_devices += 1
                    Domoticz.Device(DeviceID=device["deviceURL"]) #use deviceURL as identifier for Domoticz.Device instance
                    if (device["definition"]["uiClass"] == "VenetianBlind" or device["definition"]["uiClass"] == "ExteriorVenetianBlind"):
                        #create unit for up/down and open/close for venetian blinds
                        Domoticz.Unit(Name=device["label"] + " up/down", Unit=1, Type=deviceType, Subtype=subtype2, Switchtype=swtype, DeviceID=device["deviceURL"], Used=used).Create()
                        Domoticz.Unit(Name=device["label"] + " orientation", Unit=2, Type=244, Subtype=73, Switchtype=swtype, DeviceID=device["deviceURL"], Used=used).Create()
                    else:
                        #create a single unit for all other device types
                        Domoticz.Unit(Name=device["label"], Unit=1, Type=deviceType, Subtype=subtype2, Switchtype=swtype, DeviceID=device["deviceURL"], Used=used).Create()
                     
                    logging.info("New device created: "+device["label"])
                    Domoticz.Log("New device created: "+device["label"])
                else:
                    found = False
        logging.debug("create_devices: finished create devices")
        return len(filtered_devices),created_devices
        #return Devices

    def updateToEx(self):
        """routine to check if we can update to the Domoticz extended plugin framework"""
        if len(Devices)>0:
            Domoticz.Log("Existing devices detected. Will retain and update them.")
            return True

    def load_config_txt(self, log=False):
        config_path = os.path.join(os.path.dirname(__file__), "config.txt")
        if not os.path.exists(config_path):
            if log:
                Domoticz.Status("Somfy: config.txt niet gevonden op " + config_path)
            return

        try:
            with open(config_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                
                    key, value = line.split("=", 1)
                    key = key.strip().upper()
                    val = value.strip()

                    if key == "DOMOTICZ_HOST":
                        self.domoticz_host = val
                    elif key == "DOMOTICZ_PORT":
                        self.domoticz_port = val

            # Deze logregel is cruciaal om te zien of het gelukt is
            Domoticz.Log(f"Somfy: Config.txt loaded. Domoticz @ {self.domoticz_host}:{self.domoticz_port}")
            
        except Exception as e:
            Domoticz.Error(f"Somfy: Fout in load_config_txt: {str(e)}")

    def log_changes(self, interval, sunrise_str, sunset_str, status_label):
        """Logs changes in interval, sunrise, and sunset, only if they differ from last known values."""
    
        # Detect changes
        interval_changed = (getattr(self, 'last_interval', None) != interval)
        sunrise_changed  = (getattr(self, 'last_sunrise', None) != sunrise_str)
        sunset_changed   = (getattr(self, 'last_sunset', None) != sunset_str)

        # Log changes individually
        if interval_changed:
            Domoticz.Log(f"Polling interval changed: new interval = {interval}s")

        if sunrise_changed:
            Domoticz.Log(f"Sunrise updated ({status_label}): {getattr(self, 'last_sunrise', 'N/A')} ? {sunrise_str}")

        if sunset_changed:
            Domoticz.Log(f"Sunset updated ({status_label}): {getattr(self, 'last_sunset', 'N/A')} ? {sunset_str}")

        # Update last-known values
        self.last_interval = interval
        self.last_sunrise  = sunrise_str
        self.last_sunset   = sunset_str

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onDeviceAdded(DeviceID, Unit):
    global _plugin
    _plugin.onDeviceAdded(DeviceID, Unit)

def onDeviceModified(DeviceID, Unit):
    global _plugin
    _plugin.onDeviceModified(DeviceID, Unit)

def onDeviceRemoved(DeviceID, Unit):
    global _plugin
    _plugin.onDeviceRemoved(DeviceID, Unit)

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(DeviceId, Unit, Command, Level, Color):
    global _plugin
    _plugin.onCommand(DeviceId, Unit, Command, Level, Color)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

# Generic helper functions

def DumpConfigToLog():
    Domoticz.Debug("Parameters count: " + str(len(Parameters)))
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("Parameter: '" + x + "':'" + str(Parameters[x]) + "'")
    Configurations = Domoticz.Configuration()
    Domoticz.Debug("Configuration count: " + str(len(Configurations)))
    for x in Configurations:
        if Configurations[x] != "":
            Domoticz.Debug( "Configuration '" + x + "':'" + str(Configurations[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
    return

def firstFree():
    """check if there is room to add devices (max 255)"""
    for num in range(1, 254):
        if num not in Devices:
            return num
    return

#############
# Configuration Helpers
#############

def getConfigItem(Key=None, Default={}):
   Value = Default
   try:
       Config = Domoticz.Configuration()
       if (Key != None):
           Value = Config[Key] # only return requested key if there was one
       else:
           Value = Config      # return the whole configuration if no key
   except KeyError:
       Value = Default
   except Exception as inst:
       Domoticz.Error("Domoticz.Configuration read failed: '"+str(inst)+"'")
   return Value
   
def setConfigItem(Key=None, Value=None):
    Config = {}
    if type(Value) not in (str, int, float, bool, bytes, bytearray, list, dict):
        Domoticz.Error("A value is specified of a not allowed type: '" + str(type(Value)) + "'")
        return Config
    try:
       Config = Domoticz.Configuration()
       if (Key != None):
           Config[Key] = Value
       else:
           Config = Value  # set whole configuration if no key specified
       Config = Domoticz.Configuration(Config)
    except Exception as inst:
       Domoticz.Error("Domoticz.Configuration operation failed: '"+str(inst)+"'")
    return Config

def UpdateDevice(Device, Unit, nValue, sValue, AlwaysUpdate=False):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    if (Device in Devices):
        logging.debug("Updating device "+Devices[Device].Units[Unit].Name+ " with current sValue '"+Devices[Device].Units[Unit].sValue+"' to '" +sValue+"'")
        if (Devices[Device].Units[Unit].nValue != nValue) or (Devices[Device].Units[Unit].sValue != sValue):
            try:
                Devices[Device].Units[Unit].nValue = nValue
                Devices[Device].Units[Unit].sValue = sValue
                Devices[Device].Units[Unit].LastLevel = int(sValue)
                Devices[Device].Units[Unit].Update()
                
                #Devices[Unit].Update(nValue=nValue, sValue=str(sValue), TimedOut=TimedOut)
                Domoticz.Debug("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Device].Units[Unit].Name+")")
            except:
                Domoticz.Log("Update of device failed: "+str(Unit)+"!")
    return
