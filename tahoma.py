import requests
import logging
import exceptions
import urllib.parse
import datetime
import time
import utils

import DomoticzEx as Domoticz


def _masked_headers(headers):
    """Return response/request headers with authentication data redacted."""
    masked = dict(headers)
    for key in list(masked):
        if key.lower() in ("authorization", "cookie", "set-cookie"):
            masked[key] = "***"
    return masked


class Tahoma:
    """class to interface with tahoma web API"""
    def __init__(self):
        self.srvaddr = "tahomalink.com"
        self.base_url = "https://tahomalink.com:443"
        self.login_url = "/enduser-mobile-web/enduserAPI/login"
        self.cookie = None
        self.__logged_in = False
        self.timeout = 10
        self.__expiry_date = datetime.datetime.now()
        # Re-login interval in seconds. The cloud session lasts much longer
        # than this; a 401 (handle_response/send_command) marks us logged out
        # sooner, so this only forces a periodic fresh login.
        self.logged_in_expiry = 24 * 3600
        self.execId = None
        Domoticz.Log("TaHoma WEB client loaded")

    @property
    def logged_in(self):
        logging.debug(
            "checking logged in status: self.__logged_in = " + str(self.__logged_in) +
            " and self.__expiry_date (" + str(self.__expiry_date) +
            ") >= datetime.datetime.now() = " + str(self.__expiry_date >= datetime.datetime.now())
        )
        if self.__logged_in and (self.__expiry_date >= datetime.datetime.now()):
            return True
        elif self.__logged_in and (self.__expiry_date < datetime.datetime.now()):
            # Session expired â€“ mark as logged out; caller must log in again
            logging.debug("logged_in: session expired, marking as logged out")
            self.__logged_in = False
        return self.__logged_in

    def tahoma_login(self, username, password):
        url = self.base_url + self.login_url
        headers = {
            'Host': self.srvaddr,
            "Connection": "keep-alive",
            "Accept-Encoding": "gzip, deflate",
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = "userId=" + urllib.parse.quote(username) + "&userPassword=" + urllib.parse.quote(password)

        try:
            response = requests.post(url, data=data, headers=headers, timeout=self.timeout)
        except requests.exceptions.RequestException as exp:
            Domoticz.Error("Login request failed: " + str(exp))
            logging.error("Login request failed: " + str(exp))
            raise exceptions.LoginFailure("Network error during login: " + str(exp)) from exp

        Data = utils.response_json(response, "login")
        logging.debug(
            "Login response: status_code: '" + str(response.status_code) +
            "' response body: '" + str(Data) + "'"
        )

        if response.status_code == 200:
            self.__logged_in = True
            self.__expiry_date = datetime.datetime.now() + datetime.timedelta(seconds=self.logged_in_expiry)
            logging.info(
                "Tahoma authentication succeeded, login valid until " +
                self.__expiry_date.strftime("%Y-%m-%d %H:%M:%S")
            )
            cookie_tmp = response.headers["Set-Cookie"]
            self.cookie = cookie_tmp[:cookie_tmp.index(';')]
            logging.debug(
                "login: cookies received, headers: '" + str(_masked_headers(response.headers)) + "'"
            )

        elif response.status_code in (400, 401):
            strData = Data["error"]
            self.__logged_in = False
            self.cookie = None

            if "Too many" in strData:
                logging.error("Too many connections, must wait")
                raise exceptions.LoginFailure("Too many connections, must wait")
            elif "Bad credentials" in strData:
                logging.error("login failed: Bad credentials, please update credentials and restart plugin")
                raise exceptions.LoginFailure("Bad credentials, please update credentials and restart plugin")
            else:
                logging.error("login failed, unhandled reason: " + strData)
                raise exceptions.LoginFailure("login failed, unhandled reason: " + strData)

        else:
            logging.error(
                "other error occured during login: " + str(response.status_code) +
                ", content: " + str(response)
            )
            raise exceptions.LoginFailure("Other error")

        return self.__logged_in

    def get_devices(self):
        logging.debug("start get devices")
        Headers = {
            'Host': self.srvaddr,
            "Connection": "keep-alive",
            "Accept-Encoding": "gzip, deflate",
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": self.cookie
        }
        url = self.base_url + '/enduser-mobile-web/enduserAPI/setup/devices'
        for i in range(1, 4):
            try:
                response = requests.get(url, headers=Headers, timeout=self.timeout)
                logging.debug(
                    "get device response: url '" + str(response.url) +
                    "' response headers: '" + str(_masked_headers(response.headers)) + "'"
                )
                if response.status_code != 200:
                    logging.error("get_devices: error during get devices, status: " + str(response.status_code))
                    Domoticz.Error("get_devices: error during get devices, status: " + str(response.status_code))
                    self.handle_response(response, "get devices")
                else:
                    Data = utils.response_json(response, "get devices")
                    logging.debug(
                        "get device response: status '" + str(response.status_code) +
                        "' response body: '" + str(Data) + "'"
                    )
                    break
            except requests.exceptions.RequestException as exp:
                logging.error("get_devices RequestException: " + str(exp))
            time.sleep(min(2 * i, 5))
        else:
            raise exceptions.TooManyRetries

        filtered_list = utils.filter_devices(Data)
        return filtered_list

    def send_command(self, json_data):
        logging.debug("start command")
        Headers = {
            'Host': self.srvaddr,
            "Connection": "keep-alive",
            "Accept-Encoding": "gzip, deflate",
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Cookie": self.cookie
        }
        logging.info("Sending command to tahoma api")
        debug_headers = dict(Headers)
        debug_headers["Cookie"] = "***"
        logging.debug("onCommand: headers: '" + str(debug_headers) + "', data '" + str(json_data) + "'")

        try:
            response = requests.post(
                self.base_url + '/enduser-mobile-web/enduserAPI/exec/apply',
                headers=Headers,
                data=json_data,
                timeout=self.timeout
            )
        except requests.exceptions.RequestException as exp:
            logging.error("Send command returns RequestException: " + str(exp))
            raise exceptions.TahomaException("Network error while sending command: " + str(exp)) from exp

        if response.status_code != 200:
            self.__logged_in = False
            self.handle_response(response, "send command")

        Data = utils.response_json(response, "send command")
        logging.debug(
            "command response: status '" + str(response.status_code) +
            "' response body: '" + str(Data) + "'"
        )
        logging.debug("succeeded to post command: " + str(Data))
        self.execId = Data['execId']

        return Data

    def handle_response(self, response, action):
        """Handle faulty responses by raising appropriate exceptions."""
        if response.status_code >= 200 and response.status_code < 300:
            return
        if response.status_code >= 300 and response.status_code < 400:
            logging.error("status code " + str(response.status_code) + " this is likely a bug")
            raise exceptions.TahomaException("failed request during " + action + ": " + str(response.status_code))
        elif response.status_code == 400:
            logging.error("status code " + str(response.status_code) + " bad request, check url or body")
            raise exceptions.TahomaException("failed request during " + action + ", check url or body: " + str(response.status_code))
        elif response.status_code == 401:
            self.__logged_in = False
            logging.error("status code " + str(response.status_code) + " authorisation failed, check credentials")
            raise exceptions.TahomaException("failed request during " + action + ", check credentials: " + str(response.status_code))
        elif response.status_code == 404:
            logging.error("status code " + str(response.status_code) + " server not found")
            raise exceptions.TahomaException("failed request during " + action + ", server not found: " + str(response.status_code))
        elif response.status_code >= 500:
            logging.error("status code " + str(response.status_code) + " a server sided problem")
            raise exceptions.TahomaException("failed request during " + action + ": " + str(response.status_code))
        else:
            logging.error("status code " + str(response.status_code))
            raise exceptions.TahomaException("failed request during " + action + ": " + str(response.status_code))
