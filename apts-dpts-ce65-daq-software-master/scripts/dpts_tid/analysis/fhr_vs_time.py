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
parser.add_argument("--mask",default=False, help="...")
parser.add_argument('-q', '--quiet', action='store_true', help="Do not display plots.")
parser.add_argument('--filter', action='store_true', help="Filter for tuned runs.")
parser.add_argument('--latest', default=None, help="Filter for tuned runs.")
parser.add_argument('--linlog', default=None, type=float, help="Point at which to change from lin to log in minutes. Full linear if None")
args = parser.parse_args()

if not os.path.exists(args.outdir): os.makedirs(args.folder,args.outdir)

def add_fhr_limit(limit=1./(1e4*4.001e-5*1024), handle=plt):
    handle.axhline(limit,linestyle='dashed',color='grey')
    if isinstance(handle, plt.Axes):
        ax = handle
    else:
        ax = plt.gca()
    handle.text(ax.get_xlim()[1]*0.98,limit*0.85,
        "FHR measurement sensitivity limit",
        fontsize=7,
        ha='right', va='top',
    )

def date_to_fraction_days(date):
    return date.days + date.seconds/(3600*24)

def date_to_fraction_minutes(date):
    return date.total_seconds()/60

units = {'IRESET':'pA', 'IDB':'nA', 'IBIAS':'nA', 'VCASB':'mV', 'VCASN':'mV', 'VBB':'V'} 

excludes = []

excludes += ["dpts_fhr_20230311_104858"] #B45

excludes += ["dpts_fhr_20230314_093455", "dpts_fhr_20230313_203240", "dpts_fhr_20230406_164152"] #B46

excludes += ["dpts_fhr_20230328_174730", "dpts_fhr_20230413_182227"] #B22

excludes += ["dpts_fhr_20230406_155501", "dpts_fhr_20230406_152022"] #B44

if args.latest:
    args.latest = datetime.datetime.strptime(args.latest, r"%Y%m%d_%H%M%S")
else:
    args.latest = datetime.datetime.max

data = []

header=False
irrad_params = None
for file in sorted(os.listdir(args.folder)):
    if "fhr" in file and ".npz" in file:
        fname=file.replace("_analyzed.npz","")
        time = datetime.datetime.strptime(fname.replace("dpts_fhr_",""), r"%Y%m%d_%H%M%S")
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
    data=[date for date in data if date["json"]["vcasb"] >= 100]

if data[-1]["json"]["chip"] == "22":
    data=[date for date in data if date["json"]["vcasb"] >= 100]

for ifile, file in enumerate(data[:-1]):
    file["tuned"]=file["json"]["vcasb"] == data[ifile+1]["json"]["vcasb"]
data[-1]["tuned"]=False


# sensitivity limit of the measurement
senselimit = 1/(data[0]["json"]['ntrg']*4.001e-5*1024)

processed_data = {}

for fname in ['noiseocc', 'totalnoisy']:
    processed_data[fname] = {}


    x = []
    x_raw = []
    y = []
    y_err = []
    y_masked = []
    y_masked_err = []
    vcasb = []

    for file in data:
        if not args.filter or file["tuned"]:
            plotdata = float(file[fname])
            if plotdata is None: continue
            x.append(file["time"])
            x_raw.append(file["fname"].replace("dpts_fhr_",""))
            y.append(plotdata)
            vcasb.append(file["json"]["vcasb"])

            if fname=='noiseocc':
                plotdata_err = file[f'{fname}_err']
                plotdata_masked = float(file[f"{fname}_masked"])
                plotdata_masked_err = file[f'{fname}_masked_err']
                y_err.append(plotdata_err)
                y_masked.append(plotdata_masked)
                y_masked_err.append(plotdata_masked_err)
    processed_data[fname] = {}
    processed_data[fname]["x"] = x
    processed_data[fname]["x_raw"] = x_raw
    processed_data[fname]["y"] = y
    processed_data[fname]["y_err"] = y_err
    processed_data[fname]["y_masked"] = y_masked
    processed_data[fname]["y_masked_err"] = y_masked_err
    processed_data[fname]["vcasb"] = vcasb


for title, fname in [("Chip noise occ.", 'noiseocc'),
                     ("Number of noisy Pixels", 'totalnoisy')]:
    fig = plt.figure(f"{title} and VCASB vs time",figsize=(7.5,5))
    ax = fig.add_subplot(111)
    plt.subplots_adjust(left=0.1,right=0.72500)
    # plt.subplots_adjust(left=0.1,right=0.775)
    plt.title(f"{title} vs time")
    plt.xlabel(f'Time since start of irradiation (minutes)')
    ax2=ax.twinx()
    ax2.set_ylabel(f'VCASB (mV)')
    # plt.xlabel(f'Time since first measurement (days)')

    x = processed_data[fname]["x"]
    x_raw = processed_data[fname]["x_raw"]
    y = processed_data[fname]["y"]
    y_err = processed_data[fname]["y_err"]
    y_masked = processed_data[fname]["y_masked"]
    y_masked_err = processed_data[fname]["y_masked_err"]
    vcasb = processed_data[fname]["vcasb"]

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

    if fname=='noiseocc': 
        y_err = np.array(y_err).T
        y_masked_err = np.array(y_masked_err).T
        ax.errorbar(x_minutes,y,yerr=y_err,capsize=3,markeredgewidth=2,marker='o')
        if args.mask:
            ax.errorbar(x_minutes,y_masked,yerr=y_masked_err,capsize=3,markeredgewidth=2,marker='o',linestyle='dashed',mfc='none')
        # if config["id"] == "DPTSSW22B22":
        #     xpos = 0.52
        if args.linlog is not None:
            linlimit=args.linlog
            ax2.set_xscale("symlog", linthresh=linlimit)
            plt.text(linlimit, -0.02*(plt.gca().get_ylim()[1]-plt.gca().get_ylim()[0]), "lin → log", ha="center", va="top")
            plt.axvline(linlimit, color="grey", alpha=0.3, label="Lin → log", linestyle="--")
    else:
        ax.plot(x_minutes,y,marker='o')
        if args.linlog is not None:
            linlimit=args.linlog
            ax2.set_xscale("symlog", linthresh=linlimit)
            plt.text(linlimit, -0.02*(plt.gca().get_ylim()[1]-plt.gca().get_ylim()[0]), "lin → log", ha="center", va="top")
            plt.axvline(linlimit, color="grey", alpha=0.3, label="Lin → log", linestyle="--")

    ax2.plot(x_minutes,vcasb,marker='o', color="C1", label="VCASB")


    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines + lines2, labels + labels2, loc='lower left',bbox_to_anchor=(1.08, -0.01),prop={"size":9})
    # ax2.grid(axis='both')


    if fname=='noiseocc':
        ax.set_ylabel('Noise occupancy (hits s$^{-1}$ pixel$^{-1}$)')
        ax.set_yscale('log')
        ax.grid(axis='both')
        plt.axhline(y = senselimit, color = 'tab:gray', linestyle = 'dashed')
    if fname=='totalnoisy':
        ax2.grid(axis='both')
        ax.set_ylabel('Pixels')
    if config["chip"] in ["42", "43"]:
        dosenote="100kGy (10Mrad)"
    elif config["chip"] in ["45", "47"]:
        dosenote="10kGy (1Mrad)"
    elif config["chip"] in ["44", "46"]:
        dosenote="500kGy (50Mrad)"
    else:
        dosenote="5000kGy (500Mrad)"
    addtexts=["\n$\\bf{Irradiation}$",
                "10keV X-Rays",
                "1kGy/min",
                "Total dose:"]
    addtexts.append(dosenote)
    plot_parameters(config,1.15,1.0,addtexts)   
    add_fhr_limit(senselimit, handle=ax)



    plt.savefig(os.path.join(args.outdir,config["id"]+"_"+fname+("_tunedonly" if args.filter else "")+(f"_ll{args.linlog}" if args.linlog else "")+".png"),dpi=500)


    if fname == "noiseocc":
        # print(y)
        for i, (yc, yl, yh) in enumerate(zip(y, *y_err)):
            print(i, f"central:{yc}, lower:{yl}, upper:{yh}")
    if args.latest and fname == "noiseocc" and config["chip"] in ["42", "43", "45", "47"]:
        np.savez(f"B{config['chip']}_filtered_output_fhr", vcasb=vcasb, fhr=y, fhrerr=y_err, times=x_raw)


if not args.quiet: plt.show()







