#!/usr/bin/env python

from multiprocessing import Pool, cpu_count
from pathlib import Path
from datetime import date, datetime
from argparse import ArgumentParser
import json
import os
import sys

if sys.platform == 'win32':
    os.system('color')

parser = ArgumentParser()
parser.add_argument('input_directory')
parser.add_argument('output_file')
parser.add_argument('--pybls', default=Path(__file__).resolve().parent.parent / 'out/bin')
parser.add_argument('-s', '--script', default=Path(__file__).resolve().parent / 'layouts/controllo.bls')
parser.add_argument('-e', '--errorlist', default=Path(__file__).resolve().parent / 'layouts/errors.lst')
parser.add_argument('-f', '--force-read', action='store_true')
parser.add_argument('-c', '--cached', action='store_true')
parser.add_argument('-y', '--filter-year', type=int, default=0)
parser.add_argument('-j', '--nthreads', type=int, default=cpu_count())
parser.add_argument('-t', '--timeout', type=float, default=10.0)
args = parser.parse_args()

os.environ['PATH'] = str(args.pybls) + os.pathsep + os.environ['PATH']
sys.path.insert(0, str(args.pybls))

import pybls

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
        obj['values'][0]['codice_pod'],
        date.fromisoformat(obj['values'][0]['mese_fattura']),
        date.fromisoformat(obj['values'][0]['data_fattura'])))

    for i in range(1, len(sorted_data)):
        old_values = sorted_data[i-1]['values'][0]
        cur_values = sorted_data[i]['values'][0]

        old_pod = old_values['codice_pod']
        new_pod = cur_values['codice_pod']

        old_mesefatt = date.fromisoformat(old_values['mese_fattura'])
        new_mesefatt = date.fromisoformat(cur_values['mese_fattura'])

        old_datafatt = date.fromisoformat(old_values['data_fattura'])
        new_datafatt = date.fromisoformat(cur_values['data_fattura'])

        if old_pod == new_pod and old_mesefatt == new_mesefatt and new_datafatt > old_datafatt:
            cur_values['conguaglio'] = True

    return sorted_data + error_data

with open(args.errorlist, 'r') as file:
    errcodes = [line.strip() for line in file.readlines()]

def read_pdf(pdf_file):
    try:
        ret = pybls.execbls(args.script, input_pdf=pdf_file, timeout=args.timeout, use_cache=args.cached)
    except:
        ret = {'errcode': -6, 'error': 'Errore di Sistema'}

    ret['filename'] = str(pdf_file)
    
    rel_path = pdf_file.relative_to(input_directory)
    if ret['errcode'] == 0:
        if 'notes' in ret:
            print('\033[33m{0} ### {1}'.format(rel_path, ', '.join(ret['notes'])))
        else:
            print(rel_path)
    elif ret['errcode'] > 0:
        print('\033[30m{0} ### {1}: {2}'.format(rel_path, errcodes[ret['errcode']], ret['error']))
    else:
        print('\033[35m{0} ### {1}'.format(rel_path, ret['error']))

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
