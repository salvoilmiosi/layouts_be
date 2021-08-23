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

script_dir = Path(__file__).parent

parser = ArgumentParser()
parser.add_argument('input_path', nargs='?', type=Path, default = script_dir / 'work/fatture')
parser.add_argument('-o', '--output-path', type=Path, default = script_dir / 'work/letture')
parser.add_argument('--pybls', type=Path, default = script_dir / '../out/bin')
parser.add_argument('-s', '--script', type=Path, default = script_dir / 'layouts/controllo.bls')
parser.add_argument('-e', '--errorlist', type=Path, default = script_dir / 'layouts/errors.lst')
parser.add_argument('-f', '--force-read', action='store_true')
parser.add_argument('-q', '--quiet', action='store_true')
parser.add_argument('-y', '--filter-year', type=int, default=0)
parser.add_argument('-j', '--nthreads', type=int, default=cpu_count())
parser.add_argument('-t', '--timeout', type=float, default=10.0)
args = parser.parse_args()

os.environ['PATH'] = str(args.pybls.resolve()) + os.pathsep + os.environ['PATH']
sys.path.insert(0, str(args.pybls.resolve()))

import pybls

def check_conguagli(results):
    sorted_data = []
    error_data = []
    for x in results:
        data = {'filename': x['filename'], 'errcode': x['errcode'], 'values': []}
        if 'layouts' in x:
            data['layouts'] = [str(Path(f).resolve()) for f in x['layouts']]
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
        ret = pybls.execbls(args.script, input_pdf=pdf_file, timeout=args.timeout)
    except:
        ret = {'errcode': -6, 'error': 'Errore di Sistema'}

    ret['filename'] = str(pdf_file.resolve())

    if not args.quiet:
        rel_path = pdf_file.relative_to(args.input_path)
        if ret['errcode'] == 0:
            if 'notes' in ret:
                print('\033[33m{0} ### {1}\033[0m'.format(rel_path, ', '.join(ret['notes']))) # yellow
            else:
                print(rel_path)
        elif ret['errcode'] > 0:
            print('\033[31m{0} ### {1}: {2}\033[0m'.format(rel_path, errcodes[ret['errcode']], ret['error'])) # red
        else:
            print('\033[35m{0} ### {1}\033[0m'.format(rel_path, ret['error'])) # magenta

    return ret

def lastmodified(f):
    return datetime.fromtimestamp(Path(f).stat().st_mtime)

if __name__ == '__main__':
    keep_file = lambda f : lastmodified(f).year >= args.filter_year
    path_to_json = lambda p : args.output_path / (Path(p).resolve().relative_to(args.input_path.resolve()).parts[0] + '.json')

    if args.output_path.is_dir():
        files_dict = {path_to_json(d) : [f for f in d.rglob('*.pdf') if keep_file(f)] \
            for d in args.input_path.iterdir() if d.is_dir()}
    else:
        files_dict = {args.output_path : [f for f in args.input_path.rglob('*.pdf') if keep_file(f)]}

    results = []
    files = []

    if args.force_read:
        for fs in files_dict.values():
            files += fs
    else:
        for output_file, in_files in files_dict.items():
            if output_file.exists():
                with open(output_file, 'r') as file:
                    data_dict = {f.resolve() : [] for f in in_files}
                    for x in json.load(file):
                        p = Path(x['filename'])
                        if p in data_dict: data_dict[p].append(x)
                
                for pdf_file in in_files:
                    old_data = data_dict[pdf_file.resolve()]
                    if old_data and all('layouts' in old_obj and all(\
                        lastmodified(f) < lastmodified(output_file) for f in old_obj['layouts'] + [pdf_file]) \
                            for old_obj in old_data):
                        results += old_data
                    else:
                        files.append(pdf_file)
            else:
                files += in_files

    if files:
        with Pool(min(len(files), args.nthreads)) as pool:
            results.extend(pool.map(read_pdf, files))

    results = check_conguagli(results)

    if args.output_path.is_dir():
        ordered_results = {f : [] for f in files_dict.keys()}
        for r in results:
            ordered_results[path_to_json(r['filename'])].append(r)
        for k,v in ordered_results.items():
            with open(k, 'w') as file:
                json.dump(v, file, indent=4)
    else:
        with open(args.output_path, 'w') as file:
            json.dump(results, file, indent=4)
