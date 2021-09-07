"""Project 1 will be about using traceroute, parsing its output, and performing a
statistical analysis of the traceroute results.
This project will require using Python to create a command line tool that
automatically executes traceroute multiple times towards a target domain name or IP
address specified as command line parameter. Based on multiple traceroute
executions, the program will need to derive latency statistics for each hop between
the traceroute client and the target machine.
To allow for repeatable tests, the program should also allow reading pre-generated
traceroute output traces stored on multiple text files (one text output trace per file).
Based on this pre-generated output, the program will need to compute the latency
statistics as for the case of live traceroute execution.
Additional details about Project 1 will be provided in class."""

import argparse
import os
import subprocess
import sys
import time

import json
from statistics import mean

parser = argparse.ArgumentParser()
parser.add_argument(
    '-n', dest='NUM_RUNS', default=None, metavar='NUM_RUNS', type=int, help='Number of times traceroute will run'
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
    '-i', type=argparse.FileType('w'), default=sys.stdin, metavar='PATH', help="Input file (default: standard input).")
parser.add_argument(
    '--test', dest='TEST_DIR', default=os.getcwd() + '/folder/output.txt', metavar='TEST_DIR', type=str,
    help='Directory containing num_runs text files, each of which contains the output of a traceroute run.If present, '
         'this will override all other options and tcpdump will not be invoked. Stats will be computed over the '
         'traceroute output stored in the text files')
args = parser.parse_args()
output, prev_hop_list, tr_dict_list, tr_output, trlist = {}, None, [], None, []


def traceroute_to_file():
    global outfile
    with open(f'trace to {args.TARGET}.txt', 'a+') as outfile:
        outfile.write(f"{msg}\n")
        outfile.write(tr_output)
        outfile.write(f"\n{'=' * 88}\n\n")


def check_delay():
    if i < args.NUM_RUNS:
        if args.RUN_DELAY:
            delay = 60 * args.RUN_DELAY
            time.sleep(delay)
            print(f"{delay} seconds")


def trace_hops(trlist:list):
    global prev_hop_list
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
    for k, tr_output in output.items():
        trlist = tr_output.splitlines()
        tr_listings = list(trh for trh in trace_hops(trlist) if trh and len(trh) > 0 and all('*' not in i for i in trh))
        for line in tr_listings:
            print(f"{line = }")
            hop_dict = {}
            hop_dict['hop'] = line[0]
            hop_dict['hosts'] = [i for i in line if not i.isdigit() and not i.endswith('ms')]
            speeds = [float(i.split(' ')[0]) for i in line if i.endswith('ms')]
            print(f"{speeds = }")
            hop_dict['avg'] = round(mean(speeds), 3)
            hop_dict['max'] = max(speeds)
            hop_dict['min'] = min(speeds)
            # print(stat)
            tr_dict_list.append(hop_dict)
            print('=' * 88)
            print(hop_dict)
    return tr_dict_list


if args.TARGET:
    # input_file_name = str(args.i.name)
    # f = open(input_file_name, "w")
    # input_file_name = args.OUTPUT
    # f = open(input_file_name, "w")
    # f.write('These are the parameters used for the output above' +str(sys.argv)+ '\n')

    # f.write('================================================ \n')

    if args.NUM_RUNS:
        multi_tr_list = []
        for i in range(1, args.NUM_RUNS + 1):
            # f.write('================================================1 \n')
            msg = f"Running Traceroute to {args.TARGET}"
            print(msg)
            rslt = subprocess.run(
                ['traceroute', "-m", str(args.MAX_HOPS), args.TARGET], stdout=subprocess.PIPE  # , check=False
            )
            tr_output = rslt.stdout.decode('utf-8')
            msg = f"Traceroute {i} completed"
            print(msg)
            # write trace output to file
            traceroute_to_file()
            print(tr_output)
            output[i] = tr_output

            check_delay()

            multi_tr_list.append(process_tr_output())

        tr_json = json.dumps(multi_tr_list)
        print(tr_json)
        with open(f'trace to {args.TARGET} data.json', 'w', encoding='utf-8') as outfile:
            json.dump(multi_tr_list, outfile)


    else:
        msg = f"Running Traceroute to {args.TARGET}"
        rslt = subprocess.run(
            ['traceroute', "-m", str(args.MAX_HOPS), args.TARGET], stdout=subprocess.PIPE  # , check=False
        )
        tr_output = rslt.stdout.decode('utf-8')
        msg = f"Traceroute completed"
        print(msg)
        # write trace output to file
        traceroute_to_file()
        print(tr_output)
        output['0'] = tr_output

        tr_dict_list = process_tr_output()
        tr_json = json.dumps(tr_dict_list)
        print(tr_json)
        with open(f'trace to {args.TARGET} data.json', 'w', encoding='utf-8') as outfile:
            json.dump(tr_dict_list, outfile)
