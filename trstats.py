import argparse
import json
import os
import subprocess
import sys
import time

from datetime import datetime
from pathlib import Path
from statistics import mean, median

# import matplotlib.pyplot as plt
import pandas as pd
# import seaborn as sns


from logger import get_logger

out_dir = str(Path(__file__).resolve().parent / 'output')

if not os.path.exists(out_dir):
    os.makedirs(out_dir)

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
    help='Directory containing num_runs text files, each of which contains the output of a traceroute run.If present, '
         'this will override all other options and tcpdump will not be invoked. Stats will be computed over the '
         'traceroute output stored in the text files')
args = parser.parse_args()

output, prev_hop_list, tr_dict_list, tr_output, trlist = {}, None, [], None, []


# logger = get_logger()


def check_file(ifile):
    global logger
    try:
        if os.path.exists(ifile):
            file, ext = os.path.splitext(ifile)
            nfile = file + str(datetime.now())[:-7].replace(':', '') + ext
            os.rename(ifile, nfile)
    except Exception as e:
        logger.error(e)


def traceroute_to_file(ofile):
    global logger
    with open(ofile, 'a+') as outfile:
        outfile.write(f"{msg}\n")
        outfile.write(tr_output)
        outfile.write(f"\n{'=' * 88}\n\n")


def traceroute_to_json(jfile, tr_dict_list=None):
    global logger
    check_file(jfile)
    with open(jfile, 'w', encoding='utf-8') as outfile:
        json.dump(tr_dict_list, outfile, indent=4)


def check_delay():
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
            hop_list = [i for i in line.strip().split('  ')]
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


def process_tr_output():
    global logger
    for k, tr_output in output.items():
        trlist = tr_output.splitlines()
        tr_listings = list(trh for trh in trace_hops(trlist) if trh and len(trh) > 0 and all('*' not in i for i in trh))
        for line in tr_listings:
            logger.info(f"{line = }")
            hop_dict = {}
            speeds = [float(i.split(' ')[0]) for i in line if i.endswith('ms')]
            sorted(speeds)
            hop_dict['avg'] = round(mean(speeds), 3)
            logger.info(f"{speeds = }")
            hop_dict['hop'] = line[0]
            hop_dict['hosts'] = [i for i in line if not i.isdigit() and not i.endswith('ms')]
            hop_dict['max'] = max(speeds)
            hop_dict['med'] = median(speeds)
            hop_dict['min'] = min(speeds)
            # logger.info(stat)
            tr_dict_list.append(hop_dict)
            logger.info('=' * 88)
            logger.info(hop_dict)
    return tr_dict_list


def multi_tr_pro(multi_tr_list, file):
    global logger
    combined_dict = {}
    for i, d in enumerate(multi_tr_list):
        d_i = d['hop']
        if d_i in combined_dict:
            for k, v in d.items():
                if k not in ('hop', 'hosts',):
                    combined_dict[d_i][k] = combined_dict[d_i][k].append(v)
                if k == 'hosts':
                    combined_dict[d_i][k] = combined_dict[d_i][k] + v
        else:
            combined_dict[d_i] = {k: [v, ] for k, v in d.items() if k not in ('hop', 'hosts',)}
            combined_dict[d_i]['hop'], combined_dict[d_i]['hosts'] = d['hop'], d['hosts']

    check_file(file)
    traceroute_to_json(file, list(combined_dict.values()))


if args.TARGET:
    global logger
    logger = get_logger(f"trace to {args.TARGET}")
    logger.info(args)
    jfile, jfyl_re, tfile = f'trace to {args.TARGET} data.json', f'trace to {args.TARGET} re.json', f'trace to {args.TARGET}.txt'
    # if args.NUM_RUNS:# and args.NUM_RUNS > 1:
    check_file(tfile)
    multi_tr_list = []
    for i in range(1, args.NUM_RUNS + 1):
        # f.write('================================================1 \n')
        msg = f"Running Traceroute to {args.TARGET}"
        logger.info(msg)
        rslt = subprocess.run(
            ['traceroute', "-m", str(args.MAX_HOPS), args.TARGET], stdout=subprocess.PIPE  # , check=False
        )
        tr_output = rslt.stdout.decode('utf-8')
        # write trace output to file
        traceroute_to_file(tfile)
        msg = f"Traceroute {i} completed"
        logger.info(msg)
        logger.info(tr_output)
        output[i] = tr_output

        check_delay()

    multi_tr_list = process_tr_output()
    # process array/list of dicts
    multi_tr_pro(multi_tr_list, jfyl_re)
    tr_json = json.dumps(multi_tr_list, indent=4)

    logger.info(tr_json)
    logger.info('=' * 88)
    # check if file exist rename and add datetime stamp to backup
    traceroute_to_json(jfile)

    # df=pd.DataFrame.from_dict(tr_json, orient='columns')
    ##df.to_csv(jfile, header=None, index=None, sep=' ', mode='a')
    # logger.info(df.head())
    # sns.boxplot(y=df["avg"], x=df["hop"])
    # plt.show()

    # else:
    #    msg = f"Running Traceroute to {args.TARGET}"
    #    rslt = subprocess.run(
    #        ['traceroute', "-m", str(args.MAX_HOPS), args.TARGET], stdout=subprocess.PIPE  # , check=False
    #    )
    #    tr_output = rslt.stdout.decode('utf-8')
    #    msg = f"Traceroute completed"
    #    logger.info(msg)
    #    # write trace output to file
    #    traceroute_to_file(tfile)
    #    logger.info(tr_output)
    #    output['0'] = tr_output
#
#    tr_dict_list = process_tr_output()
#    tr_json = json.dumps(tr_dict_list)
#    logger.info(tr_json)
#    traceroute_to_json(jfile)
