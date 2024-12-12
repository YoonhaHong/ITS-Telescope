#!/usr/bin/env python3

__author__ = "Roberto Russo"
__maintainer__ = "Roberto Russo"
__email__ = "r.russo@cern.ch"
__status__ = "Development"

import logging, argparse, os, re, json
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from glob import glob
from math import sqrt, pi, ceil, floor
from lmfit import Model
from tqdm import tqdm
import analysis_utils as au


with open("okabe_ito.json") as jf:
    colors = json.load(jf)
mpl.rcParams['axes.prop_cycle'] = (
    mpl.cycler('color', [colors["black"], colors["blue"], colors["reddish purple"], colors["bluish green"], colors["orange"], colors["sky blue"], colors["vermillion"], colors["yellow"], colors["grey"]]) +
    mpl.cycler('marker', ["s","v","o","D","h",">","*","P","p"])
    )
pulse_in_coupling_capacitance = 202E-18  # pulsing capacitance resulting from dedicated measurement (in F)


def make_jitter_dataframe():
    dataframe = pd.DataFrame(
        {
            'vbb': pd.Series([], dtype='float'),           # Reverse bias voltage (V)
            'pixel_couple': pd.Series([], dtype='str'),    # couple of analyzed pixels
            'vh': pd.Series([], dtype='int'),              # Vh (mV)
            'CFD': pd.Series([], dtype='int'),             # amplitude fraction (%)
            'mean': pd.Series([], dtype='float'),          # distribution sample mean (ps)
            'mean_error': pd.Series([], dtype='float'),    # distribution sample mean error (ps)
            'rms': pd.Series([], dtype='float'),           # distribution sample rms (ps)
            'rms_error': pd.Series([], dtype='float'),     # distribution sample rms error (ps)
            'mu': pd.Series([], dtype='float'),            # 3-sigma gaussian fit mu (ps) - if fit fails, use sample mean
            'mu_error': pd.Series([], dtype='float'),      # 3-sigma gaussian fit mu error (ps) - if fit fails, use standard mean error
            'sigma': pd.Series([], dtype='float'),         # 3-sigma gaussian fit sigma (ps) - if fit fails, use sample rms
            'sigma_error': pd.Series([], dtype='float'),   # 3-sigma gaussian fit sigma error (ps) - if fit fails, use standard error of the standard deviation
        }
    )
    return dataframe


def gaussian(x, a, b, c):
    return a/(sqrt(2*pi)*c) * np.exp(-np.power(x - b, 2) / (2 * np.power(c, 2)))  # normalized gaussian


def fit_histogram(data, bin_width):
    mu = np.mean(data)
    sigma = np.std(data)
    hist_entries, bin_edges = np.histogram(data[(data > (mu-6*sigma)) & (data < (mu+6*sigma))],\
        bins=np.arange(start=ceil((mu-6*sigma)), stop=floor((mu+6*sigma)), step=bin_width), density=False)
    bin_centers = np.array([0.5 * (bin_edges[i] + bin_edges[i+1]) for i in range(len(bin_edges)-1)])
    iteration = 0
    amplitude = np.max(hist_entries)
    result = None  # initialise fit result
    xfit = None    # initialise fit range
    while True:
        idx_fit = np.where((bin_centers >= mu-3*sigma) & (bin_centers <= mu+3*sigma))[0]
        xfit = bin_centers[idx_fit]
        yfit = hist_entries[idx_fit]
        model = Model(gaussian)
        model.set_param_hint('a', value=amplitude)
        model.set_param_hint('b', value=mu)
        model.set_param_hint('c', value=sigma)
        pars = model.make_params()
        fit_counting_error = np.array([np.sqrt(i) for i in yfit])  # it is used for the correct evaluation of fit residuals
        fit_counting_error[fit_counting_error == 0] = 0.01  # force counting statistics error to 0.01 for bins with no entries
        fit_weights = 1/fit_counting_error
        try:
            result = model.fit(yfit, x=xfit, weights=fit_weights, params=pars)
            if abs(result.params['c'].value - sigma) < 0.001:  # if difference between guess sigma and fit sigma is less than 1 ps, stop iteration
                break
            iteration += 1
            if iteration > 100:
                break
            amplitude = result.params['a'].value
            mu = result.params['b'].value
            sigma = result.params['c'].value
        except TypeError as te:
            print("The time residuals gaussian fit failed!")
            print(te)
            break
    return bin_centers, hist_entries, result, xfit


def plot_histogram(data, binsctr, values, fit_points, fit_params, axis, bin_width, pixels_couple, CFD, vbb, vh):
    mpl.rc('xtick', labelsize=24)
    mpl.rc('ytick', labelsize=24)
    axis.set_title("Time residuals pixels %s, CFD %d %%, V$_{sub}$ = %.1f V, V$_h$ = %d mV" % (pixels_couple, CFD, vbb, vh), fontsize=24)
    axis.hist(binsctr, bins=len(binsctr), weights=values, fc=(0.8705882352941177, 0.5607843137254902, 0.0196078431372549, 0.5), edgecolor="#de8f05", histtype='stepfilled', density=False,\
        linewidth=2, linestyle="--", label="Time jitter")
    props = dict(boxstyle='square', facecolor='white', alpha=1.0, edgecolor='black', zorder=10)
    textstr = '\n'.join((
        'entries = %d' % (data.shape[0]),
        'mean = %d \u00B1 %d ps' % (round(np.mean(data)), round(au.compute_standard_mean_error(data))),
        'RMS = %d \u00B1 %d ps' % (round(np.std(data)), round(au.compute_standard_error_of_standard_deviation(data))),
    ))
    if (not (fit_params is None)) and (len(fit_points) > 0):
        axis.plot(fit_points, gaussian(fit_points, fit_params.params['a'].value, fit_params.params['b'].value, fit_params.params['c'].value), linestyle='-', linewidth=3.5, color='black', label='Gaussian fit')
        outside_fit_range_left = binsctr[(binsctr <= fit_points[0])]
        outside_fit_range_right = binsctr[(binsctr >= fit_points[-1])]
        axis.plot(outside_fit_range_left, gaussian(outside_fit_range_left, fit_params.params['a'].value, fit_params.params['b'].value, fit_params.params['c'].value),\
            linestyle='--', linewidth=3.5, color='black', label='Gaussian fit extrapolation')
        axis.plot(outside_fit_range_right, gaussian(outside_fit_range_right, fit_params.params['a'].value, fit_params.params['b'].value, fit_params.params['c'].value),\
            linestyle='--', linewidth=3.5, color='black')
        try:
            textstr = '\n'.join((  # statistical errors are expressed at 95% statistical significance
                textstr,
                'fit \u03BC = %d \u00B1 %d ps' % (round(fit_params.params['b'].value), round(fit_params.params['b'].stderr)),
                'fit \u03C3 = %d \u00B1 %d ps' % (round(fit_params.params['c'].value), round(fit_params.params['c'].stderr)),
                'fit \u03C7$^2_{ndof}$ = %.3f' % (round(fit_params.redchi, 3)),
            ))
        except TypeError as te:
            print(f'{te}: the standard error of one or more of the fit parameters cannot be computed')
    axis.text(0.015, 0.925, textstr, transform=axis.transAxes, fontsize=24, verticalalignment='top', bbox=props, backgroundcolor='white')
    axis.grid()
    axis.legend(fontsize=24, loc='upper right')
    axis.set_xlabel(f"{pixels_couple} CFD {CFD}% signal time (ps)", ha='center', va='center', fontsize=24, fontweight='normal', labelpad=30)
    axis.set_ylabel(f"Entries (per {bin_width} ps)", ha='center', va='center', rotation='vertical', fontsize=24, fontweight='normal', labelpad=30)


def jitter_analysis(args):
    scanned_vbb = au.list_vbb_dir(args.data_path)
    scanned_vbb.sort()
    fig, axs = plt.subplots(figsize=(21,10))
    plt.subplots_adjust(left=0.01,right=0.76,top=0.95)
    df = make_jitter_dataframe()
    vbb_array = []
    pixel_couple_array = []
    vh_array = []
    CFD_array = []
    jitter_distribution_mean = []
    jitter_distribution_mean_error = []
    jitter_distribution_rms = []
    jitter_distribution_rms_error = []
    jitter_distribution_mu = []
    jitter_distribution_mu_error = []
    jitter_distribution_sigma = []
    jitter_distribution_sigma_error = []
    for vbbpath in tqdm(scanned_vbb, desc="Vbb"):
        vbb = float(re.findall(r"vbb_(\d.\d)", vbbpath)[0])
        time_jitter_dir = os.path.join(vbbpath, f"time_jitter{args.file_suffix}")
        pixels_couple = au.list_vbb_dir(time_jitter_dir)
        for pixels_couple_path in tqdm(pixels_couple, leave=False, desc="Pixels couple"):
            pxs = re.findall(r"(J\d+-J\d+)", pixels_couple_path)[0]
            plot_dir = os.path.join(pixels_couple_path, "plots")
            os.makedirs(plot_dir, exist_ok=True)
            for jitter_array_file in tqdm(glob(f"{pixels_couple_path}/vh*.npy"), leave=False, desc="Vh"):
                vh = int(re.findall(f"vh(\d+).npy", jitter_array_file)[0])
                jitter_ndarray = np.load(jitter_array_file)
                vbb_array.extend([vbb]*9)
                pixel_couple_array.extend([pxs]*9)
                vh_array.extend([vh]*9)
                CFD_array.extend([10, 20, 30, 40, 50, 60, 70, 80, 90])
                for i, CFD in enumerate([10, 20, 30, 40, 50, 60, 70, 80, 90]):
                    jitter_array = jitter_ndarray[i, :]
                    hist_bin_centers, hist_values, gaus_fit_params, fit_interval = fit_histogram(data=jitter_array, bin_width=args.bin_width)
                    plot_histogram(jitter_array, hist_bin_centers, hist_values, fit_interval, gaus_fit_params, axs, args.bin_width, pxs, CFD, vbb, vh)
                    fig.savefig(os.path.join(f"{plot_dir}", f"vh{vh}_CFD{CFD}.png"), bbox_inches='tight', pad_inches=0.1)
                    axs.clear()
                    jitter_distribution_mean.append(round(np.mean(jitter_array),3))
                    jitter_distribution_mean_error.append(round(1.96*au.compute_standard_mean_error(jitter_array),3))
                    jitter_distribution_rms.append(round(np.std(jitter_array),3))
                    jitter_distribution_rms_error.append(round(1.96*au.compute_standard_error_of_standard_deviation(jitter_array),3))
                    mu = round(gaus_fit_params.params['b'].value,3) if (gaus_fit_params.params['b'].stderr is not None and gaus_fit_params.redchi <= 5) else\
                        round(np.mean(au.three_sigma_quantiles_dataset(jitter_array)),3)  # if fit fails, use 0.997-quantile sample mean
                    jitter_distribution_mu.append(mu)
                    mu_error = round(1.96*gaus_fit_params.params['b'].stderr,3) if (gaus_fit_params.params['b'].stderr is not None and gaus_fit_params.redchi <= 5) else\
                        round(1.96*au.compute_standard_mean_error(au.three_sigma_quantiles_dataset(jitter_array)),3)  # if fit fails, use 0.997-quantile Standard Mean Error (SME)
                    jitter_distribution_mu_error.append(mu_error)
                    sigma = round(gaus_fit_params.params['c'].value,3) if (gaus_fit_params.params['c'].stderr is not None and gaus_fit_params.redchi <= 5) else\
                        round(np.std(au.three_sigma_quantiles_dataset(jitter_array)),3)  # if fit fails, use 0.997-quantile sample rms
                    jitter_distribution_sigma.append(sigma)
                    sigma_error = round(1.96*gaus_fit_params.params['c'].stderr,3) if (gaus_fit_params.params['c'].stderr is not None and gaus_fit_params.redchi <= 5) else\
                        round(1.96*au.compute_standard_error_of_standard_deviation(au.three_sigma_quantiles_dataset(jitter_array)),3)  # if fit fails, use 0.997-quantile standard error of sample standard deviation
                    jitter_distribution_sigma_error.append(sigma_error)
    jitter_dict = {
        'vbb': np.array(vbb_array).T,
        'pixel_couple': np.array(pixel_couple_array).T,
        'vh': np.array(vh_array).T,
        'CFD': np.array(CFD_array).T,
        'mean': np.array(jitter_distribution_mean).T,
        'mean_error': np.array(jitter_distribution_mean_error).T,
        'rms': np.array(jitter_distribution_rms).T,
        'rms_error': np.array(jitter_distribution_rms_error).T,
        'mu': np.array(jitter_distribution_mu).T,
        'mu_error': np.array(jitter_distribution_mu_error).T,
        'sigma': np.array(jitter_distribution_sigma).T,
        'sigma_error': np.array(jitter_distribution_sigma_error).T,
    }
    df = pd.concat([df, pd.DataFrame(jitter_dict)], ignore_index=True)
    df.to_csv(os.path.join(args.data_path, f"jitter_statistics{args.file_suffix}.csv"), sep='|', index=False)
    return df


def plot_jitter_curves(args, dataframe):
    mpl.rc('xtick', labelsize=24)
    mpl.rc('ytick', labelsize=24)
    fig_mean, axs_mean = plt.subplots(figsize=(21,10))
    plt.subplots_adjust(left=0.01,right=0.76,top=0.95)
    fig_jitter, axs_jitter = plt.subplots(figsize=(21,10))
    plt.subplots_adjust(left=0.01,right=0.76,top=0.95)
    axs_jitter.set_xlim(275,1225)
    axs_jitter.xaxis.set_major_locator(mpl.ticker.FixedLocator([300,  400,  500,  600,  700,  800,  900, 1000, 1100, 1200]))
    axs_jitter_charge = axs_jitter.twiny()  # add second axis with charge conversion
    axs_jitter_charge.set_xlim(axs_jitter.get_xlim()[0],axs_jitter.get_xlim()[1])
    axs_jitter_charge.set_xlabel("Charge ($\it{e^{-}}$)", fontsize=28)
    vh_ticks = axs_jitter.get_xticks()
    charge_ticks = np.array([round((pulse_in_coupling_capacitance*(tick/1000)/1.602*1E19)/10)*10 for tick in [300,  400,  500,  600,  700,  800,  900, 1000, 1100, 1200]])  # round to nearest 10 in e
    axs_jitter_charge.set_xticks(vh_ticks, labels=charge_ticks.astype(int), minor=False)
    root_plot_dir = os.path.join(args.data_path, f"jitter_curves{args.file_suffix}")
    os.makedirs(root_plot_dir, exist_ok=True)
    vbbs = dataframe['vbb'].drop_duplicates().to_numpy()
    vbbs.sort()
    CFDs = dataframe['CFD'].drop_duplicates().to_numpy()
    CFDs.sort()
    pixel_couples = dataframe['pixel_couple'].drop_duplicates().to_list()
    for pixel_couple in tqdm(pixel_couples, desc="Pixels couple plot"):
        df_pixel = dataframe.query(f"pixel_couple == '{pixel_couple}'")
        plot_dir = os.path.join(root_plot_dir, f"{pixel_couple}")
        os.makedirs(plot_dir, exist_ok=True)
        for CFD in tqdm(CFDs, leave=False, desc="CFD plot"):
            df_CFD = df_pixel.query(f"CFD == {CFD}")
            for vbb in vbbs:
                df_vbb = df_CFD.query(f"vbb == {vbb}")
                df_vbb = df_vbb.sort_values(by=f'vh', ascending=True)
                vh = df_vbb['vh'].values.astype('int')
                mean = df_vbb['mu'].values.astype('int')
                mean_error = df_vbb['mu_error'].values.astype('int')
                combined_jitter = df_vbb['sigma'].values.astype('int')
                combined_jitter_error = df_vbb['sigma_error'].values.astype('int')
                axs_mean.errorbar(vh,mean,mean_error,label="V$_{sub}$=-%.1f V"%vbb, elinewidth=1.5,capsize=6.0)
                axs_jitter.errorbar(vh,combined_jitter,combined_jitter_error,label="V$_{sub}$=-%.1f V"%vbb, elinewidth=1.5,capsize=6.0)
            # distribution mean at varying injected charge plot
            axs_mean.set_title(f"{pixel_couple} CFD {CFD}% \u0394t mean (ps)")
            axs_mean.legend(ncol=2, loc='best', fontsize=20)
            axs_mean.grid(axis='both')
            axs_mean.set_xlabel("V$_h$ (mV)", fontsize=28)
            axs_mean.set_xlim(275,1225)
            axs_mean.set_ylabel("\u0394t mean (ps)", fontsize=28)
            axs_mean.set_ylim(-51,21)
            axs_mean.xaxis.set_major_locator(mpl.ticker.FixedLocator([300,  400,  500,  600,  700,  800,  900, 1000, 1100, 1200]))
            axs_mean.yaxis.set_major_locator(mpl.ticker.MultipleLocator(5))
            axs_mean.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(1))
            fig_mean.savefig(os.path.join(f"{plot_dir}", f"deltaT_mean_{pixel_couple}_CFD{CFD}{args.file_suffix}.png"), bbox_inches='tight', pad_inches=0.1)
            axs_mean.clear()
            # distribution combined sigma (jitter) at varying injected charge plot
            axs_jitter.set_title(f"{pixel_couple} CFD {CFD}% combined jitter (ps)")
            axs_jitter.legend(ncol=2, loc='upper right', fontsize=20)
            axs_jitter.grid(axis='both')
            axs_jitter.set_xlabel("V$_h$ (mV)", fontsize=28)
            axs_jitter.set_xlim(275,1225)
            axs_jitter.set_ylabel("Combined jitter (ps)", fontsize=28)
            axs_jitter.set_ylim(0,25)
            axs_jitter.xaxis.set_major_locator(mpl.ticker.FixedLocator([300,  400,  500,  600,  700,  800,  900, 1000, 1100, 1200]))
            axs_jitter.yaxis.set_major_locator(mpl.ticker.MultipleLocator(2))
            axs_jitter.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(1))
            fig_jitter.savefig(os.path.join(f"{plot_dir}", f"combined_jitter_{pixel_couple}_CFD{CFD}{args.file_suffix}.png"), bbox_inches='tight', pad_inches=0.1)
            axs_jitter.clear()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APTS OPAMP routine to analyse time residuals of pixel couples pulsed at varying Vh.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--data_path', '-d', help='Directory for input files.')
    parser.add_argument('--gain_calibration', '-g', action="store_true", help='Analyze gain calibrated data.')
    parser.add_argument('--bin_width', '-b', default=2, help='Jitter histograms bin width (ps).')
    args = parser.parse_args()
    try:
        args.file_suffix = ""
        if args.gain_calibration:
            args.file_suffix = "_calibrated"
        if not os.path.exists(os.path.join(args.data_path, f"jitter_statistics{args.file_suffix}.csv")):
            jitter_dataframe = jitter_analysis(args)
        else:
            jitter_dataframe = pd.read_csv(os.path.join(args.data_path, f"jitter_statistics{args.file_suffix}.csv"), sep="|")
        plot_jitter_curves(args, jitter_dataframe)
    except KeyboardInterrupt:
        logging.info('User stopped.')
    except Exception as e:
        logging.exception(e)
        logging.fatal('Terminating!')
