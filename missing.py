#!/usr/bin/env python

import json
import blsconfig
from pathlib import Path
from datetime import date
from dateutil.relativedelta import relativedelta

clienti = {}

for f in blsconfig.read_output_path.glob('*.json'):
    with open(f, 'r') as file:
        data = json.load(file)

    obj_cliente = {}
    for obj in data:
        if not 'values' in obj: continue
        for v in obj['values']:
            pod = v['codice_pod']
            if pod not in obj_cliente:
                obj_cliente[pod] = []
            obj_cliente[pod].append(date.fromisoformat(v['mese_fattura']))
    clienti[f.name] = obj_cliente

check_date = date.today()
check_date = date(check_date.year, check_date.month, 1)

for _ in range(10):
    check_date -= relativedelta(months=1)
    not_found = 0
    for nome,cliente in clienti.items():
        for pod,mesi in cliente.items():
            if check_date not in mesi:
                not_found += 1
                print(nome, pod, check_date)
    if not_found == 0: break