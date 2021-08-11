#!/usr/bin/env python

import login_be
import json
import os
from pathlib import Path
from datetime import date

os.system('color')

session = login_be.login_be()

getFattureRes = session.post(login_be.address + '/zelda/fornitura.ws', verify=False, data={'f':'getFatture'})
getFatture = json.loads(getFattureRes.text)['body']['getFatture']

input_directory = Path(__file__).parent / 'work/letture'

letture = []
for f in input_directory.rglob('*.json'):
    with open(f, 'r') as file:
        letture.extend(json.load(file))

def find_filename(fattura):
    fornitura = getFatture['forniture'][fattura['id_fornitura']]
    gruppo_forniture = getFatture['gruppi_forniture'][fornitura['id_gruppo_forniture']]

    ragione_sociale = getFatture['clienti'][gruppo_forniture['id_cliente']]['ragione_sociale']
    numero_fattura = fattura['numero_fattura']
    nome_fornitore = getFatture['fornitori'][fattura['id_fornitore']]['nome']

    codice_pod = fornitura['pod']
    mese_fattura = date(int(fattura['anno'][0]), int(fattura['mese'][0]), 1)

    print(ragione_sociale, codice_pod, mese_fattura, nome_fornitore, numero_fattura)

    for l in letture:
        if 'values' not in l: continue
        for v in l['values']:
            if v['fornitore'] != nome_fornitore: continue
            if v['numero_fattura'] == numero_fattura \
                or (v['codice_pod'] == codice_pod and date.fromisoformat(v['mese_fattura']) == mese_fattura):
                return l['filename']
    return None

for id_fattura, fattura in getFatture['fatture'].items():
    if 'id_file_fattura' in fattura and fattura['id_file_fattura'] is not None and len(fattura['id_file_fattura']) != 0: continue

    filename = find_filename(fattura)
    if filename is None: continue

    with open(filename, 'rb') as file:
        saveres = json.loads(session.put(login_be.address + '/file.ws?f=save', file.read(), headers={'X-File-Name': Path(filename).name, 'Content-Type':'application/pdf'}).text)
        id_file = saveres['body']['save']['file']['id']

        json.loads(session.post(login_be.address + '/zelda/fornitura.ws', verify=False, data={'f':'associaFileFattura','id_fattura':id_fattura,'id_file':id_file}).text)
        print('\033[32m{0}\033[0m'.format(filename))
