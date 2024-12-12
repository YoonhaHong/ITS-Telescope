#!/usr/bin/env python3

import argparse
import json,csv
from matplotlib import pyplot as plt
from plotting_utils import plot_parameters

parser = argparse.ArgumentParser("Comparison of threshold vs chip parameter for multiple chips.",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("csv", help="CSV file containing a column for chip IDs and a column for the path to the json files with the threshold measurement results (json file created by thresholdana_param.py).")
parser.add_argument("param", help="Chip parameter looped over by thr_fhr_parameter_scan.py.")
parser.add_argument('--outdir', default="./plots", help="Directory with output files.")
parser.add_argument('--vbb-list',nargs='+', default=["0.0","-1.2","-3.0"], help="The VBB values that will be analysed.")
parser.add_argument('--xlim',nargs=2,type=int,default=[],help='X-axis limits: lower higher.')
parser.add_argument('--save-data' , default=None, help="File name of output data written to a csv file.")
parser.add_argument('--thresh', action='store_true', help="Plot vs measured threshold")
args = parser.parse_args()

with open("okabe_ito.json") as jf:
        clrs = json.load(jf)
colors={
    "none": ["black","lightgray","gray","dimgray"],
    "tid":  [clrs["sky blue"],clrs["blue"],"cornflowerblue","tab:blue","darkblue","slateblue"],
    "niel": [clrs["reddish purple"],clrs["orange"],clrs["vermillion"],clrs["yellow"],"indianred","tab:red","darkred","coral"],
    "mixed":[clrs["bluish green"],"tab:green","limegreen","darkgreen","lime"]
}

if "NIEL" in args.csv:
    fname = args.outdir+'/chip_comp_NIEL'
elif "TID" in args.csv:
    fname = args.outdir+'/chip_comp_TID'
elif "both" in args.csv:
    fname = args.outdir+'/chip_comp_both'
else:
    fname = args.outdir+'/chip_comp'

# set up units
units = {'IRESET':'pA', 'IDB':'nA', 'IBIAS':'nA', 'VCASB':'mV', 'VCASN':'mV', 'VBB':'V'}
if args.param in units:
    units = units[args.param]
else:
    raise ValueError(f"{args.param} is not a valid chip parameter. Please choose from: VCASB, VCASN, IRESET, IDB or IBIAS.")

results_files = []
sensors = []
conv_factors = []

with open(args.csv) as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        if '#' in row['sensor']: continue
        sensors.append(row['sensor'])
        results_files.append(row['fname'])
        if 'conv_factor' in row:
                conv_factors.append(float(row['conv_factor']))
        else:
            conv_factors.append(1)

results = []
for s_fn in results_files:
    with open(s_fn) as jf:
        results.append(json.load(jf))

config = {}
config['id'] = "Different\ chips"

csv_data = {}

for title in ['Threshold mean', 'Threshold RMS', 'Noise mean', 'Noise RMS']:
    for vbb in args.vbb_list:
        colors_idx={
            "none":0,
            "tid":0,
            "niel":0,
            "mixed":0
        }

        config['vbb'] = config['sub'] = config['pwell'] = vbb

        csv_data[title] = {}

        plt.figure(f"{title} vs {args.param} at VBB = {vbb} V", figsize=(10,5))
        plt.title(f"{title} vs {args.param} at VBB = {vbb} V")
        plt.subplots_adjust(left=0.08,right=0.71,bottom=0.1,top=0.95)
        if args.thresh:
            plt.xlabel(f"Threshold ($e^-$)")
        else:
            plt.xlabel(f"{args.param} ({units})")
        plt.ylabel(f"{title} ($e^-$)")
        for is_fn,s_fn in enumerate(results_files):
            if "Non" in sensors[is_fn]:
                sensor_name = sensors[is_fn].split('_')[0]
                color = colors['none'][colors_idx['none']]
                colors_idx['none'] += 1
            elif sensors[is_fn]=="proton":
                sensor_name = "10 kGy + 10$^{13}$ 1MeV n$_{eq}$ cm$^{-2}$ (B3)"
                color = colors['mixed'][colors_idx['mixed']]
                colors_idx['mixed'] += 1
            elif "13_B" in sensors[is_fn] or "14_B" in sensors[is_fn] or "15_B" in sensors[is_fn]:
                sensor_name = f"10$^{{{sensors[is_fn].split('_')[0]}}}$ 1MeV n$_{{eq}}$ cm$^{{-2}}$ ({sensors[is_fn].split('_')[-1]})"
                color = colors['niel'][colors_idx['niel']]
                colors_idx['niel'] += 1
            elif "10_B" in sensors[is_fn] or "100_B" in sensors[is_fn] or "500_B" in sensors[is_fn]:
                sensor_name = f"{sensors[is_fn].split('_')[0]} kGy ({sensors[is_fn].split('_')[-1]})"
                color = colors['tid'][colors_idx['tid']]
                colors_idx['tid'] += 1
            else:
                sensor_name = sensors[is_fn]
                color = list(clrs.values())[is_fn]

            csv_data[title][sensor_name] = []

            assert vbb in results[is_fn][title], f"VBB = {vbb} not in {args.param}_to_thr.json for sensor {sensor_name}. Please choose a correct --vbb-list for all sensors."

            x = []
            y = []
            for i in range(len(results[is_fn][title][vbb])):
                if results[is_fn]['Threshold RMS'][vbb][i][1]>50 or results[is_fn]['Noise mean'][vbb][i][1]>30: continue
                if args.thresh:
                    x.append(results[is_fn]['Threshold mean'][vbb][i][1]*conv_factors[is_fn])
                else:
                    x.append(results[is_fn][title][vbb][i][0])
                y.append(results[is_fn][title][vbb][i][1])
                csv_data[title][sensor_name].append(y[-1])
            # if the colour cycle is exhausted, change style
            if is_fn>len(plt.rcParams['axes.prop_cycle'])-1:
                plt.plot(x,y,label=sensor_name,marker='o',linestyle="--",mfc="white",color=color)
            else:
                plt.plot(x,y,label=sensor_name,marker='o',color=color)
        
        plt.legend(loc="lower left", bbox_to_anchor=(1.01, -0.01),prop={"size":9})
        plt.grid(axis='both')
        if args.xlim:
            plt.xlim(args.xlim)
        plot_parameters(config,1.02,1.0)
        plt.savefig(fname+f"{title.replace(' ', '_')}"+"_"+args.param+"_VBB"+vbb+"V" + ("_thr" if args.thresh else "") + ".png")

if args.write_data is not None:
    with open(args.write_data, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(["ibias", "thr_mean", "thr_rms", "noise_mean", "noise_rms"])
        for j in csv_data['Threshold mean'].keys():
            for i in range(len(csv_data['Threshold mean'][j])):
                row = []
                row.append(j)
                row.append(csv_data['Threshold mean'][j][i])
                row.append(csv_data['Threshold RMS'][j][i])
                row.append(csv_data['Noise mean'][j][i])
                row.append(csv_data['Noise RMS'][j][i])
                writer.writerow(row)
    f.close()

plt.show()
            
