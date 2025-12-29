# Tahoma/Connexoon IO blind plugin
#
# Author: Nonolk, 2019-2020
#
# All credits for the plugin are for Nonolk, who is the origin plugin creator
"""
<plugin key="tahomaIO" name="Somfy Tahoma or Connexoon plugin" author="MadPatrick" version="5.0.0" externallink="https://github.com/MadPatrick/somfy">
    <description>
        <br/><h2>Somfy Tahoma/Connexoon plugin</h2><br/>
        Version: 5.0.0
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
    </description>
    <params>
        <param field="Username" label="Username" width="200px" required="true" default=""/>
        <param field="Password" label="Password" width="200px" required="true" default="" password="true"/>
        <param field="Mode2" label="Refresh interval (day;night)" width="100px" default="20;900">
            <description>
                <br/>Enter two numbers separated by a ;
                <br/>First for day refresh interval (seconds), second for night refresh interval (seconds)
            </description>
        </param>
        <param field="Mode3" label="Night Delay" width="200px" default="30;60">
            <description>
                <br/>Delay for Sunrise and Sunset
            </description>
        </param>
        <param field="Mode4" label="Connection" width="100px">
            <description>
                <br/>Choose how to interact with the Somfy/Tahoma/Connexoon box:
                <br/>Web API: via Somfy web server (requires continuous internet access)
                <br/>Local API: connect directly to the box (default)
                <br/><br/>Somfy is depreciating the Web access, so it is better to use the local API
            </description>
            <options>
                <option label="Web" value="Web"/>
                <option label="Local" value="Local" default="true"/>
            </options>
        </param>
        <param field="Address" label="Gateway PIN" width="150px" required="true" default="1234-1234-1234"/>
        <param field="Port" label="Portnumber Tahoma box" width="30px" required="true" default="8443"/>
        <param field="Mode1" label="Reset token" width="100px">
            <description>
                Set to true to request a new token. Can be used when you get access denied.
            </description>
            <options>
                <option label="False" value="False"/>
                <option label="True" value="True" default="true"/>
            </options>
        </param>
        <param field="Mode5" label="Log file location" width="200px" default="/var/log">
            <description>
                <br/>Enter a location for the logfile (omit final /), or leave empty to create logfile in the domoticz directory.
                <br/>Default directory: '/var/log' for Linux
            </description>
        </param>
        <param field="Mode6" label="Debug logging" width="100px">
            <options>
                <option label="True" value="Debug" default="true"/>
                <option label="False" value="Normal"/>
            </options>
        </param>
    </params>
</plugin>
"""
# Tahoma/Connexoon IO blind plugin
import DomoticzEx as Domoticz
import json
import sys
import logging
import exceptions
import time
import tahoma
import os
from tahoma_local import SomfyBox
import utils
import requests
import datetime
import urllib.request
class BasePlugin:
    def __init__(self):
        self.enabled = False
        self.heartbeat = False
        self.devices = None
        self.heartbeat_delay = 1
        self.con_delay = 0
        self.wait_delay = 30
        self.command_data = None
        self.command = False
        self.refresh = True
        self.actions_serialized = []
        self.logger = None
        self.log_filename = "somfy.log"
        self.version = ""
        self.local = False
        self.runCounter = 0
        # === NIEUW: Defaults voor externe Domoticz ===
        self.domoticz_host = "127.0.0.1"
        self.domoticz_port = "8080"
        self.last_sunrise = None
        self.last_sunset = None
        self.last_sunrise_date = None
        self.last_sunset_date = None
   
    def onStart(self):
        if os.path.exists(Parameters["Mode5"]):
            log_dir = Parameters["Mode5"]
        else:
            Domoticz.Status("Location {0} does not exist, logging to default location".format(Parameters["Mode5"]))
            log_dir = ""
        log_fullname = os.path.join(log_dir, self.log_filename)
        Domoticz.Log("Starting Tahoma blind plugin, logging to file {0}".format(log_fullname))
        self.logger = logging.getLogger('root')
        if Parameters["Mode6"] == "Debug":
            Domoticz.Debugging(2)
            DumpConfigToLog()
            logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(filename)-18s - %(message)s', filename=log_fullname,level=logging.DEBUG)
        else:
            logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(filename)-18s - %(message)s', filename=log_fullname,level=logging.INFO)
        Domoticz.Debug("os.path.exists(Parameters['Mode5']) = {}".format(os.path.exists(Parameters["Mode5"])))
        logging.info("starting plugin version "+Parameters["Version"])

        # Controleer Mode2 en zet standaard als leeg of ongeldig
        if not Parameters.get('Mode2') or ';' not in Parameters['Mode2']:
            Domoticz.Log("Mode2 leeg of ongeldig, instellen op standaard 300;900")
            Parameters['Mode2'] = "300;900"

        # Controleer Mode3 (sunrise;sunset delay)
        if not Parameters.get('Mode3') or ';' not in Parameters['Mode3']:
            Domoticz.Log("Mode3 leeg of ongeldig, instellen op standaard 30;60")
            Parameters['Mode3'] = "30;60"
        try:
            sr_delay_str, ss_delay_str = Parameters['Mode3'].split(';')
            self.sunriseDelay = int(sr_delay_str.strip())
            self.sunsetDelay = int(ss_delay_str.strip())
        except Exception as e:
            Domoticz.Error("Invalid Mode3 value, using defaults 30;60: " + str(e))
            self.sunriseDelay = 30
            self.sunsetDelay = 60
        try:
            day_str, night_str = Parameters['Mode2'].split(';')
            self.dayInterval = int(day_str.strip())
            self.nightInterval = int(night_str.strip())
        except Exception as e:
            Domoticz.Error("Invalid Mode2 value, using defaults 300,900: " + str(e))
            self.dayInterval = 300
            self.nightInterval = 900
        self.runCounter = self.dayInterval
        Domoticz.Heartbeat(1)
       
        # === NIEUW: config.txt inlezen voor externe Domoticz ===
        config_path = os.path.join(os.path.dirname(__file__), "config.txt")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip().upper()
                            value = value.strip()
                            if key == "DOMOTICZ_HOST":
                                self.domoticz_host = value
                            elif key == "DOMOTICZ_PORT":
                                self.domoticz_port = value
                Domoticz.Log(f"config.txt succesvol gelezen: DOMOTICZ_HOST={self.domoticz_host}, DOMOTICZ_PORT={self.domoticz_port}")
                logging.info(f"config.txt succesvol gelezen: DOMOTICZ_HOST={self.domoticz_host}, DOMOTICZ_PORT={self.domoticz_port}")
            except Exception as e:
                Domoticz.Error(f"Fout bij lezen config.txt: {e}. Gebruik defaults: {self.domoticz_host}:{self.domoticz_port}")
                logging.error(f"Fout bij lezen config.txt: {e}")
        else:
            Domoticz.Status("config.txt niet gevonden in plugin-map. Gebruik defaults: 127.0.0.1:8080 voor sunrise/sunset API")
            logging.warning("config.txt niet gevonden, gebruik defaults")

        #check upgrading of version needs actions
        self.version = Parameters["Version"]
        self.enabled = self.checkVersion(self.version)
        if not self.enabled:
            return False
        pin = Parameters["Address"]
        port = int(Parameters["Port"])
       
        logging.debug("starting to log in with mode " + Parameters["Mode4"])
        if Parameters["Mode4"] == "Local":
            self.tahoma = SomfyBox(pin, port)
            self.local = True
        else:
            self.tahoma = tahoma.Tahoma()
            self.local = False
        try:
            self.tahoma.tahoma_login(str(Parameters["Username"]), str(Parameters["Password"]))
        except exceptions.LoginFailure as exp:
            Domoticz.Error("Failed to login: " + str(exp))
            return False
       
        if self.tahoma.logged_in:
            if self.local:
                logging.debug("check if token stored in configuration")
                confToken = getConfigItem('token', '0')
                if confToken == '0' or Parameters["Mode1"] == "True":
                    logging.debug("no token found, generate a new one")
                    self.tahoma.generate_token(pin)
                    self.tahoma.activate_token(pin,self.tahoma.token)
                    #store token for later use (not generate one at each start)
                    setConfigItem('token', self.tahoma.token)
                    Parameters["Mode1"] = "False"
                else:
                    logging.debug("found token in configuration: "+str(confToken))
                    self.tahoma.token = confToken
                self.tahoma.register_listener()
            else:
                self.tahoma.register_listener()
        if self.tahoma.logged_in and firstFree() < 249:
            filtered_devices = self.tahoma.get_devices()
            self.create_devices(filtered_devices)
            self.update_devices_status(utils.filter_states(filtered_devices))
        return True
           
    def onStop(self):
        logging.info("stopping plugin")
        self.heartbeat = False

    def onConnect(self, Connection, Status, Description):
        logging.debug("onConnect: Connection: '"+str(Connection)+"', Status: '"+str(Status)+"', Description: '"+str(Description)+"' self.tahoma.logged_in: '"+str(self.tahoma.logged_in)+"'")
        if (Status == 0 and not self.tahoma.logged_in):
          self.tahoma.tahoma_login(str(Parameters["Username"]), str(Parameters["Password"]))
        elif (self.cookie and self.tahoma.logged_in and (not self.command)):
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

    def onMessage(self, Connection, Data):
        Domoticz.Error("onMessage called but not implemented")
        Domoticz.Debug("onMessage data: "+str(Data))

    def onCommand(self, DeviceId, Unit, Command, Level, Hue):
        logging.debug("onCommand: DeviceId: '"+str(DeviceId)+"' Unit: '"+str(Unit)+"', Command: '"+str(Command)+"', Level: '"+str(Level)+"', Hue: '"+str(Hue)+"'")
        commands_serialized = []
        action = {}
        commands = {}
        params = []
       
        if Unit == 1:
            # unit 1 used for up/down movement
            if (str(Command) == "Off" or str(Command) == "Close"):
                commands["name"] = "close"
            elif (str(Command) == "On" or str(Command) == "Open"):
                commands["name"] = "open"
            elif (str(Command) == "Stop"):
                commands["name"] = "stop"
            elif ("Set Level" in str(Command)):
                commands["name"] = "setClosure"
                tmp = max(100 - int(Level), 0) #invert open/close percentage
                #tmp = max(int(Level), 0)
                params.append(tmp)
                #params.append(int(Level))
                commands["parameters"] = params
        elif Unit == 2:
            # unit 2 used for orientation in venetian blinds
            if ("Set Level" in str(Command)):
                commands["name"] = "setOrientation"
                tmp = max(100 - int(Level), 1) #orientation does not accept 0
                #tmp = max(int(Level), 1) #orientation does not accept 0
                params.append(tmp)
                commands["parameters"] = params
            else:
                logging.error("command "+str(Command)+" not supported")
                return False
        else:
            logging.error("unit not supported")
            return False
        commands_serialized.append(commands)
        action["deviceURL"] = DeviceId
        action["commands"] = commands_serialized
        self.actions_serialized.append(action)
        logging.debug("preparing command: # commands: "+str(len(commands)))
        logging.debug("preparing command: # actions_serialized: "+str(len(self.actions_serialized)))
        data = {"label": "Domoticz - "+Devices[DeviceId].Units[Unit].Name+" - "+commands["name"], "actions": self.actions_serialized}
        if self.local:
            self.command_data = data
        else:
            self.command_data = json.dumps(data, indent=None, sort_keys=True)
        logging.debug("preparing command: json data: "+str(self.command_data))
        if (not self.tahoma.logged_in):
            logging.info("Not logged in, must connect")
            self.command = True
            self.tahoma.tahoma_login(str(Parameters["Username"]), str(Parameters["Password"]))
            if self.tahoma.logged_in:
                self.tahoma.register_listener()
        event_list = []
        try:
            self.tahoma.send_command(self.command_data)
        except (exceptions.TooManyRetries, exceptions.FailureWithErrorCode, exceptions.FailureWithoutErrorCode) as exp:
            Domoticz.Error("Failed to send command: " + str(exp))
            logging.error("Failed to send command: " + str(exp))
            if not self.local:
                #clear list of (failed) actions for Connexoon
                self.actions_serialized = []
            return False
        self.actions_serialized = []
        if not self.tahoma.listener.valid:
            self.tahoma.register_listener()
        try:
            event_list = self.tahoma.get_events()
        except (exceptions.TooManyRetries, exceptions.FailureWithErrorCode, exceptions.FailureWithoutErrorCode) as exp:
            Domoticz.Error("Failed to get events: " + str(exp))
            logging.error("Failed to get events: " + str(exp))
            return False
        if event_list is not None and len(event_list) > 0:
            self.update_devices_status(event_list)
            self.heartbeat = False
        if self.tahoma.logged_in == False:
            #in case the send_command detected an error due to not logged in: force a heartbeat to get logged in again
            self.heartbeat = True
        return True

    def onDisconnect(self, Connection):
        return

    def onHeartbeat(self):
        self.runCounter -= 1
        if not self.enabled:
            return False

        now = datetime.datetime.now()
        now_minutes = now.hour * 60 + now.minute
        today = datetime.date.today()

        # === Ophalen van sunrise/sunset slechts 1 keer per dag ===
        if self.last_sunrise_date != today or self.last_sunset_date != today:
            api_url = f"http://{self.domoticz_host}:{self.domoticz_port}/json.htm?type=command&param=getSunRiseSet"
            try:
                with urllib.request.urlopen(api_url, timeout=10) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    sunrise_full = data.get("Sunrise", "06:00:00")
                    sunset_full = data.get("Sunset", "22:00:00")
                    self.last_sunrise = sunrise_full[:5]
                    self.last_sunset = sunset_full[:5]
                    self.last_sunrise_date = today
                    self.last_sunset_date = today
                Domoticz.Debug(f"Sunrise/sunset opgehaald van {api_url} (sunrise: {self.last_sunrise}, sunset: {self.last_sunset})")
                logging.debug(f"Sunrise/sunset van {api_url}: {self.last_sunrise} / {self.last_sunset}")
            except Exception as e:
                Domoticz.Error(f"Kon sunrise/sunset niet ophalen van {api_url}. Gebruik fallback tijden (06:00/22:00). Fout: {e}")
                if not self.last_sunrise:
                    self.last_sunrise = "06:00"
                if not self.last_sunset:
                    self.last_sunset = "22:00"

        # Converteer naar minuten
        sr_hour, sr_min = map(int, self.last_sunrise.split(':'))
        ss_hour, ss_min = map(int, self.last_sunset.split(':'))
        sunrise = sr_hour * 60 + sr_min
        sunset = ss_hour * 60 + ss_min

        # Bepaal dag/nacht interval
        if sunrise - self.sunriseDelay <= now_minutes < sunset + self.sunsetDelay:
            interval = self.dayInterval
            status = "Day"
            next_switch_dt = now.replace(hour=ss_hour, minute=ss_min, second=0) + datetime.timedelta(minutes=self.sunsetDelay)
        else:
            interval = self.nightInterval
            status = "Night"
            next_switch_dt = now.replace(hour=sr_hour, minute=sr_min, second=0) - datetime.timedelta(minutes=self.sunriseDelay)

        if next_switch_dt < now:
            next_switch_dt += datetime.timedelta(days=1)

        # Log alleen als sunrise, sunset of interval veranderd
        changed = False
        if getattr(self, 'last_logged_sunrise', None) != self.last_sunrise or getattr(self, 'last_logged_sunset', None) != self.last_sunset:
            changed = True
            self.last_logged_sunrise = self.last_sunrise
            self.last_logged_sunset = self.last_sunset
        if getattr(self, 'last_logged_interval', None) != interval:
            changed = True
            self.last_logged_interval = interval

        if changed:
            Domoticz.Log(f"Time={now.strftime('%H:%M')} sunrise={self.last_sunrise} sunset={self.last_sunset}")
            Domoticz.Log(f"Refresh interval={interval} Seconds ({status}) until {next_switch_dt.strftime('%H:%M')}")

        # Poll Somfy box als counter op nul staat of heartbeat trigger actief
        if self.runCounter <= 0 or self.heartbeat:
            if self.local or (self.tahoma.logged_in and not getattr(self.tahoma, 'startup', False)):
                try:
                    filtered_devices = self.tahoma.get_devices()
                    self.update_devices_status(utils.filter_states(filtered_devices))
                    if hasattr(self, 'last_connection_error_time'):
                        del self.last_connection_error_time
                except (exceptions.TooManyRetries, exceptions.FailureWithErrorCode,
                        exceptions.FailureWithoutErrorCode, json.decoder.JSONDecodeError,
                        requests.exceptions.ConnectionError) as exp:
                    now_ts = time.time()
                    if not hasattr(self, 'last_connection_error_time') or (now_ts - self.last_connection_error_time > 60):
                        Domoticz.Error("Somfy: Unable to connect to the local box")
                        Domoticz.Error("This can occur during temporary internet or network interruptions")
                        Domoticz.Error("Next message in 1 minute (silent in between)")
                        short_error = str(exp).split('Caused by')[0].strip()
                        Domoticz.Error(f" Fout: {short_error}")
                        self.last_connection_error_time = now_ts
                except exceptions.NoListenerFailure as exp:
                    Domoticz.Error("Failed to request data: " + str(exp))
                    self.tahoma.register_listener()
            self.runCounter = interval
            self.heartbeat = False

        return True

    def update_devices_status(self, Updated_devices):
        logging.debug("updating device status self.tahoma.startup = "+str(self.tahoma.startup)+" on num datasets: "+str(len(Updated_devices)))
        logging.debug("updating device status on data: "+str(Updated_devices))
        if self.local:
            eventList = utils.filter_events(Updated_devices)
        else:
            eventList = Updated_devices
        num_updates = 0
        logging.debug("checking device updates for "+str(len(eventList))+" filtered events")
        for dataset in eventList:
            #logging.debug("checking dataset for URL: "+str(dataset['deviceURL']))
            logging.debug("checking dataset: "+str(dataset))

            if dataset["deviceURL"] not in Devices:
                Domoticz.Error("device not found for URL: "+str(dataset["deviceURL"]))
                logging.error("device not found for URL: "+str(dataset["deviceURL"])+" while updating states")
                continue #no deviceURL found that matches to domoticz Devices, skip to next dataset

            if (dataset["name"] == "DeviceStateChangedEvent"):

                continue #dataset does not contain correct event, skip to next dataset

            if (dataset["deviceURL"].startswith("io://")):
                dev = dataset["deviceURL"]
                
                # REPARATIE: Gebruik .get() om een KeyError te voorkomen
                deviceClassTrig = dataset.get("deviceClass", "Unknown") 
                
                # Optioneel: Als deviceClass ontbreekt, probeer het uit de bestaande Domoticz device definitie te halen
                if deviceClassTrig == "Unknown" and dev in Devices:
                     # We laten het hier op "Unknown" of je kunt proberen 
                     # het op te zoeken in een eerdere scan.
                     pass                
                level = 0
                status_num = 0
                status = None
                nValue = 0
                sValue = "0"

                states = dataset["deviceStates"]
                if not (dataset["name"] == "DeviceStateChangedEvent" or dataset["name"] == "DeviceState"):
                    logging.debug("update_devices_status: dataset['name'] != DeviceStateChangedEvent: "+str(dataset["name"])+": breaking out")
                    continue #dataset does not contain correct event, skip to next dataset

                for state in states:
                    status_num = 0
                    lumstatus_l = False

                    if ((state["name"] == "core:ClosureState") or (state["name"] == "core:DeploymentState")):
                        if (deviceClassTrig == "Awning"):
                            level = int(state["value"]) #Don't invert open/close percentage for an Awning
                            status_num = 1
                        else:
                            level = int(state["value"])
                            level = 100 - level #invert open/close percentage
                            status_num = 1
                     
                    if ((state["name"] == "core:SlateOrientationState")):
                        level = int(state["value"])
                        #level = 100 - level
                        status_num = 2

                    if (state["name"] == "core:LuminanceState"):
                        lumlevel = state["value"]
                        lumstatus_l = True
                   
                    logging.debug("checking for update on state[name]: '" +state["name"]+"' with status_num = '"+str(status_num)+ "' for device: '"+dev+"'")
                    if status_num > 0:
                        if (Devices[dev].Units[status_num].sValue):
                            int_level = int(Devices[dev].Units[status_num].sValue)
                        else:
                            int_level = 0
                        if (level != int_level):
                            Domoticz.Status("Updating device : "+Devices[dev].Units[status_num].Name)
                            logging.info("Updating device : "+Devices[dev].Units[status_num].Name)
                            if (level == 0):
                                # Devices[dev].Units[status_num].nValue = 0
                                # Devices[dev].Units[status_num].sValue = "0"
                                # Devices[dev].Units[status_num].LastLevel = 0
                                # Devices[dev].Units[status_num].Update()
                                nValue = 0
                                sValue = "0"
                            if (level == 100):
                                # Devices[dev].Units[status_num].nValue = 1
                                # Devices[dev].Units[status_num].sValue = "100"
                                # Devices[dev].Units[status_num].LastLevel = 100
                                # Devices[dev].Units[status_num].Update()
                                nValue = 1
                                sValue = "100"
                            if (level != 0 and level != 100):
                                # Devices[dev].Units[status_num].nValue = 2
                                # Devices[dev].Units[status_num].sValue = str(level)
                                # Devices[dev].Units[status_num].LastLevel = int(level)
                                # Devices[dev].Units[status_num].Update()
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

    def checkVersion(self, version):
        """checks actual version against stored version as 'Ma.Mi.Pa' and checks if updates needed"""
        #read version from stored configuration
        ConfVersion = getConfigItem("plugin version", "0.0.0")
        Domoticz.Log("Starting version: " + version )
        logging.info("Starting version: " + version )
        MaCurrent,MiCurrent,PaCurrent = version.split('.')
        MaConf,MiConf,PaConf = ConfVersion.split('.')
        logging.debug("checking versions: current '{0}', config '{1}'".format(version, ConfVersion))
        can_continue = True
        if int(MaConf) < int(MaCurrent):
            Domoticz.Log("Major version upgrade: {0} -> {1}".format(MaConf,MaCurrent))
            logging.info("Major version upgrade: {0} -> {1}".format(MaConf,MaCurrent))
            #add code to perform MAJOR upgrades
            if int(MaConf) < 3:
                can_continue = self.updateToEx()
        elif int(MiConf) < int(MiCurrent):
            Domoticz.Debug("Minor version upgrade: {0} -> {1}".format(MiConf,MiCurrent))
            logging.debug("Minor version upgrade: {0} -> {1}".format(MiConf,MiCurrent))
            #add code to perform MINOR upgrades
        elif int(PaConf) < int(PaCurrent):
            Domoticz.Debug("Patch version upgrade: {0} -> {1}".format(PaConf,PaCurrent))
            logging.debug("Patch version upgrade: {0} -> {1}".format(PaConf,PaCurrent))
            #add code to perform PATCH upgrades, if any
        if ConfVersion != version and can_continue:
            #store new version info
            self._setVersion(MaCurrent,MiCurrent,PaCurrent)
        return can_continue

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
                if device["label"] in Devices:
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
                else:
                    found = False
        logging.debug("create_devices: finished create devices")

        return len(filtered_devices),created_devices

        #return Devices

    def updateToEx(self):
        """routine to check if we can update to the Domoticz extended plugin framework"""
        if len(Devices)>0:
            Domoticz.Error("Devices are present. Please remove them before upgrading to this version!")
            Domoticz.Error("Plugin will now exit")
            return False
        else:
            return True

    def _setVersion(self, major, minor, patch):
        #set configs
        logging.debug("Setting version to {0}.{1}.{2}".format(major, minor, patch))
        setConfigItem(Key="MajorVersion", Value=major)
        setConfigItem(Key="MinorVersion", Value=minor)
        setConfigItem(Key="patchVersion", Value=patch)
        setConfigItem(Key="plugin version", Value="{0}.{1}.{2}".format(major, minor, patch))
       
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
        Domoticz.Debug("Device: " + str(x) + " - " + str(Devices[x]))
    return

def firstFree():
    """check if there is room to add devices (max 255)"""
    for num in range(1, 254):
        if num not in Devices:
            return num
    return
# Configuration Helpers
def getConfigItem(Key=None, Default={}):
   Value = Default
   try:
       Config = Domoticz.Configuration()
       if (Key != None):
           Value = Config[Key] # only return requested key if there was one
       else:
           Value = Config # return the whole configuration if no key
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
           Config = Value # set whole configuration if no key specified
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
