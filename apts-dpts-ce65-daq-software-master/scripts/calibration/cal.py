#!/usr/bin/env python3

"""

Semiautomatic calibration. # TODO: elaborate on this explanation maybe?

"""

__email__ = "valerio.sarritzu@cern.ch"

import mlr1daqboard # main library for mlr1 chips
import matplotlib.pyplot as plt
import numpy as np
import time
import pyvisa as visa # to control the multimeter
import sys
import argparse
import os
import datetime
import scipy
import uncertainties
import sigfig

from sigfig import round
from scipy.optimize import curve_fit

now = datetime.datetime.now()

parser = argparse.ArgumentParser(description="Calibration of current and voltage biases")
parser.add_argument('--min',type=int,default=0,help='Set DAC minimum (0-65535)')
parser.add_argument('--max',type=int,default=65535,help='Set DAC maximum(0-65535)')
parser.add_argument('--step',type=int,default=30,help='Set number of steps')
parser.add_argument('--verify',default=False,action='store_true',help='Verify calibration')
parser.add_argument('--proxy',required=True,help='Proximity card (see label))')
parser.add_argument('--wait',type=float,default=0.5,help='Time before setting DAC and reading value')
args = parser.parse_args()

if args.proxy[0:4] == 'OPAM': chip = 'APTS'
else: chip = args.proxy[0:4]

if chip == 'APTS': mlr1 = mlr1daqboard.APTSDAQBoard(args.proxy)
if chip == 'CE65': mlr1 = mlr1daqboard.CE65DAQBoard(args.proxy)
if chip == 'DPTS': mlr1 = mlr1daqboard.DPTSDAQBoard(args.proxy)

idacs = {key:value for key,value in mlr1.idacs_cal.items() if value is not None}
vdacs = {key:value for key,value in mlr1.vdacs_cal.items() if value is not None}

## DATABIAS

databiases = {
    'CE_DACA'                     : {'loc':'top',    'pin': 10, 'dac':28, 'ch': 0, 'type':'current source'},
    'CE_DACB'                     : {'loc':'top',    'pin': 11, 'dac':28, 'ch': 1, 'type':'current source'},
    'CE_NMOS'                     : {'loc':'top',    'pin': 12, 'dac':28, 'ch': 2, 'type':'current source'},
    'CE_COL_AP_IBIASN'            : {'loc':'top',    'pin': 13, 'dac':28, 'ch': 3, 'type':'current source'},
    'CE_MAT_AP_IBIAS4SF_DP_IBIASF': {'loc':'top',    'pin': 14, 'dac':28, 'ch': 4, 'type':'current source'},
    'CE_PMOS_AP_DP_IRESET'        : {'loc':'top',    'pin': 9,  'dac':29, 'ch': 0, 'type':'current sink'},
    'AP_IBIASP_DP_IDB'            : {'loc':'bottom', 'pin': 16, 'dac':29, 'ch': 1, 'type':'current sink'},
    'AP_IBIAS4OPA_DP_IBIASN'      : {'loc':'bottom', 'pin': 17, 'dac':29, 'ch': 2, 'type':'current sink'},
    'AP_IBIAS3_DP_IBIAS'          : {'loc':'bottom', 'pin': 18, 'dac':29, 'ch': 3, 'type':'current sink'},
    'AP_SEL0'                     : {'loc':'bottom', 'pin': 39, 'dac':28, 'ch': 6, 'type':'voltage'},
    'AP_SEL1'                     : {'loc':'bottom', 'pin': 40, 'dac':28, 'ch': 7, 'type':'voltage'},
    'AP_VCASN_MUX1_DP_VCASN'      : {'loc':'bottom', 'pin': 15, 'dac':29, 'ch': 7, 'type':'voltage'},
    'AP_VCASP_MUX0_DP_VCASB'      : {'loc':'bottom', 'pin': 14, 'dac':29, 'ch': 6, 'type':'voltage'},
    'AP_VRESET'                   : {'loc':'bottom', 'pin': 19, 'dac':29, 'ch': 5, 'type':'voltage'},
    'CE_VOFFSET_AP_DP_VH'         : {'loc':'top',    'pin': 16, 'dac':29, 'ch': 4, 'type':'voltage'},
    'CE_VRESET'                   : {'loc':'top',    'pin': 15, 'dac':28, 'ch': 5, 'type':'voltage'},
}

### INITIALIZE HARDWARE

resourceManager = visa.ResourceManager()

mlr1.proximity_on()

devices = resourceManager.list_resources('USB?*INSTR')
assert len(devices)==1
VISA_ADDRESS=devices[0]

try:
    session = resourceManager.open_resource(VISA_ADDRESS) # Open session to the instrument
except visa.Error as ex:
    print('Couldn\'t connect to \'%s\', exiting now...' % VISA_ADDRESS)
    sys.exit()
session.timeout=5000      #set a delay
session.write("*CLS")     #clear
session.write("*RST")     #reset

# PROMPT USER TO CHOOSE A BIAS

os.system('cls' if os.name == 'nt' else 'clear')
print('List of relevant biases for',chip,":\n")
biases = {**idacs,**vdacs}
for key,value in enumerate(biases): print('{:<4}'.format(key),'{:.<30}'.format(value),databiases.get(value)['loc'],databiases.get(value)['pin'])
biasnumber = int(input("\nChoose a bias : "))
biasname = [key for key in biases.keys()][biasnumber]
loc = databiases.get(biasname)['loc']
pin = databiases.get(biasname)['pin']
module = databiases.get(biasname)['dac']
channel = databiases.get(biasname)['ch']
os.system('cls' if os.name == 'nt' else 'clear')

# INITIALIZE ACQUISITION

if module==28: biasname = mlr1daqboard.DACS_U28[channel]
if module==29: biasname = mlr1daqboard.DACS_U29[channel]

iscurrent = biasname in idacs
isvoltage = biasname in vdacs

if iscurrent: q = idacs[biasname][1]; biasmax = idacs[biasname][2]; measure = "current (uA)"; command = 'MEAS:CURR:DC?'; scaling = 10**6 # uA to A
if isvoltage: q = vdacs[biasname][1]; biasmax = vdacs[biasname][2]; measure = "voltage (mV)"; command = 'MEAS:VOLT:DC?'; scaling = 10**3 # mV to V

if args.verify: print("Verifying",biasname,"\n")
else:           print("Calibrating",biasname,"\n")

readings = []

fname = args.proxy + '_' + biasname + '_' + now.strftime('%Y%m%d_%H%M%S') # filename
path = './' + args.proxy + '/'
if not os.path.exists(path): os.makedirs(path)
out=open(os.path.join(path+fname+".csv"),'w')

if args.verify:
    sepdac = 0.1 * biasmax
    a = np.linspace(q, sepdac, args.step)
    b = np.linspace(sepdac, biasmax, args.step)
    dac_values = np.concatenate((a[0:args.step-1], b)) # -1 to avoid repeating the same point twice
    settings = []
    deviations = []
    header = "setting\t\t reading\t perc. deviation\n"
    plt.title('Percent deviation of '+biasname+' wrt to calibration')
    plt.xlabel('set '+measure)
    plt.ylabel('100*|Output-Setting|/Setting')
    plt.xscale('log')
    plt.yscale('log')
    plt.grid(True, which='minor', linewidth=.3)
    plt.grid(True, which='major', linewidth=.3)
    plt.xlim([q, biasmax])
    plt.axhline(y=2, color='green', linestyle='--', linewidth=2)
    out.write('setting,reading,perc. deviation\n')
else:
    settings = []
    sepdac = int(0.1 * args.max)
    a = np.linspace(args.min, sepdac, args.step)
    b = np.linspace(sepdac, args.max, args.step)
    dac_values = np.concatenate((a[0:args.step-1], b)) # -1 to avoid repeating the same point twice
    header = 'point\t ' + 'dac\t ' + measure + '\n'
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    fig.suptitle(biasname)
    ax1.set_title('Full range')
    if isvoltage: ax1.set_xlim([args.min, 17500])
    else:         ax1.set_xlim([args.min, args.max])
    ax1.set_ylim([0,biasmax])
    ax2.set_title('Zoom')
    ax2.set_xlim([args.min, sepdac])
    #plt.title(biasname)
    ax1.set_xlabel('setting')
    ax1.set_ylabel(measure)
    ax2.set_xlabel('setting')
    ax2.set_ylabel(measure)
    out.write('dac,' + measure + '\n')
print(header)

# ACQUIRE

try:
    for i, dac in enumerate(dac_values):
        if args.verify:
            if iscurrent: mlr1.set_idac(biasname, dac)
            if isvoltage: mlr1.set_vdac(biasname, dac)
        else:
            dac = int(round(dac))
            dac_values[i] = dac
            mlr1.set_dac(biasname, dac)
        time.sleep(args.wait)
        session.write(command)
        reading = scaling * float(session.read()) # scaled to uA or mV
        readings.append(reading)
        if args.verify:
            deviation = abs(100 * (reading - dac)/(dac))
            deviations.append(deviation)
            print("%.5f" % dac, "\t", "%.5f" % reading, "\t", "%.2f" % deviation)
            settings.append(dac)
            plt.plot(settings, deviations, 'r', marker=".")
            out.write(str("%.5f" % dac)+','+str("%.5f" % reading)+','+str("%.2f" % deviation)+'\n')
            lastpoint = i
        else:
            settings.append(dac)
            print(i, "\t", dac, "\t", "{:.2f}".format(reading))
            ax1.plot(dac_values[0:i+1],readings, color='red', marker=".")
            if dac < sepdac:
                ax2.plot(dac_values[0:i+1],readings, color='red', marker=".", linestyle="None")
                ax2.annotate(i, (dac, reading), ha='right', va='bottom')
            else: ax1.annotate(i, (dac, reading), ha='right', va='bottom',)
            out.write(str(dac)+','+str("%.2f" % reading)+'\n')
        plt.pause(0.05)
        if isvoltage and biasname != 'CE_VRESET':
            if readings[i] + (readings[i] - readings[i-1]) > biasmax: break # do not exceed max for that bias
except KeyboardInterrupt:
    pass

# FIT & PLOT

if args.verify:
    x = np.array(settings[0:(lastpoint+1)])
    y = np.array(deviations[0:(lastpoint+1)])
    plt.plot(x, y, 'r-', linewidth = 0.5)
    print('\nDone. You may now save the plot and close the plot window.')
    plt.savefig(path + fname +'.png', dpi=300, format='png')
    plt.show()
else:
    def objective(x, m, b): return m * x + b # fit function
    while(True): # FIT UNTIL OK
        firstpoint = int(input("\nPlease enter first point for the fit: "))
        lastpoint = int(input("\nPlease enter last point before saturation: "))
        x = np.array(dac_values[0:(lastpoint+1)])
        y = np.array(readings[0:(lastpoint+1)])
        xfull = np.array(settings)
        yfull = np.array(readings)
        popt, pcov = curve_fit(objective, x[firstpoint:(lastpoint+1)], y[firstpoint:(lastpoint+1)])
        m = float(popt[0]); b = float(popt[1]); merr = (np.sqrt(np.diag(pcov)[0])); berr = (np.sqrt(np.diag(pcov)[1]))
        print('\nFit results:')
        #mresult = '{:.1u}'.format(uncertainties.ufloat(m, merr))
        #bresult = '{:.1u}'.format(uncertainties.ufloat(b, berr))
        sigfig_biasmax = len(str(biasmax).replace(".",""))
        sigfig_lastset = len(str(settings[-1]).replace(".",""))
        mresult = str(round(m, sigfigs = min (sigfig_lastset, sigfig_biasmax)))
        bresult = str(round(b, decimals = 2))
        fitfunc = 'y = '+ mresult + ' * x + ' + bresult
        print('m =',mresult)
        print('q =',bresult)
        fit1 = ax1.plot(x, m * x + b, 'g-', linewidth = 0.3)
        fit2 = ax2.plot(x, m * x + b, 'g-', linewidth = 0.3)
        plt.pause(0.05)
        devfig, devax = plt.subplots()
        devfig.suptitle('Percent dev. of ' + biasname + ' wrt calibration')
        devax.set_yscale('log')
        devax.set_xscale('log')
        devax.set_xlabel(measure)
        devax.set_ylabel('100*|Output-Setting|/Setting')
        devax.xaxis.grid(which = 'both', linewidth = 0.5)
        devax.yaxis.grid(which = 'both', linewidth = 0.5)
        devax.axhspan(2.5, 10**3, color = 'red', alpha = 0.1)
        devax.margins(y=0)
        #devax.plot(m * x + b, 100 * abs(y - (m * x + b)) / (m * x + b), color = 'red', marker=".")
        devax.plot(m * xfull + b, 100 * abs(yfull - (m * xfull + b)) / (m * xfull + b), color = 'red', marker=".")
        plt.pause(0.05)
        if input('Is the fit OK? (y/n) ') == 'y':
            break
        else:
            f1 = fit1.pop(0); f1.remove(); f2 = fit2.pop(0); f2.remove(); plt.pause(0.05); plt.close(devfig); plt.pause(0.05)
    plt.savefig(path + fname + '_DEV' + '.png', dpi=300, format='png')
    out.write('\nFitted between points '+ str(firstpoint) + ' and ' + str(lastpoint) + '\n')
    out.write('\nm = '+ mresult + '\n')
    out.write('q =' + bresult)
    plt.clf() # clear the plot as we want to format it differently
    plt.xlabel('setting')
    plt.ylabel(measure)
    plt.grid(True, which='both', linewidth=.3)
    plt.plot(x, y, color='red', marker=".", linestyle = "None", label=biasname)
    plt.plot(x, m * x + b, 'g', linewidth = 0.5, label=fitfunc)
    plt.legend()
    plt.savefig(path + fname + '_DAT' + '.png', dpi=300, format='png')

# CLOSE

out.close()
session.close() # Close the connection to the instrument
resourceManager.close()
