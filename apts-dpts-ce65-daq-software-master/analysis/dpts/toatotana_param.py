#!/usr/bin/env python3

import argparse
import json
import csv, os
import numpy as np
from matplotlib import pyplot as plt
from scipy.stats import skew
from plotting_utils import plot_parameters
from matplotlib.lines import Line2D

def reject_outliers(data):
    data = np.array(data)

    d = np.abs(data - np.nanmedian(data))
    mdev = np.nanmedian(d)
    s = d/mdev if mdev else 0.
    data = data[s<5]
    
    return data

# for ToA fit parameter a, it is split into two types
def get_column_data(data,p_index,version):
    data_type1 = []
    data_type2 = []
    for r in range(32):
        for c in range(32):
            if version=="X" or version=="S":
                if (c%2==0 and r%2==0) or (c%2!=0 and r%2!=0):
                    data_type1.append(data[r][c][p_index])
                if (c%2==0 and r%2!=0) or (c%2!=0 and r%2==0): 
                    data_type2.append(data[r][c][p_index])
            elif version=="O":
                if c%2==0:
                    data_type1.append(data[r][c][p_index])
                else:
                    data_type2.append(data[r][c][p_index])
            else:
                raise ValueError(f"{version} is an incorrect chip version. Please choose from 'O', 'X' or 'S'.")

    data_type1 = np.array(data_type1)
    data_type2 = np.array(data_type2)
    data_type1 = reject_outliers(data_type1)
    data_type2 = reject_outliers(data_type2)

    return data_type1, data_type2

# function for ToT vs Vh fit
def totvhFit(x,a,b,c,d):
    return a*x+b-(c/(x-d))

# function for ToA vs Vh fit
def toavhFit(x,a,b,c):
    return a+(b/(x-c))

def analyse_toatotscan(args):
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
            fname=row['fname']
            vcasb[vbb]=float(row['vcasb'])
            if vbb not in data: data[vbb]={}
            npz = np.load(inpath+fname+'_analyzed.npz')
            data[vbb][param_value] = {k:npz[k] for k in npz.files}
            if args.json is None:
                args.json = inpath+fname+".json"

    with open(args.json) as jf:
        config = json.load(jf)
    
    if args.version is None:
        args.version = config['version']
    config['vcasb'] = config[args.param.lower()] = 'variable'
    config['sub'] = None

    nbins = 50

    # plot the mean of each fit parameter vs the chip parameter
    for title,datatype,p_index in [
        ('ToT a mean','tot_params',0),
        ('ToT b mean','tot_params',1),
        ('ToT c mean','tot_params',2),
        ('ToT d mean','tot_params',3),
        ('ToA a mean','timewalk_params',0),
        ('ToA b mean','timewalk_params',1),
        ('ToA c mean','timewalk_params',2)
        ]:
        plt.figure(f"{title} vs {args.param}",figsize=(7.5,5))
        plt.subplots_adjust(left=0.13,right=0.8)
        plt.title(f"{title} vs {args.param}")
        plt.xlabel(f'{args.param} ({args.units})')
        plt.ylabel(f'{title}')
        maxy=[]
        for vbb in sorted(data.keys(),reverse=True):
            x = []
            if title=="ToA a mean":
                y = [[] for i in range(2)]
                y_err = [[] for i in range(2)]
            else:
                y = []
                y_err = []
            for param_value in sorted(data[vbb].keys()):
                x.append(param_value)
                plot_data = data[vbb][param_value][datatype]
                plot_data[plot_data==0] = np.nan

                if title=="ToA a mean":
                    plot_data_type1, plot_data_type2 = get_column_data(plot_data,p_index,args.version)
                    y[0].append(np.nanmean(plot_data_type1))
                    y[1].append(np.nanmean(plot_data_type2))
                    y_err[0].append(np.nanstd(plot_data_type1))
                    y_err[1].append(np.nanstd(plot_data_type2))
                else:
                    plot_data = plot_data[:,:,p_index].flatten()
                    plot_data = reject_outliers(plot_data)
                    y.append(np.nanmean(plot_data))
                    y_err.append(np.nanstd(plot_data))
            if title=="ToA a mean":
                color = next(plt.gca()._get_lines.prop_cycler)['color']
                plt.errorbar(x,y[0],yerr=y_err[0],capsize=3,markeredgewidth=2,marker='o',color=color,label=f"V$_{{sub}}$={vbb} V")
                plt.errorbar(x,y[1],yerr=y_err[1],capsize=3,markeredgewidth=2,marker='o',color=color,linestyle='dashed',mfc='white')
            else:
                plt.errorbar(x,y,yerr=y_err,capsize=3,markeredgewidth=2,marker='o',label=f"V$_{{sub}}$={vbb} V")
            maxy+=y
        if title=="ToA a mean":
            handles, labels = plt.gca().get_legend_handles_labels()
            line1 = plt.errorbar([],[],yerr=[],capsize=5,markeredgewidth=2,marker='o',color='grey',label=f"Type 1")
            line2 = plt.errorbar([],[],yerr=[],capsize=5,markeredgewidth=2,marker='o',color='grey',label=f"Type 2",linestyle='dashed',mfc='white')
            handles.insert(0, line2)
            handles.insert(0, line1)
            plt.legend(handles=handles,loc='lower left',bbox_to_anchor=(1.01, -0.01),prop={"size":9})
        else:
            plt.legend(loc='lower left',bbox_to_anchor=(1.01, -0.01),prop={"size":9})
        plt.grid(axis='both')
        plot_parameters(config,1.02,1.0)
        plt.savefig(outdir+title.replace(" ", "_")+f"_{args.param}.png",dpi=300)
    
    # plot the histograms of the fit parameters
    for title,datatype,p_index in [
        ('ToT a','tot_params',0),
        ('ToT b','tot_params',1),
        ('ToT c','tot_params',2),
        ('ToT d','tot_params',3),
        ('ToA a','timewalk_params',0),
        ('ToA b','timewalk_params',1),
        ('ToA c','timewalk_params',2)
        ]:
        for vbb in sorted(data.keys(),reverse=True):
            plt.figure(f"{title} histo SUB/PWELL = {vbb} V",figsize=(7.5,5))
            plt.subplots_adjust(left=0.1,right=0.80,top=0.95)
            plt.xlabel(f'{title}')
            plt.ylabel(f'# pixels')
            for param_value in sorted(data[vbb].keys()):
                plot_data = data[vbb][param_value][datatype]
                plot_data = plot_data[:,:,p_index].flatten()
                plot_data[plot_data==0] = np.nan
                plot_data = reject_outliers(plot_data)
               
                plt.hist(plot_data, bins=nbins, alpha=0.5,
                   label=f"{args.param}: {param_value:3.0f} {args.units} Avg: {np.mean(plot_data):5.1f} RMS:  {np.std(plot_data):5.1f}")
            plt.legend(loc="upper right", prop={"family":"monospace","size":8})
            config['pwell'] = config['sub'] = vbb
            if args.param!="VCASB": config['vcasb'] = vcasb[vbb]
            plot_parameters(config,1.02,1.0)
            plt.savefig(outdir+title.replace(" ", "_")+f"_histo_{args.param}_VBB{vbb}V.png",dpi=300)
    
    processed_data = {}
    # plot the mean fits for each chip parameter value
    for title,yaxis,datatype in [
        ('ToT fit','ToT ($\mu$s)','tot_params'),
        ('ToA fit','ToA (ns)','timewalk_params'),
        ]:
        if "ToA" in title:
            processed_data[title+" type 1"] = {}
            processed_data[title+" type 2"] = {}
        else:
            processed_data[title] = {}
        for vbb in sorted(data.keys(),reverse=True):
            plt.figure(f"{title}, SUB/PWELL = {vbb} V",figsize=(7.5,5))
            plt.subplots_adjust(left=0.1, right=0.80)
            plt.xlabel(f'Vh (mV)')
            plt.ylabel(f'{yaxis}')
            maxy=0
            if "ToT" in title:
                processed_data[title][vbb] = {}
            else:
                processed_data[title+" type 1"][vbb] = {}
                processed_data[title+" type 2"][vbb] = {}
            
            for param_value in sorted(data[vbb].keys()):
                if "ToT" in title:
                    plot_data = data[vbb][param_value][datatype]
                    plot_data[plot_data==0] = np.nan
                    a_mean = np.nanmean(reject_outliers(plot_data[:,:,0].flatten()))
                    b_mean = np.nanmean(reject_outliers(plot_data[:,:,1].flatten()))
                    c_mean = np.nanmean(reject_outliers(plot_data[:,:,2].flatten()))
                    d_mean = np.nanmean(reject_outliers(plot_data[:,:,3].flatten()))

                    plotx = np.arange(d_mean+0.1,1200,2)
                    ploty = totvhFit(plotx,a_mean,b_mean,c_mean,d_mean)
                    if np.amax(ploty)>maxy: maxy = np.amax(ploty) 
                    plt.plot(plotx,ploty,label=f"{args.param}={int(param_value)} {args.units}")
                    processed_data[title][vbb][param_value] = [a_mean,b_mean,c_mean,d_mean]
                else:
                    plot_data = data[vbb][param_value][datatype]
                    plot_data[plot_data==0] = np.nan
                    a1 = []
                    a2 = []
                    b1 = []
                    b2 = []
                    c1 = []
                    c2 = []
                    for ir,r in enumerate(config["rows"]):
                        for ic,c in enumerate(config["cols"]):
                            if args.version=="X" or args.version=="S":
                                if (c%2==0 and r%2==0) or (c%2!=0 and r%2!=0):
                                    a1.append(plot_data[r][c][0])
                                    b1.append(plot_data[r][c][1])
                                    c1.append(plot_data[r][c][2])
                                if (c%2==0 and r%2!=0) or (c%2!=0 and r%2==0): 
                                    a2.append(plot_data[r][c][0])
                                    b2.append(plot_data[r][c][1])
                                    c2.append(plot_data[r][c][2])
                            elif args.version=="O":
                                if c%2==0:
                                    a1.append(plot_data[r][c][0])
                                    b1.append(plot_data[r][c][1])
                                    c1.append(plot_data[r][c][2])
                                else:
                                    a2.append(plot_data[r][c][0])
                                    b2.append(plot_data[r][c][1])
                                    c2.append(plot_data[r][c][2])
                            else:
                                raise ValueError(f"{args.version} is an incorrect chip version. Please choose from 'O', 'X' or 'S'.")
                    
                    a_mean1 = np.nanmean(reject_outliers(a1))
                    a_mean2 = np.nanmean(reject_outliers(a2))
                    b_mean1 = np.nanmean(reject_outliers(b1))
                    b_mean2 = np.nanmean(reject_outliers(b2))
                    c_mean1 = np.nanmean(reject_outliers(c1))
                    c_mean2 = np.nanmean(reject_outliers(c2))
                    
                    plotx1 = np.arange(0,1200,2)
                    plotx2 = np.arange(0,1200,2)
                    ploty1 = toavhFit(plotx1,a_mean1,b_mean1,c_mean1)
                    ploty2 = toavhFit(plotx2,a_mean2,b_mean2,c_mean2)
                    
                    ploty1 = ploty1[plotx1>c_mean1+0.1]
                    ploty2 = ploty2[plotx2>c_mean2+0.1]
                    plotx1 = plotx1[plotx1>c_mean1+0.1]
                    plotx2 = plotx2[plotx2>c_mean2+0.1]
                    color = next(plt.gca()._get_lines.prop_cycler)['color']
                    plt.plot(plotx1,ploty1,label=f"{args.param}={int(param_value)} {args.units}",color=color)
                    plt.plot(plotx2,ploty2,color=color,linestyle="dashed")
                    
                    processed_data[title+" type 1"][vbb][param_value] = [a_mean1,b_mean1,c_mean1]
                    processed_data[title+" type 2"][vbb][param_value] = [a_mean2,b_mean2,c_mean2]
            
            if "ToT" in title:
                plt.legend(loc="upper left", prop={"family":"monospace"})
                plt.ylim(0,maxy+1)
            if "ToA" in title:
                handles, labels = plt.gca().get_legend_handles_labels()
                from matplotlib.lines import Line2D
                line1 = Line2D([0], [0], label='Type 1', color='grey')
                line2 = Line2D([0], [0], label='Type 2', color='grey', linestyle="dashed")
                handles.insert(0, line2)
                handles.insert(0, line1)
                plt.legend(handles=handles,loc="upper right", prop={"family":"monospace"})
                plt.ylim(0,1000)
            plt.xlim(-10,1210)
            config['pwell'] = config['sub'] = vbb
            if args.param!="VCASB": config['vcasb'] = vcasb[vbb]
            plot_parameters(config, x=1.01, y=1.0)
            plt.savefig(outdir+title.replace(" ", "_")+f"_{args.param}_VBB{vbb}V.png",dpi=300)

    with open(outdir+args.param+"_to_toatot.json",'w') as jf:
        json.dump(processed_data,jf,indent=4)


if __name__=="__main__":
    parser = argparse.ArgumentParser("Analysis of ToA and ToT vs chip parameter for data taken using scripts/toa_tot_parameter_scan.py",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("csv", help=".csv file created by toa_tot_param_scan.py")
    parser.add_argument("--param", default=None, help="Chip paramater looped over by toa_tot_parameter_scan.py")
    parser.add_argument('--version' , default=None, help="The chip version to account for column cross-connect or not, either O, X or S. Picked up from json by default.")
    parser.add_argument("--json", help=".json file containing measurement info.")
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

    analyse_toatotscan(args)

    if not args.quiet:
        plt.show()
