#!/usr/bin/env python3

__author__ = "Roberto Russo"
__maintainer__ = "Roberto Russo"
__email__ = "r.russo@cern.ch"
__status__ = "Development"

import logging, argparse, os, re
import json
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from math import sqrt
from glob import glob
from tqdm import tqdm
from lmfit import Model
import analysis_utils as au


mpl.rc('xtick', labelsize=15)
mpl.rc('ytick', labelsize=15)
with open("okabe_ito.json") as jf:
    colors = json.load(jf)
mpl.rcParams['axes.prop_cycle'] = (
    mpl.cycler('color', [colors["black"], colors["blue"], colors["reddish purple"], colors["bluish green"], colors["orange"], colors["sky blue"], colors["vermillion"], colors["yellow"], colors["grey"]]) +
    mpl.cycler('marker', ["s","v","o","D","h",">","*","P","p"])
    )


def pol1(x, m, q):
    return m*x+q


def straight_line_from_origin(x, m):
    return m*x


def fill_vh_scan_plots(vh, amplitude_mean, amplitude_std, falltimetf_mean, falltimetf_std, falltimetn_mean, falltimetn_std, noise_rms, noise_rms_error, channel, channel_to_pixel_dictionary,\
    vbb, axis1, axis2, axis3, axis4, axis5, axis6, axis7):
    x = int((int(channel)-1)/2)
    y = int((int(channel)-1)%2)
    # amplitude
    axis1[x,y].errorbar(vh,amplitude_mean,amplitude_std,label="V$_{sub}$=-%s V"%(vbb),elinewidth=1.3,capsize=1.5,alpha=1.0)
    axis1[x,y].set_title(f"{channel_to_pixel_dictionary[channel]}")
    # amplitude/Vh
    axis2[x,y].errorbar(vh,amplitude_mean/vh,amplitude_std/vh,label="V$_{sub}$=-%s V"%(vbb),elinewidth=1.3,capsize=1.5,alpha=1.0)
    axis2[x,y].set_title(f"{channel_to_pixel_dictionary[channel]}")
    # falltime 10% - 50%
    axis3[x,y].errorbar(vh,falltimetf_mean,falltimetf_std,label="V$_{sub}$=-%s V"%vbb, linewidth=1.3,capsize=1.5)
    axis3[x,y].set_title(f"{channel_to_pixel_dictionary[channel]}")
    # falltime 10% - 90%
    axis4[x,y].errorbar(vh,falltimetn_mean,falltimetn_std,label="V$_{sub}$=-%s V"%vbb, elinewidth=1.3,capsize=1.5)
    axis4[x,y].set_title(f"{channel_to_pixel_dictionary[channel]}")
    # dV/dt 10%-50%
    dvdt_tf_mean = 0.4*amplitude_mean/falltimetf_mean
    dvdt_tf_rms = dvdt_tf_mean*np.sqrt((amplitude_std/amplitude_mean)**2+(falltimetf_std/falltimetf_mean)**2)  # error propagation
    axis5[x,y].errorbar(vh,dvdt_tf_mean,dvdt_tf_rms,label="V$_{sub}$=-%s V"%vbb, elinewidth=1.3,capsize=1.5)
    axis5[x,y].set_title(f"{channel_to_pixel_dictionary[channel]}")
    # dV/dt 10%-90%
    dvdt_tn_mean = 0.8*amplitude_mean/falltimetn_mean
    dvdt_tn_rms = dvdt_tn_mean*np.sqrt((amplitude_std/amplitude_mean)**2+(falltimetn_std/falltimetn_mean)**2)  # error propagation
    axis6[x,y].errorbar(vh,dvdt_tn_mean,dvdt_tn_rms,label="V$_{sub}$=-%s V"%vbb, elinewidth=1.3,capsize=1.5)
    axis6[x,y].set_title(f"{channel_to_pixel_dictionary[channel]}")
    # noise
    axis7[x,y].errorbar(vh,noise_rms,noise_rms_error,label="V$_{sub}$=-%s V"%vbb, elinewidth=1.3,capsize=1.5)
    axis7[x,y].set_title(f"{channel_to_pixel_dictionary[channel]}")


def save_vh_scan_plots(figure1, axis1, figure2, axis2, figure3, axis3, figure4, axis4, figure5, axis5, figure6, axis6, figure7, axis7, amplitude_output_path, falltime_output_path, noise_output_path, args):
    for ax in axis1.flat:
        ax.grid()
        ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(100))
        ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(1))
        ylow = -1
        yhigh = 101
        if args.gain_calibration:
            yhigh = 121
        ax.set_ylim(ylow,yhigh)
        ax.legend(ncol=2)
    for ax in axis2.flat:
        ax.grid()
        ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(100))
        ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(0.01))
        ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(0.001))
        ylow = -0.001
        yhigh = 0.065
        if args.gain_calibration:
            yhigh = 0.101
        ax.set_ylim(ylow,yhigh)
        ax.legend(ncol=3)
    for ax in axis3.flat:
        ax.grid()
        ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(100))
        ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(20))
        ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(5))
        ax.set_ylim(49,161)
        ax.legend(ncol=2)
    for ax in axis4.flat:
        ax.grid()
        ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(100))
        ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(20))
        ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(5))
        ax.set_ylim(99,351)
        ax.legend(ncol=2)
    for ax in axis5.flat:
        ax.grid()
        ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(100))
        ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(0.02))
        ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(0.01))
        yhigh = 0.351
        if args.gain_calibration:
            yhigh = 0.441
        ax.set_ylim(-0.001,yhigh)
        ax.legend(ncol=2)
    for ax in axis6.flat:
        ax.grid()
        ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(100))
        ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(0.02))
        ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(0.01))
        yhigh = 0.351
        if args.gain_calibration:
            yhigh = 0.441
        ax.set_ylim(-0.001,yhigh)
        ax.legend(ncol=2)
    for ax in axis7.flat:
        ax.grid()
        ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(100))
        ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(0.5))
        ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(0.1))
        ax.set_ylim(-0.01,3.01)
        ax.legend(ncol=2)
    figure1.text(0.5, 0.05, 'V$_{h}$ (mV)', ha='center', va='center', rotation='horizontal', fontsize=15)
    figure1.text(0.08, 0.5, 'Signal amplitude (mV)', ha='center', va='center', rotation='vertical', fontsize=15)
    figure1.suptitle('Signal amplitude', fontsize=16)
    figure1.savefig(os.path.join(amplitude_output_path, "Signal_amplitude.png"), bbox_inches='tight', pad_inches=0.1)
    plt.close(figure1)
    figure2.text(0.5, 0.05, 'V$_{h}$ (mV)', ha='center', va='center', rotation='horizontal', fontsize=15)
    figure2.text(0.08, 0.5, '$\dfrac{Signal \\ amplitude}{V_h}$ (-)', ha='center', va='center', rotation='vertical', fontsize=15)
    figure2.suptitle('Output/Input signal amplitude ratio', fontsize=16)
    figure2.savefig(os.path.join(amplitude_output_path, "Output_input_signal_ratio.png"), bbox_inches='tight', pad_inches=0.1)
    plt.close(figure2)
    figure3.text(0.5, 0.05, 'V$_{h}$ (mV)', ha='center', va='center', rotation='horizontal', fontsize=15)
    figure3.text(0.08, 0.5, 'Falltime (ps)', ha='center', va='center', rotation='vertical', fontsize=15)
    figure3.suptitle(r'Falltime 10%-50%', fontsize=16)
    figure3.savefig(os.path.join(falltime_output_path, "Falltime_10_50.png"), bbox_inches='tight', pad_inches=0.1)
    plt.close(figure3)
    figure4.text(0.5, 0.05, 'V$_{h}$ (mV)', ha='center', va='center', rotation='horizontal', fontsize=15)
    figure4.text(0.08, 0.5, 'Falltime (ps)', ha='center', va='center', rotation='vertical', fontsize=15)
    figure4.suptitle(r'Falltime 10%-90%', fontsize=16)
    figure4.savefig(os.path.join(falltime_output_path, "Falltime_10_90.png"), bbox_inches='tight', pad_inches=0.1)
    plt.close(figure4)
    figure5.text(0.5, 0.05, 'V$_{h}$ (mV)', ha='center', va='center', rotation='horizontal', fontsize=15)
    figure5.text(0.08, 0.5, r'$\dfrac{dV}{dt}$ ($\dfrac{mV}{ps}$)', ha='center', va='center', rotation='vertical', fontsize=15)
    figure5.suptitle(r'$\dfrac{dV}{dt}$ 10%-50%', fontsize=16)
    figure5.savefig(os.path.join(falltime_output_path, "dV_dt_10_50.png"), bbox_inches='tight', pad_inches=0.1)
    plt.close(figure5)
    figure6.text(0.5, 0.05, 'V$_{h}$ (mV)', ha='center', va='center', rotation='horizontal', fontsize=15)
    figure6.text(0.08, 0.5, r'$\dfrac{dV}{dt}$ ($\dfrac{mV}{ps}$)', ha='center', va='center', rotation='vertical', fontsize=15)
    figure6.suptitle(r'$\dfrac{dV}{dt}$ 10%-90%', fontsize=16)
    figure6.savefig(os.path.join(falltime_output_path, "dV_dt_10_90.png"), bbox_inches='tight', pad_inches=0.1)
    plt.close(figure6)
    figure7.text(0.5, 0.05, 'V$_{h}$ (mV)', ha='center', va='center', rotation='horizontal', fontsize=15)
    figure7.text(0.08, 0.5, 'Noise RMS (mV)', ha='center', va='center', rotation='vertical', fontsize=15)
    figure7.suptitle('Noise RMS', fontsize=16)
    figure7.savefig(os.path.join(noise_output_path, "Noise_RMS.png"), bbox_inches='tight', pad_inches=0.1)
    plt.close(figure7)


def fit_parameter_plots(vbb_array, fit_parameters_dict, pixel_connections_dict, figure8, axis8, figure9, axis9, output_path):
    m_wo_origin_matrix = np.zeros((len(pixel_connections_dict.keys()), len(vbb_array)), dtype=float)
    m_wo_origin_error_matrix = np.zeros((len(pixel_connections_dict.keys()), len(vbb_array)), dtype=float)
    q_wo_origin_matrix = np.zeros((len(pixel_connections_dict.keys()), len(vbb_array)), dtype=float)
    q_wo_origin_error_matrix = np.zeros((len(pixel_connections_dict.keys()), len(vbb_array)), dtype=float)
    m_w_origin_matrix = np.zeros((len(pixel_connections_dict.keys()), len(vbb_array)), dtype=float)
    m_w_origin_error_matrix = np.zeros((len(pixel_connections_dict.keys()), len(vbb_array)), dtype=float)
    for j, vbb in enumerate(vbb_array):
        for i, channel in enumerate(fit_parameters_dict[f"{vbb}"].keys()):
            m_wo_origin_matrix[i, j] = fit_parameters_dict[f"{vbb}"][channel]["fit_w/o_origin"]["m"]
            m_wo_origin_error_matrix[i, j] = fit_parameters_dict[f"{vbb}"][channel]["fit_w/o_origin"]["m_err"]
            q_wo_origin_matrix[i, j] = fit_parameters_dict[f"{vbb}"][channel]["fit_w/o_origin"]["q"]
            q_wo_origin_error_matrix[i, j] = fit_parameters_dict[f"{vbb}"][channel]["fit_w/o_origin"]["q_err"]
            m_w_origin_matrix[i, j] = fit_parameters_dict[f"{vbb}"][channel]["fit_w/_origin"]["m"]
            m_w_origin_error_matrix[i, j] = fit_parameters_dict[f"{vbb}"][channel]["fit_w/_origin"]["m_err"]
    for idx, channel in enumerate(pixel_connections_dict.keys()):
        x = int((int(channel)-1)/2)
        y = int((int(channel)-1)%2)
        # line slope
        axis8[x,y].errorbar(vbb_array,m_wo_origin_matrix[idx, :],m_wo_origin_error_matrix[idx, :],marker='s',elinewidth=1.3,capsize=1.5,label="Intercept free parameter")
        axis8[x,y].errorbar(vbb_array,m_w_origin_matrix[idx, :],m_w_origin_error_matrix[idx, :],marker='s',elinewidth=1.3,capsize=1.5,label="Forced from origin")
        axis8[x,y].set_title(f"{pixel_connections_dict[channel]}")
        axis8[x,y].xaxis.set_ticks(vbb_array)
        axis8[x,y].grid()
        axis8[x,y].legend(fontsize=15, loc='lower right')
        # line intercept
        axis9[x,y].errorbar(vbb_array,q_wo_origin_matrix[idx, :],q_wo_origin_error_matrix[idx, :],marker='s',elinewidth=1.3,capsize=1.5)
        axis9[x,y].set_title(f"{pixel_connections_dict[channel]}")
        axis9[x,y].xaxis.set_ticks(vbb_array)
        axis9[x,y].grid()
    figure8.text(0.5, 0.05, 'V$_{sub}$ (V)', ha='center', va='center', rotation='horizontal', fontsize=15)
    figure8.text(0.07, 0.5, 'Fit slope $m$ (-)', ha='center', va='center', rotation='vertical', fontsize=15)
    figure8.suptitle('m fit parameter', fontsize=16)
    figure8.savefig(os.path.join(output_path, "Fit_slope_parameter.png"), bbox_inches='tight', pad_inches=0.1)
    plt.close(figure8)
    figure9.text(0.5, 0.05, 'V$_{sub}$ (V)', ha='center', va='center', rotation='horizontal', fontsize=15)
    figure9.text(0.07, 0.5, 'Fit intercept $q$ (mV)', ha='center', va='center', rotation='vertical', fontsize=15)
    figure9.suptitle(r'q fit parameter', fontsize=16)
    figure9.savefig(os.path.join(output_path, "Fit_intercept_parameter.png"), bbox_inches='tight', pad_inches=0.1)
    plt.close(figure9)


def vh_scan_analysis(args):
    fig1, ax1, fig2, ax2, fig3, ax3, fig4, ax4, fig5, ax5, fig6, ax6, fig7, ax7, fig8, ax8, fig9, ax9, _, _, _, _, _, _ = au.define_figures()
    scanned_vbb = au.list_vbb_dir(args.data_path)
    scanned_vbb.sort()
    vbb_array = []
    pixel_amplitude_fit_dict = {}
    for vbbpath in tqdm(scanned_vbb):
        vbb = float(re.findall(r"vbb_(\d.\d)", vbbpath)[0])
        pixel_amplitude_fit_dict[f'{vbb}'] = {}
        data = pd.read_csv(f"{vbbpath}/vh_scan_statistics{args.file_suffix}.csv", sep="|")
        for ch in args.pixel_connections.keys():
            pixel_amplitude_fit_dict[f'{vbb}'][f'{ch}'] = {}
            pixel_amplitude_fit_dict[f'{vbb}'][f'{ch}']["fit_w/o_origin"] = {}
            pixel_amplitude_fit_dict[f'{vbb}'][f'{ch}']["fit_w/_origin"] = {}
            data_filtered = data.query(f"ch=={int(ch)}")
            data_filtered = data_filtered.sort_values(by='vh', ascending=True)
            vh = data_filtered['vh'].values.astype(int)
            ampl_mean = data_filtered['amplitude_mean'].values.astype(float)
            ampl_std = data_filtered['amplitude_rms'].values.astype(float)
            ft_tf_mean = data_filtered['falltime1050_mean'].values.astype(float)
            ft_tf_std = data_filtered['falltime1050_rms'].values.astype(float)
            ft_tn_mean = data_filtered['falltime1090_mean'].values.astype(float)
            ft_tn_std = data_filtered['falltime1090_rms'].values.astype(float)
            noise_rms = data_filtered['baseline_noise_rms'].values.astype(float)
            noise_rms_error = data_filtered['baseline_noise_rms_error'].values.astype(float)
            # fit amplitude curves at varying vh
            data_fit = data_filtered
            xdata = data_fit['vh'].values.astype(int)
            ydata = data_fit['amplitude_mean'].values.astype(float)
            ydata_err = data_fit['amplitude_mean_error'].values.astype(float)
            # straight line fit with intercept as a parameter
            mod_wo_origin = Model(pol1)
            mod_wo_origin.set_param_hint('m', value=0.02)
            mod_wo_origin.set_param_hint('q', value=0)
            pars_wo_origin = mod_wo_origin.make_params()
            result_wo_origin = mod_wo_origin.fit(ydata, x=xdata, params=pars_wo_origin, weights=1/ydata_err)
            pixel_amplitude_fit_dict[f'{vbb}'][f'{ch}']["fit_w/o_origin"]['m'] = result_wo_origin.params['m'].value
            pixel_amplitude_fit_dict[f'{vbb}'][f'{ch}']["fit_w/o_origin"]['m_err'] = result_wo_origin.params['m'].stderr
            pixel_amplitude_fit_dict[f'{vbb}'][f'{ch}']["fit_w/o_origin"]['q'] = result_wo_origin.params['q'].value
            pixel_amplitude_fit_dict[f'{vbb}'][f'{ch}']["fit_w/o_origin"]['q_err'] = result_wo_origin.params['q'].stderr
            pixel_amplitude_fit_dict[f'{vbb}'][f'{ch}']["fit_w/o_origin"]['chi2'] = result_wo_origin.chisqr
            pixel_amplitude_fit_dict[f'{vbb}'][f'{ch}']["fit_w/o_origin"]['n_deg_free'] = result_wo_origin.nfree
            pixel_amplitude_fit_dict[f'{vbb}'][f'{ch}']["fit_w/o_origin"]['redchi2'] = result_wo_origin.redchi
            # straight line fit passing from origin
            mod_w_origin = Model(straight_line_from_origin)
            mod_w_origin.set_param_hint('m', value=0.02)
            pars_w_origin = mod_w_origin.make_params()
            result_w_origin = mod_w_origin.fit(ydata, x=xdata, params=pars_w_origin, weights=1/ydata_err)
            pixel_amplitude_fit_dict[f'{vbb}'][f'{ch}']["fit_w/_origin"]['m'] = result_w_origin.params['m'].value
            pixel_amplitude_fit_dict[f'{vbb}'][f'{ch}']["fit_w/_origin"]['m_err'] = result_w_origin.params['m'].stderr
            pixel_amplitude_fit_dict[f'{vbb}'][f'{ch}']["fit_w/_origin"]['chi2'] = result_w_origin.chisqr
            pixel_amplitude_fit_dict[f'{vbb}'][f'{ch}']["fit_w/_origin"]['n_deg_free'] = result_w_origin.nfree
            pixel_amplitude_fit_dict[f'{vbb}'][f'{ch}']["fit_w/_origin"]['redchi2'] = result_w_origin.redchi            
            fill_vh_scan_plots(vh, ampl_mean, ampl_std, ft_tf_mean, ft_tf_std, ft_tn_mean, ft_tn_std, noise_rms, noise_rms_error, ch, args.pixel_connections,\
                vbb, ax1, ax2, ax3, ax4, ax5, ax6, ax7)
        vbb_array.append(vbb)
    amplitude_plot_path = os.path.join(args.data_path, f"amplitude_plots{args.file_suffix}")
    os.makedirs(amplitude_plot_path, exist_ok=True)
    falltime_plot_path = os.path.join(args.data_path, f"falltime_plots{args.file_suffix}")
    os.makedirs(falltime_plot_path, exist_ok=True)
    noise_plot_path = os.path.join(args.data_path, f"noise_plots{args.file_suffix}")
    os.makedirs(noise_plot_path, exist_ok=True)
    save_vh_scan_plots(fig1, ax1, fig2, ax2, fig3, ax3, fig4, ax4,  fig5, ax5, fig6, ax6, fig7, ax7, amplitude_plot_path, falltime_plot_path, noise_plot_path, args)
    with open(os.path.join(amplitude_plot_path, f"fit_parameters{args.file_suffix}.json"),'w') as file_handle:
        json.dump(pixel_amplitude_fit_dict, file_handle, indent=4)
    vbb_array = np.array(vbb_array)
    fit_parameter_plots(vbb_array, pixel_amplitude_fit_dict, args.pixel_connections, fig8, ax8, fig9, ax9, amplitude_plot_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APTS OPAMP routine for the analysis of signal amplitude and falltime at varying vh.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--data_path', '-d', help='Directory for input files.')
    parser.add_argument('--pixel_connections', type=dict, default={"1": "J5", "2": "J6", "3": "J9", "4": "J10"}, help='Dictionary with scope channels and connected pixels.')
    parser.add_argument('--gain_calibration', '-g', action="store_true", help='Analyze gain calibrated data.')
    args = parser.parse_args()
    try:
        args.file_suffix = ""
        if args.gain_calibration:
            args.file_suffix = "_calibrated"
        vh_scan_analysis(args)
    except KeyboardInterrupt:
        logging.info('User stopped.')
    except Exception as e:
        logging.exception(e)
        logging.fatal('Terminating!')
