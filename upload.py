#!/usr/bin/env python

import blsconfig
import login_be
import json
import sys
import os
from pathlib import Path
from datetime import date

if sys.platform == 'win32':
    os.system('color')

in_path = Path(sys.argv[1]) if len(sys.argv) > 1 else blsconfig.read_output_path

def filter_and_upload(f, do_upload = True):
    with open(f, 'r') as file:
        data = json.load(file)
    for x in data:
        x['values'] = [t for t in x['values'] if 'conguaglio' not in t and date.fromisoformat(t['mese_fattura']).year >= filter_year]
    if do_upload:
        response = session.put(login_be.address + '/zelda/fornitura.ws?f=importDatiFattureJSON', json.dumps(data))
        uploadr = json.loads(response.text)
        if (uploadr['head']['status']['code'] == 0):
            print(f)
        else:
            print('{0} \033[31m{1}\033[0m'.format(f, uploadr['head']['status']['message']))

try:
    filter_year = int(input("Filtrare fatture prima dell'anno: "))
except ValueError:
    filter_year = 0

do_upload = input('Proseguire? S/n ').lower() in ('s','')

if do_upload:
    session = login_be.login_be()

if in_path.is_dir():
    for f in in_path.rglob('*.json'):
        filter_and_upload(f, do_upload)
else:
    filter_and_upload(in_path, do_upload)
