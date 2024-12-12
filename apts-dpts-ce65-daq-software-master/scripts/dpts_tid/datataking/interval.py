#!/usr/bin/env python3
import datetime
from time import sleep
import os
import argparse
import re

units = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}

parser = argparse.ArgumentParser("Script to run command in fixed intervals")
parser.add_argument("--interval", "-i", default="30m", help="Interval between executions. Use s, m, h, d as unit.")
parser.add_argument("--after", "-a", help="Command to be executed before the program closes.")
parser.add_argument("command", help="Command to be executed.")
args = parser.parse_args()    

match = re.fullmatch(r"(?P<value>\d+)(?P<unit>[smhd])\b", args.interval)
assert match is not None, "Invalid interval."
interval = match.groupdict()
dt_interval = datetime.timedelta(**{units[interval["unit"]]: float(interval["value"])})
print(f"\"{args.command}\" will be executed every {interval['value']} {units[interval['unit']]}...")

last_exec_time = datetime.datetime.min

try:
    while True:
        if datetime.datetime.now() - last_exec_time >= dt_interval:
            last_exec_time = datetime.datetime.now()
            os.system(args.command)
        sleep(1)
except KeyboardInterrupt as e:
    if args.after:
        print("")
        os.system(args.after)
