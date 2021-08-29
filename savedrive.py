#!/usr/bin/env python

from pathlib import Path
from datetime import date
import blsconfig
import json
import shutil
import os

with open(Path(__file__).parent / 'clienti.json', 'r') as file:
    clienti = json.load(file)

for k,v in clienti['clients'].items():
    try:
        with open(blsconfig.read_output_path / (k + ".json"), 'r') as file:
            in_lettura = json.load(file)
    except FileNotFoundError:
        continue

    for f in in_lettura:
        filename = blsconfig.google_drive_dir
        if 'dir' in v:
            filename /= v['dir']
        try:
            file_from = f['filename']
            if not f['values']: continue

            mese_fattura=date.fromisoformat(f['values'][0]['mese_fattura'])
            if mese_fattura.year < 2020:
                continue
            pod=f['values'][0]['codice_pod'][-3:]
            if 'pods' in v:
                pattern = v['pods'][pod]['filename']
            else:
                pattern = v['filename']
            filename /= pattern.replace('%filename%',Path(file_from).stem).replace('%pod%', pod).replace('%year%', '{:04}'.format(mese_fattura.year)).replace('%month%', '{:02}'.format(mese_fattura.month))
            if not filename.exists():
                print(file_from, filename)
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                shutil.copy(file_from, filename)
        except (KeyError, ValueError):
            pass
