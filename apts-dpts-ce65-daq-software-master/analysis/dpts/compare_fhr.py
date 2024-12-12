#!/usr/bin/env python3

import argparse
import json,csv
import numpy as np
from matplotlib import pyplot as plt
from plotting_utils import plot_parameters
from plotting_utils import add_fhr_limit

def interpolate(data, it, param):
    x1,y1=data[it-1]
    x2,y2=data[it]
    thr=(y1+(param-x1)*(y2-y1)/(x2-x1))
    return thr

def fill_in_data(param_list, param_list_thr, data_fhr, data_thr):
    param_list_copy = param_list.copy()
    thrs = {}
    for param in param_list_copy:
        if param not in param_list_thr:
            it=next((i for i,d in enumerate(data_thr) if d[0]<param),0)
            if it==0:
                # take into account the different param vs threshold relations
                it=next((i for i,d in enumerate(data_thr) if d[0]>param),0)
                if it==0:
                    print(f"[INFO]:\tWill not extrapolate a threshold value to {param}. Removing from FHR data points.")
                    param_list.pop(param_list.index(param))
                    pop_index = [x[0] for x in data_fhr].index(param)
                    data_fhr.pop(pop_index)
                else:
                    thrs[param] =  interpolate(data_thr, it, param)
            else:
                thrs[param] =  interpolate(data_thr, it, param)
        else:
            thr_index = param_list_thr.index(param)
            thrs[param] = data_thr[thr_index][1]

    return thrs

parser = argparse.ArgumentParser("Comparison of fake hit-rate vs chip parameter for multiple chips.",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("csv", help="CSV file containing a column for chip IDs and and a column for the path to the json files with the FHR measurement results (json file created by fhrana_param.py).")
parser.add_argument("param", help="Chip parameter looped over by thr_fhr_parameter_scan.py.")
parser.add_argument('--outdir', default="./plots", help="Directory with output files.")
parser.add_argument('--vbb-list',nargs='+', default=["0.0","-1.2","-3.0"], help="The VBB values that will be analysed.")
parser.add_argument('--ntrgs', type=int, default=10000, help="Number of triggers used in measurement.")
parser.add_argument('--xlim',nargs=2,type=int,default=[],help='X-axis limits: lower higher.')
parser.add_argument('--mask' , action='store_true', help="Whether the fhr is plotted with masked data as well")
parser.add_argument('--save-data' , default=None, help="File name of output data written to a csv file.")
parser.add_argument('--thresh', action='store_true', help="Read the third column in the csv file, which contains the path to the json files "\
                    "with the threshold measurement results (json file created by thresholdana_param.py) and put the threshold on the x-axis "\
                    "instead of the parameter. There is a possibility to add the threshold conversion value (mV to e-) as the fourth "
                    "column, if not added it will take a value of 1.")
args = parser.parse_args()

with open("okabe_ito.json") as jf:
        clrs = json.load(jf)
colors={
    "none": ["black","lightgray","gray","dimgray"],
    "tid":  [clrs["sky blue"],clrs["blue"],"cornflowerblue","tab:blue","darkblue","slateblue"],
    "niel": [clrs["reddish purple"],clrs["orange"],clrs["vermillion"],clrs["yellow"],"indianred","tab:red","darkred","coral"],
    "mixed":[clrs["bluish green"],"tab:green","limegreen","darkgreen","lime"]
}
colors_idx={
    "none":0,
    "tid":0,
    "niel":0,
    "mixed":0
}

if "NIEL" in args.csv:
    fname = args.outdir+'/chip_comp_noiseocc_NIEL'
elif "TID" in args.csv:
    fname = args.outdir+'/chip_comp_noiseocc_TID'
elif "both" in args.csv:
    fname = args.outdir+'/chip_comp_noiseocc_both'
else:
    fname = args.outdir+'/chip_comp_noiseocc'    

# set up units
units = {'IRESET':'pA', 'IDB':'nA', 'IBIAS':'nA', 'VCASB':'mV', 'VCASN':'mV', 'VBB':'V'}
if args.param in units:
    units = units[args.param]
else:
    raise ValueError(f"{args.param} is not a valid chip parameter. Please choose from: VCASB, VCASN, IRESET, IDB or IBIAS.")

results_files = []
sensors = []
thr_files = []
conv_factors = []

with open(args.csv) as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        if '#' in row['sensor']: continue
        sensors.append(row['sensor'])
        results_files.append(row['fname'])
        if args.thresh:
            thr_files.append(row['thr'])
            if 'conv_factor' in row:
                conv_factors.append(float(row['conv_factor']))
            else:
                conv_factors.append(1)                

results = []
for s_fn in results_files:
    with open(s_fn) as jf:
        results.append(json.load(jf))

if args.thresh:
    thrs = []
    for s_fn in thr_files:
        with open(s_fn) as jf:
            thrs.append(json.load(jf))

config = {}
config['id'] = "Different\ chips"

csv_data = {}

for vbb in args.vbb_list:

    config['vbb'] = config['sub'] = config['pwell'] = vbb
    
    # sensitivity limit of the measurement
    senselimit = 1/(args.ntrgs*4.001e-5*1024)

    plt.figure(f"Noise occ vs {args.param} at VBB = {vbb} V", figsize=(10,5))
    plt.title(f"Noise occ vs {args.param} at VBB = {vbb} V")
    plt.subplots_adjust(left=0.08,right=0.71,bottom=0.1,top=0.95)
    if args.thresh:
        plt.xlabel(f"Threshold ($e^-$)")
    else:
        plt.xlabel(f"{args.param} ({units})")
    plt.ylabel('Noise occupancy (pixel$^{-1}$ s$^{-1}$)')
    plt.yscale('log')

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

        csv_data[sensor_name] = []

        assert vbb in results[is_fn], f"VBB = {vbb} not in {args.param}_to_fhr.json for sensor {sensor_name}. Please choose a correct --vbb-list for all sensors."

        param_list = [x[0] for x in results[is_fn][vbb]]
        # fill in missing data values via linear interpolation for the thresholds
        # code will not interpolate FHR values and will not extrapolate threshold values
        if args.thresh:
            param_list_thr = [x[0] for x in thrs[is_fn]['Threshold mean'][vbb]]
            if len(param_list)>len(param_list_thr):
                print(f"[INFO]:\tFor VBB = {vbb} V and sensor = {sensor_name}:\n"\
                    "\tLength of FHR parameter list > length of THR parameter list.\n"\
                    f"\tMeasured FHR parameter values = {param_list}\n"\
                    f"\tMeasured THR parameter values = {param_list_thr}\n"\
                    f"\tMeasured THR values           = {[round(x[1],1) for x in thrs[is_fn]['Threshold mean'][vbb]]}\n"\
                    "\tWill add missing points via interpolation.")
                final_thrs = fill_in_data(param_list,param_list_thr,results[is_fn][vbb],thrs[is_fn]['Threshold mean'][vbb])
                print(f"\tNew THR parameter values      = {[round(key,1) for key in final_thrs.keys()]}")
                print(f"\tNew THR values                = {[round(value,1) for value in final_thrs.values()]}")
            elif len(param_list)<len(param_list_thr):
                final_thrs = dict(zip(param_list, [dict(thrs[is_fn]['Threshold mean'][vbb])[x] for x in param_list]))
            else:
                final_thrs = dict(zip(param_list, [x[1] for x in thrs[is_fn]['Threshold mean'][vbb]]))

        x = []
        y = []
        y_err = []
        y_mask = []
        y_mask_err = []

        for i in range(len(param_list)):
            error = []
            error_mask = []
            if args.thresh:
                x.append(final_thrs[param_list[i]]*conv_factors[is_fn])
            else:
                x.append(results[is_fn][vbb][i][0])
            y.append(results[is_fn][vbb][i][1])
            error.append(results[is_fn][vbb][i][2])
            error.append(results[is_fn][vbb][i][3])
            y_err.append(error)
            if args.mask:
                y_mask.append(results[is_fn][vbb][i][4])
                error_mask.append(results[is_fn][vbb][i][5])
                error_mask.append(results[is_fn][vbb][i][6])
                y_mask_err.append(error_mask)
                csv_data[sensor_name].append((y[-1],y_err[-1][0],y_err[-1][1],y_mask[-1],y_mask_err[-1][0],y_mask_err[-1][1]))
            else:
                csv_data[sensor_name].append((y[-1],y_err[-1][0],y_err[-1][1]))

        y_err = np.array(y_err).T
        y_mask_err = np.array(y_mask_err).T

        # if the colour cycle is exhausted, change style
        if is_fn>len(plt.rcParams['axes.prop_cycle'])-1:
            plt.errorbar(x,y,yerr=y_err,capsize=3,markeredgewidth=2,label=sensor_name,marker='s',linestyle=":",mfc="None",color=color)
            if args.mask: plt.errorbar(x,y_mask,yerr=y_mask_err,capsize=3,markeredgewidth=2,marker='s',linestyle="-.",mfc="None",color=color)
        else:
            plt.errorbar(x,y,yerr=y_err,capsize=3,markeredgewidth=2,label=sensor_name,marker='o',color=color)
            if args.mask: plt.errorbar(x,y_mask,yerr=y_mask_err,capsize=3,markeredgewidth=2,marker='o',linestyle="--",color=color)

    plt.legend(loc="lower left", bbox_to_anchor=(1.01, -0.01),prop={"size":9})
    plt.grid(axis='both')
    if args.xlim:
        plt.xlim(args.xlim)
    add_fhr_limit(senselimit)
    plot_parameters(config,1.02,1.0)
    plt.savefig(fname+"_"+args.param+"_VBB"+vbb+"V"+ ("_thr" if args.thresh else "") + ".png")

if args.write_data is not None:
    with open(args.write_data, 'w') as f:
        writer = csv.writer(f)
        if args.mask: writer.writerow(["ibias", "fhr", "fhr_err_l", "fhr_err_h", "fhr_mask", "fhr_mask_err_l", "fhr_mask_err_h"])
        else: writer.writerow(["ibias", "fhr", "fhr_err_l", "fhr_err_h"])
        for j in csv_data.keys():
            for i in range(len(csv_data[j])):
                row = []
                row.append(j)
                row.append(csv_data[j][i][0])
                row.append(csv_data[j][i][1])
                row.append(csv_data[j][i][2])
                if args.mask:
                    row.append(csv_data[j][i][3])
                    row.append(csv_data[j][i][4])
                    row.append(csv_data[j][i][5])
                writer.writerow(row)
    f.close()

plt.show()
            
