#!/usr/bin/env python3

#====================
#
# IMPORTS
#
#====================

from matplotlib import pyplot as plt
import numpy as np
import argparse
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scipy.optimize import curve_fit
import pylandau

#====================
#
# FUNCTIONS
#
#====================

#read in spectrum without pixel position information
def get_corrected_spectrum_in_electrons(infile):
    npzfile = np.load(infile)
    spec_corr_elec = npzfile['corrected_electrons'] #unpack seedpixel distribution
    spec_corr_elec = spec_corr_elec[np.isfinite(spec_corr_elec)] #remove nan values
    return spec_corr_elec


#read in spectrum with pixel position information
def get_corrected_spectrum_in_electrons_pix(infile):
    npzfile = np.load(infile)
    spec_corr_elec = npzfile['corrected_electrons_pix'] #unpack seedpixel distribution including pixel information
    return spec_corr_elec


#perform threshold cut
def threshold_cut(spec_corr_elec_pix, thrmap, target_thr, thr_cut_electrons):

    #Define output list
    spec_corr_elec_thrcut = []

    #Define cut values
    thrmax = target_thr + thr_cut_electrons
    thrmin = target_thr - thr_cut_electrons

    #Load threshold map
    thrmap_npz = np.load(thrmap)
    thrmap = thrmap_npz['thresholds'] #Attention: thrmap is parametrized in [row, col], not [col, row] (!)
    print(thrmap)

    #perform cut
    #el =[[col, row, thr], ..., [col, row, thr]]
    for el in spec_corr_elec_pix:
        print(int(el[1]), int(el[0]))
        thr = thrmap[int(el[1]), int(el[0])]
        if not (thr < thrmin) and not (thr > thrmax) and not np.isnan(el[2]):
            spec_corr_elec_thrcut.append(el[2])

    return spec_corr_elec_thrcut


#create histogram
def create_histogram(spectrum, nbins, xmax):
    data_entries, bins = np.histogram(spectrum, bins=nbins, range=(0,xmax), density=True)
    bincenters = np.array([0.5 * (bins[i] + bins[i+1]) for i in range(len(bins)-1)])
    return data_entries, bins, bincenters


#fit and plot histogram
def fit_hist(data_entries, bins, bincenters, xmax, nbins, fname, outdir, quiet):
    #Plot spectrum
    plt.bar(bincenters, data_entries, width=bins[1]-bins[0], color='navy', label=r'Histogram entries')

    # Estimate prefit parameters
    max_bin = np.where(data_entries == data_entries.max())
    mpv = bincenters[int(max_bin[0])] #take position of the maximum bin
    eta = 1 #fit quite stable here
    sigma = 0.2 * mpv
    A = np.max(data_entries/len(data_entries)) #since reletive frequency is plotted

    #Define Fitting range
    fit_start = mpv - 3 * sigma
    fit_end = mpv + 20 * sigma
    fit_msk=(bincenters > fit_start) & (bincenters < fit_end)

    print("[INFO] Prefit parameters:")
    print("     | MPV: ", mpv)
    print("     | eta: ", eta)
    print("     | sigma: ", sigma)
    print("     | A: ", A)

    # Fit with constrains
    coeff, pcov = curve_fit(pylandau.langau, bincenters[fit_msk], data_entries[fit_msk], absolute_sigma=True, p0=(mpv, eta, sigma, A), bounds=(0, 1000))
    
    print("[INFO] Fit range:")
    print("     | Start: ", fit_start)
    print("     | End: ", fit_end)
    print("[INFO] Fit parameters:")
    print("     | MPV: ", coeff[0])
    print("     | eta: ", coeff[1])
    print("     | sigma: ", coeff[2])
    print("     | A: ", coeff[3])

    #Plot Fit
    plt.plot(bincenters[fit_msk], pylandau.langau(bincenters[fit_msk], *coeff), "-", color="red")
    plot_fit_params(0.68, 0.9, coeff)
    plt.ylabel(f"Relative frequency per {xmax/nbins:.1f}"+"e$^{-}$ bin")
    plt.xlabel("Calibrated seedpixel ToT (e$^{-}$)")
    plt.xlim([0, xmax])
    plt.savefig(os.path.join(outdir, fname), bbox_inches = 'tight', dpi = 600)
    if not (quiet): plt.show()

    return coeff, pcov


def plot_fit_params(x, y, coeff):
    plt.text(x, y,     '\n'.join([
    '$\\bf{Fit\:parameters:}$',
    'MPV: %s'%round(coeff[0],2),
    '$\eta$: %s'%round(coeff[1],2),
    '$\sigma$: %s'%round(coeff[2],2),
    'A: %s'%round(coeff[3],4)
    ]),
    fontsize=10,
    ha='left', va='top',
    transform=plt.gca().transAxes)
    return 0

#====================
#
# MAIN
#
#====================

if __name__ == "__main__":

  # Read commandline args
  parser = argparse.ArgumentParser("Script to fit single landau spectrum and obtain MPV. Contains possibility to cut on specific threshold value.",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument('totspectrum', type=str, help="ToT spectrum to fit (.npz file created by landau_creator.py)")
  parser.add_argument('--outdir', type=str, default="./plots")
  parser.add_argument('-q', '--quiet', action = 'store_true', help= "Do not plot control plots")
  parser.add_argument('-sp', '--save_params', action = 'store_true', help= "Save fit parameters")
  parser.add_argument('--xmax', type=int, default=3000, help="maximum x value for plot")
  parser.add_argument('--nbins', type=int, default=100, help="number of bins for hist")
  parser.add_argument('--thrmap', type=str, help=" Threshold map created by thresholdana.py in order to cut on exact thresholds.")
  parser.add_argument('--target_thr', type=int, help="Targeted number of electrons", default=100)
  parser.add_argument('--thr_cut_electrons', type=int, help="Electron cut (e.g 5 for +- 5 electron cut)", default=5)

  args = parser.parse_args()

  print("[INFO] Starting Landau Fitter")

  if not (args.thrmap): #no thrshold cut will be performed:
    #upack seedpixel distribution
    spec_corr_elec = get_corrected_spectrum_in_electrons(args.totspectrum)

    #create numpy histogram
    data_entries, bins, bincenters = create_histogram(spec_corr_elec, args.nbins, args.xmax)

    #plot histogram
    coeff, pcov = fit_hist(data_entries, bins, bincenters, args.xmax, args.nbins, "landau_spectrum", args.outdir, args.quiet)

  else:
    spec_cor_elec_pix = get_corrected_spectrum_in_electrons_pix(args.totspectrum)

    spec_corr_elec_thrcut = threshold_cut(spec_cor_elec_pix, args.thrmap, args.target_thr, args.thr_cut_electrons)
    
    print("[INFO] Entries before thrcut:", len(spec_cor_elec_pix))
    print("[INFO] Entries after thrcut:", len(spec_corr_elec_thrcut))

    #create numpy histogram
    data_entries, bins, bincenters = create_histogram(spec_corr_elec_thrcut, args.nbins, args.xmax)

    #plot histogram
    coeff, pcov = fit_hist(data_entries, bins, bincenters, args.xmax, args.nbins, "landau_spectrum_thrcut", args.outdir, args.quiet)

  #Save fit parameters for further processing:
  if (args.save_params): np.savez(os.path.join(args.outdir, "landau_fit_parameters.npz"), coeff=coeff, pcov=pcov)

  print("[INFO] Landau fitter finished. Thank you for using landau_fiiter.py!")