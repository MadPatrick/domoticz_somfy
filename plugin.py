    def onCommand(self, DeviceId, Unit, Command, Level, Hue):
        Domoticz.Debug(f"onCommand: DeviceId: {DeviceId}, Unit: {Unit}, Command: {Command}, Level: {Level}, Hue: {Hue}")
        
        # Original command handling
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
                self._login_fail_count += 1
                Domoticz.Error(f"Login mislukt, commando wordt afgebroken: {e}")
                if self._login_fail_count >= self._max_login_failures:
                    self._do_reconnect()
                return False

            if not self.tahoma.logged_in:
                self._login_fail_count += 1
                Domoticz.Error("Login mislukt (geen exception), commando wordt afgebroken")
                if self._login_fail_count >= self._max_login_failures:
                    self._do_reconnect()
                return False

            self._login_fail_count = 0

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
