# Mauro Aresti and Paola La Rocca, 05/2022
# Python script to validate the working point for APTS. 
# It compares the data collected at the working point (produced by the script 'apts_gain.py') with reference curves.
# Reference curves are retrieved from npz files (available in the TWiki page). To produce new npz reference files use the script 'apts_produce_reference.py'.
# Check paths (line 55) and Vbb values explored (line 48)

import matplotlib.pyplot as plt
import numpy as np
import json
import argparse
import pprint as p
import os
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
    parser.add_argument('REF_chip',type=str,help='Reference chip name ex: AF15P_W22B4')
    parser.add_argument('DUT_dir',type=str,help='Directory DUT chip ex: apts_gain_20220510_145629')
    args = parser.parse_args()
    
    vres_range = np.arange(20, 901, 10)
    vbb_range = [0.0,0.3,0.6,0.9,1.2,2.4,3.6,4.8]
    
    # Loop over Vbb values
    for n,ivbb in enumerate(vbb_range):
        print('-----< Vbb = ', ivbb,'>------')

        # Retrieve data for DUT chip
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

        # Retrieve data for reference chip
        ref = np.load(f'reference_{args.REF_chip}.npz')
        baseline_mean = ref['bsl'][n]
        rms_mean = ref['rms'][n]
        derivative_mean = ref['der'][n]
        assert np.array_equal(ref['vbb'],np.array(vbb_range)), 'Vbb values not corresponding to those explored in the .npz reference file'

        # Graphics (displayed only if -p option is specified)
        fig, ax = plt.subplots(2, 3, figsize=(17,8), sharex=True)
        cmap = ['jet','Reds', 'Blues']

        ilegend = []
        for i in range(16):
            ax[0,0].plot(vres_range, 0.0381*baseline_all_T[i], linestyle='', marker='v', markersize=2, fillstyle='none', color=plt.cm.get_cmap(cmap[0])(i*20))
            l, = ax[0,1].plot(vres_range, 0.0381*rms_all_T[i], linestyle='-', marker='', linewidth=1, fillstyle='none', color=plt.cm.get_cmap(cmap[0])(i*20))
            ax[0,2].plot(vres_range, 0.0381*derivative[i], linestyle='-', marker='', linewidth=1, fillstyle='none', color=plt.cm.get_cmap(cmap[0])(i*20))
            ilegend.append(l)
        ax[0,0].plot(vres_range, 0.0381*baseline_mean, linestyle='-', linewidth=2, fillstyle='none', color='black')
        ax[0,0].set_title('Baseline vs V_RESET')
        #ax[0,0].set_xlabel(r'V_RESET [mV]')
        ax[0,0].set_ylabel(r'Baseline [mV]')
        ax[0,0].grid(alpha=0.3)
        
        ax[0,1].plot(vres_range, 0.0381*rms_mean, linestyle='-', fillstyle='none', color='black')
        ax[0,1].set_title('RMS vs V_RESET')
        #ax[0,1].set_xlabel(r'V_RESET [mV]')
        ax[0,1].set_ylabel(r'RMS [mV]')
        ax[0,1].grid(alpha=0.3)

        ax[0,2].plot(vres_range, 0.0381*derivative_mean, linestyle='-', fillstyle='none', color='black')
        ax[0,2].set_title('Derivative vs V_RESET')
        #ax[0,2].set_xlabel(r'V_RESET [mV]')
        ax[0,2].set_ylabel(r'Derivative [mV]')
        ax[0,2].grid(alpha=0.3)

        for i in range(16):
            ax[1,0].plot(vres_range, 100*np.abs(baseline_all_T[i]-baseline_mean)/baseline_mean, linestyle='', marker='v', markersize=2, fillstyle='none', color=plt.cm.get_cmap(cmap[0])(i*20))
            ax[1,1].plot(vres_range, 100*np.abs(rms_all_T[i]-rms_mean)/rms_mean, linestyle='-', marker='', linewidth=1, fillstyle='none', color=plt.cm.get_cmap(cmap[0])(i*20))
            ax[1,2].plot(vres_range, 100*np.abs(derivative[i]-derivative_mean)/derivative_mean, linestyle='-', marker='', linewidth=1, fillstyle='none', color=plt.cm.get_cmap(cmap[0])(i*20))

        ax[1,0].set_title('Baseline Difference vs V_RESET')
        ax[1,0].set_xlabel(r'V_RESET [mV]')
        ax[1,0].set_ylabel(r'Abs Baseline Diff (DUT-REF) [%]')
        ax[1,0].grid(alpha=0.3)

        ax[1,1].set_title('RMS difference vs V_RESET')
        ax[1,1].set_xlabel(r'V_RESET [mV]')
        ax[1,1].set_ylabel(r'Abs RMS Diff (DUT-REF) [%]')
        ax[1,1].grid(alpha=0.3)

        ax[1,2].set_title('Derivative Difference vs V_RESET')
        ax[1,2].set_xlabel(r'V_RESET [mV]')
        ax[1,2].set_ylabel(r'Abs Derivative Diff (DUT-REF) [%]')
        ax[1,2].grid(alpha=0.3)

        fig.subplots_adjust(wspace=0.2)
        fig.subplots_adjust(wspace=0.2)
        plt.suptitle(f'Compare REFERENCE {args.REF_chip} vs DUT ' + data_json['chip_ID'] + f', -Vbb = {ivbb} V')
        if(args.plot):
            plt.show()
        plt.close()
	
if __name__ == '__main__':
    main()
