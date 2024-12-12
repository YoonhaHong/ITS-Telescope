#!/usr/bin/env python3

import argparse
import json
import csv, os
import numpy as np
from matplotlib import pyplot as plt
from plotting_utils import plot_parameters
from plotting_utils import add_fhr_limit

parser = argparse.ArgumentParser("Analysis of fake hit-rate vs chip parameter for data taken using scripts/thr_fhr_parameter_scan.py",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("csv", help=".csv file created by thr_fhr_parameter_scan.py")
parser.add_argument("--param", default=None, help="Chip paramater looped over by thr_fhr_parameter_scan.py")
parser.add_argument('--outdir' , default="./plots/", help="Directory with output files")
parser.add_argument("--json", help=".json file containing measurement info.")
parser.add_argument('--mask' , action='store_true', help="Whether the fhr is plotted with masked data as well")
parser.add_argument('-q', '--quiet', action='store_true', help="Do not display plots.")
args = parser.parse_args()

if args.param is None:
    args.param = args.csv.split("_vbb")[0].split("_")[-1]

# set up units
units = {'IRESET':'pA', 'IDB':'nA', 'IBIAS':'nA', 'VCASB':'mV', 'VCASN':'mV', 'VBB':'V'} 
if args.param in units:
    args.units = units[args.param]
else:
    raise ValueError(f"{args.param} is not a valid chip parameter. Please choose from: VCASB, VCASN, IRESET, IDB, IBIAS or VBB.")

data = {}

inpath = args.csv[:args.csv.rfind('/')+1]
outdir = inpath+args.outdir
if not os.path.exists(outdir): os.makedirs(outdir)

with open(args.csv) as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        if '#' in row['vbb']: continue
        vbb=float(row['vbb'])
        param_value=float(row[f'{args.param.lower()}'])
        fname=row['fname'] if 'fname' in row else row['fhr']
        if vbb not in data: data[vbb]={}
        fpath=inpath+fname+'_analyzed.npz'
        if not os.path.exists(fpath):
            print(fpath, "not found, skipping.")
            continue
        npz = np.load(fpath)
        data[vbb][param_value] = {k:npz[k] for k in npz.files}
        if args.json is None:
            args.json = inpath+fname+".json"

with open(args.json) as jf:
    config = json.load(jf)
config['vcasb'] = config[args.param.lower()] = "variable"
config['sub'] = None

# sensitivity limit of the measurement
senselimit = 1/(config['ntrg']*4.001e-5*1024)

processed_data = {}
for title,fname in [
    ('Chip noise occ.','noiseocc'),
    ('Number of noisy pixels','totalnoisy'),
    ('Fraction of bad trains','bad_train_fraction'),
    ]:
    processed_data[fname] = {}
    if args.param=="VBB":
        plt.figure(f"{title} vs VBB",figsize=(7.5,5))
        plt.title(f"{title} vs VBB")
        plt.xlabel('VBB (V)')
        x = []
        y = []
        y_err = []
        y_masked = []
        y_masked_err = []
        for vbb in sorted(data.keys(),reverse=True):
            param_value = list(data[vbb].keys())
            plotdata = float(data[vbb][param_value[0]][fname])
            x.append(abs(vbb))
            y.append(plotdata)
            if fname=='noiseocc':
                plotdata_err = data[vbb][param_value[0]][f'{fname}_err']
                plotdata_masked = data[vbb][param_value[0]][f"{fname}_masked"]
                plotdata_masked_err = data[vbb][param_value[0]][f'{fname}_masked_err']
                y_err.append(plotdata_err)
                y_masked.append(plotdata_masked)
                y_masked_err.append(plotdata_masked_err)
        if fname=='noiseocc':
            y_err = np.array(y_err).T
            y_masked_err = np.array(y_masked_err).T
            if args.mask:
                plt.errorbar(x,y,yerr=y_err,capsize=3,markeredgewidth=2,marker='o',label="no mask")
                plt.errorbar(x,y_masked,yerr=y_masked_err,capsize=3,markeredgewidth=2,marker='o',label="masked")
            else:
                plt.errorbar(x,y,yerr=y_err,capsize=3,markeredgewidth=2,marker='o')
            plt.legend(loc="best", prop={"family":"monospace","size":8})
        else:
            plt.plot(x,y,marker='o',label="with cal.")
        if args.mask and fname=='noiseocc':
            processed_data[fname][vbb] = list(zip(x,y,y_err[0],y_err[1],y_masked,y_masked_err[0],y_masked_err[1]))
        elif fname=='noiseocc':
            processed_data[fname][vbb] = list(zip(x,y,y_err[0],y_err[1]))
        else:
            processed_data[fname][vbb] = list(zip(x,y,y_err))
    else:
        plt.figure(f"{title} vs {args.param}",figsize=(7.5,5))
        plt.title(f"{title} vs {args.param}")
        plt.xlabel(f'{args.param} ({args.units})')
        for ivbb,vbb in enumerate(sorted(data.keys(),reverse=True)):
            x = []
            y = []
            y_err = []
            y_masked = []
            y_masked_err = []
            for param_value in sorted(data[vbb].keys()):
                plotdata = float(data[vbb][param_value][fname])
                if plotdata is None: continue
                x.append(param_value)
                y.append(plotdata)
                if fname=='noiseocc':
                    plotdata_err = data[vbb][param_value][f'{fname}_err']
                    plotdata_masked = float(data[vbb][param_value][f"{fname}_masked"])
                    plotdata_masked_err = data[vbb][param_value][f'{fname}_masked_err']
                    y_err.append(plotdata_err)
                    y_masked.append(plotdata_masked)
                    y_masked_err.append(plotdata_masked_err)
            if fname=='noiseocc': 
                y_err = np.array(y_err).T
                y_masked_err = np.array(y_masked_err).T
                plt.errorbar(x,y,yerr=y_err,capsize=3,markeredgewidth=2,label=f"V$_{{sub}}$={vbb} V",marker='o',color=f"C{ivbb}")
                if args.mask:
                    plt.errorbar(x,y_masked,yerr=y_masked_err,capsize=3,markeredgewidth=2,label=f"V$_{{sub}}$={vbb} V,\n masked",marker='o',linestyle='dashed',color=f"C{ivbb}",mfc='none')
            else:
                plt.plot(x,y,label=f"V$_{{sub}}$={vbb} V",marker='o')
            if args.mask and fname=='noiseocc':
                processed_data[fname][vbb] = list(zip(x,y,y_err[0],y_err[1],y_masked,y_masked_err[0],y_masked_err[1]))
            elif fname=='noiseocc':
                processed_data[fname][vbb] = list(zip(x,y,y_err[0],y_err[1]))
            else:
                processed_data[fname][vbb] = list(zip(x,y,y_err))
        plt.legend(loc='lower left',bbox_to_anchor=(1.01, -0.01),prop={"size":9})

    if fname=='noiseocc':
        plt.ylabel('Noise occupancy (hits s$^{-1}$ pixel$^{-1}$)')
        plt.yscale('log')
        plt.axhline(y = senselimit, color = 'tab:gray', linestyle = 'dashed')
    if fname=='totalnoisy':
        plt.ylabel('Pixels')
    if fname=='bad_train_fraction':
        plt.ylabel('% of bad trains')
        plt.axhline(y = 1, color = 'tab:gray', linestyle = 'dashed')
        plt.text(plt.xlim()[0]-1,1.15,"1",fontsize=10,ha='right', va='top')
    plt.grid(axis='both')
    plt.subplots_adjust(left=0.1,right=0.80)
    plot_parameters(config,1.02,1.0)
    if fname=='noiseocc': add_fhr_limit(senselimit)
    plt.savefig(outdir+fname+".png",dpi=300)

with open(outdir+args.param+"_to_fhr.json",'w') as jf:
    json.dump(processed_data['noiseocc'],jf,indent=4)

if not args.quiet: plt.show()
