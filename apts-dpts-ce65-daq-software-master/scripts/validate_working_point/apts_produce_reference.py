# Mauro Aresti and Paola La Rocca, 05/2022
# Python script that produces and stores reference curves (baseline, rms, derivative VS VReset) to be used as reference to validate the working point for APTS. 
# Once the reference curves are produced and stored in npz files, it is possible to compare new data with them running the script 'apts_validate_working_point.py'
# Plots can be produced with -p option

import matplotlib.pyplot as plt
import numpy as np
import json
import argparse
import os
import re
import mlr1daqboard
import sys
sys.path.append('../../apts/')
from apts_decode import raw_to_npy

# Function to evaluate the derivative
def der(y,x):
    dy = [0.0]*len(x)
    dy[0] = (y[0] - y[1])/(x[0] - x[1])
    for i in np.arange(1,len(y)-1):
        num = 0
        den = 0
        if i<5: 
            npoints = i
        elif i>=len(y)-5:
            npoints = len(y)-i-1
        else:
            npoints = 5
        for n in range(npoints):
            num+= y[i-(n+1)] - y[i+(n+1)]
            den+= x[i-(n+1)] - x[i+(n+1)]
        dy[i] = num/den
    dy[-1] = (y[-1] - y[-2])/(x[-1] - x[-2])
    return dy

# ---# main 
def main():
    
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-plot','-p', action='store_true',default=False,help='show plot')
    parser.add_argument('DUT_dir',type=str,help='Directory DUT chip ex: apts_gain_20220510_145629')
    args = parser.parse_args()
    
    vres_range = np.arange(20, 901, 10)
    vbb_range = [0.0,0.3,0.6,0.9,1.2,2.4,3.6,4.8]
    
    # Data to be stored in the npz output file
    baseline_vbb = np.empty(shape=(len(vbb_range),vres_range.size))
    rms_vbb = np.empty(shape=(len(vbb_range),vres_range.size))
    derivative_vbb = np.empty(shape=(len(vbb_range),vres_range.size))

    # Loop over Vbb values
    for n,ivbb in enumerate(vbb_range):
        print('-----< Vbb = ', ivbb,'>------')

        # Retrieve data
        directory = os.path.realpath(f'../../Data/{args.DUT_dir}/vbb_{ivbb:.1f}')
        # Check if decode has been done
        decodeFlag = False
        for file in os.listdir(directory):
            if file.endswith(".npy"):
                decodeFlag = True
        if not decodeFlag:
            for file in os.listdir(directory):
                if not file.endswith('.raw'): continue
                print('#### Decoding........')
                raw_to_npy(directory + '/' + file, directory + '/' + file.replace('.raw','_decoded.npy'))

        for file in os.listdir(directory):
            if file.endswith(".npy"):
                waveforms = np.load(directory + '/' + file)
                
            if file.endswith(".json"):
                with open(directory + '/' + file, 'r') as j:
                    data_json = json.load(j)

        k = 0
        baseline_all = []
        rms_all = []
        for ivr in range(len(vres_range)):
            rms = []
            baseline = []
            for i in range(4):
                for j in range(4):
                    baseline.append(np.mean(waveforms[k:k+data_json['ntrg']-1,i,j,:]))
                    rms.append(np.std(waveforms[k:k+data_json['ntrg']-1,i,j,:]))
            baseline_all.append(baseline)
            rms_all.append(rms)
            k += data_json['ntrg']
        baseline_all = np.array(baseline_all) # cointains 89 arrays of 16 values
        rms_all = np.array(rms_all) # cointains 89 arrays of 16 values
        baseline_all_T = baseline_all.T # Transpose
        rms_all_T = rms_all.T # Transpose
        derivative = []
        for i in range(16):
            derivative.append(der(baseline_all_T[i], vres_range))
        derivative = np.array(derivative)

        # Evaluate the average over the 16 pixels
        baseline_mean = np.mean(baseline_all_T,axis=0)
        baseline_vbb[n,:] = baseline_mean
        rms_mean = np.mean(rms_all_T,axis=0)
        rms_vbb[n,:] = rms_mean
        derivative_mean = np.mean(derivative,axis=0)
        derivative_vbb[n,:] = derivative_mean

        # Graphics (displayed only if -p option is specified)
        fig, (ax1,ax2,ax3) = plt.subplots(1, 3, figsize=(20,5))
        cmap = ['jet','Reds', 'Blues']

        ilegend = []
        for i in range(16):
            ax1.plot(vres_range, 0.0381*baseline_all_T[i], linestyle='', marker='v', markersize=2, fillstyle='none', color=plt.cm.get_cmap(cmap[0])(i*20))
            l, = ax2.plot(vres_range, 0.0381*rms_all_T[i], linestyle='-', marker='', linewidth=1, fillstyle='none', color=plt.cm.get_cmap(cmap[0])(i*20))
            ax3.plot(vres_range, 0.0381*derivative[i], linestyle='-', marker='', linewidth=1, fillstyle='none', color=plt.cm.get_cmap(cmap[0])(i*20))
            ilegend.append(l)
        ax1.plot(vres_range, 0.0381*baseline_mean, linestyle='-', linewidth=2, fillstyle='none', color='black')
        ax1.set_title('Baseline vs V_RESET')
        ax1.set_xlabel(r'V_RESET [mV]')
        ax1.set_ylabel(r'Baseline [mV]')
        ax1.grid(alpha=0.3)

        chip_ID = data_json['chip_ID']
        mux = False
        if 'chip_ID' in data_json:
            extract_name_volt = re.match(r"A[AF]([12]?[05]?)([BP])?([M])?_(W\d{2})(B\d{1})", chip_ID)
            mux = True if extract_name_volt.group(3)=="M" else False
        mapping = mlr1daqboard.APTS_MUX_PIXEL_ADC_MAPPING if mux else mlr1daqboard.APTS_PIXEL_ADC_MAPPING

        ax2.plot(vres_range, 0.0381*rms_mean, linestyle='-', fillstyle='none', color='black')
        ax2.set_title('RMS vs V_RESET')
        ax2.set_xlabel(r'V_RESET [mV]')
        ax2.set_ylabel(r'RMS [mV]')
        ax2.grid(alpha=0.3)
        ax2.legend(ilegend,mapping,title=f'Pixels',ncol=4, fontsize='small', loc='lower center', bbox_to_anchor=(0.5,0.1))

        ax3.plot(vres_range, 0.0381*derivative_mean, linestyle='-', fillstyle='none', color='black')
        ax3.set_title('Derivative vs V_RESET')
        ax3.set_xlabel(r'V_RESET [mV]')
        ax3.set_ylabel(r'Derivative [mV]')
        ax3.grid(alpha=0.3)

        fig.subplots_adjust(wspace=0.3)
        plt.suptitle(f'Reference data: -Vbb = {ivbb} V, chip: ' + data_json['chip_ID'] )
        if(args.plot):
            plt.show()
        plt.close()
	
    # Fill and save output file
    np.savez('./reference_' + data_json['chip_ID'] + '.npz', vbb = vbb_range, bsl = baseline_vbb, rms = rms_vbb, der = derivative_vbb)

if __name__ == '__main__':
    main()
