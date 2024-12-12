#!/usr/bin/env python3

import argparse
import json
import os
import numpy as np
from matplotlib import pyplot as plt
from plotting_utils import plot_parameters
from plotting_utils import add_fhr_limit
import pandas as pd
from scipy import special, stats

import scipy.integrate as integrate

def read_fhr_info(json_file):
    with open(json_file) as jf:
        par_to_fhr = json.load(jf)
    ret = []
    for vbb,plist in par_to_fhr.items():
        for row in plist:
            vcasb,fhr,fhr_low,fhr_high,fhr_masked,fhr_low_masked,fhr_high_masked=row[:7]
            ret.append({
                "vbb": float(vbb),
                "vcasb": float(vcasb),
                "fhr": fhr_masked,
                "fhr_low_err": fhr_low_masked,
                "fhr_up_err": fhr_high_masked
            })

    return pd.DataFrame(ret)

def read_thr_info(json_file):    
    with open(json_file) as jf:
        par_to_fhr = json.load(jf)
    ret = []
    for parameter,par_name in [('Threshold mean','thr_mean'),('Threshold RMS','thr_RMS'),('Noise mean','noise_mean'),('Noise RMS','noise_RMS')]:
        for vbb,plist in par_to_fhr[parameter].items():
            for row in plist:
                vcasb,par=row
                ret.append({
                    "vbb": float(vbb),
                    "vcasb": float(vcasb),
                    par_name: par
                })
    
    ret = pd.DataFrame(ret)
    ret = ret.groupby(['vbb','vcasb'],as_index=False).agg('first')

    return ret

def pol2(x,a,b,c):
    return a*x*x+b*x+c

def FHR_model(sigma_noise,mu_noise,sigma_thr,mu_thr):
    return integrate.quad(lambda n: special.erfc(mu_thr/(np.sqrt(2.)*np.sqrt(n*n+sigma_thr*sigma_thr)))*stats.norm.pdf(n,mu_noise,sigma_noise),0.0,20.0)


parser = argparse.ArgumentParser("Analysis of noise vs threshold for data taken using scripts/thr_fhr_parameter_scan.py",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("vcasb_to_fhr", help=".json file created by fhrana_param.py")
parser.add_argument("vcasb_to_thr", help=".json file created by thresholdana_param.py with threshold vs parameter")
parser.add_argument("fit_output", help=".json file created by thresholdana_param.py when fit option is True")
parser.add_argument("json", help=".json file containing measurement info.")
parser.add_argument("--param", default="VCASB", help="Chip paramater looped over by thr_fhr_parameter_scan.py")
parser.add_argument('--outdir' , default="./plots", help="Directory with output files")
parser.add_argument('-q', '--quiet', action='store_true', help="Do not display plots.")
args = parser.parse_args()

# set up units
units = {'IRESET':'pA', 'IDB':'nA', 'IBIAS':'nA', 'VCASB':'mV', 'VCASN':'mV', 'VBB':'V'} 
if args.param in units:
    args.units = units[args.param]
else:
    raise ValueError(f"{args.param} is not a valid chip parameter. Please choose from: VCASB, VCASN, IRESET, IDB, IBIAS or VBB.")

outdir = args.outdir+'/'
if not os.path.exists(outdir): os.makedirs(outdir)

with open(args.json) as jf:
    config = json.load(jf)
config['vcasb'] = config[args.param.lower()] = "variable"

with open(args.fit_output) as jf:
    fit_parameters = json.load(jf)

data = pd.merge(read_fhr_info(args.vcasb_to_fhr),read_thr_info(args.vcasb_to_thr),on=["vcasb","vbb"])

# sensitivity limit of the measurement
senselimit = 1/(config['ntrg']*4.001e-5*1024)

# compute the FHR model
data_FHR_model = []
data = data.reset_index()
for index, row in data.iterrows():
    mu_thr = pol2(row["vcasb"],fit_parameters["Threshold mean"]["a"],fit_parameters["Threshold mean"]["b"],fit_parameters["Threshold mean"]["c"])
    sigma_thr = pol2(row["vcasb"],fit_parameters["Threshold RMS"]["a"],fit_parameters["Threshold RMS"]["b"],fit_parameters["Threshold RMS"]["c"])
    mu_noise = pol2(row["vcasb"],fit_parameters["Noise mean"]["a"],fit_parameters["Noise mean"]["b"],fit_parameters["Noise mean"]["c"])
    sigma_noise = pol2(row["vcasb"],fit_parameters["Noise RMS"]["a"],fit_parameters["Noise RMS"]["b"],fit_parameters["Noise RMS"]["c"])
    data_FHR_model.append({"FHR_model"           : 1./40e-6*FHR_model(sigma_noise,mu_noise,sigma_thr,mu_thr)[0],
                           "FHR_model_10+"       : 1./40e-6*FHR_model(1.10*sigma_noise,1.10*mu_noise,1.10*sigma_thr,0.90*mu_thr)[0],
                           "FHR_model_10-"       : 1./40e-6*FHR_model(0.90*sigma_noise,0.90*mu_noise,0.90*sigma_thr,1.10*mu_thr)[0],
                           "FHR_model_error"     : 1./40e-6*FHR_model(sigma_noise,mu_noise,sigma_thr,mu_thr)[1],
                           "vbb"                 : row["vbb"],
                           "vcasb"               : row["vcasb"]})


data=pd.merge(data,pd.DataFrame(data_FHR_model),on=["vcasb","vbb"])
data.to_csv(outdir+"FHR_model_data.csv", index=False, header=True)

plt.figure(f"FHR vs threshold",figsize=(7.5,5))
plt.title(f"FHR vs threshold")
plt.ylabel('Noise occupancy (hits s$^{-1}$ pixel$^{-1}$)')
plt.xlabel(f'Threshold (mV)')
plt.yscale('log')
plt.errorbar(data['thr_mean'],data['fhr'],yerr=[data['fhr_low_err'],data['fhr_up_err']],capsize=3,markeredgewidth=1,label="FHR data",marker='o',markersize=3,color="#D55E00")
plt.errorbar(data['thr_mean'],data['FHR_model'],data['FHR_model_error'],label="FHR model",color="#0072B2",linewidth=0.5)
plt.fill_between(data['thr_mean'],data['FHR_model']-data['FHR_model_error'], data['FHR_model']+data['FHR_model_error'], alpha=0.5,color="#0072B2")
plt.fill_between(data['thr_mean'],data['FHR_model_10-'], data['FHR_model_10+'],label=r"$\pm$10% param.", alpha=0.2,color="#56B4E9")
plt.grid(axis='both')
plt.subplots_adjust(left=0.1,right=0.80)
add_fhr_limit(senselimit)
plot_parameters(config,1.02,1.0)
plt.legend(loc='lower left',bbox_to_anchor=(1.01, -0.01),prop={"size":9})
plt.savefig(outdir+"FHR_model_thr.png",dpi=300)

plt.figure(f"FHR vs VCASB",figsize=(7.5,5))
plt.title(f"FHR vs VCASB")
plt.ylabel('Noise occupancy (hits s$^{-1}$ pixel$^{-1}$)')
plt.xlabel(f'VCASB (mV)')
plt.yscale('log')
plt.errorbar(data['vcasb'],data['fhr'],yerr=[data['fhr_low_err'],data['fhr_up_err']],capsize=3,markeredgewidth=1,label="FHR data",marker='o',markersize=3,color="#D55E00")
plt.errorbar(data['vcasb'],data['FHR_model'],data['FHR_model_error'],label="FHR model",color="#0072B2",linewidth=0.5)
plt.fill_between(data['vcasb'],data['FHR_model']-data['FHR_model_error'], data['FHR_model']+data['FHR_model_error'], alpha=0.5,color="#0072B2")
plt.fill_between(data['vcasb'],data['FHR_model_10-'], data['FHR_model_10+'],label=r"$\pm$10% param.", alpha=0.2,color="#56B4E9")
plt.grid(axis='both')
plt.subplots_adjust(left=0.1,right=0.80)
add_fhr_limit(senselimit)
plot_parameters(config,1.02,1.0)
plt.legend(loc='lower left',bbox_to_anchor=(1.01, -0.01),prop={"size":9})
plt.savefig(outdir+"FHR_model_VCASB.png",dpi=300)

if not args.quiet: plt.show()