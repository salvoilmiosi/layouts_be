#!/usr/bin/env python

import requests
import urllib3
import json
from getpass import getpass

address = 'https://portale.bollettaetica.com'

def login_be():
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    session = requests.Session()

    while True:
        login = {'f':'login'}
        login['login'] = input('Nome utente: ')
        login['password'] = getpass('Password: ')

        loginr = json.loads(session.post(address + '/login.ws', verify=False, data=login).text)
        print('Login:', loginr['head']['status']['type'])
        if loginr['head']['status']['code'] == 1:
            return session