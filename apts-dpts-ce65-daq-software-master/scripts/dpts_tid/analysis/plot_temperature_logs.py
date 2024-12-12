#!/usr/bin/env python3

import argparse
import json
import csv, os
import numpy as np
from matplotlib import pyplot as plt
from scipy.stats import skew
from plotting_utils import plot_parameters
from matplotlib.lines import Line2D
import datetime
import glob



parser = argparse.ArgumentParser("Plot chip currents and temperatures.")
parser.add_argument("folder", help="Folder of .csv files with current and temperature logs")
parser.add_argument('--outdir' , default="./plots", help="Directory for output plots")
parser.add_argument('--id' , default=None, help="Chip ID for logging purposes.")
parser.add_argument('--quiet', '-q', action="store_true", help="Don't show plots.")
parser.add_argument('--times', help="Path to irradiation times.")
args = parser.parse_args()

units = {"ia_ma": r"I$_{a}$ (mA)",
         "id_ma": r"I$_{d}$ (mA)",
         "ib_ma": r"I$_{b}$ (mA)",
         "ivbb_ma": r"I$_{VBB}$ (mA)",
         "t_degc": r"T$_{air}$ (°C)",
         "p_hpa": r"p (hPa)",
         "h_prh": r"H (%RH)",
         "tjig_degc": r"T$_{jig}$ (°C)"
        }

names = {"ia_ma": r"I$_{a}$",
         "id_ma": r"I$_{d}$",
         "ib_ma": r"I$_{b}$",
         "ivbb_ma": r"I$_{VBB}$",
         "t_degc": r"Air Temperature",
         "p_hpa": r"Pressure",
         "h_prh": r"Humidity",
         "tjig_degc": r"Cooling Jig Temperature"
        }


outdict = {}
header=False
for file in sorted(os.listdir(args.folder)):
    if ".csv" in file:
        with open(args.folder+file) as csvfile:
            reader = csv.DictReader(csvfile)
            if not header:
                for key in reader.fieldnames:
                    outdict[key] = []
                header=True
            for key in outdict:
                outdict[key].append([])            
            for row in reader:
                for key in row:
                    if key == "time":
                        outdict[key][-1].append(datetime.datetime.strptime(row[key], r"%Y%m%d_%H%M%S"))
                    elif key != "tjig_degc":
                        outdict[key][-1].append(float(row[key]))

            # print(len(outdict["time"]))
# print(outdict)
if args.times:
    with open(args.times) as jf:
        timesfile = json.load(jf)

# print(outdict["time"][0])
for key in outdict:
    if key != "time":
        plt.figure(key)
        for iset, set in enumerate(outdict["time"]):
                plt.plot(outdict["time"][iset], outdict[key][iset])
        plt.title((f"{args.id} " if args.id else "")+names[key])
        plt.xlabel("Timestamp")
        plt.ylabel(units[key])
        plt.grid()
        plt.xticks(rotation = 45)
        if key == "p_hpa" and args.id == "DPTSSW22B22":
            plt.annotate("Thunderstorm\nin Geneva", (0.8,0.4), (-25,100),arrowprops=dict(facecolor='red',edgecolor="red", shrink=0.05),xycoords="axes fraction", textcoords='offset pixels',bbox=dict(boxstyle="round,pad=0.3",fc="white", ec="red", lw=2))
        plt.tight_layout()
        # plt.savefig(f"{args.outdir}/{args.folder.split('/')[-3]}_{key}.png", bbox_inches="tight")
        plt.savefig(f"{args.outdir}/{args.id if args.id else args.folder.split('/')[-3]}_{key}.png", bbox_inches="tight")


plt.figure("currents")
for ikey, key in enumerate(["ia_ma", "id_ma", "ib_ma", "ivbb_ma"]):
    for iset, set in enumerate(outdict["time"]):
        plt.plot(outdict["time"][iset], outdict[key][iset], label=names[key] if iset==0 else None, color=f"C{ikey}")
plt.title((f"{args.id} " if args.id else "")+"Currents")
if args.id == "DPTSOW22B46":
    plt.annotate("Forgot to turn\non the script", (0.35,0.5), (-25,40),arrowprops=dict(facecolor='red',edgecolor="red", shrink=0.05),xycoords="axes fraction", textcoords='offset pixels',bbox=dict(boxstyle="round,pad=0.3",fc="white", ec="red", lw=2))
if args.times:

    if isinstance(timesfile["minutes_per_step"], list):
        timesfile["minutes_per_step_dt"]=[datetime.timedelta(minutes=min) for min in timesfile["minutes_per_step"]]
    else:
        timesfile["minutes_per_step_dt"]=[datetime.timedelta(minutes=timesfile["minutes_per_step"]) for _ in timesfile["stepstarts"]]
    timesfile["stepstarts_dt"]=[]
    for time in timesfile["stepstarts"]:
        timesfile["stepstarts_dt"].append(datetime.datetime.strptime(time, r"%Y%m%d_%H%M%S"))


    # step = datetime.timedelta(minutes=timesfile["minutes_per_step"])
    radnote = "Irradiation"
    printed = False
    for time, length in zip(timesfile["stepstarts_dt"], timesfile["minutes_per_step_dt"]):
        # start_time = datetime.datetime.strptime(timestamp, r"%Y%m%d_%H%M%S")
        # end_time = start_time + step
        # plt.axvspan(start_time, end_time, color="red", alpha=0.2, label=(radnote if not printed else None))
        plt.axvspan(time, time + length, color="red", alpha=0.3, label=(radnote if not printed else None))

        printed = True
plt.xlabel("Timestamp")
plt.ylabel("Current (mA)")
plt.xticks(rotation = 45)
plt.tight_layout()
plt.legend()
plt.grid()
# plt.savefig(f"{args.outdir}/{args.folder.split('/')[-3]}_currents.png", bbox_inches="tight")
plt.savefig(f"{args.outdir}/{args.id if args.id else args.folder.split('/')[-3]}_currents.png", bbox_inches="tight")


if "tjig_degc" in outdict.keys():
    plt.figure("temperatures")
    for ikey, key in enumerate(["t_degc", "tjig_degc"]):
        for iset, set in enumerate(outdict["time"]):
            plt.plot(outdict["time"][iset], outdict[key][iset], label=names[key] if iset==0 else None, color=f"C{ikey}")
    plt.title((f"{args.id} " if args.id else "")+"Temperatures")
    plt.xlabel("Timestamp")
    plt.ylabel("Temperature (°C)")
    plt.xticks(rotation = 45)
    plt.tight_layout()
    plt.legend()
    plt.grid()
    plt.savefig(f"{args.outdir}/{args.folder.split('/')[-3]}_temperatures.png", bbox_inches="tight")
    plt.savefig(f"{args.outdir}/{args.id if args.id else args.folder.split('/')[-3]}_temperatures.png", bbox_inches="tight")

if not args.quiet: plt.show()