import argparse
import json
import os
import subprocess
import sys
import time

from datetime import datetime
from pathlib import Path
from statistics import mean, median

import plotly.express as px
import plotly.io as pio

import pandas as pd


from logger import get_logger

logger, prev_hop_list = get_logger(), []
# check_stamp = None
out_dir = str(Path(__file__).resolve().parent / 'traces to')


def check_tr_path(out_dir):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)


check_tr_path(out_dir)


def check_file(ifile, check_stamp):
    global logger
    try:
        if os.path.exists(ifile):
            file, ext = os.path.splitext(ifile)
            nfile = f"{file} {check_stamp}{ext}"
            os.rename(ifile, nfile)
    except Exception as e:
        logger.error(e)


def get_stamp():
    return str(datetime.now())[:-7].replace(':', '')


def traceroute_to_file(data, ofile, msg=None):
    global logger
    with open(ofile, 'a+') as outfile:
        outfile.write(f"{msg}\n")
        outfile.write(data)
        outfile.write(f"\n{'=' * 88}\n\n")


def traceroute_to_json(jfile, tr_dict_list=None):
    global logger, check_stamp
    check_file(jfile, check_stamp)
    with open(jfile, 'w', encoding='utf-8') as outfile:
        json.dump(tr_dict_list, outfile, indent=4)


def check_delay(i, args):
    global logger
    if i < args.NUM_RUNS:
        if args.RUN_DELAY:
            delay = args.RUN_DELAY
            time.sleep(delay)
            logger.info(f"{delay} seconds")


def trace_hops(trlist: list):
    global logger, prev_hop_list
    for i, line in enumerate(trlist):
        if 'traceroute' not in line:
            hop_list = [i for i in line.replace('*', '').strip().split('  ')]
            if i == 0 or i == len(trlist) - 1:
                # tr_listings.append(hop_list)
                yield hop_list
            else:
                if not hop_list[0].isdigit():
                    if prev_hop_list[0].isdigit() and hop_list[0].isdigit():
                        # tr_listings.append(prev_hop_list)
                        yield prev_hop_list
                    else:
                        prev_hop_list += hop_list
                else:
                    # tr_listings.append(prev_hop_list)
                    yield prev_hop_list
                    prev_hop_list = hop_list


def process_tr_output(output):
    global logger
    tr_dict_list = []
    for k, tr_output in output.items():
        trlist = tr_output.splitlines()
        tr_listings = list(trh for trh in trace_hops(trlist) if trh and len(trh) > 0)
        for line in tr_listings:
            logger.info(f"{line = }")
            hop_dict = {}

            speeds = [float(i.split(' ')[0]) for i in line if i.endswith('ms')]
            logger.info(f"{speeds = }")
            hop_dict['hop'], hop_dict['speeds'] = line[0], speeds
            hop_dict['hosts'] = [i for i in line if not i.isdigit() and not i.endswith('ms')]

            tr_dict_list.append(hop_dict)
            logger.info('=' * 88)
            logger.info(hop_dict)

    return tr_dict_list


def multi_tr_pro(multi_tr_list, file):
    global check_stamp, logger
    combined_dict = {}
    for i, d in enumerate(multi_tr_list):
        d_i = d['hop']
        if d_i in combined_dict:
            for k, v in d.items():
                if k in ('hosts', 'speeds', ):
                    combined_dict[d_i][k] = combined_dict[d_i][k] + v
        else:
            combined_dict[d_i] = {}
            combined_dict[d_i]['hop'] = d['hop']
            combined_dict[d_i]['hosts'] = d['hosts']
            combined_dict[d_i]['speeds'] = d['speeds']

    check_file(file, check_stamp)
    traceroute_to_json(file, list(combined_dict.values()))
    return combined_dict


def main(argv=None):
    global logger, prev_hop_list
    logger.info(f"{argv = }")
    output ={}
    logger.info(f"{sys.argv = }")
    args = parse_trace_args()
    if args.TARGET:
        # global logger
        global check_stamp
        check_stamp = get_stamp()
        logger = get_logger(f"trace to {args.TARGET}")
        logger.info(args)
        cfile = f'{out_dir}{os.sep}{args.TARGET} cmptd.json'
        for i in range(1, args.NUM_RUNS + 1):
            tfile = f'{out_dir}{os.sep}{args.TARGET}-{i}.txt'
            jfile = f'{out_dir}{os.sep}{args.TARGET}-{i} data.json'
            jfyl_re = f'{out_dir}{os.sep}{args.TARGET}-{i} re.json'
            check_file(tfile, check_stamp)
            msg = f"Running Traceroute to {args.TARGET}"
            logger.info(msg)
            rslt = subprocess.run(
                ['traceroute', "-m", str(args.MAX_HOPS), args.TARGET], stdout=subprocess.PIPE  # , check=False
            )
            tr_output = rslt.stdout.decode('utf-8')
            # write trace output to file
            traceroute_to_file(tr_output, tfile, msg)
            msg = f"Traceroute {i} completed"
            logger.info(msg)
            logger.info(tr_output)
            output[i] = tr_output

            check_delay(i, args)

        multi_tr_list = process_tr_output(output)
        traceroute_to_json(jfile, multi_tr_list)

        d4c = multi_tr_pro(multi_tr_list, jfyl_re)
        computed = [{
            "hop": d["hop"], "hosts": d["hosts"],
            "avg": round(mean(d["speeds"]), 3), "min": min(d["speeds"]), "med": round(median(sorted(d["speeds"])), 3),
            "max": max(d["speeds"]),
        } for i, d in d4c.items() if len(d["speeds"])>0]
        logger.info('=' * 88)
        check_file(cfile, check_stamp)
        traceroute_to_json(cfile, computed)

        dl = [{k: v for k, v in i.items() if k in ('hop', 'speeds',)} for i in d4c.values()]
        df = pd.DataFrame(dl)

        df = df.assign(speeds=df.speeds).explode('speeds')

        return d4c


def parse_trace_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-n', dest='NUM_RUNS', default=1, metavar='NUM_RUNS', type=int, help='Number of times traceroute will run'
    )
    parser.add_argument(
        '-d', dest='RUN_DELAY', default=None, metavar='RUN_DELAY', type=float,
        help='Number of seconds to wait between two consecutive runs')
    parser.add_argument(
        '-m', dest='MAX_HOPS', default=52, metavar='MAX_HOPS', type=int, help='Number of times traceroute will run')
    parser.add_argument(
        '-o', dest='OUTPUT', default=os.getcwd() + os.sep + 'output.txt', metavar='OUTPUT', type=str,
        help='Path and name of output JSON file containing the stats')
    parser.add_argument(
        '-g', dest='GRAPH', default=None, metavar='GRAPH', type=str,
        help='Path and name of output PDF file containing stats graph')
    parser.add_argument(
        '-t', dest='TARGET', default=None, metavar='TARGET', type=str, help='A target domain name or IP address')
    parser.add_argument(
        '--test', dest='TEST_DIR', default=os.getcwd() + '/folder/output.txt', metavar='TEST_DIR', type=str,
        help='Directory containing num_runs text files, each of which contains the output of a traceroute run. '
             'If present, this will override all other options and tcpdump will not be invoked. '
             'Stats will be computed over the  traceroute output stored in the text files')
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    main(sys.argv[1:])
