import requests
import exceptions
import logging
import datetime
import utils
import json

class Listener:
    def __init__(self, Minutes=4):
        self.__listenerId = None
        self.__listener_expiry = datetime.datetime.now()
        self.__valid = False
        logging.debug("listener created")
        self.__expiry_time = datetime.timedelta(minutes=Minutes)

    @property
    def listenerId(self):
        return self.__listenerId

    @property
    def valid(self):
        self.__valid = self.__listener_expiry > datetime.datetime.now()
        logging.debug("listener vald: self.__listener_expiry = " + self.__listener_expiry.strftime("%Y-%m-%d %H:%M:%S") + " self.__valid = " + str(self.__valid))
        return self.__valid

    @valid.setter
    def valid(self, v):
        if not v:
            self.__valid = v
        elif not self.__valid:
            logging.error("It is not allowed to set the listener to valid externally")
            raise AttributeError
        
    def refresh_listener(self):
        """method to reset expiry time after succesfull interaction"""
        self.__listener_expiry = datetime.datetime.now() + self.__expiry_time
        self.__valid = True        

    def register_listener(self, url, headers, verify=False, timeout=10):
        logging.debug("start register listener")
        logging.debug("register request: self.headers_with_token: '" + json.dumps(headers) + "'")
        response = requests.post(url, headers=headers, verify=verify, timeout=timeout)
        logging.debug("register response: status '" + str(response.status_code) + "' response body: '"+str(response)+"'")
        if response.status_code == 200:
            logging.debug("succeeded to get listener ID: " + str(response.json()))
            self.__listenerId = response.json()['id']
            self.__listener_expiry = datetime.datetime.now() + self.__expiry_time
            self.__valid = True
        else:
            self.__valid = False
            #utils.handle_response(response, "get listener ID")
        return response
