import sys
import types
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


fake_domoticz = types.ModuleType("DomoticzEx")
fake_domoticz.Debug = lambda message: None
fake_domoticz.Debugging = lambda level: None
fake_domoticz.Error = lambda message: None
fake_domoticz.Heartbeat = lambda seconds: None
fake_domoticz.Log = lambda message: None
fake_domoticz.Status = lambda message: None
fake_domoticz.Configuration = lambda *args: {}
sys.modules.setdefault("DomoticzEx", fake_domoticz)


class FakeRequestException(Exception):
    pass


fake_requests = types.ModuleType("requests")
fake_requests.exceptions = types.SimpleNamespace(
    ConnectionError=FakeRequestException,
    RequestException=FakeRequestException,
)
sys.modules.setdefault("requests", fake_requests)

fake_urllib3 = types.ModuleType("urllib3")
fake_urllib3.exceptions = types.SimpleNamespace(
    InsecureRequestWarning=type("InsecureRequestWarning", (Warning,), {})
)
sys.modules.setdefault("urllib3", fake_urllib3)

import plugin
import tahoma
import tahoma_local


class FakeUnit:
    def __init__(self, name, nvalue=0, svalue="0"):
        self.Name = name
        self.nValue = nvalue
        self.sValue = svalue
        self.LastLevel = 0
        self.update_count = 0

    def Update(self):
        self.update_count += 1


class FakeDevice:
    def __init__(self, *units):
        self.Units = {index + 1: unit for index, unit in enumerate(units)}


class FakeLocalClient:
    def __init__(self, devices=None):
        self.logged_in = False
        self.startup = False
        self.token = None
        self._devices = devices or []
        self.listener_registered = False

    def register_listener(self):
        self.listener_registered = True

    def get_devices(self):
        return self._devices

    def get_gateways(self):
        return [{
            "gatewayId": "1237-0000-0000",
            "connectivity": {"status": "online", "protocolVersion": "1.0"},
            "mode": "ACTIVE",
        }]


class PluginTests(unittest.TestCase):
    def test_command_is_queued_without_touching_devices_before_startup(self):
        instance = plugin.BasePlugin()
        instance.devices_ready = False

        class DevicesMustNotBeRead:
            def __getitem__(self, key):
                raise AssertionError("Devices was accessed before startup completed")

        with mock.patch.object(plugin, "Devices", DevicesMustNotBeRead(), create=True):
            result = instance._dispatch_command("io://device", 1, "Open", 0, 0, None)

        self.assertFalse(result)
        self.assertEqual(1, len(instance._pending_commands))

    def test_local_startup_uses_stored_token_without_cloud_login(self):
        instance = plugin.BasePlugin()
        instance.local = True
        instance.local_ip_mode = True
        instance.tahoma = FakeLocalClient()
        instance.create_devices = mock.Mock()
        instance.create_connection_device = mock.Mock()
        instance.update_devices_status = mock.Mock()
        instance.update_connection_device = mock.Mock()
        instance._refresh_local_token = mock.Mock(
            side_effect=AssertionError("stored token must not trigger cloud token refresh")
        )

        with mock.patch.object(plugin, "getConfigItem", return_value="stored-token"), mock.patch.object(
            plugin, "Parameters", {"ResetToken": "false"}, create=True
        ):
            result = instance.setup_and_sync_devices("1234-5678-9012")

        self.assertTrue(result)
        self.assertEqual("stored-token", instance.tahoma.token)
        self.assertTrue(instance.tahoma.listener_registered)
        instance._refresh_local_token.assert_not_called()

    def test_on_start_completes_local_mode_with_stored_token(self):
        instance = plugin.BasePlugin()
        instance.load_config_txt = mock.Mock()
        instance.create_devices = mock.Mock()
        instance.create_connection_device = mock.Mock()
        instance.update_devices_status = mock.Mock()
        instance.update_connection_device = mock.Mock()
        local_client = FakeLocalClient()
        parameters = {
            "Version": "5.4.6",
            "ConnectionMode": "LocalIP",
            "Address": "192.0.2.10",
            "Gateway": "1234-5678-9012",
            "Port": "8443",
            "ResetToken": "false",
            "EnableDebug": "false",
        }

        with mock.patch.object(plugin, "Parameters", parameters, create=True), mock.patch.object(
            plugin, "SomfyBox", return_value=local_client
        ), mock.patch.object(plugin, "getConfigItem", return_value="stored-token"):
            result = instance.onStart()

        self.assertTrue(result)
        self.assertTrue(instance.enabled)
        self.assertTrue(instance.devices_ready)
        self.assertEqual("stored-token", local_client.token)

    def test_local_startup_refreshes_token_when_none_is_stored(self):
        instance = plugin.BasePlugin()
        instance.local = True
        instance.local_ip_mode = True
        instance.tahoma = FakeLocalClient()
        instance.create_devices = mock.Mock()
        instance.create_connection_device = mock.Mock()
        instance.update_devices_status = mock.Mock()
        instance.update_connection_device = mock.Mock()

        def set_refreshed_token(pin):
            instance.tahoma.token = "new-token"

        instance._refresh_local_token = mock.Mock(side_effect=set_refreshed_token)

        with mock.patch.object(plugin, "getConfigItem", return_value="0"), mock.patch.object(
            plugin, "Parameters", {"ResetToken": "false"}, create=True
        ):
            result = instance.setup_and_sync_devices("1234-5678-9012")

        self.assertTrue(result)
        self.assertEqual("new-token", instance.tahoma.token)
        instance._refresh_local_token.assert_called_once_with("1234-5678-9012")

    def test_empty_gateway_information_is_not_reported_as_an_error(self):
        instance = plugin.BasePlugin()
        instance.local = True
        instance.local_ip_mode = True
        instance.tahoma = FakeLocalClient()
        instance.tahoma.get_gateways = mock.Mock(return_value=[])
        instance.create_devices = mock.Mock()
        instance.create_connection_device = mock.Mock()
        instance.update_devices_status = mock.Mock()
        instance.update_connection_device = mock.Mock()

        with mock.patch.object(plugin, "getConfigItem", return_value="stored-token"), mock.patch.object(
            plugin, "Parameters", {"ResetToken": "false"}, create=True
        ), mock.patch.object(plugin.Domoticz, "Error") as error_log:
            result = instance.setup_and_sync_devices("1234-5678-9012")

        self.assertTrue(result)
        error_log.assert_not_called()

    def test_failed_startup_does_not_enable_heartbeat_processing(self):
        instance = plugin.BasePlugin()
        instance.load_config_txt = mock.Mock()
        parameters = {
            "Version": "5.4.6",
            "ConnectionMode": "LocalIP",
            "Address": "",
            "Mode3": "",
            "Port": "8443",
            "EnableDebug": "false",
        }

        with mock.patch.object(plugin, "Parameters", parameters, create=True):
            result = instance.onStart()

        self.assertFalse(result)
        self.assertFalse(instance.enabled)
        self.assertFalse(instance.devices_ready)

    def test_stop_disables_processing_and_device_access(self):
        instance = plugin.BasePlugin()
        instance.enabled = True
        instance.devices_ready = True

        instance.onStop()

        self.assertFalse(instance.enabled)
        self.assertFalse(instance.devices_ready)

    def test_open_closed_state_updates_the_domoticz_unit(self):
        instance = plugin.BasePlugin()
        instance.local = False
        instance.tahoma = types.SimpleNamespace(startup=False)
        unit = FakeUnit("Gate", nvalue=1, svalue="100")
        device_id = "io://gate"
        devices = {device_id: FakeDevice(unit)}
        update = [{
            "deviceURL": device_id,
            "deviceClass": "Gate",
            "name": "DeviceState",
            "deviceStates": [{"name": "core:OpenClosedState", "value": "closed"}],
        }]

        with mock.patch.object(plugin, "Devices", devices, create=True):
            instance.update_devices_status(update)

        self.assertEqual(0, unit.nValue)
        self.assertEqual("0", unit.sValue)
        self.assertEqual(1, unit.update_count)

    def test_zero_lux_replaces_the_previous_reading(self):
        instance = plugin.BasePlugin()
        instance.local = False
        instance.tahoma = types.SimpleNamespace(startup=False)
        unit = FakeUnit("Light sensor", nvalue=3, svalue="25")
        device_id = "io://light"
        devices = {device_id: FakeDevice(unit)}
        update = [{
            "deviceURL": device_id,
            "deviceClass": "LightSensor",
            "name": "DeviceState",
            "deviceStates": [{"name": "core:LuminanceState", "value": 0}],
        }]

        with mock.patch.object(plugin, "Devices", devices, create=True):
            instance.update_devices_status(update)

        self.assertEqual(3, unit.nValue)
        self.assertEqual("0", unit.sValue)
        self.assertEqual(1, unit.update_count)

    def test_debug_helpers_redact_authentication_secrets(self):
        self.assertEqual("***", plugin._mask_secret("Gateway", "1234-5678-9012"))
        self.assertEqual("***", plugin._mask_secret("Password", "secret"))
        self.assertEqual("192.0.2.1", plugin._mask_secret("Address", "192.0.2.1"))

        headers = {
            "Authorization": "Bearer secret",
            "Cookie": "session=secret",
            "Set-Cookie": "session=secret",
            "Content-Type": "application/json",
        }
        expected = {
            "Authorization": "***",
            "Cookie": "***",
            "Set-Cookie": "***",
            "Content-Type": "application/json",
        }
        self.assertEqual(expected, tahoma._masked_headers(headers))
        self.assertEqual(expected, tahoma_local._masked_headers(headers))


if __name__ == "__main__":
    unittest.main()
