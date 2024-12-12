# this is a python script

#=======================================================================
#   Copyright (C) 2023 Univ. of Bham  All rights reserved.
#   
#   		FileName：		apts_leakage_analysis.py
#   	 	Author：		LongLI <long.l@cern.ch>
#   		Time：			2023.04.09
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
from scipy.optimize import curve_fit
from lmfit import Model
import json
import leakage_utils as utils
import apts_leakage_fit

args = argparse.Namespace() # bad fix for bad code

text_par = {
    'id': 'APTS~SF',
    'vreset':500,
    'ibias3': 200,
    'ibias4': 150,
    'ibiasn':20,
    'ibiasp':2,
    'vh':1200
}




def linear_fit(x, b, m):
    y = b + m*x
    return y


def get_file_parameters(args):
    parameters  = []
    data_path = args.data + '/' + args.proximity + '/' + args.chip + '/data/'
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

def get_chip_info(chip_ID):
    extract_name = re.match(r'AF([12]?[05]?)([BP])?_(W\d{2})(B\d{1})', chip_ID)
    pitch = extract_name.group(1)
    design = extract_name.group(2)
    typ = design
    if design == None:
        design = 'standard'
    elif design == 'B':
        design = 'modified'
    elif design == 'P':
        design = 'modified with gap'

    wafer = extract_name.group(3)
    number = extract_name.group(4)
    split, chip = utils.get_split(wafer, chip_ID)

    return chip, pitch, design, wafer, number, split, typ


def leakage_determination(parameters, tr, vbbr, irr, args):
    
    # for recording of positive offset in linear fit 
    fpoi = open('positive_offset_info.txt', 'a')
    
    pixels = 16
    npar = 4
    #fit_dict = np.zeros((len(tr), len(vbbr), pixels, npar))    
    fit_dict = np.empty((len(tr), len(vbbr), pixels, npar))
    fit_dict[:] = np.nan
    chip_ID = None 
   # stop here Long LI 2023-10-10 
    for (j,T) in enumerate(tr):
        par_T = []
        for par in parameters:
            if par['T'] != T: continue
            par_T.append(par)
        for (k,vbb) in enumerate(vbbr):
            par_vbb = []
            ir = []
            i_eff = []
            i_eff_err = []
            for par in par_T:
                if par['vbb'] != vbb:
                    continue
                par_vbb.append(par)
            # sorted by ir
            par_sorted = sorted(par_vbb, key= lambda x:x['ir'])
            for par in par_sorted: 
                ir.append(par['ir'])
                i_eff.append(par['I_eff'])
                i_eff_err.append(par['I_eff_err'])
                chip_ID = par['chip']
            # start plotting and fitting
            fig, ax = plt.subplots(1, num=f'vbb={vbb}', figsize=(12,6))
            for row in range(4):
                for col in range(4):
                    label = f'pixel[{row}][{col}]'

                    ir_np = np.array(ir)
                    i_eff_np = np.array(i_eff)[:,row,col]
                    i_eff_err_np = np.array(i_eff_err)[:,row,col]
                  
                    # for bad pulsing shape fitting points    -- Long LI 2023-12-04 
                    nan = None 
                    nan = np.isnan(i_eff_np)
                
                    if True in nan:
                    #    print('Waveform fit failed, problematic pixel listed as below:')
                        idxs = []
                        for (i, item) in enumerate(nan):
                            if item == True:
                                ir_v = ir[i]
                                idxs.append(i)
                     #           print('(vbb, ir, row, col)', vbb, ir_v, row, col)
                                
                        # delete bad fitting poionts
                        ir_np = np.delete(ir_np, idxs)
                        i_eff_np = np.delete(i_eff_np, idxs)
                        i_eff_err_np = np.delete(i_eff_err_np, idxs)
                        
                        det_nan = np.isnan(i_eff_np)
                        if True in det_nan:
                            print(i_eff_np) 
                    if len(i_eff_np) <= args.data_points: continue # enough points for linear fit
                    idx = 0 
                    # find the index to thr ireset cut
                    for i in list(ir_np):
                        if i >= args.ir_cut:
                            idx = list(ir_np).index(i)
                            break

                    ax.errorbar(ir_np[idx:], i_eff_np[idx:], i_eff_err_np[idx:], ls='', marker='s', label=label)
                    a_fit, cov = curve_fit(linear_fit, xdata=ir_np[idx:], ydata=i_eff_np[idx:], sigma=i_eff_err_np[idx:], absolute_sigma=True)
                    b = a_fit[0]
                    m = a_fit[1]
                    db = np.sqrt(cov[0][0])
                    dm = np.sqrt(cov[1][1])
                    
                    if m == 1.0 and b == 1.0: # problematic linear fit -> through NaN
                        continue
                    #record the fit results
                    pix = row*4+col
                    fit_dict[j,k,pix,0] = b   
                    fit_dict[j,k,pix,1] = m  
                    fit_dict[j,k,pix,2] = db   
                    fit_dict[j,k,pix,3] = dm   
                                        
                    
                    # record the positive offset
                    if b >=0:
                        fpoi.write(f'{chip_ID}, {vbb}V: {row}, {col}, {b}\n')

                    # plotting the fit results
                    x_fit1 = np.linspace(args.ir_cut, ir[-1], 500)
                    plt.plot(x_fit1, m*x_fit1+b, c='k')
                    x_fit2 = np.linspace(0, args.ir_cut, 100)
                    plt.plot(x_fit2, m*x_fit2+b, c='lightgrey', ls='--')

            ax.grid(alpha=0.5)
            ax.set(title='',
                    xlabel = 'Reset Current [pA]',
                    ylabel = 'Effective Current [pA]'
                    )
            old_cpar = args.compared_params
            args.compared_params = 'pixel'
            text_par['vbb'] = vbb
            text_par['T'] = T
            text_par['chip_ID'] = chip_ID
           
            chip, pitch, design, wafer, number, split, typ = get_chip_info(chip_ID) 
            
            info = utils.add_parameters(args, text_par, design, pitch, split)
            ax.legend(ncols=2, bbox_to_anchor=(1.385, 0.5), prop={'size':11}, frameon=True)
            utils.add_text_to_plots(args, ax, ax, info, 1.05, 0.97, 'left')
            fig.subplots_adjust(left=0.1, bottom=0.1, right=0.75, top=0.9)
            

            save_dir = args.output_dir+'/'+args.proximity+'/'+args.chip+'/Leakage_results'
            if not os.path.exists(save_dir):
                os.makedirs(save_dir) 
            fig_name = f'I_eff_vs_I_reset_linear_fit_vbb_{vbb}_T{T}_IRESET_CUT{args.ir_cut}.pdf'
            fig.savefig(os.path.join(save_dir, fig_name))
            plt.close(fig)
    
            args.compared_params = old_cpar


    return fit_dict
   
def comparison_plots(results, sub_compared_all, sub_compared_par, dict_x, sub_compared_name):
    fig_leakage, ax_leakage = plt.subplots(1, num='voltage comarison', figsize=(12,6))
    
    old_compared_params = args.compared_params
    # leakage vs. vbb
    for c_all in sub_compared_all:
        for key in results.keys():
            fig_single, ax_single = plt.subplots(1, num = f'leakage of {key}', figsize=(12, 6))
            for c in sub_compared_par[key]:
                idx = sub_compared_par[key].index(c)
                x = dict_x[key]

                # calculate the mean/std ignoring NaN
                I = np.nanmean(results[key], axis = 2)
                I_err = np.nanstd(results[key], axis=2)

                if sub_compared_name == 'Temperature':
                    I = -I[idx,:,0]   # negative offset, now reverse it to be leakage
                    I_err = I_err[idx,:,0]
                    label = f'T: {c} \u2103'
                elif sub_compared_name == 'Vbb':
                    I = -I[:,idx,0]
                    I_err = I_err[:,idx,0]
                    label = f'Vbb: {c} V'
            
                chip_ID = key.split(',')[-1]
                proximity = key.split(',')[0] 
                text_par['chip_ID'] = chip_ID
                text_par['proximity'] = proximity

                # the I/I_err values  were 0, if the waveform fit failed
                # now exclude these data points    --Long LI 2023-12-07
                list_I = []
                list_I_err = []
                list_x = []
                for (i, item) in enumerate(I):
                    if not(I[i] == 0 and I_err[i] == 0):
                        
                        # set range for the comparison plots
                        # vbb range
                        if sub_compared_name == 'Temperature' and x[i] in args.vbb_range:
                            list_x.append(x[i])
                            list_I.append(I[i])
                            list_I_err.append(I_err[i])
                        elif sub_compared_name == 'Vbb' and x[i] in args.temperature_range:
                            list_x.append(x[i])
                            list_I.append(I[i])
                            list_I_err.append(I_err[i])
                        
                            


                x = np.array(list_x)
                I = np.array(list_I)
                I_err = np.array(list_I_err)
                

                if len(x) == 0:
                    print('No data points in vbb range:', args.vbb_range, ' and temperature range:', args.temperature_range)
                    print('Please adjust the Vbb & temperature range')
                    exit(-1)

                ax_single.errorbar(x, I, I_err, ls='', marker = 's', label=label)
                chip, pitch, design, wafer, number, split, typ = get_chip_info(chip_ID) 

                # legend for leakage comparison
                args.compared_params = old_compared_params 
                if args.compared_params == 'proximity':
                    label = proximity
                elif args.compared_params == 'chip':
                    label = chip_ID
                elif args.compared_params == 'split':
                    label = f'split {split}'
                elif args.compared_params == 'pitch':
                    label = f'pitch {pitch}\u03BCm'
                elif args.compared_params == 'flavour':
                    label = design
                else:
                    label = chip_ID

                if c == c_all:
                    color = utils.color_setting(args, split, pitch, typ)
                    ax_leakage.errorbar(x, I, I_err, ls='', color = color, marker='s', label=label)

            ax_single.grid(alpha=0.5)
            ax_single.set(
                    title='',
                    ylabel = 'Leakage Current [pA]',
                    ylim = (args.y_range[0], args.y_range[1])
                )
            if sub_compared_name == 'Temperature':
                ax_single.set(xlabel = '-Vbb [V]')
                args.compared_params = 'temp'
            
            elif sub_compared_name == 'Vbb':
                ax_single.set(xlabel = 'T [\u2103]')
                args.compared_params = 'vbb'    
        
            info = utils.add_parameters(args, text_par, design, pitch, split)
            ax_single.legend(bbox_to_anchor=(1.25, 0.35), prop={'size':12}, frameon=True)
            utils.add_text_to_plots(args, ax_single, ax_single, info, 1.05, 0.97, 'left')
            fig_single.subplots_adjust(left=0.1, bottom=0.1, right=0.75, top=0.9)
            
            # save fig
            save_dir = args.output_dir+'/'+ proximity+'/'+chip_ID+'/'+'Leakage_results'
            if sub_compared_name == 'Temperature':
                file_name = f'leakage_over_vbb_IRESET_CUT{args.ir_cut}pA.pdf'
            elif sub_compared_name == 'Vbb':
                file_name = f'leakage_over_T_IRESET_CUT{args.ir_cut}pA.pdf'
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
       
            fig_single.savefig(os.path.join(save_dir, file_name)) 
            plt.close(fig_single)



        args.compared_params = old_compared_params
        ax_leakage.grid(alpha=0.5)
        ax_leakage.set(
                title='',
                ylabel = 'Leakage current [pA]',
                ylim = (args.y_range[0], args.y_range[1])
            )
        if sub_compared_name == 'Temperature':
            ax_leakage.set( xlabel = '-Vbb [V]')
        elif sub_compared_name == 'Vbb':
            ax_leakage.set(xlabel = 'T [\u2103]')
        text_par['sub_compared'] = c_all
        args.sub_compared = sub_compared_name
        info = utils.add_parameters(args, text_par, design, pitch, split)
        ax_leakage.legend(bbox_to_anchor=(1.3, 0.35), prop={'size':12}, frameon=True)
        utils.add_text_to_plots(args, ax_leakage, ax_leakage, info, 1.05, 0.97, 'left')
        fig_leakage.subplots_adjust(left=0.1, bottom=0.1, right=0.75, top=0.9)
        
        # save fig
        save_dir = args.output_dir+'/leakage_comparison'
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        file_name = f'leakage_comparison.pdf'
        if sub_compared_name == 'Temperature':
            if args.compared_params == 'chip':
                file_name = f'chip_comparison_over_vbb_T{c_all}_IRESET_CUT{args.ir_cut}.pdf'
            elif args.compared_params == 'split':
                file_name = f'split_comparison_over_vbb_pitch{pitch}_{typ}_T{c_all}_IRESET_CUT{args.ir_cut}.pdf'
            elif args.compared_params == 'pitch':
                file_name = f'pitch_comparison_over_vbb_split{split}_{typ}_T{c_all}_IRESET_CUT{args.ir_cut}.pdf'
            elif args.compared_params == 'proximity':
                file_name = f'proximity_comparison_over_vbb_IRESET_CUT{args.ir_cut}.pdf'
            elif args.compared_params == 'flavour':
                file_name = f'flavour_comparison_over_vbb_split{split}_pitch{pitch}_T{c_all}_IRESET_CUT{args.ir_cut}.pdf'
        
        elif sub_compared_name == 'Vbb':
            if args.compared_params == 'chip':
                file_name = f'chip_comparison_over_T_vbb{c_all}_IRESET_CUT{args.ir_cut}.pdf'
            elif args.compared_params == 'split':
                file_name = f'split_comparison_over_T_pitch{pitch}_{typ}_vbb{c_all}_IRESET_CUT{args.ir_cut}.pdf'
            elif args.compared_params == 'pitch':
                file_name = f'pitch_comparison_over_T_split{split}_{typ}_vbb{c_all}_IRESET_CUT{args.ir_cut}.pdf'
            elif args.compared_params == 'proximity':
                file_name = f'proximity_comparison_over_T_IRESET_CUT{args.ir_cut}.pdf'
            elif args.compared_params == 'flavour':
                file_name = f'flavour_comparison_over_T_split{split}_pitch{pitch}_vbb{c_all}_IRESET_CUT{args.ir_cut}.pdf'

        fig_leakage.savefig(os.path.join(save_dir, file_name)) 
        ax_leakage.clear()
        plt.close(fig_leakage)


        
def apts_leakage_analysis(args):
    
    results = {}
    vbbrs = {}
    trs = {}

    # for vbbr and tr check 
    vbbr_ints = set()
    tr_ints = set()
    for chip in args.compared_chip:
        proximities = set()
        for path, cDir, files in os.walk(args.data):
            if path.endswith('data'):
                chip_target = path.split('/')[-2]
                if chip_target != chip:
                    continue
                proximity = path.split('/')[-3]
                if proximity.startswith('APTS'):
                    proximities.add(proximity)
        proximities = sorted(proximities)
        for proxi in proximities:
            args.proximity = proxi
            args.chip = chip
            parameters = get_file_parameters(args)
            print(proxi, chip)
            vbbr = set()
            tr = set()
            irr = set()
            for pars in parameters:
                vbbr.add(float(pars['vbb']))
                tr.add(float(pars['T']))
                irr.add(float(pars['ir']))

            vbbr = sorted(vbbr)
            tr = sorted(tr)
            irr = sorted(irr)
            
            # select vbb & T that works for all chips/proximities
            if len(vbbr_ints) == 0 and len(tr_ints) == 0:
                vbbr_ints = vbbr
                tr_ints = tr

            else:
                vbbr_ints = set(vbbr_ints)
                tr_ints = set(tr_ints)
                vbbr_ints = vbbr_ints.intersection(vbbr)
                tr_ints = tr_ints.intersection(tr)
            fit_dict = leakage_determination(parameters, tr, vbbr, irr, args)
           
            key = proxi+','+chip 
            results[key] = fit_dict
            vbbrs[key] = vbbr
            trs[key] = tr
        
    # leakage vs. vbb
    #for vbb in vbbr_ints:
     #   C = apts_leakage_fit.Capacitance(args.chip, vbb)

    comparison_plots(results, tr_ints, trs, vbbrs, 'Temperature')
    # leakage vs. T
    comparison_plots(results, vbbr_ints, vbbrs, trs, 'Vbb')
                

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="I_eff vs Ireset measurement result comparison")
    parser.add_argument('--data', '-d', type=str, default='../../Data/', help="Directory for data file")
    parser.add_argument('--output_dir', '-o', default=None, help="Directory to save the results")
    parser.add_argument('--ir_cut', '-ic', type=float, default=20.0, help='Set i_reset cut for leakage determination')
    parser.add_argument('--compared_chip', '-cc', type=str, nargs='+', help='Choose chip to do leakage comparison')
    parser.add_argument('--compared_params', '-cpar', type=str, default='split', choices=['split', 'flavour', 'pitch', 'chip', 'proximity'])
    parser.add_argument('--y_range', '-yr', type=float, nargs = 2, default=[-10, 20], help= 'Set the range in y axis')
    parser.add_argument('--temperature_range', '-tr', type=float, nargs = '+', default=[15.0, 20.0, 25.0, 30.0, 35.0, 40.0], help= 'Set the temperature range in comparison plots')
    parser.add_argument('--vbb_range', '-vbbr', type=float, nargs = '+', default=[0.0, 1.2, 2.4, 3.6, 4.8], help= 'Set the Vbb range in comparison plots')
    parser.add_argument('--data_points', '-dp', type=int, default=3, help= 'Data points at least in the linear fit stage.')
    args = parser.parse_args()
  
    if args.output_dir == None:
        args.output_dir = args.data 
    apts_leakage_analysis(args)

