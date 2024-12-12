#!/usr/bin/env python3

import argparse
import glob
import numpy as np
from matplotlib import pyplot as plt
import os
from scipy.optimize import curve_fit
from tqdm import tqdm

def Gauss(x, mu, sig, amp, offset):
    return amp*np.exp(-1*(1/2)*((x-mu)**2/(sig)**2))+offset


def fe55_energy_calibration(spectrum_file, outdir):
    #takes ToT corrected Fe55 spectrum to produce conversion factor for theToT to energy calibration
    if not os.path.exists(outdir): os.makedirs(outdir)
    fname = outdir+'/'+spectrum_file[spectrum_file.rfind('/')+1:].replace('.npy','')
    
    #load spectrum
    data = np.load(spectrum_file)
    spectrum = data['calibratedToT']

    #Preparing ToT spectrum
    spectrum_entries, bins = np.histogram(spectrum, bins=350)
    bincenters = np.array([0.5 * (bins[i] + bins[i+1]) for i in range(len(bins)-1)])

    #estimate prefit parameters and fit range
    max_bin = np.where(spectrum_entries == spectrum_entries.max())
    mu_prefit = bincenters[int(min(max_bin[0]))] #take position of the maximum bin
    amp_prefit = np.max(spectrum_entries) #take height of the maximum bin
    sig_prefit = 0.05*mu_prefit #take 5% of mu ) usual resolution value
    base_prefit = 0.1*amp_prefit #take 10% of the spectrum height

    fit_start = mu_prefit - 1 *sig_prefit
    fit_end = mu_prefit + 1.5 *sig_prefit
    fitrange = np.linspace(fit_start, fit_end, 1000)
    allrange = np.linspace(0, bincenters[-1], 1000)

    msk_fitrange = (bincenters > fit_start) & (bincenters < fit_end) #create mask to restrict on fitrange

    parameter_restriction=([mu_prefit-1*sig_prefit, 0.01*mu_prefit/2.35, 0, 0], [mu_prefit+1*sig_prefit, 0.3*mu_prefit/2.35, np.inf, 0.3*amp_prefit ]) #([x1_low, x2_low, ...] , [x1_high, x2_high, ...]) [mu, sig, amp, base]

    #Plot prefit parameters for easier debugging from plots
    plt.axvline(mu_prefit, color='green', label='Prefit parameters')
    plt.axhline(amp_prefit, color='green')
    plt.axhline(base_prefit, color='green')
 
    print("[INFO] Prefit parameters:")
    print("    -| mu: ", mu_prefit)
    print("    -| sig: ", sig_prefit)
    print("    -| amp: ", amp_prefit)
    print("    -| base: ", base_prefit)
    print("    -| fit_start: ", fit_start)
    print("    -| fit_end: ", fit_end)
    
    #K-alpha Gauss Fit
    popt_peak, pcov = curve_fit(Gauss, xdata=bincenters[msk_fitrange], ydata=spectrum_entries[msk_fitrange],
            p0=[mu_prefit, sig_prefit, amp_prefit, base_prefit], bounds=parameter_restriction, sigma=np.sqrt(spectrum_entries[msk_fitrange]))
    perr_peak = np.sqrt(np.diag(pcov))

    #fit control plot
    plt.grid()
    plt.bar(bincenters, spectrum_entries, width=bins[1] - bins[0], color='navy', label=r'Fe55 spectrum')
    plt.plot(allrange , Gauss(allrange, *popt_peak), color='grey', linewidth=2, label=r'Fit (extended)')
    plt.plot(fitrange , Gauss(fitrange, *popt_peak), color='red', linewidth=2, label=f'Fit (within fitrange) \n$\mu$: {popt_peak[0]:5.1f} mV, $\sigma$:  {popt_peak[1]:5.1f} mV')
    plt.xlabel('ToT-calibrated ToT (mV)')
    plt.ylabel('Entries')
    plt.xlim([0,mu_prefit+7*sig_prefit])
    plt.legend()
    plt.savefig(fname+"_spectrum_fit.png")

    print("[INFO] Optimized parameters:")
    print(f"    -| mu: {popt_peak[0]} ± {perr_peak[0]}")
    print(f"    -| sig: {popt_peak[1]} ± {perr_peak[1]}")
    print(f"    -| amp: {popt_peak[2]} ± {perr_peak[2]}")
    print(f"    -| base: {popt_peak[3]} ± {perr_peak[3]}")

    mu_fit = popt_peak[0]
    mu_fit_err = perr_peak[0]

    #calculate energy conversion factor
    K_alpha_energy = 5.89875*1000/3.6 #e-
    energy_conversion_factor = K_alpha_energy / mu_fit
    energy_conversion_factor_err = K_alpha_energy / mu_fit**2 * mu_fit_err

    #energy-calibration control plot
    plt.figure()
    plt.plot([0, mu_fit], [0, K_alpha_energy], label=f'Energy calibration factor (slope): {energy_conversion_factor:5.2f} e$^-$/mV',marker='o', color = 'red', ms=5, mec='navy', mfc='navy')
    plt.xlabel('ToT (mV)')
    plt.ylabel('Energy (e$^{-}$)')
    plt.legend()
    plt.grid()
    plt.savefig(fname+"_energy_calib.png")

    energy_spectrum = spectrum * energy_conversion_factor
    np.save(fname+"_energySpectrum.npy", energy_spectrum)

    return energy_conversion_factor, energy_conversion_factor_err


if __name__=="__main__":
    parser = argparse.ArgumentParser("Energy calibrator",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('spectrum', help="file.npz with the ToT calibrated Fe55 spectrum produced by sourceana.py or directory containing such files.")
    parser.add_argument('--outdir' , default="./plots", help="Directory for output parameters and plots")
    parser.add_argument('-q', '--quiet', action = 'store_true', help= "Do not plot control plots")

    args = parser.parse_args()

    print('[INFO] Starting Fe55 energy calibration')

    if '.npz' in args.spectrum:
        #perform calibration
        energy_conversion_factor, energy_conversion_factor_err = fe55_energy_calibration(args.spectrum, args.outdir)
        print('[INFO] Energy conversion factor: ')
        print(f"    -| E (e-) = ToT (mV) * {energy_conversion_factor} ± {energy_conversion_factor_err}")
    else:
        if '*' not in args.spectrum: args.spectrum+='*.npz'
        print("[INFO] Processing all file matching pattern ", args.spectrum)
        for f in tqdm(glob.glob(args.spectrum),desc="Processing file"):
            print(f)
            if '.npz' in f:
                #perform calibration
                energy_conversion_factor, energy_conversion_factor_err = fe55_energy_calibration(f, args.outdir)
                print('[INFO] Energy conversion factor: ')
                print(f"    -| E (e-) = ToT (mV) * {energy_conversion_factor} ± {energy_conversion_factor_err}")
                plt.close('all')

    #plot control plots
    if not(args.quiet): plt.show()

