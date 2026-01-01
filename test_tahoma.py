import time
import logging
import json
import consolemenu
import tahoma
from tahoma_local import SomfyBox
import exceptions
from tests.params import *

class testTahoma():
    def __init__(self):
        logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(filename)-18s - %(message)s', filename='somfy_test.log',
                            level=logging.DEBUG)
        logging.info("=== starting test run ===")

        self.menuoptions = ['0 exit',"1 log in for local", "2 login for web", "3 check log in web", "4 generate toke", "5 activate token", "6 get tokens", "7 delete token", "8 print token",
            "10 web register", "11 web get devices", "12 web get events", "13 web send command",
            "20 get local API version", "21 get local gateway", "22 get local devices", "23 register local listener", "24 get local events", "25 get local device state", "26 send local command",
            "31 send open", "32 send close", "33 send precentage"]
        self.mymenu = consolemenu.SelectionMenu(self.menuoptions)

        device_list = list()

        #tahoma = tahoma()
        self.tahoma = tahoma.Tahoma()
        self.theBox = SomfyBox(p_pin, p_port)

    def print_menu(self):
        print("=====")
        if str(p_token) != '0':
            self.theBox.token = p_token
            print ("token loaded from params, no need to get from web")
        else:
            print("No token loaded from param, first get it from web, steps <10")

        if self.theBox.cookie is None:
            self.theBox.cookie = dict(JSESSIONID='F290EEAEC03B4838EBDA4B0CD0034BAB')

        if True:
            while True:
                print("=====")
                for i in self.menuoptions:
                    print(i) 
                x = int(input("Please Select:"))
                print(x)
                logging.info("selected menu option: "+str(x))
                if x == 0: 
                    logging.info("== end test run ===")
                    exit()
                elif x == 1: #log in
                    status = False
                    try:
                        status = self.theBox.tahoma_login(p_email, p_password)
                    except exceptions.LoginFailure as exp:
                        print("Failed to login: " + str(exp))
                    if self.theBox.cookie is None:
                        self.theBox.cookie = dict(JSESSIONID='F290EEAEC03B4838EBDA4B0CD0034BAB')
                    print("login status: "+str(status))
                elif x == 2: #log in
                    status = False
                    try:
                        status = self.tahoma.tahoma_login(p_email, p_password)
                    except exceptions.LoginFailure as exp:
                        print("Failed to login: " + str(exp))
                    if self.tahoma.cookie is None:
                        self.tahoma.cookie = 'JSESSIONID=F290EEAEC03B4838EBDA4B0CD0034BAB; Path=/enduser-mobile-web; Secure; HttpOnly; SameSite=None'
                    print("login status: "+str(status))
                elif x == 3: print(str(self.tahoma.logged_in)) #check log in
                elif x == 4: #generate token
                    try:
                        response = self.theBox.generate_token(p_pin)
                        print("you can store the token in params.py for later use")
                        print(json.dumps(response, sort_keys = True, indent=4))
                    except exceptions.LoginFailure as exp:
                        print("Failed to login: " + str(exp))
                    if self.theBox.token is None:
                        print('not token generated, using default from file')
                        self.theBox.token = str(p_token)
                elif x == 5: #activate token
                    response = self.theBox.activate_token(p_pin, theBox.token)
                    #theBox.token = tahoma.token
                    print(json.dumps(response, sort_keys = True, indent=4))
                elif x == 6: #get list of tokens
                    response = self.theBox.get_tokens(p_pin)
                    print(json.dumps(response, sort_keys = True, indent=4))
                elif x == 7:#delete token
                    uuid = input("Please enter uuid to delete:")
                    response = self.theBox.delete_tokens(p_pin, uuid)
                    print(json.dumps(response, sort_keys = True, indent=4))
                elif x == 8:
                    print("token = " + str(self.theBox.token))
                elif x == 10: # register listener
                    self.tahoma.register_listener()
                    if self.tahoma.listenerId is None:
                        self.tahoma.listenerId = 'b4e62511-ac10-3e01-60e0-9b9f656aea77'
                elif x == 11: print(self.tahoma.get_devices())
                elif x == 12: print(self.tahoma.get_events())
                elif x == 13: 
                    device = str(input("enter deviceURL to command: "))
                    command = str(input("enter command <open|close>: "))
                    commando = {"actions":[{"commands":[{"name":command}], "deviceURL":device}], "label":"test command"}
                    #data = '{"actions": [{"commands": [{"name": "open"}], "deviceURL": "io://1234-5678-9012/10464619"}], "label": "Domoticz - Somfy - test - open"}'
                    print(self.tahoma.send_command(json.dumps(commando)))
                elif x == 20: #get version of local API
                    response = self.theBox.get_version()
                    print(json.dumps(response, sort_keys = True, indent=4))
                elif x == 21: #get version of local API
                    response = self.theBox.get_gateways()
                    print(json.dumps(response, sort_keys = True, indent=4))
                elif x == 22: #get devices of local API
                    response = self.theBox.get_devices()
                    print(json.dumps(response, sort_keys = True, indent=4))
                elif x == 23: #register listener of local API
                    response = self.theBox.register_listener()
                    print(json.dumps(response, sort_keys = True, indent=4))
                elif x == 24: #get events of local API
                    response = self.theBox.get_events()
                    print(json.dumps(response, sort_keys = True, indent=4))
                elif x == 25: #get device state on local API
                    device = str(input("enter deviceurl to get state: "))
                    response = self.theBox.get_device_state(device)
                    print(json.dumps(response, sort_keys = True, indent=4))
                elif x == 26: #send a command to the local API
                    device = str(input("enter deviceURL to command: "))
                    command = str(input("enter command <open|close>: "))
                    commando = {"actions":[{"commands":[{"name":command}], "deviceURL":device}], "label":"test command"}
                    response = self.theBox.send_command(commando)
                    print(json.dumps(response, sort_keys = True, indent=4))
                elif x == 31: # open command
                    response = self.theBox.get_devices()
                    print(json.dumps(response, sort_keys = True, indent=4))
                    device = str(input("enter deviceURL to command: "))
                    commando = {"actions":[{"commands":[{"name":"open"}], "deviceURL":device}], "label":"test command"}
                    response = self.theBox.send_command(commando)
                    print(json.dumps(response, sort_keys = True, indent=4))
                elif x == 32: #close command
                    response = self.theBox.get_devices()
                    print(json.dumps(response, sort_keys = True, indent=4))
                    device = str(input("enter deviceURL to command: "))
                    commando = {"actions":[{"commands":[{"name":"close"}], "deviceURL":device}], "label":"test command"}
                    response = self.theBox.send_command(commando)
                    print(json.dumps(response, sort_keys = True, indent=4))
                elif x == 33: # send closure %
                    response = self.theBox.get_devices()
                    print(json.dumps(response, sort_keys = True, indent=4))
                    device = str(input("enter deviceURL to command: "))
                    params = []
                    params.append(int(input("enter percentage: ")))
                    commando = {"actions":[{"commands":[{"name":"set closure"},{"parameters" : params}], "deviceURL":device}], "label":"test command"}
                    response = self.theBox.send_command(commando)
                    print(json.dumps(response, sort_keys = True, indent=4))
                    
                else:
                    print("this option is not supported")
                input("Press Enter to continue...")
                # except (ValueError) as err:
                    # print("error in menu keuze")
        else:
            logging.error("initialisation failed")

def main():
    myT = testTahoma()
    myT.print_menu()


if __name__ == "__main__":
    main()
