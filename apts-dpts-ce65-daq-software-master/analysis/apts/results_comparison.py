#!/usr/bin/env python3

import numpy as np
import json
import matplotlib
import matplotlib.pyplot as plt
import time
import argparse
import os
import os.path
import collections
import re
import datetime
import constants
import utils

def results_comparison(args):
    list_json = {}
    list_name_chip = list()
    list_name_mux = list()
    for i,file in enumerate(args.file_input_json):
        #JSON file
        with open(file, 'r') as file_json:
            data_json = json.load(file_json)
        list_json[i] = data_json
        p = {k: '?' for k in ['wafer','chip','version','split',
                          'pwell','sub','vcasn','vcasb', 'idb',
                          'ireset', 'ibias', 'ibiasn', 'mux']}
        p['id'] = 'APTS~SF'
        p.update(data_json)
        chip_ID = data_json['chip_ID']
        extract_name_volt = re.match(r"[E]?[R]?[1]?A[AF]([12]?[05]?)([BP])?([M])?_(W\d{2})(B\d{1})", chip_ID)
        pitch =  extract_name_volt.group(1)
        design =  extract_name_volt.group(2)
        isMux = True if extract_name_volt.group(3)=="M" else False
        if design == None:
            design = 'standard'
        if design == 'B':
            design = 'modified'
        if design == 'P':
            design = 'modified with gap'
        if design == 'P' and isMux == True:
            design = "Multiplexer"
        wafer =  extract_name_volt.group(4)
        number =  extract_name_volt.group(5)
        split,chip_ID = utils.get_split(wafer, chip_ID)

        if args.compared_params == "mux":
            list_name_chip.append(data_json['chip_ID'])
            mux = -1
            if 'mux' in data_json:
                mux = data_json['mux']
            label = utils.get_mux_label(mux, isMux)
            list_name_mux.append(label)
        else:
            list_name_chip = set([ sub['chip_ID'] for sub in list_json.values() ])

    photon_energy = np.array([0., 5.9, 6.4]) #keV

    y_box = args.y_max*5
    seed_limit = args.seed_max
    rms_limit = 4
    if args.unit == 'adc':
        seed_label = 'ADC'
        rms_limit = 50
    else:
        seed_label = 'mV'

    if args.rms_p2p:
        fig_all, ax_comp_all_chip = plt.subplots(3,3, sharex=False,num='Comparison',figsize=(20,10))
        fig_all.delaxes(ax_comp_all_chip[2,1])
        fig_all.delaxes(ax_comp_all_chip[2,2])
    if not args.rms_p2p:
        fig_all, ax_comp_all_chip = plt.subplots(2,3, sharex=False,num='Comparison',figsize=(20,8))
    color_index = 0
    index = 0

    with open('library_seed_1640.json', 'r') as file_lib:
        library_seed_1640 = json.load(file_lib)
    for single_name in list_name_chip:
        single_chip_list = {key: value for key, value in list_json.items() if value.get('chip_ID') == single_name}
        single_chip_list = collections.OrderedDict(sorted(single_chip_list.items(), key=lambda t:t[1]["vbb"]))
        if args.compared_params == 'mux': single_name = list_name_mux[index]
        fig, ax_comp_same_chip = plt.subplots(2,2,num = single_name,figsize=(10,5))
        bias_voltages = [float(sub['vbb']) for sub in single_chip_list.values()]
        if not args.pulse:
            ax_comp_same_chip[0,0].plot(bias_voltages, [ sub['seed_1640'] for sub in single_chip_list.values() ],"ob-.")
            ax_comp_same_chip[0,0].set(xlabel='$V_{BB}$ (V)',
                ylabel = f'Seed signal ({seed_label})',
                title = 'Seed VS $V_{BB}$ '+single_name)
            ax_comp_same_chip[0,0].axis([0,5, 0, seed_limit])#xmin xmax ymin ymax
        else:
            ax_comp_same_chip[0,0].plot(bias_voltages, [ sub['seed_mean'] for sub in single_chip_list.values() ],"ob-.")
            ax_comp_same_chip[0,0].set(xlabel='$V_{BB}$ (V)',
                ylabel = f'Seed mean ({seed_label})',
                title = 'Seed VS $V_{BB}$ '+single_name)
            ax_comp_same_chip[0,0].axis([0,5, 0, seed_limit])#xmin xmax ymin ymax
        
        for single_run in single_chip_list.values():
            if not args.pulse:
                try:
                    m,b = np.polyfit(photon_energy, [0,single_run.get('seed_1640'),single_run.get('seed_1800')], 1)
                except TypeError:
                    print('No value found for peak at 1800 electrons for '+ single_name + '_' + str(bias_voltages)+' , used only 1640 for the fit')
                    m,b = np.polyfit([photon_energy[0],photon_energy[1]], [0,single_run.get('seed_1640')], 1)
                
                color = next(ax_comp_same_chip[1,1]._get_lines.prop_cycler)['color']
                ax_comp_same_chip[1,1].plot(photon_energy, [0,single_run.get('seed_1640'),single_run.get('seed_1800')],"o",color=color)
                ax_comp_same_chip[1,1].plot(photon_energy, m*photon_energy+b, '--',color=color, label = str(single_run.get('vbb'))+'V')
        if not (args.pulse_seed_1640 or args.pulse):
            print(args.pulse_seed_1640)

            ax_comp_same_chip[1,1].set(xlabel='Photon energy (keV)',
                ylabel = f'Amplitude peaks ({seed_label})',
                title = 'Calibration '+single_name)
            ax_comp_same_chip[1,1].axis([0, 7, 0, seed_limit])#xmin xmax ymin ymax
            plt.legend()
        
            ax_comp_same_chip[1,0].plot(bias_voltages, [ sub['C'] for sub in single_chip_list.values() ],"ob-.")

            ax_comp_same_chip[1,0].set(xlabel='$V_{BB}$ (V)',
                ylabel = 'Capacitance (fF)',
                title = 'Capacitance VS $V_{BB}$ '+single_name)
            ax_comp_same_chip[1,0].axis([0, 5, 0, 7*10**(-15)])#xmin xmax ymin ymax
            
            ax_comp_same_chip[0,1].plot(bias_voltages, [ sub['CCE'] for sub in single_chip_list.values() ],"ob-.")

            ax_comp_same_chip[0,1].set(xlabel='$V_{BB}$ (V)',
                ylabel = 'CCE (%)',
                title = 'CCE VS $V_{BB}$ '+single_name)
            ax_comp_same_chip[0,1].axis([0, 5, 85, 105])#xmin xmax ymin ymax
        elif args.pulse_seed_1640:
            single_seed_1640 = [entry for entry in library_seed_1640["library_seed_1640"] if entry["chip_ID"] == single_name]
            single_seed_1640 = [value for value in single_seed_1640 if value["vbb"] in bias_voltages]
            single_seed_1640 = sorted(single_seed_1640, key=lambda x: x["vbb"])
            seed_1640 = [entry["seed_1640"] for entry in single_seed_1640]

            v_h = [ sub['vh'] for sub in single_chip_list.values() ]
            seed_mean = [ sub['seed_mean'] for sub in single_chip_list.values() ]
            seed_mean_array = np.array(seed_mean)
            v_h_array = np.array(v_h)
            seed_1640_array =  np.array(seed_1640)

            c_pulse = 1.e18*seed_mean_array * constants.EL_5_9_KEV * constants.Q_E/(v_h_array*seed_1640_array*1e-3)
            ax_comp_same_chip[1,0].plot(bias_voltages, c_pulse,"ob-.")
            ax_comp_same_chip[1,0].set(xlabel='$V_{BB}$ (V)',
                ylabel = 'Pulsing capacitance (aF)',
                title = 'Pulsing capacitance VS $V_{BB}$ '+single_name)
            #ax_comp_same_chip[1,0].axis([0, 5, 0, 7*10**(-15)])#xmin xmax ymin ymax
        
        fig.tight_layout()
        fig.savefig(os.path.join(args.output_dir,single_name + '.pdf'))

        if single_name == args.reference_dut:
            color = 'k'
        else:
            color = 'C'+str(color_index)
            color_index += 1
        chip_ID = single_run.get('chip_ID')
        
        #Compare all DUTs
        if not args.pulse:
            ax_comp_all_chip[0,0].plot(bias_voltages, [ sub['seed_1640'] for sub in single_chip_list.values() ],"o-.",color=color)
            ax_comp_all_chip[0,1].plot(bias_voltages, [ sub['C']*10**(15) for sub in single_chip_list.values() ],"o-.", color=color)
            ax_comp_all_chip[1,0].plot(bias_voltages, [ sub['CCE'] for sub in single_chip_list.values() ],"o-.", color=color)
            ax_comp_all_chip[1,1].plot(bias_voltages, [ sub['Mean_cluster_size'] for sub in single_chip_list.values() ],"o-.", color=color)
        else:
            ax_comp_all_chip[0,0].plot(bias_voltages, [ sub['seed_mean'] for sub in single_chip_list.values() ],"o-.",color=color)
            if args.pulse_seed_1640:
                ax_comp_all_chip[0,1].plot(bias_voltages, c_pulse,"o-.", color=color)

        if args.rms_p2p:
            ax_comp_all_chip[0,2].plot(bias_voltages, [ sub['RMS'] for sub in single_chip_list.values() ],"o-.", color=color, label = single_name[0:12])
            ax_comp_all_chip[1,2].plot(bias_voltages, [ sub['p2p'] for sub in single_chip_list.values() ],"o-.", color=color)
            ax_comp_all_chip[2,0].plot(bias_voltages, [ 1 / ((sub['C']*10**(15)) * (sub['noise'])) for sub in single_chip_list.values()],"o-.", color=color)
        else:
            ax_comp_all_chip[0,2].plot(bias_voltages, [ sub['noise'] for sub in single_chip_list.values() ],"o-.", color=color, label = single_name[0:12])
            if not args.pulse:
                ax_comp_all_chip[1,2].plot(bias_voltages, [ 1 / ((sub['C']*10**(15)) * (sub['noise'])) for sub in single_chip_list.values()],"o-.", color=color)

        index += 1

        info = utils.add_parameters(args,p,design,pitch)
        utils.add_text_to_plots(fig_all,ax_comp_all_chip[0,2],info, 1.1, 0.97, 'left')

    if not args.pulse_seed_1640 :
        ax_comp_all_chip[0,0].set(xlabel='$V_{BB}$ (V)',
                ylabel = f'Seed signal ({seed_label})')
        ax_comp_all_chip[0,0].axis([0,5, 0, seed_limit])#xmin xmax ymin ymax
        ax_comp_all_chip[0,1].set(xlabel='$V_{BB}$ (V)',
                    ylabel = 'Capacitance (fF)')
        ax_comp_all_chip[0,1].axis([0, 5, 0, 7])#xmin xmax ymin ymax

    else:
        ax_comp_all_chip[0,0].set(xlabel='$V_{BB}$ (V)',
                ylabel = f'Seed mean ({seed_label})')
        ax_comp_all_chip[0,0].axis([0,5, 0, seed_limit])#xmin xmax ymin ymax
        ax_comp_all_chip[0,1].set(xlabel='$V_{BB}$ (V)',
                    ylabel = 'Pulse capacitance (aF)')
        ax_comp_all_chip[0,1].axis([0, 5, 200, 280])#xmin xmax ymin ymax

    ax_comp_all_chip[1,0].set(xlabel='$V_{BB}$ (V)',
               ylabel = 'CCE (%)')
    ax_comp_all_chip[1,0].axis([0, 5, 85, 102])#xmin xmax ymin ymax

    ax_comp_all_chip[1,1].set(xlabel='$V_{BB}$ (V)',
               ylabel = 'Mean cluster size')
    ax_comp_all_chip[1,1].axis([0, 5, 1, 3.5])#xmin xmax ymin ymax
    
    if args.rms_p2p:
        ax_comp_all_chip[0,2].set(xlabel='$V_{BB}$ (V)',
                   ylabel = f'RMS ({seed_label})')
        ax_comp_all_chip[0,2].axis([0, 5, 0, rms_limit])#xmin xmax ymin ymax

        ax_comp_all_chip[1,2].set(xlabel='$V_{BB}$ (V)',
                   ylabel = f'p2p ({seed_label})')
        ax_comp_all_chip[1,2].axis([0, 5, 0, 4*rms_limit])#xmin xmax ymin ymax

        ax_comp_all_chip[2,0].set(xlabel='$V_{BB}$ (V)',
                ylabel='$1/(C_{eff}Noise)$ (1/aC)')
        ax_comp_all_chip[2,0].axis([0, 5, 0, 0.5])#xmin xmax ymin ymax
    else: 
        ax_comp_all_chip[0,2].set(xlabel='$V_{BB}$ (V)',
                   ylabel = f'Noise ({seed_label})')
        ax_comp_all_chip[0,2].axis([0, 5, 0, rms_limit])#xmin xmax ymin ymax

        ax_comp_all_chip[1,2].set(xlabel='$V_{BB}$ (V)',
                ylabel='$1/(C_{eff}Noise)$ (1/aC)')
        ax_comp_all_chip[1,2].axis([0, 5, 0, 0.5])#xmin xmax ymin ymax

    ax_comp_all_chip[0,2].legend(bbox_to_anchor=(1.62, 0), prop={"size":10}, frameon=False)
    fig_all.subplots_adjust(left=0.1, bottom=0.1, right=0.75, top=0.9)

    fig_all.savefig(os.path.join(args.output_dir,'Compare_all' + '.pdf'))

def results_comparison_dict(args):
    seed_limit = args.seed_max
    seed_label = args.unit
    if args.unit=='adc':
        bins = int(seed_limit/10)
    elif args.unit=='el':
        bins = 250
        seed_label = '$e^{-}$'
    else:
        bins = int(seed_limit)
    
    fig_hist, ax_hist = plt.subplots(sharex = False, sharey = False, figsize=(11,5))
    fig_matrix, ax_matrix = plt.subplots(sharex = False, sharey = False, figsize=(9,5))
    fig_cluster , ax_cluster = plt.subplots(1,figsize = (9,5))
    fig_noise, ax_noise = plt.subplots(sharex = False, sharey = False, figsize=(11,5))
    fig_baseline, ax_baseline = plt.subplots(sharex = False, sharey = False, figsize=(11,5))

    max_hist_cluster = 10
    bin_width_cluster = 1
    c = 0
    index = 0
    if not args.y_max:
        args.y_max = 1
    y_box = args.y_max/6
    list_files = args.file_input_dict
    list_chipID = []
    #list_files.sort()
    vbb_array = []
    seed_array = []
    for file in list_files:
        #JSON file
        data_dict = np.load(file)
        file_json_name = file.replace('return_dict_cluster_apts','Analysis/results_apts')
        file_json_name = file_json_name.replace('.npz','.json')
        with open(file_json_name, 'r') as file_json:
            data_json = json.load(file_json)
        seed = data_dict['seed']
        matrix = data_dict['matrix']
        cluster_size = data_dict['cluster_size']
        noise = data_dict['noise']
        baseline = data_dict['baseline']

        matrix = matrix[cluster_size>0]
        cluster_size = cluster_size[cluster_size>0]
        chip_ID = data_json['chip_ID']
        vbb = data_json['vbb']
        extract_name_volt = re.match(r"[E]?[R]?[1]?AF([12]?[05]?)([BP])?([M])?_(W\d{2})(B\d{1})", chip_ID)
        pitch =  extract_name_volt.group(1)
        design =  extract_name_volt.group(2)
        isMux = True if extract_name_volt.group(3)=="M" else False
        if design == None:
            design = 'standard'
        elif design == 'B':
            design = 'modified'
        elif design == 'P' and isMux == True:
            design = "Multiplexer"
        elif design == 'P':
            design = 'modified with gap'
        wafer =  extract_name_volt.group(4)
        number =  extract_name_volt.group(5)
        split,chip_ID = utils.get_split(wafer, chip_ID)
        if (chip_ID == args.reference_dut and not args.compared_params == "vbb"):
            color = 'k'
        else: 
            color = matplotlib.cm.tab20(c)
            c += 1

        if args.compared_params == "pitch":
            label=f'pitch = {pitch} \u03BCm'
        
        if args.compared_params == "flavour":
            label=f'split {split}, {design} type'
            
        if args.compared_params == "vbb":
            label='$V_{sub}$ = -%s V'%vbb

        if args.compared_params == "irradiation":
            label= args.irradiation[index]

        if args.compared_params == "mux":
            mux = -1
            try:
                mux = data_json['mux']
            except:
                mux = -1
            label = utils.get_mux_label(mux, isMux)

        if args.unit=='el':
            seed = seed*constants.EL_5_9_KEV/data_json['seed_1640']
            matrix = matrix*constants.EL_5_9_KEV/data_json['seed_1640']
        ax_hist.hist(seed[seed>0], bins = bins, color = color, label = label, histtype = 'step', density=True, range=[0, seed_limit])
        ax_matrix.hist(matrix[matrix>0], bins = bins, color = color, label = label, histtype = 'step', density=True, range=[0, seed_limit])
        ax_cluster.hist(cluster_size[:], bins = np.arange(0, max_hist_cluster + bin_width_cluster, bin_width_cluster), color = color, label = label, histtype = 'step', density = True)
        ax_noise.hist(noise.flatten(), bins = 67, color = color, label = label, histtype = 'step', density=True)
        ax_baseline.hist(baseline.flatten(), bins = 67, color = color, label = label, histtype = 'step', density=True)

        list_chipID.append(chip_ID)
        index+=1

    if args.compared_params == "mux":
        list_chipID = list(set(list_chipID))

    for chip_ID in list_chipID:
        if 0:#not (args.compared_params == "vbb"):
            ax_hist.text(seed_limit*1.1, 0.9*args.y_max/8, f'Chips:', fontsize = 7, va="bottom", ha="left")
            ax_hist.text(seed_limit*1.1, 4*y_box/8, f'- {chip_ID}', fontsize = 7, va="bottom", ha="left")
            ax_matrix.text(seed_limit*1.1, 0.9*args.y_max/8, f'Chips:', fontsize = 7, va="bottom", ha="left")
            ax_matrix.text(seed_limit*1.1, 4*y_box/8, f'- {chip_ID}', fontsize = 7, va="bottom", ha="left")
            ax_noise.text(seed_limit*1.1, 0.9*args.y_max/8, f'Chips:', fontsize = 7, va="bottom", ha="left")
            ax_noise.text(seed_limit*1.1, 4*y_box/8, f'- {chip_ID}', fontsize = 7, va="bottom", ha="left")
            ax_baseline.text(seed_limit*1.1, 0.9*args.y_max/8, f'Chips:', fontsize = 7, va="bottom", ha="left")
            ax_baseline.text(seed_limit*1.1, 4*y_box/8, f'- {chip_ID}', fontsize = 7, va="bottom", ha="left")
            y_box -= args.y_max/25    

    p = {k: '?' for k in ['wafer','chip','version','split',
                          'pwell','sub','vcasn','vcasb', 'idb',
                          'ireset', 'ibias', 'ibiasn']}
    p['id'] = 'APTS~SF'
    p.update(data_json)
    
    info = utils.add_parameters(args,p,design,pitch)
    utils.add_text_to_plots(ax_hist,ax_hist,info,1.05,0.97, 'left')
    utils.add_text_to_plots(ax_matrix,ax_matrix,info,1.05,0.97, 'left')
    utils.add_text_to_plots(ax_noise,ax_noise,info,1.05,0.97, 'left')
    utils.add_text_to_plots(ax_baseline,ax_baseline,info,1.05,0.97, 'left')

    if args.y_max:
        ax_hist.set_ylim(0,args.y_max)
        ax_matrix.set_ylim(0,args.y_max)

    ax_hist.legend(bbox_to_anchor=(1.03, 0.33), prop={"size":7}, frameon=False)
    ax_matrix.legend(bbox_to_anchor=(1.03, 0.33), prop={"size":7}, frameon=False)
    ax_cluster.legend(bbox_to_anchor=(1.03, 0.33), prop={"size":7}, frameon=False)
    ax_noise.legend(bbox_to_anchor=(1.03, 0.33), prop={"size":7}, frameon=False)
    ax_baseline.legend(bbox_to_anchor=(1.03, 0.33), prop={"size":7}, frameon=False)

    fig_hist.subplots_adjust(left=0.1, bottom=0.1, right=0.75, top=0.9)

    ax_hist.set(
                xlabel=f'Seed pixel signal ({seed_label})',
                ylabel=f'Relative frequency (per {int(seed_limit/bins)} {seed_label})')
    ax_hist.grid(alpha=0.3)

    fig_hist.tight_layout()
    fig_hist.savefig(os.path.join(args.output_dir,'Compare_all_hist' + '.pdf'))

    ax_matrix.set(
                xlabel=f'Matrix signal ({seed_label})',
                ylabel=f'Relative frequency (per {int(seed_limit/bins)} {seed_label})')
    ax_matrix.grid(alpha=0.3)
    fig_matrix.tight_layout()

    fig_matrix.savefig(os.path.join(args.output_dir,'Compare_all_matrix' + '.pdf'))
    
    ax_cluster.set(xlabel = 'Cluster size',
        ylabel = 'Relative frequency',
        xlim = ([1, max_hist_cluster]))
    utils.add_text_to_plots(ax_cluster,ax_cluster,info,1.05,0.97, 'left')

    fig_cluster.tight_layout()

    fig_cluster.savefig(os.path.join(args.output_dir,'Compare_all_cluster' + '.pdf'))
  

    fig_noise.subplots_adjust(left=0.1, bottom=0.1, right=0.75, top=0.9)
    ax_noise.set(
                xlabel=f'Noise ({seed_label})',
                ylabel=f'Relative frequency (per {int(seed_limit/bins)} {seed_label})')
    ax_noise.grid(alpha=0.3)
    fig_noise.tight_layout()
    fig_noise.savefig(os.path.join(args.output_dir,'Compare_all_noise' + '.pdf'))

    fig_baseline.subplots_adjust(left=0.1, bottom=0.1, right=0.75, top=0.9)
    ax_baseline.set(
                xlabel=f'Baseline ({seed_label})',
                ylabel=f'Relative frequency (per {int(seed_limit/bins)} {seed_label})')
    ax_baseline.grid(alpha=0.3)
    fig_baseline.tight_layout()
    fig_baseline.savefig(os.path.join(args.output_dir,'Compare_all_baseline' + '.pdf'))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APTS signal extraction",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('file_input_json', nargs = '+', help = 'Select all the json input files you want to compare. If you want to compare all the files inside a certain directory run the following: python3 results_comparison.py  $(find /directory -name "results_apts_*.json"). Required argument.')
    parser.add_argument('--file_input_dict', nargs = '+', help = 'Select all the dictionary input files from clusterization you want to compare. If you want to compare all the files inside a certain directory run the following: python3 results_comparison.py  $(find /directory -name "return_dict_cluster_apts_*.npz"). Optional argument.')
    parser.add_argument('--compared_params', default='vbb',type=str.lower, help='Select the parameter you want to compare (ex: --compared_params vbb)',choices=['pitch','flavour','vbb','irradiation','ires','mux'])
    parser.add_argument('--irradiation', nargs='+', type=str,default= ['Not irradiated'] , help='To be used if you used irradiation in --compared_params: put all the levels of irradiation (string type)')
    parser.add_argument('--unit', default='mv',type=str.lower, help='Select if you want to plot the seed signal with ADC, mV or el (electrons) units',choices=['mv','adc','el'])
    parser.add_argument('--y_max', type=float, default=1, help='Maximum value for the y axes (Relative frequency)')
    parser.add_argument('--seed_max','-srM', default = 150, type=float, help='Select the maximum of the range for the seed plot.')
    parser.add_argument('--reference_dut', type=str, default='AF15P_W22B2', help='Select the chip you want to use as reference, tha will be fixed with black color.')
    parser.add_argument('--output_dir','-o',default = '.', help = 'Directory for output plots.')
    parser.add_argument('--rms_p2p', action = 'store_true', help='Select if you want to plot rms and p2p distributions')
    parser.add_argument('--pulse', '-pulse', action = 'store_true',help='Select if you do not want to analyse pulsing data')
    parser.add_argument('--pulse_seed_1640','-ps1640', action = 'store_true' , help = 'Select if you want to plot capacitance pusling (accept only mV data). Caveat: can be used only if the chip and voltage is present in the library_seed_1640.')


    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    results_comparison(args)
    if args.file_input_dict is not None:
        results_comparison_dict(args)
