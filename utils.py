import logging
import exceptions

# States that trigger a Domoticz widget update
stateSet = {
    "core:ClosureState",
    "core:OpenClosedState",
    "core:LuminanceState",
    "core:DeploymentState",
    "core:OpenClosedPartialState",
    "core:OpenClosedPedestrianState",
    "core:SlateOrientationState",
    "core:OnOffState",
    "core:TemperatureState"
}

# Supported uiClasses for io:// and rts:// devices
_SUPPORTED_IO_CLASSES = {
    "RollerShutter",
    "LightSensor",
    "ExteriorScreen",
    "Screen",
    "Awning",
    "Pergola",
    "GarageDoor",
    "Gate",
    "Window",
    "VenetianBlind",
    "ExteriorVenetianBlind",
    "Light",
    "TemperatureSensor"
}


def has_state(device, state_name):
    """True when the device definition or its current states list state_name."""
    definition_states = device.get("definition", {}).get("states", [])
    if any(s.get("qualifiedName") == state_name for s in definition_states):
        return True
    return any(s.get("name") == state_name for s in device.get("states", []))


def is_temperature_device(device):
    """Temperature-only devices: TemperatureSensor sub-devices, or io devices of an
    otherwise unsupported class (e.g. a remote) that report core:TemperatureState."""
    if not device["deviceURL"].startswith("io://"):
        return False
    ui_class = device["definition"]["uiClass"]
    if ui_class == "TemperatureSensor":
        return True
    return ui_class not in _SUPPORTED_IO_CLASSES and has_state(device, "core:TemperatureState")


def filter_devices(Data):
    logging.debug("start filter devices")

    if not any("uiClass" in str(d.get("definition", {})) for d in Data):
        logging.error("filter_devices: missing uiClass in response")
        logging.debug(str(Data))
        return []

    filtered_devices = []
    for device in Data:
        ui_class  = device["definition"]["uiClass"]
        device_url = device["deviceURL"]
        logging.debug("filter_devices: Device name: " + device["label"] + " Device class: " + ui_class)

        is_io_or_rts = device_url.startswith("io://") or device_url.startswith("rts://")
        is_supported_io = ui_class in _SUPPORTED_IO_CLASSES and is_io_or_rts
        if ui_class in ("Light", "TemperatureSensor") and not device_url.startswith("io://"):
            # Only io lights/sensors report state; RTS lights are not supported
            is_supported_io = False
        is_pod = ui_class == "Pod" and device_url.startswith("internal://")

        if is_supported_io or is_pod or is_temperature_device(device):
            filtered_devices.append(device)
            logging.debug("supported device found: " + str(device))
        else:
            logging.debug("unsupported device found: " + str(device))

    logging.debug("finished filter devices")
    return filtered_devices


def filter_events(Data):
    """Filters relevant (DeviceStateChangedEvent / DeviceState) events out of an events list."""
    logging.debug("start filter events")
    filtered_events = []

    for event in Data:
        if event["name"] in ("DeviceStateChangedEvent", "DeviceState"):
            logging.debug(
                "get_events: add event: URL: '" + event["deviceURL"] +
                "' num states: '" + str(len(event["deviceStates"])) + "'"
            )
            for event_state in event["deviceStates"]:
                logging.debug(
                    "   get_events: eventname: '" + event_state["name"] +
                    "' with value: '" + str(event_state["value"]) + "'"
                )
            filtered_events.append(event)

    logging.debug("finished filter events")
    return filtered_events


def filter_states(Data):
    """Filters relevant state data from a device setup API reply."""
    logging.debug("start filter states")
    filtered_states = []

    for device in Data:
        device_url   = device["deviceURL"]
        device_class = device["definition"]["uiClass"]

        if "states" not in device:
            continue

        state_list = [
            state for state in device["states"]
            if state["name"] in stateSet
        ]

        if state_list:
            filtered_states.append({
                "deviceURL":    device_url,
                "deviceStates": state_list,
                "deviceClass":  device_class,
                "name":         "DeviceState"
            })
            logging.debug("Device state: " + str(filtered_states[-1]))

    return filtered_states


_GATEWAY_TYPES = {
    86: "Connexoon IO",
    87: "TaHoma",
    88: "TaHoma Switch",
    89: "Connexoon RTS",
    90: "TaHoma Beecon",
    101: "Cozytouch",
    136: "Rexel Energeasy Connect",
    137: "Hi Kumo",
    162: "Connexoon Window RTS",
}

# Fallback: map the first segment of gatewayId (e.g. "1237" in "1237-2024-7920")
# to a human-readable label for gateways that don't expose a numeric `type` field.
_GATEWAY_ID_PREFIXES = {
    "0240": "Connexoon IO",
    "1237": "TaHoma Switch",
    "2015": "TaHoma",
    "2110": "TaHoma v2",
}


def parse_gateway_info(gateways):
    """Extract a summary dict from the /setup/gateways API response.

    Returns a dict with keys: gateway_id, type_label, connectivity, protocol_version, mode.
    Falls back to empty strings when a field is missing.
    """
    if not gateways:
        return {}
    gw = gateways[0]
    gateway_id = gw.get("gatewayId", "")
    gw_type_int = gw.get("type")
    if gw_type_int is not None:
        type_label = _GATEWAY_TYPES.get(gw_type_int, f"Unknown ({gw_type_int})")
    else:
        prefix = gateway_id.split("-")[0] if gateway_id else ""
        type_label = _GATEWAY_ID_PREFIXES.get(prefix, "TaHoma")
    connectivity = gw.get("connectivity", {})
    return {
        "gateway_id":       gateway_id,
        "type_label":       type_label,
        "connectivity":     connectivity.get("status", ""),
        "protocol_version": connectivity.get("protocolVersion", ""),
        "mode":             gw.get("mode", ""),
    }


def response_json(response, action):
    """Return response JSON or raise a readable plugin exception."""
    try:
        return response.json()
    except ValueError as exc:
        body = getattr(response, "text", "")
        snippet = body.replace("\r", " ").replace("\n", " ")[:200]
        logging.error(
            "invalid JSON during " + action +
            ", status: " + str(getattr(response, "status_code", "unknown")) +
            ", body: " + snippet
        )
        raise exceptions.TahomaException("Invalid JSON response during " + action) from exc


def handle_response(response, action):
    """Raise an appropriate exception for non-2xx HTTP responses."""
    if 200 <= response.status_code < 300:
        return
    if 300 <= response.status_code < 400:
        logging.error("status code " + str(response.status_code) + " this is likely a bug")
        raise exceptions.TahomaException("failed request during " + action + ": " + str(response.status_code))
    elif response.status_code == 400:
        logging.error("status code " + str(response.status_code) + " bad request, check url or body")
        raise exceptions.TahomaException("failed request during " + action + ", check url or body: " + str(response.status_code))
    elif response.status_code == 401:
        logging.error("status code " + str(response.status_code) + " authorisation failed, check credentials")
        raise exceptions.AuthenticationFailure(action)
    elif response.status_code == 404:
        logging.error("status code " + str(response.status_code) + " server not found")
        raise exceptions.TahomaException("failed request during " + action + ", server not found: " + str(response.status_code))
    elif response.status_code >= 500:
        logging.error("status code " + str(response.status_code) + " a server sided problem")
        raise exceptions.TahomaException("failed request during " + action + ": " + str(response.status_code))
    else:
        logging.error("status code " + str(response.status_code))
        raise exceptions.TahomaException("failed request during " + action + ": " + str(response.status_code))
