import requests
import logging
import exceptions
import urllib.parse
import datetime
import time
import json
import utils
import listener
import DomoticzEx as Domoticz

import urllib3
urllib3.disable_warnings()

class TahomaWebApi:
    base_url_web = "https://ha101-1.overkiz.com"
    headers_url = {"Content-Type": "application/x-www-form-urlencoded"}
    headers_json = {"Content-Type": "application/json"}
    headers_with_token = {"Content-Type": "application/json"}
    login_url = "/enduser-mobile-web/enduserAPI/login"
    timeout = 10
    __expiry_date = datetime.datetime.now()
    logged_in_expiry_days = 6
    cookie = None
    __token = None
    __logged_in = False

    @property
    def logged_in(self):
        logging.debug("checking logged in status: self.__logged_in = "+str(self.__logged_in)+" and self.__expiry_date >= datetime.datetime.now() = " + str(self.__expiry_date >= datetime.datetime.now()))
        if self.__logged_in and (self.__expiry_date >= datetime.datetime.now()):
            return True
        else:
            return False

    def tahoma_login(self, username, password):
        data = {"userId": username, "userPassword": password}
        try:
            response = requests.post(self.base_url_web + self.login_url, headers=self.headers_url, data=data, timeout=self.timeout)
        except requests.exceptions.RequestException as exp:
            logging.error("Login request failed: " + str(exp))
            raise exceptions.LoginFailure("Network error during login: " + str(exp))

        Data = utils.response_json(response, "login")
        logging.debug("Login response: status_code: '"+str(response.status_code)+"' response body: '"+str(Data)+"'")

        if (response.status_code == 200 and not self.__logged_in):
            self.__logged_in = True
            self.__expiry_date = datetime.datetime.now() + datetime.timedelta(days=self.logged_in_expiry_days)
            logging.info("Tahoma authentication succeeded, login valid until " + self.__expiry_date.strftime("%Y-%m-%d %H:%M:%S"))
            self.cookie = response.cookies
            logging.debug("login: cookies: '"+ str(response.cookies)+"', headers: '"+str(response.headers)+"'")

        elif ((response.status_code == 401) or (response.status_code == 400)):
            strData = Data["error"]
            self.__logged_in = False
            self.cookie = None

            if ("Too many" in strData):
                logging.error("Too many connections, must wait")
                raise exceptions.LoginFailure("Too many connections, must wait")
            elif ("Bad credentials" in strData):
                logging.error("login failed: Bad credentials, please update credentials and restart plugin")
                raise exceptions.LoginFailure("Bad credentials, please update credentials and restart plugin")
            else:
                logging.error("login failed, unhandled reason: "+strData)
                raise exceptions.LoginFailure("login failed, unhandled reason: "+strData)

        else:
            self.__logged_in = False
            self.cookie = None
            logging.error("login failed with unexpected status code: " + str(response.status_code))
            raise exceptions.LoginFailure("Login failed with unexpected status code: " + str(response.status_code))

        return self.__logged_in

    def generate_token(self, pin):
        url_gen = "/enduser-mobile-web/enduserAPI/config/"+pin+"/local/tokens/generate"
        logging.debug("generate token: url_gen = '" + url_gen + "'")
        logging.debug("generate token: cookie present = '" + str(bool(self.cookie)) + "'")
        response = requests.get(self.base_url_web + url_gen, headers=self.headers_json, cookies=self.cookie, timeout=self.timeout)
        logging.debug("generate token: response = '" + str(response) + "'")
        
        if response.status_code == 200:
            data = utils.response_json(response, "generate token")
            self.__token = data['token']
            self.headers_with_token["Authorization"] = "Bearer " + str(self.__token)
            logging.debug("succeeded to generate token: " + str(self.token))
            return data
        elif ((response.status_code == 401) or (response.status_code == 400)):
            self.__logged_in = False
            self.cookie = None
            logging.debug("generate token failed: status = '" + str(response.status_code) + "', body = '" + str(response.text) + "'")
            logging.error("failed to generate token")
            raise exceptions.LoginFailure("failed to generate token")
        else:
            logging.error(f"generate token: unexpected status code {response.status_code}")
            raise exceptions.TahomaException(f"Failed to generate token: unexpected status {response.status_code}")

    @property
    def token(self):
        return self.__token

    @token.setter
    def token(self, t):
        """setter to allow external update of token"""
        self.__token = t
        self.headers_with_token["Authorization"] = "Bearer " + str(self.__token)
        logging.debug("headers_with_token updated with new token")

    def activate_token(self, pin, token):
        url_act = "/enduser-mobile-web/enduserAPI/config/"+pin+"/local/tokens"
        data_act = {"label": "Domoticz token", "token": token, "scope": "devmode"}
        response = requests.post(self.base_url_web + url_act, headers=self.headers_json, json=data_act, cookies=self.cookie, timeout=self.timeout)
        data = utils.response_json(response, "activate token")
        logging.debug("activate_token: response: "+str(data))

        if response.status_code == 200:
            logging.debug("succeeded to activate token: " + str(self.token))
            return data
        elif ((response.status_code == 401) or (response.status_code == 400)):
            self.__logged_in = False
            self.cookie = None
            logging.error("failed to activate token")
            raise exceptions.LoginFailure("failed to activate token")
        else:
            logging.error(f"activate token: unexpected status code {response.status_code}")
            raise exceptions.TahomaException(f"Failed to activate token: unexpected status {response.status_code}")

    def get_tokens(self, pin):
        url_act = "/enduser-mobile-web/enduserAPI/config/"+pin+"/local/tokens/devmode"
        response = requests.get(self.base_url_web + url_act, headers=self.headers_json, cookies=self.cookie, timeout=self.timeout)
        data = utils.response_json(response, "get tokens")

        if response.status_code == 200:
            logging.debug("succeeded to get tokens: " + str(data))
        elif ((response.status_code == 401) or (response.status_code == 400)):
            self.__logged_in = False
            self.cookie = None
            logging.error("failed to get tokens")
            raise exceptions.LoginFailure("failed to get tokens")
        return data

    def delete_tokens(self, pin, uuid):
        url_del = "/enduser-mobile-web/enduserAPI/config/"+pin+"/local/tokens/"+str(uuid)
        response = requests.delete(self.base_url_web + url_del, headers=self.headers_json, cookies=self.cookie, timeout=self.timeout)
        data = utils.response_json(response, "delete token")

        if response.status_code == 200:
            logging.debug("succeeded to delete token: " + str(data))
        elif ((response.status_code == 401) or (response.status_code == 400)):
            self.__logged_in = False
            self.cookie = None
            logging.error("failed to delete token")
            raise exceptions.LoginFailure("failed to delete tokens")
        return data

class SomfyBox(TahomaWebApi):
    def __init__(self, pin=None, port=8443, ip=None):
        host = ip if ip else str(pin) + ".local"
        self.headers_url = dict(self.headers_url)
        self.headers_json = dict(self.headers_json)
        self.headers_with_token = {"Content-Type": "application/json"}
        self.base_url_local = "https://" + host + ":" + str(port) + "/enduser-mobile-web/1/enduserAPI"
        self.startup = True
        self.listener = listener.Listener(8)
        logging.debug("SomfyBox initialised")
        Domoticz.Log("TaHoma LOCAL client loaded")

    def get_version(self):
        if self.token is None or self.token == "0":
            raise exceptions.TahomaException("No token has been provided")
        response = requests.get(self.base_url_local + "/apiVersion", headers=self.headers_with_token, verify=False, timeout=10)
        if response.status_code == 200:
            data = utils.response_json(response, "get API version")
            logging.debug("succeeded to get API version: " + str(data))
        else:
            utils.handle_response(response, "get API version")
            data = {}
        return data

    #setup endpoints
    def get_gateways(self):
        if self.token is None or self.token == "0":
            raise exceptions.TahomaException("No token has been provided")
        response = requests.get(self.base_url_local + "/setup/gateways", headers=self.headers_with_token, verify=False, timeout=10)
        logging.debug(response)
        if response.status_code == 200:
            data = utils.response_json(response, "get gateways")
            logging.debug("succeeded to get local API gateways: " + str(data))
        else:
            utils.handle_response(response, "get gateways")
            data = {}
        return data

    def get_devices(self):
        logging.debug("start get devices")

        if self.token is None or self.token == "0":
            raise exceptions.TahomaException("No token has been provided")

        try:
            response = requests.get(
                self.base_url_local + "/setup/devices",
                headers=self.headers_with_token,
                verify=False,
                timeout=10
            )
        except requests.exceptions.RequestException as exp:
            raise exceptions.TahomaException(
                f"Failed to get devices: {exp}"
            )

        if response.status_code == 200:
            data = utils.response_json(response, "get devices")
            logging.debug(
                "get device response: status '" +
                str(response.status_code) +
                "' response body: '" +
                str(data) + "'"
            )
            logging.debug(
                "succeeded to get local API devices: " +
                str(data)
            )
        else:
            utils.handle_response(response, "get devices")
            data = []

        filtered_list = utils.filter_devices(data)
        self.startup = False

        return filtered_list


    def get_device_state(self, device):
        if self.token is None or self.token == "0":
            raise exceptions.TahomaException("No token has been provided")
        if not device.startswith("io://"):
            raise exceptions.TahomaException("Invalid url, needs to start with io://")
        url = self.base_url_local + "/setup/devices/" + urllib.parse.quote(device, safe="") + "/states"
        logging.debug("url for device state: " + str(url))
        response = requests.get(url, headers=self.headers_with_token, verify=False, timeout=10)
        logging.debug(response)
        if response.status_code == 200:
            data = utils.response_json(response, "get device state")
            logging.debug("succeeded to get local API device states: " + str(data))
        else:
            utils.handle_response(response, "get device state")
            data = {}
        return data
        
    #events endpoints
    def get_events(self):
        logging.debug("start get events")
        if self.token is None or self.token == "0":
            raise exceptions.TahomaException("No token has been provided")
        if not self.listener.valid:
            logging.error("cannot fetch events if no listener registered")
            raise exceptions.NoListenerFailure()
        for i in range(1, 4):
            try:
                response = requests.post(self.base_url_local + "/events/" + self.listener.listenerId + "/fetch", headers=self.headers_with_token, verify=False, timeout=10)
                logging.debug("get events response: status '" + str(response.status_code) + "' response body: '" + str(response) + "'")
                if response.status_code != 200:
                    logging.error("error during get events, status: " + str(response.status_code) + ", " + str(response.text))
                    try:
                        data = utils.response_json(response, "get events")
                    except exceptions.TahomaException:
                        data = {}
                    if response.status_code == 400 and "error" in data:
                        if "No registered event listener" in data["error"]:
                            self.listener.valid = False
                            logging.error("fetch events failed due to no valid listener registered")
                            raise exceptions.NoListenerFailure()
                    return []
                elif response.status_code == 200:
                    strData = utils.response_json(response, "get events")
                    self.listener.refresh_listener()
                    logging.debug("succeeded to get local API events: " + str(strData))
                    if "DeviceStateChangedEvent" not in response.text:
                        logging.debug("get_events: no DeviceStateChangedEvent found in response: " + str(strData))
                        return []
                    else:
                        return strData

                else:
                    logging.info("Return status " + str(response.status_code))
            except requests.exceptions.RequestException as exp:
                logging.error("get_events RequestException: " + str(exp))
            time.sleep(i ** 3)
        else:
            raise exceptions.TooManyRetries
        logging.debug("finished get events")

    def register_listener(self):
        logging.debug("start register")
        if self.token is None or self.token == "0":
            raise exceptions.TahomaException("No token has been provided")
        response = self.listener.register_listener(self.base_url_local + "/events/register", headers=self.headers_with_token, verify=False, timeout=10)
        return response

    #execution endpoints
    def send_command(self, json_data):
        if self.token is None or self.token == "0":
            raise exceptions.TahomaException("No token has been provided")
        logging.info("Sending command to local api")
        logging.debug("onCommand: data '"+str(json_data)+"'")
        try:
            response = requests.post(self.base_url_local + "/exec/apply", headers=self.headers_with_token, json=json_data, verify=False, timeout=self.timeout)
        except requests.exceptions.RequestException as exp:
            logging.error("Send command returns RequestException: " + str(exp))
            return ""
        if response.status_code != 200:
            utils.handle_response(response, "send command")
        data = utils.response_json(response, "send command")
        logging.debug("command response: status '" + str(response.status_code) + "' response body: '"+str(data)+"'")
        logging.debug("succeeded to post command: " + str(data))
        self.execId = data['execId']
        return data
