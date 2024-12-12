#!/usr/bin/env python3

__author__ = "Roberto Russo"
__maintainer__ = "Roberto Russo"
__email__ = "r.russo@cern.ch"
__status__ = "Development"

from opamp_decode import raw_to_npz
import logging, argparse, os, re, json
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import pathlib


# global settings and variables
mpl.rc('xtick', labelsize=12)
mpl.rc('ytick', labelsize=12)


def der(baseline,baseline_error,vreset,points=5):
    ''' Takes two arrays and returns the numerical derivative as a slope calculated considering a number of points equal to `points` before and after each point'''
    dy = [0.0]*len(vreset)
    dy_error = [0.0]*len(vreset)
    dy[0] = (baseline[0] - baseline[1])/(vreset[0] - vreset[1])
    dy_error[0] = 0.5*np.sqrt((baseline_error[0])**2 + (baseline_error[1])**2)/(vreset[0] - vreset[1])  # error propagation of baseline uncertainty
    for i in np.arange(1,len(baseline)-1):
        num = 0
        den = 0
        num_error = 0
        if i<points: 
            npoints = i
        elif i>=len(baseline)-points:
            npoints = len(baseline)-i-1
        else:
            npoints = points
        for n in range(npoints):
            num+= baseline[i-(n+1)] - baseline[i+(n+1)]
            den+= vreset[i-(n+1)] - vreset[i+(n+1)]
            num_error+= (baseline_error[i-(n+1)])**2 + (baseline_error[i+(n+1)])**2  # error propagation of baseline uncertainty
        dy[i] = num/den
        dy_error[i] = 1/(2*npoints)*np.sqrt(num_error)/den
    dy[-1] = (baseline[-1] - baseline[-2])/(vreset[-1] - vreset[-2])
    dy_error[-1] = 0.5*np.sqrt((baseline_error[-1])**2 + (baseline_error[-2])**2)/(vreset[-1] - vreset[-2])  # error propagation of baseline uncertainty
    return dy, np.abs(dy_error)


def list_files(dir): # function used to list all the files present inside all the subdirectories of a directory (given in input)
    r = []
    for subdir,_,files in os.walk(dir):
        for file in files:
            if not (file.endswith('raw') and (file.startswith('apts_gain') or file.startswith('opamp_gain'))): continue
            r.append(os.path.join(subdir, file))
    return r


def analysis_gain(args):
    vres_range = np.arange(20, 901, 10)
    plot_dir = os.path.join(args.data_path, "gain_plots")
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    for file in list_files(args.data_path):
        with open(file.replace('.raw','.json'), 'r') as j:
            data_json = json.load(j)
        if not ("fixed_vreset_measurement" in data_json.keys()):
            data_json["fixed_vreset_measurement"] = False
        pixel_dict = data_json['inner_pixel_connections']
        scope_measured_pixels = []
        for p in pixel_dict.keys():
            scope_measured_pixels.append(int(re.findall(r'J(\d+)', pixel_dict[p])[0]))
        with open(os.path.join(pathlib.Path(file).parent,"scope_channel_settings.json"), 'r') as j:
            scope_ADC_to_mV_json = json.load(j)
        if not os.path.exists(file.replace('.raw','_decoded.npz')):
            raw_to_npz(file, file.replace('.raw','_decoded.npz'), n_scope_channels=len(scope_measured_pixels), scope_memory_depth=data_json['scope_memory_depth'],\
                scope_data_precision=args.scope_data_precision, header=args.header)
        waveforms = np.load(file.replace('.raw','_decoded.npz'))
        ADC_waveforms = np.transpose(waveforms['ADC'], axes=(0, 2, 1, 3))  # transpose row and column to have them in the correct position as they are tansposed in the converter
        scope_waveforms = waveforms['scope']
        if data_json["fixed_vreset_measurement"]:
            vres_range = np.array([data_json["vreset"]])
        baseline_all = np.zeros((16, len(vres_range)), dtype=np.float32)
        baseline_rms_all = np.zeros((16, len(vres_range)), dtype=np.float32)
        k = 0
        for ivr in range(len(vres_range)):
            for i in range(4):
                for j in range(4):
                    p = i * 4 + j
                    if p in scope_measured_pixels:
                        idx = scope_measured_pixels.index(p)
                        baseline_all[p, ivr] = np.round(np.mean((scope_ADC_to_mV_json[f'v0_ch{idx+1}']+scope_waveforms[k:k+data_json['ntrg'],idx,:]*scope_ADC_to_mV_json[f'dv_ch{idx+1}'])*1E3), 2)    # convert scope ADC units in mV
                        baseline_rms_all[p, ivr] = np.round(np.std((scope_ADC_to_mV_json[f'v0_ch{idx+1}']+scope_waveforms[k:k+data_json['ntrg'],idx,:]*scope_ADC_to_mV_json[f'dv_ch{idx+1}'])*1E3), 2) # convert scope ADC units in mV
                    else:
                        baseline_all[p, ivr] = np.round(np.mean(ADC_waveforms[k:k+data_json['ntrg'],i,j,:])*0.0381, 2)    # convert ADC units in mV
                        baseline_rms_all[p, ivr] = np.round(np.std(ADC_waveforms[k:k+data_json['ntrg'],i,j,:])*0.0381, 2) # convert ADC units in mV
            k += data_json['ntrg']
        if not data_json["fixed_vreset_measurement"]:
            vbb = data_json['vbb']
            gain_all = []
            gain_rms_all = []
            for k in range(16):
                derivative,err_derivative = der(baseline=baseline_all[k, :], baseline_error=baseline_rms_all[k, :], vreset=vres_range, points=7)
                gain_all.append(derivative)
                gain_rms_all.append(err_derivative)
            gain_all = np.round(np.array(gain_all),4)
            gain_rms_all = np.round(np.array(gain_rms_all),4)
            np.savez(file.replace('.raw','_analysed.npz'), vres_range=vres_range, baseline_all=baseline_all, baseline_rms_all=baseline_rms_all, gain_all=gain_all, gain_rms_all=gain_rms_all)  # vres and baseline expressed in mV
            # produce control plots of baseline and derivative
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10,5))
            for k in range(16):
                ax1.errorbar(vres_range, baseline_all[k, :], yerr=baseline_rms_all[k, :], linestyle=' ',marker='v', markersize=1)
                ax2.errorbar(vres_range, gain_all[k, :], yerr=gain_rms_all[k, :], linestyle='-', linewidth=1, label=f'{k}')
                ax2.legend(fontsize='x-small', ncol=3)
            ax1.set_title('Baseline vs V$_{reset}$')
            ax1.set_xlabel('V$_{reset}$ (mV)')
            ax1.set_ylabel('Baseline (mV)')
            ax1.set_xlim([0, 910])
            ax1.set_ylim([0, 600])
            ax1.grid(alpha=0.3)
            ax2.set_title('Derivative vs V$_{reset}$')
            ax2.set_xlabel('V$_{reset}$ (mV)')
            ax2.set_ylabel('Derivative (-)')
            ax2.set_xlim([0, 910])
            ax2.set_ylim([0, 0.8])
            ax2.grid(alpha=0.3)
            fig.savefig(os.path.join(plot_dir, f"Vsub_{vbb}_control_plot.png"))
        else:
            np.savez(file.replace('.raw','_analysed.npz'), vres_range=vres_range, baseline_all=baseline_all, baseline_rms_all=baseline_rms_all)  # vres and baseline expressed in mV
    json_data = {}
    for file in sorted(list_files(args.data_path)):
        with open(file.replace('.raw','.json'), 'r') as j:
            data_json = json.load(j)
        if not ("fixed_vreset_measurement" in data_json.keys()):
            data_json["fixed_vreset_measurement"] = False
        measured_pixels = data_json['inner_pixel_connections']
        dataset = np.load(file.replace('.raw', '_analysed.npz'))
        vres_range = dataset['vres_range']
        baseline = dataset['baseline_all']
        baseline_rms = dataset['baseline_rms_all']
        if not data_json["fixed_vreset_measurement"]:
            gain = dataset['gain_all']
            gain_rms = dataset['gain_rms_all']
            baseline_dict = {}
            for i in measured_pixels.keys():
                pixel_dict = {}
                p = int(re.findall(r'J(\d+)', measured_pixels[i])[0])
                index = np.where(gain[p, :] >= 0.8*np.max(gain[p, :]))[0]  # identify vreset where gain is in the region of 80% of the maximum or above
                pixel_dict['vreset'] = [int(elem) for elem in vres_range[index[0]:index[-1]+1]] # list comprehension with explicit cast to avoid issues with JSON serializer
                pixel_dict['baseline'] = [round(float(elem),2) for elem in baseline[p, index[0]:index[-1]+1]]
                pixel_dict['baseline_rms'] = [round(float(elem),2) for elem in baseline_rms[p, index[0]:index[-1]+1]]
                pixel_dict['gain'] = [round(float(elem),4) for elem in gain[p, index[0]:index[-1]+1]]
                pixel_dict['gain_rms'] = [round(float(elem),4) for elem in gain_rms[p, index[0]:index[-1]+1]]
                baseline_dict[p] = pixel_dict
            if 'vbb' in data_json.keys():
                vbb = data_json['vbb']
                json_data[vbb] = baseline_dict
            else:
                json_data = baseline_dict
        else:
            vbb = data_json['vbb']
            vreset = data_json['vreset']
            json_data[str(vbb)] = {}
            json_data[str(vbb)]["vreset"] = vreset
            json_data[str(vbb)]["pixels"] = {}
            for i in measured_pixels.keys():
                pixel_dict = {}
                p = int(re.findall(r'J(\d+)', measured_pixels[i])[0])
                pixel_dict['baseline'] = round(float(baseline[p]),2)
                pixel_dict['baseline_rms'] = round(float(baseline_rms[p]),2)
                json_data[str(vbb)]["pixels"][p] = pixel_dict
    return json_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APTS OPAMP routine for gain calibration data processing and analysis.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--data_path','-d',help='Directory for input files.')
    parser.add_argument('--scope_data_precision','-s',type=int,choices=[1, 2, 4],default=1,const=1,nargs='?',help='Number of bytes used to store scope waveform data.')
    parser.add_argument('--header','-hd',nargs='+',default=None,help='Remove the header by giving: byte in header  byte in footer  num pulses  num points scanned.')
    args = parser.parse_args()
    
    if args.header is not None:
        assert len(args.header)==4, f"Missing information in header. Only {len(args.header)} elements found: {args.header}. Expected arguments are:  byte in header  byte in footer  num pulses  num points scanned"
    
    try:
        gain_dict = analysis_gain(args)
        with open(os.path.join(args.data_path, "gain.json"),'w') as file_handle:
            json.dump(gain_dict, file_handle, indent=4)
    except KeyboardInterrupt:
        logging.info('User stopped.')
    except Exception as e:
        logging.exception(e)
        logging.fatal('Terminating!')
