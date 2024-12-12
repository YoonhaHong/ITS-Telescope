#!/usr/bin/env python3

from cmath import exp
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import argparse
import os
from pathlib import Path
import datetime
import sys
import re
import json
from lmfit import Model
from scipy.special import erf
from tqdm import tqdm
import constants
# capacitance dictionary for various vbb for all measured chips     --Long LI 2023-06-25

args = argparse.Namespace() # bad fix for bad code

def get_file_parameters(args):
    Fit_values = ["data_mean", "rms_mean", "I_eff", "I_eff_err", "t0", "t0_err", "redchi", "start_frame", "end_frame"]
    data_path = args.data+f'/{args.proximity}/{args.chip}'
    for path, currentDirectory, files in os.walk(data_path): #scan through specified directory and
        for file in files:
            if file.endswith("calibrated.npy") and file.find("B")>=0 and file.find("T")>=0 and file.find("vh")>=0 and file.find("vbb")>=0 and file.find("ir")>=0:
                print(file)
                #extract parammeters from filename
                args.Temp = int(file.split("T")[1].split("_")[0])
                # vh = int(file.split("vh")[1].split("_")[0])
                args.vbb = float(file.split("vbb")[1].split("_")[0])/1000
                args.ir = int(file.split("ir")[1].split("_")[0])/10
                args.chip = "A"+file.split("A")[1].split("_")[0]+"_W"+file.split("W")[1].split("_")[0]
                vh = file.split('vh')[-1].split('_')[0] 
                vr = file.split('vr')[-1].split('_')[0]
                # only fit the data with vh = 1200mV
                if not vh == '1200' or not vr == '500': continue          

                # find the corresponding capa info    --Long LI 2023-06-25
                Capac = Capacitance(args.chip, args.vbb) 
                if Capac == None:
                    print(f'Capacitance value not found for {args.chip} at -Vbb {args.vbb}')
                    continue
              
                args.Capac = Capac

                print(f"T: {args.Temp}, ir: {args.ir}, vbb: {args.vbb}")

                file_path = os.path.join(path, file)
                full_data = np.load(file_path)
                data_centered_mean, rms_mean, I_eff, I_eff_err, t0, t0_err, redchi, start_frame, end_frame = data_compression(args,full_data,file_path)
                # save dictionary to .npz file
                Fit_arrays = [data_centered_mean, rms_mean, I_eff, I_eff_err, t0, t0_err, redchi, start_frame, end_frame]
                Fit_dictionary = dict(zip(Fit_values, Fit_arrays))
                print(f"I_eff = {np.mean(I_eff)}, redchi = {np.mean(redchi)}")
                np.savez(file_path.replace('calibrated.npy','Fit_results'), **Fit_dictionary)
    
    #TODO:delete calib file ans save only fit result data?
    
def leakage_fit(t, I_eff, t0):
    Temp=273.15 + float(args.Temp) #kelvin 273.15
    const=25*1.5*Temp/300*1e-3 #V, n k_b T /q
    C = args.Capac #sensor capacitance. 
    U_t = - const*(np.log(np.exp(-((I_eff)*(t-t0))/(C*const))+1))
    return U_t

def plot_parameters(CHIP=False, VBB=-1,irrad=False,TEMP=False,IRESET=False, x=1.01, y=1):
    info = [
            f'$\\bf{{ITS3\;Work\; In\; Progress}}$',
            f'$\\bf{{APTS-SF}}$'
            ]
    if CHIP:
        info.append(f'chip: {CHIP}')
    info.append('version: modified with gap')
    info.append('split: 4')
    if VBB !=-1:
        if VBB ==0 or VBB==0.0:
            info.append(f'$V_{{sub}}=V_{{pwell}}= 0\,\\mathrm{{V}}$')
        else:
            info.append(f'$V_{{sub}}=V_{{pwell}}= -{VBB}\,\\mathrm{{V}}$')
    if IRESET:
        info.append(f'$I_{{reset}}={IRESET}\,\\mathrm{{pA}}$')
    
    info.append(f'$I_{{biasn}}=5\,\\mathrm{{µA}}$')
    info.append(f'$I_{{biasp}}=0.5\,\\mathrm{{µA}}$')
    info.append(f'$I_{{bias3}}=200\,\\mathrm{{µA}}$')
    info.append(f'$I_{{bias4}}=150\,\\mathrm{{µA}}$')
    info.append(f'$V_{{reset}}=500\,\\mathrm{{mV}}$')
    if irrad:
        info.append(f"Irradiation: {irrad}")
    if TEMP:
        info.append(f'Temperature={TEMP}°C')
    plt.text(x,y,
        '\n'.join([i for i in info if "None" not in i]),
        fontsize=10,
        ha='left', va='top',
        transform=plt.gca().transAxes
    )
    # add_text_to_plots(ax_cluster,ax_cluster,info,1.05,0.97, 'left')
def add_text_to_plots(fig,ax,info,x, y, position):
        fig.text(x,y,
        '\n'.join([
        '$\\bf{ALICE\;ITS3}$ $\\it{WIP}$'
        ]),
        fontsize=12,
        ha= position, va='top',
        transform=ax.transAxes
        )

        fig.text(x,y-0.05,
        '\n'.join([
        'Fe55 source measurements',
        ]),
        fontsize=9,
        ha= position, va='top',
        transform=ax.transAxes
        )

        fig.text(x,y-0.1,
        '\n'.join([
        datetime.datetime.now().strftime("Plotted on %d %b %Y"),
        ]),
        fontsize=8,
        ha= position, va='top',
        transform=ax.transAxes
        )
   
        fig.text(
            x,y-0.17,
            '\n'.join(info),
            fontsize=10,
            ha= position, va='top',
            transform=ax.transAxes
        )

def Capacitance(chip, vbb):#Capacitance from Fe55 measurements
    C = None
    file_name = '../../analysis/apts/library_seed_1640.json'
    try:
        file_json = open(file_name, 'r')
    except:
        print('library_seed_1640.json file not found!')
        exit(-1)
    data_json = json.load(file_json)
    data_all = data_json['library_seed_1640']
    for data in data_all:
        if chip == data['chip_ID'] and vbb == data['vbb']:
            seed_1640 = data['seed_1640']
            C = constants.EL_5_9_KEV*constants.Q_E*pow(10,3)/seed_1640

    return C
    


def data_compression(args,data,path):
    #needed once (assuming whole data set was taken with same specifications for nfb, nfa and ntrg)
    #if args.expansion ==0:
    # extracting eventnumber and framenumber
    n_events,n_frame = data.shape[0], data.shape[3]
    #JSON file of first data set
    with open(path.replace('_calibrated.npy','.json'), 'r') as file_json:
        data_json = json.load(file_json)
    # args.chip_ID = data_json['chip_ID']
    args.nfb = data_json['n_frames_before']        
    #needed data operations
    args.n_frame_baseline = args.nfb - 10
    args.time = np.arange(len(data[1,1,1,:-1]))*250e-9  #get physical args.time

    #args.expansion =1

    args.time = np.arange(len(data[1,1,1,:-1]))*250e-9  #get physical args.time
    rms = np.std(data[:,:,:,:args.n_frame_baseline], axis = 3)
    rms_mean = np.mean(rms, axis = 0)
    args.rms_mean= rms_mean
    args.n_frame_baseline = args.nfb - 10
    # baseline = np.mean(data[:,:,:,:args.n_frame_baseline],axis = 3)
    baseline = np.mean(data[:,:,:,args.n_frame_baseline-4:args.n_frame_baseline-3],axis = 3)
    data_centered = baseline[:,:,:,np.newaxis] - data # [the pulse,row,col,mean_data for frame n]
    # print(np.std(data_centered, axis=0)[1,3,:]/np.sqrt(999))

    data_centered_mean = np.mean(data_centered, axis=0)
    # print(data_centered[1,3,:])
    I_eff = np.zeros((4,4))
    I_eff_err = np.zeros((4,4))
    t0 = np.zeros((4,4))
    t0_err = np.zeros((4,4))
    redchi = np.zeros((4,4))

    for row in range(4):
        for column in range(4):
            I_eff[row,column], I_eff_err[row,column], t0[row,column], t0_err[row,column], redchi[row,column], start_frame, end_frame = simple_fit(args, data_centered_mean[row,column], rms_mean[row,column], 103, 150)
    return data_centered_mean, rms_mean, I_eff, I_eff_err, t0, t0_err, redchi, start_frame, end_frame

def simple_fit(args, U, rms, start_frame_fit, end_frame_fit):
    U = U*1e-3 #mV to V
    #X-Axis boundaries
    x_min = 0
    x_max = 20
    #x-axis correction to t=0
    x_corr = 20 - x_min
    time = args.time - x_corr*1e-6
    # FIt initial conditions
    I_eff_initial = 1e-10 #100pA
    t0_init = 32*1e-6 - x_corr*1e-6

    if len(U)<=1:
        return np.nan, np.nan, np.nan, np.nan, 0, round(time[start_frame_fit]*1e6,2),round(time[end_frame_fit]*1e6,2)
    elif np.max(-U)>4: #ensure good data, no signal greater zero expected
        return np.nan, np.nan, np.nan, np.nan, 0, round(time[start_frame_fit]*1e6,2),round(time[end_frame_fit]*1e6,2)

    # # # ---------------FITTING--------------------------------
    pmodel = Model(leakage_fit, independent_vars=["t"])
    pmodel.set_param_hint('I_eff', value=I_eff_initial, min=I_eff_initial*1e-5, max= I_eff_initial*1e3)
    pmodel.set_param_hint('t0', value=t0_init, min=t0_init*0.02, max= t0_init*50)
    params = pmodel.make_params()
    result = pmodel.fit(-U[start_frame_fit:end_frame_fit], params, t=time[start_frame_fit:end_frame_fit],weights = 2000/rms, nan_policy="propagate") #weight is used multiplicative: error =  weight*(data-fit) -->> weight = 1/error
    # print(result.redchi)
    if result.params['I_eff'].stderr is not None or result.params['t0'].stderr is not None:
        if result.params['I_eff'].stderr*1e12>=10: #or result.redchi <=0.01 or result.redchi >=2.5 : #cut too big errors or too small redchi
            return np.nan, np.nan, np.nan, np.nan, result.redchi, round(time[start_frame_fit]*1e6,2),round(time[end_frame_fit]*1e6,2)
    else:
        return np.nan, np.nan, np.nan, np.nan, result.redchi, round(time[start_frame_fit]*1e6,2),round(time[end_frame_fit]*1e6,2)
    return result.params['I_eff'].value*1e12,  result.params['I_eff'].stderr*1e12, result.params['t0'].value*1e6, result.params['t0'].stderr*1e6, result.redchi, round(time[start_frame_fit]*1e6,2),round(time[end_frame_fit]*1e6,2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APTS signal extraction from calibrated file")
    parser.add_argument('--data', '-d', default = "../../Data",help='Directory for input files. (where to look for recursively) recommended structure: ..../apts-dpts-ce65-daq-software/Data/AF15P_W22B2/data/')
    parser.add_argument('--proximity', '-prox', type=str,help='Proximity board in the measurement. i.e APTS-013')
    parser.add_argument('--chip', '-c', type=str,help='Chip to be measured. i.e AF15P_W22B3')
    
    args = parser.parse_args()
    args.expansion = 0  #if 0, Inititializes things like nfb, ntrg,result_path and time
    get_file_parameters(args)
