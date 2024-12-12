# this is a python script

#=======================================================================
#   Copyright (C) 2023 Univ. of Bham  All rights reserved.
#   
#   		FileName：		apts_pulse_waveform.py
#   	 	Author：		LongLI <long.l@cern.ch>
#   		Time：			2023.10.02
#   		Description：
#
#======================================================================

import numpy as np
import matplotlib.pyplot as plt
from sys import getsizeof as size
import matplotlib
import argparse
import os 
import sys 
import re 
import json
import leakage_utils as utils
import apts_leakage_fit 
import apts_leakage_analysis

args = argparse.Namespace() # bad fix for bad code

def leakage_fit(t, T, I_eff, t0, vbb): # in unit of V
    Temp = 273.15 + T
    const = 25*1.5*Temp/300*1e-3
    # print(args.chip, vbb)
    C = apts_leakage_fit.Capacitance(args.chip, vbb)
    U_t = -const*(np.log(np.exp(-(I_eff*(t-t0))/(C*const))+1))
    return U_t

def get_file_parameters(args):
    parameters  = []
    data_path = args.data+'/'+args.proximity+'/'+args.chip+'/data'
    print(args.proximity, args.chip)
    for path, cDir, files in os.walk(data_path):
        for file in files:
            if file.endswith('Fit_results.npz') and file.find('A')>=0 and file.find('T') >=0 and file.find('vh') >=0 and file.find('vbb') >=0 and file.find('ir') >=0:
                T = int(file.split('T')[-1].split('_')[0])
                vh = int(file.split('vh')[-1].split('_')[0])
                vbb = float(file.split('vbb')[-1].split('_')[0])/1000
                ir = int(file.split('ir')[-1].split('_')[0])/10
                chip = 'A'+file.split('A')[-1].split('_')[0]+'_W'+file.split('W')[-1].split('_')[0]
                if file.find('vr')>=0:
                    vr = int(file.split('vr')[-1].split('_')[0])
                else:
                    vr = 500
                file_path = os.path.join(path,file)
                with np.load(file_path) as data:
                    data_dict = {'vh':vh, 'vr':vr, 'vbb':vbb, 'ir':ir, 'T':T, 'chip':chip, 
                        'file_path':file_path, 'data_mean':data['data_mean'], 'rms_mean':data['rms_mean'],
                        'I_eff':data['I_eff'], 'I_eff_err':data['I_eff_err'], 't0':data['t0'],
                        't0_err':data['t0_err'], 'redchi':data['redchi'], 'start_frame':data['start_frame'],
                        'end_frame':data['end_frame']
                        }
                    parameters.append(data_dict)
        return parameters



def waveform(data, vbb, T, ir, i_eff, i_eff_err, t0, t0_err, start_frame, end_frame, redchi, chip):
    time = np.arange(len(data[1,1,:-1]))*250e-9
    # set starting point of 20us
    x_cor = 20*1e-6
    time -= x_cor
    fig_wf, ax_wf = plt.subplots(1, num = f'ir= {ir}', figsize=(12,6))
    print('waveform called')
    data2 = data.reshape((16, len(data[1][1])))

    data_mean = -np.mean(data2, axis=0)
    data_std = np.std(data2, axis=0)
    ax_wf.plot(time*1e6, data_mean[:-1], lw=1.5, color='b')
    ax_wf.fill_between(time*1e6, data_mean[:-1]+data_std[:-1], data_mean[:-1]-data_std[:-1], alpha=0.2, lw=0, color='b')
    ax_wf.grid(alpha=0.5)
    ax_wf.set(title='',
            xlabel = 'time [\u03BCs]',
            ylabel = 'Voltage [mV]',
            xlim = (0, 50)
            )
    chip, pitch, design, wafer, number, split, _ = apts_leakage_analysis.get_chip_info(chip)
    text_par = apts_leakage_analysis.text_par
    text_par['chip_ID'] = chip
    text_par['vbb'] = vbb
    text_par['T'] = T
    args.compared_params = 'waveform'
    info = utils.add_parameters(args, text_par, design, pitch, split)
    utils.add_text_to_plots(args, ax_wf, ax_wf, info, 1.05, 0.97, 'left')
    fig_wf.subplots_adjust(left=0.1, bottom=0.1, right=0.75, top=0.9)

    save_dir = args.output_dir+'/'+args.proximity+'/'+args.chip+'/Leakage_results' 
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    filename = f'average_waveform_T{T}_vbb{vbb}_ir{ir}.pdf'
    fig_wf.savefig(os.path.join(save_dir, filename))
    plt.close(fig_wf)

    fig_pix, ax_pix = plt.subplots(1, num = f'ir= {ir}', figsize=(12,6))
    for row in range(4):
        for col in range(4):
            if row == args.pixel[0] and col == args.pixel[1]:
                ax_pix.plot(time*1e6, -data[row, col,:-1], lw=1.5, color='b', label=f'pixel[{row}][{col}]')
                t_lin = np.linspace(start_frame, end_frame, 1000)
                fit_result = leakage_fit(t_lin*1e-6, float(T), float(i_eff[row, col])*1e-12, float(t0[row, col])*1e-6, float(vbb))    
                ax_pix.plot(t_lin, fit_result*1e3, ls='--', color='r', label='Leakage Fit')
                ax_pix.legend(bbox_to_anchor=(0.72, 0.4), prop={'size':12}, frameon=True)
                ax_pix.set(title=f'',
                            xlabel = 'time [\u03BCs]',
                            ylabel = 'Voltage [mV]',
                            xlim = (0, 50)
                            )
                # texting
                res_txt = f'Fit parameters:\n$I_{{effective}}$ = ({round(i_eff[row    ][col],1)} +- {round(i_eff_err[row][col],1)})pA\n$\chi^2_r$ = {round(redchi[row][col],1)}'
                plt.text(0.52, 0.4, res_txt, color='r', va='bottom', transform=ax_pix.transAxes)
    ax_pix.grid(alpha=0.5)
    utils.add_text_to_plots(args, ax_pix, ax_pix, info, 1.05, 0.97, 'left')
    fig_pix.subplots_adjust(left=0.1, bottom=0.1, right=0.75, top=0.9)
    filename = f'waveform_pix[{args.pixel[0]}][{args.pixel[1]}]_T{T}_vbb{vbb}_ir{ir}.pdf'
    fig_pix.savefig(os.path.join(save_dir, filename))
    plt.close(fig_pix)
    print(f'{filename} saved')
    

def apts_leakage_waveform(args):
    pars = get_file_parameters(args)
    for par in pars:
        data = par['data_mean'] 
        vbb = par['vbb']
        ir = par['ir']
        T = par['T'] 
        i_eff = par['I_eff']
        i_eff_err = par['I_eff_err']
        t0 = par['t0']
        t0_err = par['t0_err']
        start_frame = par['start_frame']
        end_frame = par['end_frame']
        redchi = par['redchi']
        chip = par['chip']
        if vbb == args.vbb and ir == args.ireset:
            waveform(data, vbb, T, ir, i_eff, i_eff_err, t0, t0_err, start_frame, end_frame, redchi, chip)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="APTS pulse wavform plotting")
    parser.add_argument('--data', '-d', type=str, default='../../Data', help="Directory for data file")
    parser.add_argument('--output_dir', '-o', default=None, help="Directory to save the results")
    parser.add_argument('--proximity', '-prox', help='Proximity board for chip tested')
    parser.add_argument('--chip', '-c', help='Choose the chip to show the waveform')
    parser.add_argument('--ireset', '-ir', type=float, default=100.0, help='Set ireset for waveform plotting')
    parser.add_argument('--vbb', '-v', type=float, default=4.8, help='Set vbb for waveform plotting')
    parser.add_argument('--pixel', '-p', type=int, nargs=2, default = [0, 0], help='Choose the pixel to show the pulse[0,0] to [3, 3]')
    args = parser.parse_args()
    if args.output_dir == None:
        args.output_dir = args.data
    apts_leakage_waveform(args)
