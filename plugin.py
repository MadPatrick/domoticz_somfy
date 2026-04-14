###################################################################################
# Tahoma/Connexoon IO blind plugin
#
#
# All credits for the plugin are for Nonolk, who is the origin plugin creator
#
#
###################################################################################
"""
<plugin key="tahomaIO" name="Somfy Tahoma or Connexoon plugin" author="MadPatrick" version="5.3.0" externallink="https://github.com/MadPatrick/somfy">
    <description>
        <br/><h2>Somfy Tahoma/Connexoon plugin</h2><br/>
        Version: 5.3.0
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
<table border="1" cellpadding="4" cellspacing="0">
    <tr>
        <th>Parameter</th>
        <th>Description</th>
    </tr>
    <tr>
        <td>Username</td>
        <td>Enter your Somfy login name </td>
    </tr>
    <tr>
        <td>Password</td>
        <td>Enter your Somfy Password</td>
    </tr>
    <tr>
        <td>Connection</td>
        <td>Choose how to interact with the Somfy/Tahoma/Connexoon box:
        <br/>Web: via Somfy web server (requires continuous internet access)
        <br/>Local PIN: connect directly to the box using the Gateway PIN (requires DNS or /etc/hosts entry for &lt;PIN&gt;.local)
        <br/>Local IP: connect directly to the box using an IP address (no DNS required)
        <br/>
        <br/>Somfy is depreciating the Web access, so it is better to use the local API
        <br/>Preferable use the Local IP mode</td>
    </tr>
    <tr>
        <td>Address</td>
        <td>Gateway PIN of the Tahoma box, e.g. 1234-1234-1234.
        <br/>
        <br/>Used for all connection modes to generate and activate the local API token via the Somfy web API.</td>
    </tr>
    <tr>
        <td>Local IP Address</td>
        <td>Only used in Local IP mode. Enter the IP address of the Tahoma box, e.g. 192.168.1.100
        <br/>Leave empty when using Web or Local PIN mode.</td>
    </tr>
    <tr>
        <td>Port</td>
        <td>Portnumber of the Tahoma box (8443)</td>
    </tr>
    <tr>
        <td>Reset token</td>
        <td>Set to True to request a new token. Can be used when you get access denied</td>
    </tr>
    <tr>
        <td>Debug logging</td>
        <td>Set to TRUE to enable debug logging for troubleshooting</td>
    </tr>
    </table>
    <br/>
</description>
    <params>
        <param field="Username" label="Username" width="200px" required="true" default=""/>
        <param field="Password" label="Password" width="200px" required="true" default="" password="true"/>
        <param field="Mode4" label="Connection" width="150px">
            <description><br/>Somfy is depreciating the Web access, so it is better to use the local API</description>
            <options>
                <option label="Web" value="Web"/>
                <option label="Local PIN" value="Local"/>
                <option label="Local IP" value="LocalIP" default="true"/>
            </options>
        </param>
        <param field="Address" label="Gateway PIN" width="175px" required="true" default="1234-1234-1234"/>
        <param field="Mode3" label="Local IP Address" width="175px" default=""/>
        <param field="Port" label="Portnumber Tahoma box" width="100px" required="true" default="8443"/>
        <param field="Mode1" label="Reset token" width="100px">            
            <options>
                <option label="False" value="false" default="true"/>
                <option label="True" value="true" />
            </options>
        </param>
        <param field="Mode6" label="Debug logging" width="100px">
            <options>
                <option label="On" value="Debug"/>
                <option label="Off" value="Normal" default="true"/>
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
import ipaddress

_CONNECTION_DEVICE_ID = "connection_indicator"

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
        self.local_ip_mode = False  # True when Mode4 == "LocalIP"

        # Device / mode tracking
        self._last_mode = None

        # Sunrise/sunset / daily refresh
        self.last_sunrise = None
        self.last_sunset = None
        self.sun_refresh_time = "02:00"  # Fallback
        self.last_sun_refresh_ts = datetime.datetime.min
        self._last_logged_sunrise = None
        self._last_logged_sunset = None
        self.last_interval = None

        self.last_sunrise_ts = None
        self.last_sunset_ts = None

        # Domoticz / polling defaults
        self.domoticz_host = "127.0.0.1"
        self.domoticz_port = "8080"
        self.dayInterval = 30
        self.nightInterval = 900
        self.sunriseDelay = 30
        self.sunsetDelay = 60
        self.temp_delay = 10
        self.temp_time  = 60

        self.temp_interval_end = time.time()

        self.connected = None  # None = unknown, True = connected, False = error
        self._last_connected_time = None
        self._last_error = ""
        self._temp_log_active = False
        self._sun_refreshed_today = None  # type: Optional[datetime.date]  # Track which date we last refreshed
        self._gateway_info = {}

    def onStart(self):
        """
        Plugin initialization.
        Sets up logging, polling intervals, sunrise/sunset delays,
        and TEMP_DELAY / TEMP_TIME from config.txt.
        """
        log_dir = ""
        log_fullname = os.path.join(log_dir, self.log_filename)
        Domoticz.Log(f"Starting Plugin version {Parameters['Version']}")
        Domoticz.Log(f"Logging to file {log_fullname}")

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

        # --- Enable heartbeat ---
        Domoticz.Heartbeat(1)

        # --- Load all settings from config.txt (includes polling intervals) ---
        self.load_config_txt(log=True)

        # --- Set initial runCounter for heartbeat ---
        self.runCounter = self.dayInterval

        self.last_config_day = datetime.datetime.now().day
        self.enabled = True

        # --- Connect to Tahoma/Connexoon box ---
        pin     = Parameters.get("Address", "").strip()
        mode3   = Parameters.get("Mode3", "").strip()
        port    = int(Parameters.get("Port", 8443))
        mode4   = Parameters.get("Mode4", "LocalIP")

        if mode4 == "LocalIP":
            # Mode3 holds the IP address in Local IP mode
            if not mode3:
                Domoticz.Error("Local IP mode: no IP address set in 'Local IP Address' field. Plugin cannot start.")
                return False
            try:
                ipaddress.ip_address(mode3)
            except ValueError:
                Domoticz.Error(f"Invalid IP address in 'Local IP Address' field: '{mode3}'. Plugin cannot start.")
                return False
            self.tahoma = SomfyBox(None, port, ip=mode3)
            self.local       = True
            self.local_ip_mode = True
            Domoticz.Log(f"Local IP connection configured: {mode3}:{port}")
        elif mode4 == "Local":
            self.tahoma = SomfyBox(pin, port)
            self.local       = True
            self.local_ip_mode = False
            Domoticz.Log(f"Local PIN connection configured: {pin}.local:{port}")
        else:
            self.tahoma = tahoma.Tahoma()
            self.local       = False
            self.local_ip_mode = False
            Domoticz.Log("Web connection configured (via Somfy cloud)")

        try:
            self.tahoma.tahoma_login(str(Parameters.get("Username")), str(Parameters.get("Password")))
        except Exception as exp:
            Domoticz.Error("Failed to login: " + str(exp))
            return False

        # pin (Address) is used by setup_and_sync_devices for token management
        self.setup_and_sync_devices(pin)

    def setup_and_sync_devices(self, pin):
        if not self.tahoma.logged_in:
            Domoticz.Error("TaHoma not logged in")
            return False

        # --- TOKEN / LISTENER ---
        if self.local:
            logging.debug("check if token stored in configuration")
            confToken = getConfigItem('token', '0')

            if self.local_ip_mode:
                # In Local IP mode the PIN (Address field) is still available for token generation via web API.
                if confToken == '0' or Parameters["Mode1"].lower() == "true":
                    if not pin or pin == "1234-1234-1234":
                        Domoticz.Error(
                            "Local IP mode: no stored token and no valid Gateway PIN in Address field. "
                            "Please enter the Gateway PIN in the Address field so a token can be generated."
                        )
                        self.enabled = False
                        return False
                    logging.debug("no token found (LocalIP mode), generating a new one using PIN")
                    self.tahoma.generate_token(pin)
                    self.tahoma.activate_token(pin, self.tahoma.token)
                    setConfigItem('token', self.tahoma.token)
                    setConfigItem('token_created', datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
                    Domoticz.Log("Token created (LocalIP mode)")
                else:
                    logging.debug("found token in configuration (LocalIP mode): " + str(confToken))
                    self.tahoma.token = confToken
                    Domoticz.Log("Token present (LocalIP mode), loaded from configuration")
            else:
                if confToken == '0' or Parameters["Mode1"].lower() == "true":
                    logging.debug("no token found, generate a new one")
                    self.tahoma.generate_token(pin)
                    self.tahoma.activate_token(pin, self.tahoma.token)
                    setConfigItem('token', self.tahoma.token)
                    setConfigItem('token_created', datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
                    Domoticz.Log("Token created")
                else:
                    logging.debug("found token in configuration: " + str(confToken))
                    self.tahoma.token = confToken
                    Domoticz.Log("Token present, loaded from configuration")

        try:
            self.tahoma.register_listener()
        except Exception as e:
            Domoticz.Error(f"Connection failed during startup: {e}")
            self.enabled = False
            return False

        # --- DEVICES OPHALEN ---
        try:
            filtered_devices = self.tahoma.get_devices()
        except exceptions.AuthenticationFailure:
            if self.local:
                if self.local_ip_mode:
                    if not pin or pin == "1234-1234-1234":
                        Domoticz.Error(
                            "Local IP mode: stored token rejected and no valid Gateway PIN in Address field. "
                            "Please enter the Gateway PIN in Address and set Reset token to True."
                        )
                        self.enabled = False
                        return False
                    Domoticz.Log("Local IP mode: stored token rejected (401), regenerating token using PIN...")
                    try:
                        self.tahoma.generate_token(pin)
                        self.tahoma.activate_token(pin, self.tahoma.token)
                        setConfigItem('token', self.tahoma.token)
                        setConfigItem('token_created', datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
                        Domoticz.Log("Token refreshed (LocalIP mode)")
                        self.tahoma.register_listener()
                        filtered_devices = self.tahoma.get_devices()
                    except Exception as retry_e:
                        Domoticz.Error("Failed to get devices after token regeneration: " + str(retry_e))
                        self.enabled = False
                        return False
                else:
                    Domoticz.Log("Stored token rejected (401), regenerating token...")
                    try:
                        self.tahoma.generate_token(pin)
                        self.tahoma.activate_token(pin, self.tahoma.token)
                        setConfigItem('token', self.tahoma.token)
                        setConfigItem('token_created', datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
                        Domoticz.Log("Token refreshed")
                        self.tahoma.register_listener()
                        filtered_devices = self.tahoma.get_devices()
                    except Exception as retry_e:
                        Domoticz.Error("Failed to get devices after token regeneration: " + str(retry_e))
                        self.enabled = False
                        return False
            else:
                Domoticz.Error("Failed to get devices: authentication failure")
                self.enabled = False
                return False
        except exceptions.TahomaException as e:
            Domoticz.Error("Failed to get devices: " + str(e))
            self.enabled = False
            return False

        self.create_devices(filtered_devices)

        # --- GATEWAY INFO OPHALEN (alleen local) ---
        if self.local:
            try:
                gateways = self.tahoma.get_gateways()
                self._gateway_info = utils.parse_gateway_info(gateways)
                Domoticz.Log(
                    "Gateway: {type_label} (id={gateway_id}) | Status: {connectivity} | "
                    "FW: {protocol_version} | Mode: {mode}".format(**self._gateway_info)
                )
                logging.debug("Gateway info: " + str(self._gateway_info))
            except Exception as e:
                Domoticz.Error("Failed to get gateway info: " + str(e))
                logging.error("Failed to get gateway info: " + str(e))

        self.create_connection_device()

        # --- STATUS UPDATEN ---
        self.update_devices_status(utils.filter_states(filtered_devices))

        self._last_connected_time = datetime.datetime.now()
        self.update_connection_device(True)

        return True

    def onStop(self):
        logging.info("Plugin stopped")
        Domoticz.Log("Plugin stopped")
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
        Refresh sunrise/sunset daily from Domoticz JSON API.
        - On first call after (re)start: always refresh once.
        - After that: refresh once per day at sun_refresh_time.
        Uses an in-memory date flag to prevent repeated refreshes within the same session.
        """
        now = datetime.datetime.now()
        today = now.date()

        # Determine if a refresh is needed
        first_refresh = self._sun_refreshed_today is None

        if not first_refresh:
            try:
                refresh_hour, refresh_min = map(int, self.sun_refresh_time.split(":"))
                refresh_time_passed = (now.hour, now.minute) >= (refresh_hour, refresh_min)
                daily_refresh_needed = refresh_time_passed and self._sun_refreshed_today < today
            except Exception:
                daily_refresh_needed = False
        else:
            daily_refresh_needed = False

        if not first_refresh and not daily_refresh_needed:
            return

        try:
            api_url = f"http://{self.domoticz_host}:{self.domoticz_port}/json.htm?type=command&param=getSunRiseSet"
            with urllib.request.urlopen(api_url, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                sunrise_full = data.get("Sunrise", "06:00:00")
                sunset_full  = data.get("Sunset", "22:00:00")

                self.last_sunrise = sunrise_full[:5]
                self.last_sunset  = sunset_full[:5]

                self.last_sunrise_ts = now.replace(
                    hour=int(self.last_sunrise.split(":")[0]),
                    minute=int(self.last_sunrise.split(":")[1]),
                    second=0, microsecond=0
                )
                self.last_sunset_ts = now.replace(
                    hour=int(self.last_sunset.split(":")[0]),
                    minute=int(self.last_sunset.split(":")[1]),
                    second=0, microsecond=0
                )

            Domoticz.Log(
                f"Sunrise/sunset refreshed @ {now.strftime('%H:%M')}: "
                f"sunrise={self.last_sunrise} sunset={self.last_sunset} | "
                + self._day_night_times_str()
            )

        except Exception as e:
            Domoticz.Error(f"Sunrise/sunset couldn't be loaded: {e}")
            if not self.last_sunrise:
                self.last_sunrise = "06:00"
            if not self.last_sunset:
                self.last_sunset = "22:00"

        # Mark today as refreshed regardless of success/failure
        self._sun_refreshed_today = today

    def _day_night_times_str(self):
        """Returns a formatted string with day/night start times based on sunrise/sunset + delays."""
        if not self.last_sunrise or not self.last_sunset:
            return ""

        sr_hour, sr_min = map(int, self.last_sunrise.split(':'))
        ss_hour, ss_min = map(int, self.last_sunset.split(':'))

        day_start_min   = sr_hour * 60 + sr_min - self.sunriseDelay
        night_start_min = ss_hour * 60 + ss_min + self.sunsetDelay

        day_str   = f"{day_start_min // 60:02d}:{day_start_min % 60:02d}"
        night_str = f"{night_start_min // 60:02d}:{night_start_min % 60:02d}"

        return f"Day starts {day_str} | Night starts {night_str}"

    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage called (not implemented). Data: " + str(Data))

    def onCommand(self, DeviceId, Unit, Command, Level, Hue):
        Domoticz.Debug(f"onCommand: DeviceId: {DeviceId}, Unit: {Unit}, Command: {Command}, Level: {Level}, Hue: {Hue}")
        self.actions_serialized = []
        commands_serialized = []
        action = {}
        commands = {}
        params = []

        if Unit == 1:
            if Command in ("Off", "Close"):
                commands["name"] = "close"
            elif Command in ("On", "Open"):
                commands["name"] = "open"
            elif Command == "Stop":
                commands["name"] = "stop"
            elif "Set Level" in Command:
                commands["name"] = "setClosure"
                tmp = max(100 - int(Level), 0)
                params.append(tmp)
                commands["parameters"] = params
            else:
                Domoticz.Error(f"Command {Command} not supported for unit 1")
                return False
        elif Unit == 2:
            if "Set Level" in Command:
                commands["name"] = "setOrientation"
                tmp = max(100 - int(Level), 1)
                params.append(tmp)
                commands["parameters"] = params
            else:
                Domoticz.Error(f"Command {Command} not supported for unit 2")
                return False
        else:
            Domoticz.Error(f"Unit {Unit} not supported")
            return False

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

        if not self.tahoma.logged_in:
            Domoticz.Log("Not logged in, trying to login")
            self.command = True
            try:
                self.tahoma.tahoma_login(str(Parameters["Username"]), str(Parameters["Password"]))
            except Exception as e:
                Domoticz.Error(f"Login mislukt, commando wordt afgebroken: {e}")
                return False

            if not self.tahoma.logged_in:
                Domoticz.Error("Login mislukt (geen exception), commando wordt afgebroken")
                return False

            try:
                self.tahoma.register_listener()
            except Exception as e:
                Domoticz.Error(f"register_listener mislukt na login: {e}")
                return False

        # Send command
        try:
            self.tahoma.send_command(self.command_data)
            self.temp_interval_end = time.time() + self.temp_time
            self.runCounter = 0

        except (exceptions.TooManyRetries,
                exceptions.FailureWithErrorCode,
                exceptions.FailureWithoutErrorCode,
                Exception) as exp:
            Domoticz.Error(f"Failed to send command: {exp}")
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

        today = datetime.datetime.now().day
        if today != self.last_config_day:
            Domoticz.Log("New day detected, config.txt reloaded")
            self.load_config_txt(log=True)
            self.last_config_day = today

        self.refresh_daily_data()

        # Seed last-known values after first refresh so log_changes
        # does not report spurious "changed from None" on first heartbeat
        if self._last_logged_sunrise is None:
            self._last_logged_sunrise = self.last_sunrise
        if self._last_logged_sunset is None:
            self._last_logged_sunset = self.last_sunset

        now = datetime.datetime.now()
        now_minutes = now.hour * 60 + now.minute

        sunrise_str = self.last_sunrise or "06:00"
        sunset_str  = self.last_sunset  or "22:00"

        sr_hour, sr_min = map(int, sunrise_str.split(":"))
        ss_hour, ss_min = map(int, sunset_str.split(":"))

        sunrise_minutes = sr_hour * 60 + sr_min
        sunset_minutes  = ss_hour * 60 + ss_min

        if sunrise_minutes - self.sunriseDelay <= now_minutes < sunset_minutes + self.sunsetDelay:
            standard_interval = self.dayInterval
            status_label = "DAY-MODE"
        else:
            standard_interval = self.nightInterval
            status_label = "NIGHT-MODE"

        if self._last_mode != status_label:
            Domoticz.Status(f"Mode switched to {status_label}. Polling interval is now {standard_interval}s")
            logging.info(f"Mode switched to {status_label}. Polling interval is now {standard_interval}s")
            self._last_mode = status_label

        # Seed last_interval on first heartbeat so log_changes won't report a spurious change
        if self.last_interval is None:
            self.last_interval = standard_interval

        self.log_changes(standard_interval, self.last_sunrise, self.last_sunset, status_label)

        # Temporary fast polling after command
        if time.time() < self.temp_interval_end:
            interval = self.temp_delay
            if not self._temp_log_active:
                remaining = math.ceil(self.temp_interval_end - time.time())
                Domoticz.Status(f"Action detected! Fast polling ({self.temp_delay}s) active for {remaining}s")
                self._temp_log_active = True
        else:
            interval = standard_interval
            if self._temp_log_active:
                Domoticz.Status(f"Fast polling ended. Returning to standard interval ({interval}s)")
                self._temp_log_active = False

        if self.runCounter <= 0 or self.heartbeat:

            try:
                if self.local:
                    filtered_devices = self.tahoma.get_devices()
                else:
                    if not self.tahoma.logged_in:
                        self.tahoma.tahoma_login(str(Parameters["Username"]), str(Parameters["Password"]))
                    filtered_devices = None

                if self.connected is False:
                    Domoticz.Log("Connection restored")
                self.connected = True
                self._last_error = ""
                self._last_connected_time = datetime.datetime.now()
                self.update_connection_device(True)

            except Exception as e:
                msg = str(e).lower()
                if "no route to host" in msg:
                    short = "No route to host"
                elif "connection refused" in msg:
                    short = "Connection refused"
                elif "timed out" in msg:
                    short = "Connection timed out"
                else:
                    short = "Connection failed"

                if self.connected is True or self.connected is None:
                    Domoticz.Error(f"{short} (box not reachable)")
                    self._last_error = short
                    self.update_connection_device(False)
                self.connected = False
                filtered_devices = None

            if self.connected:
                try:
                    if not self.local:
                        filtered_devices = self.tahoma.get_devices()
                    if filtered_devices is not None:
                        self.update_devices_status(utils.filter_states(filtered_devices))
                except Exception:
                    pass

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
                continue

            if dataset["deviceURL"].startswith("io://"):
                dev = dataset["deviceURL"]
                deviceClassTrig = dataset.get("deviceClass")
                level = None
                status_num = 0
                nValue = 0
                sValue = "0"

                states = dataset["deviceStates"]
                if not (dataset["name"] == "DeviceStateChangedEvent" or dataset["name"] == "DeviceState"):
                    Domoticz.Debug("update_devices_status: dataset['name'] != DeviceStateChangedEvent: "+str(dataset["name"])+": breaking out")
                    continue

                lumstatus_l = False
                lumlevel = 0

                for state in states:
                    if state["name"] in ("core:ClosureState", "core:DeploymentState"):
                        raw_level = max(0, min(int(state["value"]), 100))
                        if deviceClassTrig == "Awning":
                            level = raw_level
                        else:
                            level = 100 - raw_level
                        status_num = 1

                    elif state["name"] == "core:SlateOrientationState":
                        level = int(state["value"])
                        status_num = 2

                    elif state["name"] == "core:LuminanceState":
                        lumlevel = state["value"]
                        lumstatus_l = True

                    elif state["name"] in ("core:OpenClosedPedestrianState", "core:OpenClosedPartialState"):
                        if state["value"] == "closed":
                            level = 0
                        elif state["value"] == "open":
                            level = 100
                        status_num = 1

                    Domoticz.Debug("checking for update on state[name]: '" + state["name"] + "' with status_num = '" + str(status_num) + "' for device: '" + dev + "'")

                    if status_num > 0 and level is not None:
                        if Devices[dev].Units[status_num].sValue:
                            int_level = int(Devices[dev].Units[status_num].sValue)
                        else:
                            int_level = 0
                        if level != int_level:
                            Domoticz.Status("Updating device : " + Devices[dev].Units[status_num].Name)
                            logging.info("Updating device : " + Devices[dev].Units[status_num].Name)
                            if level == 0:
                                nValue = 0
                                sValue = "0"
                            elif level == 100:
                                nValue = 1
                                sValue = "100"
                            else:
                                nValue = 2
                                sValue = str(level)
                            UpdateDevice(dev, status_num, nValue, sValue)

                if lumstatus_l:
                    try:
                        int_lumlevel = float(Devices[dev].Units[1].sValue or 0)
                    except (ValueError, TypeError):
                        int_lumlevel = 0
                    if float(lumlevel) != int_lumlevel:
                        Domoticz.Status("Updating device : " + Devices[dev].Units[1].Name)
                        logging.info("Updating device : " + Devices[dev].Units[1].Name)
                        if lumlevel not in (0, 120000):
                            nValue = 3
                            sValue = str(lumlevel)
                            UpdateDevice(dev, 1, nValue, sValue)

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

        logging.debug("New device(s) detected")
        for device in filtered_devices:
            if type(device) is str:
                logging.debug("create_device: device in filter_list is of type string, need to convert")
                device = json.loads(device)

            logging.debug("create_devices: check if need to create device: "+device["label"])

            if device["deviceURL"] in Devices:
                logging.debug("create_devices: device bestaat al, overslaan: " + device["label"])
                continue

            swtype = None
            logging.debug("create_devices: Must create new device: "+device["label"])

            if device["deviceURL"].startswith("io://") or device["deviceURL"].startswith("rts://"):
                deviceType = 244
                swtype = 13
                subtype2 = 73
                used = 1
                if device["definition"]["uiClass"] == "Awning":
                    swtype = 13
                elif device["definition"]["uiClass"] in ("GarageDoor","Gate"):
                    """ Garage Door and Gate are created as Inverted Door Lock """
                    swtype = 20
                elif device["definition"]["uiClass"] == "RollerShutter":
                    deviceType = 244
                    swtype = 21
                    subtype2 = 73
                elif device["definition"]["uiClass"] == "LightSensor":
                    deviceType = 246
                    swtype = 12
                    subtype2 = 1
            elif device["definition"]["uiClass"] == "Pod":
                deviceType = 244
                subtype2 = 73
                swtype = 9
                used = 0

            created_devices += 1
            Domoticz.Device(DeviceID=device["deviceURL"])
            if device["definition"]["uiClass"] in ("VenetianBlind", "ExteriorVenetianBlind"):
                Domoticz.Unit(Name=device["label"] + " up/down", Unit=1, Type=deviceType, Subtype=subtype2, Switchtype=swtype, DeviceID=device["deviceURL"], Used=used).Create()
                Domoticz.Unit(Name=device["label"] + " orientation", Unit=2, Type=244, Subtype=73, Switchtype=swtype, DeviceID=device["deviceURL"], Used=used).Create()
            else:
                Domoticz.Unit(Name=device["label"], Unit=1, Type=deviceType, Subtype=subtype2, Switchtype=swtype, DeviceID=device["deviceURL"], Used=used).Create()

            logging.info("New device created: "+device["label"])
            Domoticz.Log("New device created: "+device["label"])

        logging.debug("create_devices: finished create devices")
        return len(filtered_devices), created_devices

    def create_connection_device(self):
        if _CONNECTION_DEVICE_ID not in Devices:
            Domoticz.Device(DeviceID=_CONNECTION_DEVICE_ID)
            Domoticz.Unit(
                Name="Somfy Connection Status",
                Unit=1,
                Type=243,
                Subtype=22,
                DeviceID=_CONNECTION_DEVICE_ID,
                Used=1
            ).Create()
            Domoticz.Log("Connection indicator device created")
            logging.info("Connection indicator device created")

    def update_connection_device(self, connected):
        if _CONNECTION_DEVICE_ID not in Devices:
            return
        if self.local_ip_mode:
            conn_type = "Local IP"
        elif self.local:
            conn_type = "Local PIN"
        else:
            conn_type = "Web"
        if connected:
            nValue = 1
            gw = self._gateway_info
            type_label = gw.get("type_label", "")
            protocol = gw.get("protocol_version", "")
            status = gw.get("connectivity", "")
            line1 = f"Connect - {conn_type} API | {type_label}" if type_label else f"Connect - {conn_type} API"
            line2 = f"FW : {protocol} | Status: {status}" if protocol or status else ""
            if self.local:
                token_created = getConfigItem('token_created', '')
                line3 = f"Token created: {token_created}" if token_created else "Token: present"
            else:
                line3 = ""
            parts = [p for p in [line1, line2, line3] if p]
            sValue = "\n".join(parts)
        else:
            error = self._last_error if self._last_error else "unknown"
            nValue = 4
            sValue = f"Disconnected | Error: {error}"
        unit = Devices[_CONNECTION_DEVICE_ID].Units[1]
        if unit.nValue != nValue or unit.sValue != sValue:
            unit.nValue = nValue
            unit.sValue = sValue
            unit.Update()
            logging.info(f"Connection device updated: {sValue}")

    def load_config_txt(self, log=False):
        config_path = os.path.join(os.path.dirname(__file__), "config.txt")
        if not os.path.exists(config_path):
            if log:
                Domoticz.Status("config.txt not found at " + config_path)
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
                    elif key == "DAY_INTERVAL":
                        try:
                            self.dayInterval = int(val)
                        except ValueError:
                            Domoticz.Error(f"Invalid DAY_INTERVAL value in config.txt: {val}")
                    elif key == "NIGHT_INTERVAL":
                        try:
                            self.nightInterval = int(val)
                        except ValueError:
                            Domoticz.Error(f"Invalid NIGHT_INTERVAL value in config.txt: {val}")
                    elif key == "TEMP_DELAY":
                        try:
                            self.temp_delay = int(val)
                        except ValueError:
                            Domoticz.Error(f"Invalid TEMP_DELAY value in config.txt: {val}")
                    elif key == "TEMP_TIME":
                        try:
                            self.temp_time = int(val)
                        except ValueError:
                            Domoticz.Error(f"Invalid TEMP_TIME value in config.txt: {val}")
                    elif key == "SUN_REFRESH_TIME":
                        self.sun_refresh_time = val  # expected format "HH:MM"
                    elif key == "SUNRISE_DELAY":
                        try:
                            self.sunriseDelay = int(val)
                        except ValueError:
                            Domoticz.Error(f"Invalid SUNRISE_DELAY value in config.txt: {val}")
                    elif key == "SUNSET_DELAY":
                        try:
                            self.sunsetDelay = int(val)
                        except ValueError:
                            Domoticz.Error(f"Invalid SUNSET_DELAY value in config.txt: {val}")

            if log:
                Domoticz.Log("Config.txt loaded.")
                # Domoticz.Log(
                #     f"Domoticz @ {self.domoticz_host}:{self.domoticz_port} | "
                #     f"Polling intervals Day / Night: {self.dayInterval}s / {self.nightInterval}s | "
                #     f"Temp: {self.temp_delay}s delay for {self.temp_time}s | "
                #     f"Sunset and Sunrise refresh time: {self.sun_refresh_time} | "
                #     f"Sunrise delay: {self.sunriseDelay}m, Sunset delay: {self.sunsetDelay}m"
                # )
        except Exception as e:
            Domoticz.Error(f"Error in load_config_txt: {str(e)}")

    def log_changes(self, interval, sunrise_str, sunset_str, status_label):
        """Logs changes in interval, sunrise, and sunset, only if they differ from last known values."""
        sunrise_changed  = self._last_logged_sunrise != sunrise_str
        sunset_changed   = self._last_logged_sunset  != sunset_str
        interval_changed = self.last_interval != interval

        if interval_changed:
            Domoticz.Log(f"Polling interval changed to {interval}s")

        if sunrise_changed or sunset_changed:
            Domoticz.Log(
                f"Sun times changed: sunrise {self._last_logged_sunrise} -> {sunrise_str} | "
                f"sunset {self._last_logged_sunset} -> {sunset_str}"
            )

        self.last_interval        = interval
        self._last_logged_sunrise = sunrise_str
        self._last_logged_sunset  = sunset_str


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
            Domoticz.Debug("Configuration '" + x + "':'" + str(Configurations[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
    return

#############
# Configuration Helpers
#############

def getConfigItem(Key=None, Default={}):
    Value = Default
    try:
        Config = Domoticz.Configuration()
        if Key is not None:
            Value = Config[Key]
        else:
            Value = Config
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
        if Key is not None:
            Config[Key] = Value
        else:
            Config = Value
        Config = Domoticz.Configuration(Config)
    except Exception as inst:
        Domoticz.Error("Domoticz.Configuration operation failed: '"+str(inst)+"'")
    return Config

def UpdateDevice(Device, Unit, nValue, sValue, AlwaysUpdate=False):
    if Device in Devices:
        logging.debug("Updating device " + Devices[Device].Units[Unit].Name +
                      " with current sValue '" + Devices[Device].Units[Unit].sValue +
                      "' to '" + sValue + "'")
        if (Devices[Device].Units[Unit].nValue != nValue) or (Devices[Device].Units[Unit].sValue != sValue):
            try:
                Devices[Device].Units[Unit].nValue = nValue
                Devices[Device].Units[Unit].sValue = sValue
                Devices[Device].Units[Unit].LastLevel = int(sValue)
                Devices[Device].Units[Unit].Update()
                Domoticz.Debug("Update " + str(nValue) + ":'" + str(sValue) + "' (" + Devices[Device].Units[Unit].Name + ")")
            except Exception as e:
                Domoticz.Log("Update of device failed: " + str(Unit) + " - " + str(e))
    return
