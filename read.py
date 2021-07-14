#!/usr/bin/env python

from multiprocessing import Pool, cpu_count
from pathlib import Path
from datetime import date, datetime
from argparse import ArgumentParser
from termcolor import cprint
import json
import os
import sys

pybls_path = str(Path(__file__).resolve().parent.parent / 'out/bin')
os.environ['PATH'] = pybls_path + os.pathsep + os.environ['PATH']
sys.path.insert(0, pybls_path)

import pybls

os.system('color')

parser = ArgumentParser()
parser.add_argument('input_directory')
parser.add_argument('output_file')
parser.add_argument('-s', '--script', default=Path(__file__).resolve().parent / 'layouts/controllo.bls')
parser.add_argument('-e', '--errorlist', default=Path(__file__).resolve().parent / 'layouts/errors.lst')
parser.add_argument('-f', '--force-read', action='store_true')
parser.add_argument('-c', '--cached', action='store_true')
parser.add_argument('-y', '--filter-year', type=int, default=0)
parser.add_argument('-j', '--nthreads', type=int, default=cpu_count())
parser.add_argument('-t', '--timeout', type=float, default=10.0)
parser.add_argument('-l', '--language', default='')
args = parser.parse_args()

input_directory = Path(args.input_directory).resolve()
output_file = Path(args.output_file)

def check_conguagli(results):
    sorted_data = []
    error_data = []
    for x in results:
        data = {'filename': x['filename'], 'errcode': x['errcode'], 'values': []}
        if 'layouts' in x:
            data['layouts'] = x['layouts']
        if 'error' in x:
            data['error'] = x['error']
            error_data.append(data.copy())
        elif 'values' in x:
            for v in x['values']:
                data['values'] = [v]
                sorted_data.append(data.copy())
        
    sorted_data.sort(key = lambda obj : (
        obj['values'][0]['codice_pod'][0],
        date.fromisoformat(obj['values'][0]['mese_fattura'][0]),
        date.fromisoformat(obj['values'][0]['data_fattura'][0])))

    for i in range(1, len(sorted_data)):
        old_values = sorted_data[i-1]['values'][0]
        cur_values = sorted_data[i]['values'][0]

        old_pod = old_values['codice_pod'][0]
        new_pod = cur_values['codice_pod'][0]

        old_mesefatt = date.fromisoformat(old_values['mese_fattura'][0])
        new_mesefatt = date.fromisoformat(cur_values['mese_fattura'][0])

        old_datafatt = date.fromisoformat(old_values['data_fattura'][0])
        new_datafatt = date.fromisoformat(cur_values['data_fattura'][0])

        if old_pod == new_pod and old_mesefatt == new_mesefatt and new_datafatt > old_datafatt:
            cur_values['conguaglio'] = True

    return sorted_data + error_data

required_data = ('fornitore', 'numero_fattura', 'mese_fattura', 'data_fattura', 'codice_pod')

with open(args.errorlist, 'r') as file:
    errcodes = [line.strip() for line in file.readlines()]

def read_pdf(pdf_file):
    try:
        ret = pybls.execbls(args.script, input_pdf=pdf_file, timeout=args.timeout, language=args.language, use_cache=args.cached)
    except:
        ret = {'errcode': -6, 'error': 'Errore di Sistema'}

    ret['filename'] = str(pdf_file)

    if 'values' in ret and not all(all(i in v for i in required_data) for v in ret['values']):
        ret.pop('values')
        ret['errcode'] = -1
        ret['error'] = 'Dati Mancanti'
    
    rel_path = pdf_file.relative_to(input_directory)
    if ret['errcode'] == 0:
        if 'notes' in ret:
            cprint('{0} ### {1}'.format(rel_path, ', '.join(ret['notes'])), 'yellow')
        else:
            print(rel_path)
    elif ret['errcode'] > 0:
        cprint('{0} ### {1}: {2}'.format(rel_path, errcodes[ret['errcode']], ret['error']), 'red')
    else:
        cprint('{0} ### {1}'.format(rel_path, ret['error']), 'magenta')

    return ret

def lastmodified(f):
    return datetime.fromtimestamp(Path(f).stat().st_mtime)

if __name__ == '__main__':
    in_files = [f for f in input_directory.rglob('*.pdf') if lastmodified(f).year >= args.filter_year]

    results = []
    files = []

    # Rilegge i vecchi file solo se il layout e' stato ricompilato
    if not args.force_read and output_file.exists():
        with open(output_file, 'r') as file:
            in_data = json.load(file)

        for pdf_file in in_files:
            skip = False
            for old_obj in filter(lambda x : x['filename'] == str(pdf_file), in_data):
                if 'layouts' in old_obj and all(lastmodified(f) < lastmodified(output_file) for f in old_obj['layouts'] + [pdf_file]):
                    results.append(old_obj)
                    skip = True
            if not skip: files.append(pdf_file)
    else:
        files = in_files

    if files:
        with Pool(min(len(files), args.nthreads)) as pool:
            results.extend(pool.map(read_pdf, files))

    results = check_conguagli(results)

    with open(output_file, 'w') as file:
        json.dump(results, file, indent=4)
