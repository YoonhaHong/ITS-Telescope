#!/usr/bin/env python3
import argparse
import json
import os
import numpy as np
from matplotlib import pyplot as plt
import matplotlib.ticker as ticker
import datetime
import copy
import sys
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__),"../../analysis/dpts")))
from plotting_utils import plot_parameters

parser = argparse.ArgumentParser()
parser.add_argument("folder", help="File containing the folders of all measurements.")
parser.add_argument('--outdir' , default="./plots", help="Directory with output files")
parser.add_argument("--json", help=".json file containing measurement info.")
parser.add_argument('-q', '--quiet', action='store_true', help="Do not display plots.")
parser.add_argument('--filter', action='store_true', help="Filter for tuned runs.")
parser.add_argument('--latest', default=None, help="Filter for tuned runs.")
parser.add_argument('--linlog', default=None, type=float, help="Point at which to change from lin to log in minutes. Full linear if None")
args = parser.parse_args()

if not os.path.exists(args.outdir): os.makedirs(args.outdir)


def date_to_fraction_days(date):
    return date.days + date.seconds/(3600*24)

def date_to_fraction_minutes(date):
    return date.total_seconds()/60

units = {'IRESET':'pA', 'IDB':'nA', 'IBIAS':'nA', 'VCASB':'mV', 'VCASN':'mV', 'VBB':'V'} 

if args.latest:
    args.latest = datetime.datetime.strptime(args.latest, r"%Y%m%d_%H%M%S")
else:
    args.latest = datetime.datetime.max

excludes = []
includes = []
#B43
excludes += ["dpts_threshold_20230310_092038", "dpts_threshold_20230310_091628", "dpts_threshold_20230310_153834", "dpts_threshold_20230310_153601",\
                "dpts_threshold_20230310_153240", "dpts_threshold_20230310_124428", "dpts_threshold_20230310_114947", "dpts_threshold_20230310_153240"\
                "dpts_threshold_20230310_153601", "dpts_threshold_20230310_153834"]
#B47
excludes += ["dpts_threshold_20230311_140904"]

#B22
excludes += ["dpts_threshold_20230310_122037"]

#B44
includes += ["dpts_threshold_20230314_130953", "dpts_threshold_20230317_232911"]
excludes += ["dpts_threshold_20230327_140655", "dpts_threshold_20230327_144332"]


data = []
header=False
irrad_params = None
for file in sorted(os.listdir(args.folder)):
    if "threshold" in file and ".npz" in file:
        fname=file.replace("_analyzed.npz","")
        time = datetime.datetime.strptime(fname.replace("dpts_threshold_",""), r"%Y%m%d_%H%M%S")
        if time > args.latest or fname in excludes:
            continue
        npz=np.load(args.folder+file)
        data.append({n:npz[n] for n in npz.files})
        data[-1]["fname"]=fname
        with open(args.folder+fname+".json") as jf:
            data[-1]["json"]=json.load(jf)
        data[-1]["time"] = time
    if "irrad" in file:
        with open(args.folder+file) as jf:
            irrad_params = json.load(jf)

assert irrad_params is not None, "No irradiaton steps loaded. This is not implemented yet"

if isinstance(irrad_params["minutes_per_step"], list):
    irrad_params["minutes_per_step_dt"]=[datetime.timedelta(minutes=min) for min in irrad_params["minutes_per_step"]]
else:
    irrad_params["minutes_per_step_dt"]=[datetime.timedelta(minutes=irrad_params["minutes_per_step"]) for _ in irrad_params["stepstarts"]]
irrad_params["stepstarts_dt"]=[]
for time in irrad_params["stepstarts"]:
    irrad_params["stepstarts_dt"].append(datetime.datetime.strptime(time, r"%Y%m%d_%H%M%S"))

if data[-1]["json"]["chip"] == "44":
    data=[date for date in data if date["json"]["vcasb"] >= 100 and not date["json"]["vcasb"] == 180]

for ifile, file in enumerate(data[:-1]):
    file["tuned"]=file["json"]["vcasb"] == data[ifile+1]["json"]["vcasb"]
    if file["fname"] in includes: file["tuned"]=True
data[-1]["tuned"]=False



xmax = 600
nbins = 60

processed_data = {}

for func,title,datatype in [
    (np.nanmean,'threshold_mean','thresholds'),
    (np.nanstd,'threshold_rms','thresholds'),
    (np.nanmean,'noise_mean','noise'),
    ]:
    processed_data[title] = {}
    maxy=[]
    
    x = []
    x_raw = []
    y = []
    vcasb = []

    for file in data:
        if not args.filter or file["tuned"]:
            # if file["json"]["chip"] == "44" and file["json"]["vcasb"] < 100: continue
            plot_data = file[datatype]
            plot_data[plot_data==0] = np.nan
            
            # reject outliers
            d = np.abs(plot_data - np.nanmedian(plot_data))
            mdev = np.nanmedian(d)
            s = d/mdev if mdev else 0.
            plot_data = plot_data[s<5]
            
            plot_data = plot_data.ravel()
            temp = func(plot_data)
            if not np.isnan(temp):
                x.append(file["time"])
                x_raw.append(file["fname"].replace("dpts_threshold_",""))
                y.append(temp)
                vcasb.append(file["json"]["vcasb"])
    processed_data[title] = {}
    processed_data[title]["x"] = x
    processed_data[title]["x_raw"] = x_raw
    processed_data[title]["y"] = y
    processed_data[title]["vcasb"] = vcasb





for title in ['threshold_mean', 'threshold_rms', 'noise_mean']:
    fig = plt.figure(f"{title} and VCASB vs time",figsize=(7.5,5))
    ax = fig.add_subplot(111)
    plt.subplots_adjust(left=0.1,right=0.72500)
    plt.title(f"{title.replace('_',' ').title().replace('Rms','RMS')} and VCASB vs Time")
    plt.xlabel(f'Time since start of irradiation (minutes)')
    ax.set_ylabel(f"{title.replace('_',' ').title().replace('Rms','RMS')} (e$^-$)")
    ax2=ax.twinx()
    ax2.set_ylabel(f'VCASB (mV)')

    x = processed_data[title]["x"]
    x_raw = processed_data[title]["x_raw"]
    y = processed_data[title]["y"]
    vcasb = processed_data[title]["vcasb"]

    config=copy.deepcopy(data[0]["json"])
    config["vcasb"] = "variable"

    if config["chip"] in ["42", "43"]:
        radnote="Irradiation\n10x 10kGy"
    elif config["chip"] in ["45", "47"]:
        radnote="Irradiation\n10x 1kGy"
    elif config["chip"] in ["44", "46"]:
        radnote="Irradiation\n[1,2,5,10,20,\n50,100,200] kGy"
    else:
        radnote=None

    if irrad_params is None:
        starting_date = min(x)
    else:
        starting_date = min(irrad_params["stepstarts_dt"])
    x_minutes = [(date - starting_date).total_seconds()/60 for date in x]
    if irrad_params is not None:
        printed=False
        for time, length in zip(irrad_params["stepstarts_dt"], irrad_params["minutes_per_step_dt"]):
            ax.axvspan(date_to_fraction_minutes(time - starting_date), date_to_fraction_minutes(time + length - starting_date), color="red", alpha=0.3, label=(radnote if not printed else None))
            printed=True

    if title == "threshold_mean":
        target=125
        if config["chip"] in ["42", "43"]:
            pm=5
        elif config["chip"] in ["45", "47"]:
            pm=1
        else:
            radnote=None
        if radnote:
            ax.axhspan(target-pm,target+pm, color="C0", alpha=0.2)
        if config["chip"] in ["42", "43", "45", "47"]:
            ax.axhline(125, label="Target Threshold", linestyle = 'dashed', alpha=0.5)

    ax.plot(x_minutes,y,marker='o', label="Meas. Threshold")
    ax2.plot(x_minutes,vcasb,marker='o', color="C1", label="VCASB")
    if args.linlog is not None:
        linlimit=args.linlog
        ax2.set_xscale("symlog", linthresh=linlimit)
        plt.text(linlimit, -0.02*(plt.gca().get_ylim()[1]-plt.gca().get_ylim()[0]), "lin → log", ha="center", va="top")
        plt.axvline(linlimit, color="grey", alpha=0.3, label="Lin → log", linestyle="--")
    maxy+=y
    ax.set_ylim(0,round((max([m for m in maxy if m<1000])+10)/10)*10)      
    ax2.set_ylim(0,1.1*max([file["json"]["vcasb"] for file in data]))
    # ax.set_ylim(100,150)      


    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines + lines2, labels + labels2, loc='lower left',bbox_to_anchor=(1.08, -0.01),prop={"size":9})
    ax2.grid(axis='both')
    if config["chip"] in ["42", "43"]:
        dosenote="100kGy (10Mrad)"
    elif config["chip"] in ["45", "47"]:
        # dosenote="Irradiation\n10x 1kGy"
        dosenote="10kGy (1Mrad)"
    elif config["chip"] in ["44", "46"]:
        # dosenote="Irradiation\n[1,2,5,10,20,\n50,100,200] kGy"
        dosenote="500kGy (50Mrad)"
    elif config["chip"] == "22":
        dosenote="5000kGy (500Mrad)"
    else:
        dosenote=None
    addtexts=["\n$\\bf{Irradiation}$",
                "10keV X-Rays",
                "1kGy/min",
                "Total dose:"]
    addtexts.append(dosenote)
    plot_parameters(config,1.15,1.0,addtexts)
    # fig.tight_layout()

    if args.filter and title == "threshold_mean" and config["chip"] in ["42", "43", "45", "47"]:
        np.savez(f"B{config['chip']}_filtered_output", vcasb=vcasb, threshold=y, times=x_raw)

    if title=="threshold_mean":
        print(list(zip(vcasb,x_raw,y)))

    plt.savefig(os.path.join(args.outdir,config["id"]+"_"+title+("_tunedonly" if args.filter else "")+(f"_ll{args.linlog}" if args.linlog else "")+".png"),dpi=500)


if not args.quiet: plt.show()

