import requests
import logging
import exceptions
import urllib.parse
import datetime
import time
import json
import utils
import listener

try:
    import DomoticzEx as Domoticz
except ImportError:
    import fakeDomoticz as Domoticz

class Tahoma:
    """class to interface with tahoma web API"""
    def __init__(self):
        self.srvaddr = "tahomalink.com"
        self.base_url = "https://tahomalink.com:443"
        self.login_url = "/enduser-mobile-web/enduserAPI/login"
        self.cookie = None
        self.listenerId = None
        self.__logged_in = False
        self.startup = True
        #self.heartbeat = False
        self.devices = None
        self.filtered_devices = None
        self.events = None
        self.heartbeat_delay = 1
        self.con_delay = 0
        self.wait_delay = 30
        self.json_data = None
        self.refresh = True
        self.timeout = 10
        self.__expiry_date = datetime.datetime.now()
        self.logged_in_expiry = 90 #expiry time out in seconds
        self.execId = None
        self.listener = listener.Listener(1)

    @property
    def logged_in(self):
        logging.debug("checking logged in status: self.__logged_in = "+str(self.__logged_in)+" and self.__expiry_date ("+str(self.__expiry_date)+") >= datetime.datetime.now() = " + str(self.__expiry_date >= datetime.datetime.now()))
        if self.__logged_in and (self.__expiry_date >= datetime.datetime.now()):
            return True
        elif self.__logged_in and (self.__expiry_date < datetime.datetime.now()):
            #only ask Tahoma server if we're logged in due to expiry time, not when we know we're not logged in
            self.__logged_in = self.get_login()
        return self.__logged_in

    def get_login(self):
        logging.debug("Asking tahoma server if we're good to go")
        url = self.base_url + "/enduser-mobile-web/enduserAPI/authenticated"
        Headers = { 'Host': self.srvaddr,"Connection": "keep-alive","Accept-Encoding": "gzip, deflate", "Accept": "*/*", "Content-Type": "application/x-www-form-urlencoded", "Cookie": self.cookie}
        try:
            response = requests.get(url, headers=Headers, timeout=self.timeout)
        except (requests.exceptions.ConnectionError) as exp:
            Domoticz.Error("Failed to contact server: " + str(exp))
            logging.error("Failed to contact server: " + str(exp))
            return False
            
        logging.debug("get login status response: status '" + str(response.status_code) + "' response body: '"+str(response.json())+"'")
        if response.status_code != 200:
            logging.error("get_login: error during get devices, status: " + str(response.status_code))
            Domoticz.Error("get_login: error during get devices, status: " + str(response.status_code))
            return False

        return response.json()['authenticated']
        
    def tahoma_login(self, username, password):

        #url = self.base_url + '/enduser-mobile-web/enduserAPI/login'
        url = self.base_url + self.login_url 
        headers = { 'Host': self.srvaddr,"Connection": "keep-alive","Accept-Encoding": "gzip, deflate", "Accept": "*/*", "Content-Type": "application/x-www-form-urlencoded"}
        data = "userId="+urllib.parse.quote(username)+"&userPassword="+urllib.parse.quote(password)+""
        response = requests.post(url, data=data, headers=headers, timeout=self.timeout)

        Data = response.json()
        logging.debug("Login respone: status_code: '"+str(response.status_code)+"' reponse body: '"+str(Data)+"'")

        #if (response.status_code == 200 and not self.__logged_in):
        if (response.status_code == 200):
            self.__logged_in = True
            self.__expiry_date = datetime.datetime.now() + datetime.timedelta(seconds=self.logged_in_expiry)
            logging.info("Tahoma authentication succeeded, login valid until " + self.__expiry_date.strftime("%Y-%m-%d %H:%M:%S"))
            #self.cookie = response.headers["Set-Cookie"]
            cookie_tmp = response.headers["Set-Cookie"]
            self.cookie = cookie_tmp[:cookie_tmp.index(';')]
            logging.debug("login: cookies: '"+ str(response.cookies)+"', headers: '"+str(response.headers)+"'")

        elif ((response.status_code == 401) or (response.status_code == 400)):
            strData = Data["error"]
            #logging.error("Tahoma error: must reconnect")
            self.__logged_in = False
            self.cookie = None
            #self.listenerId = None
            self.listener.valid = False

            if ("Too many" in strData):
                logging.error("Too many connections, must wait")
                #self.heartbeat = True
                raise exceptions.LoginFailure("Too many connections, must wait")
            elif ("Bad credentials" in strData):
                logging.error("login failed: Bad credentials, please update credentials and restart plugin")
                #self.heartbeat =  False
                raise exceptions.LoginFailure("Bad credentials, please update credentials and restart plugin")
            else:
                logging.error("login failed, unhandled reason: "+strData)
                raise exceptions.LoginFailure("login failed, unhandled reason: "+strData)

            if (not self.logged_in):
                self.tahoma_login(username, password)
                return
        else:
            logging.error("other error occured during login: "+str(response.status_code)+", content: "+str(response))
            raise exceptions.LoginFailure("Other error")
        return self.__logged_in

    def get_devices(self):
        logging.debug("start get devices")
        Headers = { 'Host': self.srvaddr,"Connection": "keep-alive","Accept-Encoding": "gzip, deflate", "Accept": "*/*", "Content-Type": "application/x-www-form-urlencoded", "Cookie": self.cookie}
        url = self.base_url + '/enduser-mobile-web/enduserAPI/setup/devices'
        for i in range(1,4):
            #do several retries on reaching events end point before going to time out error
            try:
                response = requests.get(url, headers=Headers, timeout=self.timeout)
                logging.debug("get device response: url '" + str(response.url) + "' response headers: '"+str(response.headers)+"'")
                logging.debug("get device response: status '" + str(response.status_code) + "' response body: '"+str(response.json())+"'")
                if response.status_code != 200:
                    logging.error("get_devices: error during get devices, status: " + str(response.status_code))
                    Domoticz.Error("get_devices: error during get devices, status: " + str(response.status_code))
                    return
                else:
                    break
            except requests.exceptions.RequestException as exp:
                logging.error("get_devices RequestException: " + str(exp))
            #wait increasing time before next try
            time.sleep(i ** 3)
        else:
            raise exceptions.TooManyRetries

        filtered_list = utils.filter_devices(response.json())
        self.startup = False
        return filtered_list

    def get_events(self):
        logging.debug("start get events")
        if not self.listener.valid:
            raise exceptions.TahomaException("No listenerId has been provided")
        Headers = { 'Host': self.srvaddr,"Connection": "keep-alive","Accept-Encoding": "gzip, deflate", "Accept": "*/*", "Content-Type": "application/json", "Cookie": self.cookie}
        url = self.base_url + '/enduser-mobile-web/enduserAPI/events/'+self.listener.listenerId+'/fetch'

        for i in range(1,4):
            #do several retries on reaching events end point before going to time out error
            try:
                response = requests.post(url, headers=Headers, timeout=self.timeout)
                logging.debug("get events response: status '" + str(response.status_code) + "' response body: '"+str(response)+"'")
                if response.status_code != 200:
                    logging.error("error during get events, status: " + str(response.status_code) + ", " + str(response.text))
                    self.__logged_in = False
                    if (response.status_code ==400 or response.status_code ==401) and "error" in response.json():
                        if ("No registered event listener" in response.json()["error"]) or ("authenticated" in response.json()["error"]):
                            self.listener.valid = False
                            logging.error("fetch events failed due to no valid listener registered")
                            raise exceptions.NoListenerFailure()
                    return
                elif (response.status_code == 200 and self.logged_in and (not self.startup)):
                    strData = response.json()

                    if (not "DeviceStateChangedEvent" in response.text):
                        logging.debug("get_events: no DeviceStateChangedEvent found in response: " + str(strData))
                        return

                    self.events = strData
                    self.listener.refresh_listener()

                    if (self.events):
                        filtered_events = list()

                        for event in self.events:
                            if (event["name"] == "DeviceStateChangedEvent"):
                                logging.debug("get_events: add event: URL: '"+event["deviceURL"]+"' num states: '"+str(len(event["deviceStates"]))+"'")
                                filtered_events.append(event)

                        return filtered_events

                else:
                  logging.info("Return status " + str(response.status_code))
            except requests.exceptions.RequestException as exp:
                logging.error("get_events RequestException: " + str(exp))
            #wait increasing time before next try
            time.sleep(i ** 3)
        else:
            raise exceptions.TooManyRetries
        logging.debug("finished get events")

    def register_listener(self):
        logging.debug("start register")
        if not self.logged_in:
            raise exceptions.TahomaException("Not logged in")
        Headers = { 'Host': self.srvaddr,"Connection": "keep-alive","Accept-Encoding": "gzip, deflate", "Accept": "*/*", "Content-Type": "application/json", "Cookie": self.cookie}
        response = self.listener.register_listener(self.base_url + '/enduser-mobile-web/enduserAPI/events/register', headers=Headers, verify = True, timeout=self.timeout)
        if response.status_code == 200:
            logging.debug("succeeded to get listener ID: " + str(response.json()))
        else:
            self.handle_response(response, "register listener")
        self.refresh = False
        return response

    def register_listener_old(self):
        logging.debug("start register")
        Headers = { 'Host': self.srvaddr,"Connection": "keep-alive","Accept-Encoding": "gzip, deflate", "Accept": "*/*", "Content-Type": "application/json", "Cookie": self.cookie}
        response = requests.post(self.base_url + '/enduser-mobile-web/enduserAPI/events/register', headers=Headers, timeout=self.timeout)
        logging.debug("register response: status '" + str(response.status_code) + "' response body: '"+str(response)+"'")
        if response.status_code == 200:
            logging.debug("succeeded to get local listener ID: " + str(response.json()))
            self.listenerId = response.json()['id']
        else:
            self.handle_response(response, "register listener")

        logging.info("Tahoma listener registred")
        self.refresh = False
        return response.json()

    def send_command(self, json_data):
        timeout = 4
        logging.debug("start command")
        Headers = { 'Host': self.srvaddr, "Connection": "keep-alive","Accept-Encoding": "gzip, deflate", "Accept": "*/*", "Content-Type": "application/json", "Cookie": self.cookie}
        logging.info("Sending command to tahoma api")
        logging.debug("onCommand: headers: '"+str(Headers)+"', data '"+str(json_data)+"'")
        try:
            response = requests.post(self.base_url + '/enduser-mobile-web/enduserAPI/exec/apply', headers=Headers, data=json_data, timeout=timeout)
        except requests.exceptions.RequestException as exp:
            logging.error("Send command returns RequestException: " + str(exp))
            return ""

        logging.debug("command response: status '" + str(response.status_code) + "' response body: '"+str(response.json())+"'")
        if response.status_code == 200:
            logging.debug("succeeded to post command: " + str(response.json()))
            self.execId = response.json()['execId']
        else:
            self.__logged_in = False
            self.handle_response(response, "send command")
        #event_list = self.get_events()
        return response.json()

    def handle_response(self, response, action):
        """handle (faulty) responses"""
        if response.status_code >= 200 and response.status_code < 300:
            return
        if response.status_code >= 300 and response.status_code < 400:
            logging.error("status code " + str(response.status_code) + " this is likely a bug")
            raise exceptions.TahomaException("failed request during "+ action + ": " + str(response.status_code))
        elif response.status_code == 400:
            logging.error("status code " + str(response.status_code) + " this is a bug, bad request made, url or body needs to be checked")
            raise exceptions.TahomaException("failed request during "+ action + ", check url or body: " + str(response.status_code))
        elif response.status_code == 401:
            self.__logged_in = False
            logging.error("status code " + str(response.status_code) + " authorisation failed, check credentials")
            raise exceptions.TahomaException("failed request during "+ action + ", check credentials: " + str(response.status_code))
        elif response.status_code == 404:
            logging.error("status code " + str(response.status_code) + " server not found")
            raise exceptions.TahomaException("failed request during "+ action + ", server not found: " + str(response.status_code))
        elif response.status_code >= 500:
            logging.error("status code " + str(response.status_code) + " a server sided problem")
            raise exceptions.TahomaException("failed request during "+ action + ": " + str(response.status_code))
        else:
            logging.error("status code " + str(response.status_code))
            raise exceptions.TahomaException("failed request during "+ action + ": " + str(response.status_code))        
        return
