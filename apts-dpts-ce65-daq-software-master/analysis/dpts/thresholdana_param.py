#!/usr/bin/env python3

import argparse
import json
import csv, os
import numpy as np
from matplotlib import pyplot as plt
from scipy.stats import skew
from plotting_utils import plot_parameters
import glob
from matplotlib import patches as ptc

def fit_func(x,a,b,c):
    return a*x*x+b*x+c

parser = argparse.ArgumentParser("Analysis of threshold vs chip parameter for data taken using scripts/thr_fhr_parameter_scan.py",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("csv", help=".csv file created by scripts/thr_fhr_parameter_scan.py")
parser.add_argument("--param", default=None,help="Chip paramater looped over by thr_fhr_parameter_scan.py")
parser.add_argument("--json", help=".json file containing measurement info.")
parser.add_argument('--axis-ratio', action='store_true', help="Plot the x-axis as the ratio of VCASB/param.")
parser.add_argument('-f', '--fit', action='store_true', help="Do fit of plots.")
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
vcasb = {}

infile = args.csv
inpath = infile[:infile.rfind('/')+1]
outdir = inpath+'plots/'
if not os.path.exists(outdir): os.makedirs(outdir)

with open(infile) as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        if '#' in row['vbb']: continue
        vbb=float(row['vbb'])
        param_value=float(row[f'{args.param.lower()}'])
        fname=row['fname'] if 'fname' in row else row['thr']
        vcasb[vbb]=float(row['vcasb'])
        if vbb not in data: data[vbb]={}
        npz = np.load(inpath+fname+'_analyzed.npz')
        data[vbb][param_value] = {k:npz[k] for k in npz.files}
        if args.json is None:
            args.json = inpath+fname+".json"

with open(args.json) as jf:
    config = json.load(jf)
config['vcasb'] = config[args.param.lower()] = "variable"
config['sub'] = None

xmax = config['vmax']
nbins = int(config['vmax']/10)

processed_data = {}
if args.fit:
    fit_parameters = {}

for func,title,datatype,lims in [
    (np.nanmean,'Threshold mean','thresholds','auto'),
    (np.nanstd,'Threshold RMS','thresholds','auto'),
    (lambda x: skew(x,nan_policy='omit'),'Threshold skewness','thresholds',(-0.5,4)),
    (np.nanmean,'Noise mean','noise','auto'),
    (np.nanstd,'Noise RMS','noise','auto'),
    (lambda x: skew(x,nan_policy='omit'),'Noise skewness','noise',(-0.5,4))
    ]:
    plt.figure(f"{title} vs {args.param}",figsize=(7.5,5))
    plt.subplots_adjust(left=0.1,right=0.80)
    plt.title(f"{title} vs {args.param}")
    if args.axis_ratio and args.param!='VCASB': plt.xlabel(f'VCASB/{args.param}')
    else: plt.xlabel(f'{args.param} ({args.units})')
    plt.ylabel(f'{title} (e$^-$)')
    processed_data[title] = {}
    if args.fit:
        fit_parameters[title] = {}
    maxy=[]
    for vbb in sorted(data.keys(),reverse=True):
        x = []
        y = []
        for param_value in sorted(data[vbb].keys()):
            plot_data = data[vbb][param_value][datatype]
            plot_data[plot_data==0] = np.nan
            
            # reject outliers
            d = np.abs(plot_data - np.nanmedian(plot_data))
            mdev = np.nanmedian(d)
            s = d/mdev if mdev else 0.
            plot_data = plot_data[s<5]
            
            plot_data = plot_data.ravel()
            if args.axis_ratio and args.param!='VCASB': x.append(vcasb[vbb]/param_value)
            else: x.append(param_value)
            y.append(func(plot_data))
        plt.plot(x,y,label=f"V$_{{sub}}$={vbb} V",marker='o')
        maxy+=y
        processed_data[title][vbb] = list(zip(x,y))
        if args.fit:
            a,b,c = np.polyfit(x,y,2)
            fit_parameters[title]['a'] = a
            fit_parameters[title]['b'] = b
            fit_parameters[title]['c'] = c
            x1 = np.linspace(x[0],x[-1],200)
            plt.plot(x1, fit_func(x1,a,b,c), color='tab:red', linewidth=1, label='fit')
            parameter_patch=ptc.Patch(color='tab:red',label=f'a: {a:5.2f} \n b: {b:5.2f} \n c: {c:5.2f}')
            legend1 = plt.legend(handles=[parameter_patch])
    plt.legend(loc='lower left',bbox_to_anchor=(1.01, -0.01),prop={"size":9})
    if args.fit:
        plt.gca().add_artist(legend1)
    if lims=='auto':
        plt.ylim(0,round((max([m for m in maxy if m<1000])+10)/10)*10)      
    else:
        plt.ylim(lims)  
    plt.grid(axis='both')
    plot_parameters(config,1.02,1.0)
    plt.savefig(outdir+title.replace(" ", "_")+f"_{args.param}.png",dpi=300)

with open(outdir+args.param+"_to_thr.json",'w') as jf:
    json.dump(processed_data,jf,indent=4,allow_nan=True)

if args.fit:
    with open(outdir+"thr_fit_parameters.json",'w') as jf:
        json.dump(fit_parameters,jf,indent=4,allow_nan=True)

for title,datatype in [
    ('Threshold','thresholds'),
    ('Noise', 'noise')
    ]:
    if title=='Noise': xmax*=0.1
    for vbb in sorted(data.keys(),reverse=True):
        plt.figure(f"{title}, VBB = {vbb} V",figsize=(7.5,5))
        plt.title(f"{title}, V$_{{sub}}$ = {vbb} V")
        plt.subplots_adjust(left=0.1,right=0.80,top=0.95)
        plt.xlabel(f'{title} (e$^-$)')
        plt.ylabel(f'# pixels / ({xmax/nbins:.1f} e$^-$)')
        for param_value in sorted(data[vbb].keys()):
            plot_data = data[vbb][param_value][datatype]
            plot_data[plot_data==0] = np.nan
           
            # reject outliers
            d = np.abs(plot_data - np.nanmedian(plot_data))
            mdev = np.nanmedian(d)
            s = d/mdev if mdev else 0.
            plot_data = plot_data[s<5]
           
            plot_data = plot_data.ravel()
            plt.hist(plot_data,range=(0,xmax), bins=nbins, alpha=0.5,
                label=f"{args.param}: {param_value:3.0f} {args.units} Avg: {np.nanmean(plot_data):5.1f} e$^-$ RMS:  {np.nanstd(plot_data):5.1f} e$^-$")
        plt.legend(loc="upper right", prop={"family":"monospace","size":8})
        plt.xlim(0,xmax)
        args.json = glob.glob(fr"{inpath}*{vbb}*.json")[0]
        with open(args.json) as jf:
            config = json.load(jf)
        config[args.param.lower()] = "variable"
        plot_parameters(config,1.02,1.0)
        plt.savefig(outdir+f"{title}_{args.param}_VBB{vbb}V.png",dpi=300)

if not args.quiet: plt.show()
