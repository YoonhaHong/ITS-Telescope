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
from glob import glob
from scipy.interpolate import splrep, splev
import analysis_utils as au


mpl.rc('xtick', labelsize=15)
mpl.rc('ytick', labelsize=15)
with open("okabe_ito.json") as jf:
    colors = json.load(jf)
mpl.rcParams['axes.prop_cycle'] = (
    mpl.cycler('color', [colors["black"], colors["blue"], colors["reddish purple"], colors["bluish green"], colors["orange"], colors["sky blue"], colors["vermillion"], colors["yellow"], colors["grey"]]) +
    mpl.cycler('marker', ["s","v","o","D","h",">","*","P","p"])
    )


def fill_pulsing_plots(vreset, amplitude_mean, amplitude_rms, falltimetf, falltimetn, dvdt_tf, dvdt_tn, baseline_mean, baseline_rms, baseline_noise, underline_mean, underline_rms, underline_noise,\
    channel, channel_to_pixel_dictionary, vbb, axes):
    x = int((int(channel)-1)/2)
    y = int((int(channel)-1)%2)
    # amplitude mean
    axes[0][x,y].errorbar(vreset,amplitude_mean[0],amplitude_mean[1],label="V$_{sub}$=-%s V"%vbb,elinewidth=1.3,capsize=1.5)
    axes[0][x,y].set_title(f"{channel_to_pixel_dictionary[channel]}")
    # amplitude RMS
    axes[1][x,y].errorbar(vreset,amplitude_rms[0],amplitude_rms[1],label="V$_{sub}$=-%s V"%vbb,elinewidth=1.3,capsize=1.5)
    axes[1][x,y].set_title(f"{channel_to_pixel_dictionary[channel]}")
    # falltime 10%-50%
    axes[2][x,y].errorbar(vreset,falltimetf[0],falltimetf[1],label="V$_{sub}$=-%s V"%vbb,elinewidth=1.3,capsize=1.5)
    axes[2][x,y].set_title(f"{channel_to_pixel_dictionary[channel]}")
    # falltime 10%-90%
    axes[3][x,y].errorbar(vreset,falltimetn[0],falltimetn[1],label="V$_{sub}$=-%s V"%vbb,elinewidth=1.3,capsize=1.5)
    axes[3][x,y].set_title(f"{channel_to_pixel_dictionary[channel]}")
    # dv/dt computed with falltime 10%-50%
    axes[4][x,y].errorbar(vreset,dvdt_tf[0],dvdt_tf[1],label="V$_{sub}$=-%s V"%vbb,elinewidth=1.3,capsize=1.5)
    axes[4][x,y].set_title(f"{channel_to_pixel_dictionary[channel]}")
    # dv/dt computed with falltime 10%-90%
    axes[5][x,y].errorbar(vreset,dvdt_tn[0],dvdt_tn[1],label="V$_{sub}$=-%s V"%vbb,elinewidth=1.3,capsize=1.5)
    axes[5][x,y].set_title(f"{channel_to_pixel_dictionary[channel]}")
    # baseline mean
    axes[6][x,y].errorbar(vreset,baseline_mean[0],baseline_mean[1],label="V$_{sub}$=-%s V"%vbb,elinewidth=1.3,capsize=1.5)
    axes[6][x,y].set_title(f"{channel_to_pixel_dictionary[channel]}")
    # baseline RMS
    axes[7][x,y].errorbar(vreset,baseline_rms[0],baseline_rms[1],label="V$_{sub}$=-%s V"%vbb,elinewidth=1.3,capsize=1.5)
    axes[7][x,y].set_title(f"{channel_to_pixel_dictionary[channel]}")
    # underline mean
    axes[8][x,y].errorbar(vreset,underline_mean[0],underline_mean[1],label="V$_{sub}$=-%s V"%vbb,elinewidth=1.3,capsize=1.5)
    axes[8][x,y].set_title(f"{channel_to_pixel_dictionary[channel]}")
    # underline RMS
    axes[9][x,y].errorbar(vreset,underline_rms[0],underline_rms[1],label="V$_{sub}$=-%s V"%vbb,elinewidth=1.3,capsize=1.5)
    axes[9][x,y].set_title(f"{channel_to_pixel_dictionary[channel]}")
    # baseline noise
    axes[10][x,y].errorbar(vreset,baseline_noise[0],baseline_noise[1],label="V$_{sub}$=-%s V"%vbb,elinewidth=1.3,capsize=1.5)
    axes[10][x,y].set_title(f"{channel_to_pixel_dictionary[channel]}")
    # underline noise
    axes[11][x,y].errorbar(vreset,underline_noise[0],underline_noise[1],label="V$_{sub}$=-%s V"%vbb,elinewidth=1.3,capsize=1.5)
    axes[11][x,y].set_title(f"{channel_to_pixel_dictionary[channel]}")


def save_pulsing_plots(figs, axes, analysis_argument_dict, output_path):
    for ax in axes[0].flat:
        ax.grid()
        ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(50))
        ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(1))
        ax.set_ylim(19,101)
        ax.legend(ncol=2, loc='upper right')
    for ax in axes[1].flat:
        ax.grid()
        ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(50))
        ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(1))
        ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(0.1))
        ax.set_ylim(-0.01,3.01)
        ax.legend(ncol=2, loc='upper right')
    for ax in axes[2].flat:
        ax.grid()
        ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(50))
        ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(20))
        ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(5))
        ax.set_ylim(79,181)
        ax.legend(ncol=2, loc='upper right')
    for ax in axes[3].flat:
        ax.grid()
        ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(50))
        ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(20))
        ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(5))
        ax.set_ylim(139,371)
        ax.legend(ncol=2, loc='upper right')
    for ax in axes[4].flat:
        ax.grid()
        ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(50))
        ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(0.02))
        ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(0.01))
        ax.set_ylim(0.079,0.321)
        ax.legend(ncol=2, loc='upper left')
    for ax in axes[5].flat:
        ax.grid()
        ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(50))
        ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(0.02))
        ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(0.01))
        ax.set_ylim(0.079,0.321)
        ax.legend(ncol=2, loc='upper left')
    for ax in axes[6].flat:
        ax.grid()
        ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(50))
        ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(1))
        ax.set_ylim(49.9,250.1)
        ax.legend(ncol=2, loc='upper left')
    for ax in axes[7].flat:
        ax.grid()
        ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(50))
        ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(0.5))
        ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(0.1))
        ax.set_ylim(-0.01,2.01)
        ax.legend(ncol=2, loc='upper right')
    for ax in axes[8].flat:
        ax.grid()
        ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(50))
        ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(1))
        ax.set_ylim(9.9,200.1)
        ax.legend(ncol=2, loc='upper left')
    for ax in axes[9].flat:
        ax.grid()
        ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(50))
        ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(0.5))
        ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(0.1))
        ax.set_ylim(-0.01,2.01)
        ax.legend(ncol=2, loc='upper right')
    for ax in axes[10].flat:
        ax.grid()
        ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(50))
        ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(1))
        ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(0.1))
        ax.set_ylim(-0.01,3.01)
        ax.legend(ncol=2, loc='upper left')
    for ax in axes[11].flat:
        ax.grid()
        ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(50))
        ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(1))
        ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(0.1))
        ax.set_ylim(-0.01,3.01)
        ax.legend(ncol=2, loc='upper left')
    root_plot_dir = os.path.join(output_path, "plots")
    os.makedirs(root_plot_dir, exist_ok=True)
    figs[0].text(0.5, 0.05, 'V$_{reset}$ (mV)', ha='center', va='center', rotation='horizontal', fontsize=15)
    figs[0].text(0.09, 0.5, 'Signal amplitude (mV)', ha='center', va='center', rotation='vertical', fontsize=15)
    figs[0].suptitle('Signal amplitude mean', fontsize=16)
    figs[0].savefig(os.path.join(root_plot_dir, "Signal_amplitude_mean.png"), bbox_inches='tight', pad_inches=0.1)
    plt.close(figs[0])
    figs[1].text(0.5, 0.05, 'V$_{reset}$ (mV)', ha='center', va='center', rotation='horizontal', fontsize=15)
    figs[1].text(0.09, 0.5, 'Signal amplitude RMS (mV)', ha='center', va='center', rotation='vertical', fontsize=15)
    figs[1].suptitle('Signal amplitude RMS', fontsize=16)
    figs[1].savefig(os.path.join(root_plot_dir, "Signal_amplitude_RMS.png"), bbox_inches='tight', pad_inches=0.1)
    plt.close(figs[1])
    figs[2].text(0.5, 0.05, 'V$_{reset}$ (mV)', ha='center', va='center', rotation='horizontal', fontsize=15)
    figs[2].text(0.09, 0.5, 'Falltime (ps)', ha='center', va='center', rotation='vertical', fontsize=15)
    figs[2].suptitle(r'Falltime 10%-50%', fontsize=16)
    figs[2].savefig(os.path.join(root_plot_dir, "Falltime_10_50.png"), bbox_inches='tight', pad_inches=0.1)
    plt.close(figs[2])
    figs[3].text(0.5, 0.05, 'V$_{reset}$ (mV)', ha='center', va='center', rotation='horizontal', fontsize=15)
    figs[3].text(0.09, 0.5, 'Falltime (ps)', ha='center', va='center', rotation='vertical', fontsize=15)
    figs[3].suptitle(r'Falltime 10%-90%', fontsize=16)
    figs[3].savefig(os.path.join(root_plot_dir, "Falltime_10_90.png"), bbox_inches='tight', pad_inches=0.1)
    plt.close(figs[3])
    figs[4].text(0.5, 0.05, 'V$_{reset}$ (mV)', ha='center', va='center', rotation='horizontal', fontsize=15)
    figs[4].text(0.09, 0.5, r'$\dfrac{dV}{dt}$ ($\dfrac{mV}{ps}$)', ha='center', va='center', rotation='vertical', fontsize=15)
    figs[4].suptitle(r'dV/dt 10%-50%', fontsize=16)
    figs[4].savefig(os.path.join(root_plot_dir, "Slope_10_50.png"), bbox_inches='tight', pad_inches=0.1)
    plt.close(figs[4])
    figs[5].text(0.5, 0.05, 'V$_{reset}$ (mV)', ha='center', va='center', rotation='horizontal', fontsize=15)
    figs[5].text(0.09, 0.5, r'$\dfrac{dV}{dt}$ ($\dfrac{mV}{ps}$)', ha='center', va='center', rotation='vertical', fontsize=15)
    figs[5].suptitle(r'dV/dt 10%-90%', fontsize=16)
    figs[5].savefig(os.path.join(root_plot_dir, "Slope_10_90.png"), bbox_inches='tight', pad_inches=0.1)
    plt.close(figs[5])
    figs[6].text(0.5, 0.05, 'V$_{reset}$ (mV)', ha='center', va='center', rotation='horizontal', fontsize=15)
    figs[6].text(0.09, 0.5, 'Baseline (mV)', ha='center', va='center', rotation='vertical', fontsize=15)
    figs[6].suptitle(f'Baseline mean evaluated on {analysis_argument_dict["baseline_evaluation_interval"]} ns time interval', fontsize=16)
    figs[6].savefig(os.path.join(root_plot_dir, "Baseline_mean.png"), bbox_inches='tight', pad_inches=0.1)
    plt.close(figs[6])
    figs[7].text(0.5, 0.05, 'V$_{reset}$ (mV)', ha='center', va='center', rotation='horizontal', fontsize=15)
    figs[7].text(0.09, 0.5, 'Baseline RMS (mV)', ha='center', va='center', rotation='vertical', fontsize=15)
    figs[7].suptitle(f'Baseline RMS evaluated on {analysis_argument_dict["baseline_evaluation_interval"]} ns time interval', fontsize=16)
    figs[7].savefig(os.path.join(root_plot_dir, "Baseline_RMS.png"), bbox_inches='tight', pad_inches=0.1)
    plt.close(figs[7])
    figs[8].text(0.5, 0.05, 'V$_{reset}$ (mV)', ha='center', va='center', rotation='horizontal', fontsize=15)
    figs[8].text(0.09, 0.5, 'Underline (mV)', ha='center', va='center', rotation='vertical', fontsize=15)
    figs[8].suptitle(f'Underline mean evaluated on {analysis_argument_dict["underline_evaluation_interval"]} ns time interval', fontsize=16)
    figs[8].savefig(os.path.join(root_plot_dir, "Underline_mean.png"), bbox_inches='tight', pad_inches=0.1)
    plt.close(figs[8])
    figs[9].text(0.5, 0.05, 'V$_{reset}$ (mV)', ha='center', va='center', rotation='horizontal', fontsize=15)
    figs[9].text(0.09, 0.5, 'Underline RMS (mV)', ha='center', va='center', rotation='vertical', fontsize=15)
    figs[9].suptitle(f'Underline RMS evaluated on {analysis_argument_dict["underline_evaluation_interval"]} ns time interval', fontsize=16)
    figs[9].savefig(os.path.join(root_plot_dir, "Underline_RMS.png"), bbox_inches='tight', pad_inches=0.1)
    plt.close(figs[9])
    figs[10].text(0.5, 0.05, 'V$_{reset}$ (mV)', ha='center', va='center', rotation='horizontal', fontsize=15)
    figs[10].text(0.09, 0.5, 'Baseline noise RMS (mV)', ha='center', va='center', rotation='vertical', fontsize=15)
    figs[10].suptitle(f'Baseline noise RMS (sample measured {analysis_argument_dict["baseline_first_time_before_t0"]} ns before t$_0$)', fontsize=16)
    figs[10].savefig(os.path.join(root_plot_dir, "baseline_noise.png"), bbox_inches='tight', pad_inches=0.1)
    plt.close(figs[10])
    figs[11].text(0.5, 0.05, 'V$_{reset}$ (mV)', ha='center', va='center', rotation='horizontal', fontsize=15)
    figs[11].text(0.09, 0.5, 'Underline noise RMS (mV)', ha='center', va='center', rotation='vertical', fontsize=15)
    figs[11].suptitle(f'Underline noise RMS (sample measured {analysis_argument_dict["underline_first_time_after_t0"]} ns after t$_0$)', fontsize=16)
    figs[11].savefig(os.path.join(root_plot_dir, "Underline_noise.png"), bbox_inches='tight', pad_inches=0.1)
    plt.close(figs[11])


def smoothen(x, y_mean, y_rms, x_dense):
    # s = np.rint(0.5*((len(x)-np.sqrt(2*len(x)))+(len(x)+np.sqrt(2*len(x)))))  # smoothing condition as suggested in https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.splrep.html
    tck = splrep(x=x, y=y_mean, w=1/y_rms, k=3, s=len(x)-np.sqrt(2*len(x)))  # k=3 is cubic spline, s=len(x)-np.sqrt(2*len(x) would be the default smoothing condition when weights are passed
    y_mean_dense = splev(x_dense, tck, der=0)
    return y_mean_dense


def pulsing_analysis(args):
    if args.make_plots:
        fig1, ax1, fig2, ax2, fig3, ax3, fig4, ax4, fig5, ax5, fig6, ax6, fig7, ax7, fig8, ax8, fig9, ax9, fig10, ax10, fig11, ax11, fig12, ax12 = au.define_figures()
    with open(args.gain_dict, 'r') as g:
        gain_json = json.load(g)
    scanned_vbb = au.list_vbb_dir(args.data_path)
    scanned_vbb.sort()
    output_dict = {}
    for vbb_path in scanned_vbb:
        vbb_dict = {}
        vbb = float(re.findall(r"vbb_(\d.\d)", vbb_path)[0])
        vbbpath = os.path.join(args.data_path, vbb_path)
        data_json_file = glob(f"{vbbpath}/opamp_pulsing_*.json")[0]
        with open(data_json_file, 'r') as jd:
            data_json = json.load(jd)
        analysis_arguments_json_file = glob(f"{vbbpath}/pulsing_processing_arguments.json")[0]
        with open(analysis_arguments_json_file, 'r') as ja:
            analysis_arguments_json = json.load(ja)
        connections_dict = data_json['inner_pixel_connections']
        data = pd.read_csv(f"{vbbpath}/pulsing_statistics.csv", sep="|")
        for ch in connections_dict.keys():
            pixel_dict={}
            # gain
            pixel = re.findall(r'J(\d+)', connections_dict[str(ch)])[0]
            gain_vreset_range = np.array(gain_json[str(vbb)][pixel]["vreset"])
            gain_mean = np.array(gain_json[str(vbb)][pixel]["gain"])
            gain_rms = np.array(gain_json[str(vbb)][pixel]["gain_rms"])
            gain_vreset_dense = np.arange(start=gain_vreset_range[0], stop=gain_vreset_range[-1]+1, step=1)
            gain_mean_dense = smoothen(x=gain_vreset_range, y_mean=gain_mean, y_rms=gain_rms, x_dense=gain_vreset_dense)
            pixel_dict["maximum_gain"] = float(np.round(np.max(gain_mean_dense),4))
            pixel_dict["vreset_maximum_gain"] = int(gain_vreset_dense[np.argmax(gain_mean_dense)])
            data_filtered = data.query(f"ch=={int(ch)}")
            data_filtered = data_filtered.sort_values(by="vreset", ascending=True)
            vres = data_filtered["vreset"].values.astype('int')
            vres_dense = np.arange(start=vres[0], stop=vres[-1]+1, step=1)
            # signal amplitude
            ampl_mean = data_filtered["amplitude_mean"].values.astype('float')
            ampl_rms = data_filtered["amplitude_rms"].values.astype('float')
            ampl_mean_dense = smoothen(x=vres, y_mean=ampl_mean, y_rms=ampl_rms, x_dense=vres_dense)
            # signal amplitude RMS
            ampl_rms_mean = data_filtered["amplitude_rms_mean"].values.astype('float')
            ampl_rms_rms = data_filtered["amplitude_rms_rms"].values.astype('float')
            pixel_dict["maximum_amplitude"] = round(np.max(ampl_mean_dense),2)
            pixel_dict["vreset_maximum_amplitude"] = int(vres_dense[np.argmax(ampl_mean_dense)])
            # falltime 10%-50%
            ft_tf_mean = data_filtered["falltime1050_mean"].values.astype('float')
            ft_tf_rms = data_filtered["falltime1050_rms"].values.astype('float')
            ft_tf_mean_dense = smoothen(x=vres, y_mean=ft_tf_mean, y_rms=ft_tf_rms, x_dense=vres_dense)
            pixel_dict["minimum_falltime_1050"] = round(np.min(ft_tf_mean_dense))
            pixel_dict["vreset_minimum_falltime_1050"] = int(vres_dense[np.argmin(ft_tf_mean_dense)])
            # falltime 10%-90%
            ft_tn_mean = data_filtered["falltime1090_mean"].values.astype('float')
            ft_tn_rms = data_filtered["falltime1090_rms"].values.astype('float')
            ft_tn_mean_dense = smoothen(x=vres, y_mean=ft_tn_mean, y_rms=ft_tn_rms, x_dense=vres_dense)
            pixel_dict["minimum_falltime_1090"] = round(np.min(ft_tn_mean_dense))
            pixel_dict["vreset_minimum_falltime_1090"] = int(vres_dense[np.argmin(ft_tn_mean_dense)])
            # dv/dt 10%-50%
            dvdt_tf_mean = 0.4*ampl_mean/ft_tf_mean
            dvdt_tf_rms = dvdt_tf_mean*np.sqrt((ampl_rms/ampl_mean)**2+(ft_tf_rms/ft_tf_mean)**2)  # error propagation
            dvdt_tf_mean_dense = smoothen(x=vres, y_mean=dvdt_tf_mean, y_rms=dvdt_tf_rms, x_dense=vres_dense)
            pixel_dict["maximum_dvdt_1050"] = round(np.max(dvdt_tf_mean_dense),2)
            pixel_dict["vreset_maximum_dvdt_1050"] = int(vres_dense[np.argmax(dvdt_tf_mean_dense)])
            # dv/dt 10%-90%
            dvdt_tn_mean = 0.8*ampl_mean/ft_tn_mean
            dvdt_tn_rms = dvdt_tn_mean*np.sqrt((ampl_rms/ampl_mean)**2+(ft_tn_rms/ft_tn_mean)**2)  # error propagation
            dvdt_tn_mean_dense = smoothen(x=vres, y_mean=dvdt_tn_mean, y_rms=dvdt_tn_rms, x_dense=vres_dense)
            pixel_dict["maximum_dvdt_1090"] = round(np.max(dvdt_tn_mean_dense),2)
            pixel_dict["vreset_maximum_dvdt_1090"] = int(vres_dense[np.argmax(dvdt_tn_mean_dense)])
            # baseline
            bsl_mean = data_filtered["baseline_mean"].values.astype('float')
            bsl_rms = data_filtered["baseline_rms"].values.astype('float')
            # baseline RMS
            bsl_rms_mean = data_filtered["baseline_rms_mean"].values.astype('float')
            bsl_rms_rms = data_filtered["baseline_rms_rms"].values.astype('float')
            # baseline noise
            bsl_noise_rms = data_filtered["baseline_noise_rms"].values.astype('float')
            bsl_noise_rms_error = data_filtered["baseline_noise_rms_error"].values.astype('float')
            # underline
            udl_mean = data_filtered["underline_mean"].values.astype('float')
            udl_rms = data_filtered["underline_rms"].values.astype('float')
            # underline RMS
            udl_rms_mean = data_filtered["underline_rms_mean"].values.astype('float')
            udl_rms_rms = data_filtered["underline_rms_rms"].values.astype('float')
            # underline noise
            udl_noise_rms = data_filtered["underline_noise_rms"].values.astype('float')
            udl_noise_rms_error = data_filtered["underline_noise_rms_error"].values.astype('float')
            vbb_dict[pixel] = pixel_dict
            if args.make_plots:
                fill_pulsing_plots(vres, (ampl_mean,ampl_rms), (ampl_rms_mean,ampl_rms_rms), (ft_tf_mean,ft_tf_rms), (ft_tn_mean,ft_tn_rms), (dvdt_tf_mean,dvdt_tf_rms), (dvdt_tn_mean,dvdt_tn_rms),\
                    (bsl_mean,bsl_rms), (bsl_rms_mean,bsl_rms_rms), (bsl_noise_rms,bsl_noise_rms_error), (udl_mean,udl_rms), (udl_rms_mean,udl_rms_rms), (udl_noise_rms,udl_noise_rms_error),\
                    ch, connections_dict, vbb, (ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8, ax9, ax10, ax11, ax12))
        output_dict[str(vbb)] = vbb_dict
    if args.make_plots:
        save_pulsing_plots((fig1, fig2, fig3, fig4, fig5, fig6, fig7, fig8, fig9, fig10, fig11, fig12), (ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8, ax9, ax10, ax11, ax12), analysis_arguments_json, args.data_path)
    return output_dict


def find_optimal_vreset(vreset_dict, args):
    with open(args.gain_dict, 'r') as g:
        baseline_data = json.load(g)
    output_dict = {}
    for vbb in vreset_dict.keys():
        vbb_dict = {}
        pixel_dict = {}
        # find optimal vreset as mean of vreset for each pixel
        optimal_vres_list = []
        for pixel in vreset_dict[vbb].keys():
            optimal_vres_list.append(vreset_dict[vbb][pixel]["vreset_maximum_gain"])
            optimal_vres_list.append(vreset_dict[vbb][pixel]["vreset_maximum_dvdt_1050"])
        optimal_vres = round(np.mean(optimal_vres_list))
        optimal_vres_uncertainty = round(np.std(optimal_vres_list)/np.sqrt(len(optimal_vres_list)))
        # round optimal vreset to nearest multiple of 10
        optimal_vres = round(optimal_vres/10)*10
        values_dict = {}
        for pixel in vreset_dict[vbb].keys():
            pixel_dict = {}
            index = (baseline_data[vbb][pixel]["vreset"]).index(optimal_vres)
            pixel_dict["baseline"] = baseline_data[vbb][pixel]["baseline"][index]
            pixel_dict["baseline_rms"] = baseline_data[vbb][pixel]["baseline_rms"][index]
            pixel_dict["gain"] = baseline_data[vbb][pixel]["gain"][index]
            pixel_dict["gain_rms"] = baseline_data[vbb][pixel]["gain_rms"][index]
            values_dict[pixel] = pixel_dict
        vbb_dict["vreset"] = optimal_vres
        vbb_dict["vreset_uncertainty"] = optimal_vres_uncertainty
        vbb_dict["pixels"] = values_dict
        output_dict[vbb] = vbb_dict
    if args.make_plots:
        vbb = [float(v) for v in output_dict.keys()]
        vreset = [output_dict[v]["vreset"] for v in output_dict.keys()]
        vreset_uncertainty = [output_dict[v]["vreset_uncertainty"] for v in output_dict.keys()]
        fig, ax = plt.subplots(figsize=(21,10))
        ax.errorbar(vbb,vreset,vreset_uncertainty,elinewidth=1.3,capsize=1.5)
        ax.xaxis.set_major_locator(mpl.ticker.FixedLocator(vbb))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(10))
        ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(1))
        ax.set_xlabel("\u2212V$_{sub}$ (V)", fontsize=15)
        ax.set_ylabel("V$_{reset}$ (mV)", fontsize=15)
        ax.grid()
        fig.suptitle('Optimal V$_{reset}$', fontsize=16)
        fig.savefig(os.path.join(f"{args.data_path}/plots", "Optimal_vreset.png"), bbox_inches='tight', pad_inches=0.1)
    return output_dict


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APTS OPAMP routine to analyse processed data of pulsing at varying vreset. It produces a .json file with optimal vreset for each vbb value.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--data_path', '-d', help='Directory for input files.')
    parser.add_argument('--gain_dict', '-g', help='.json file resulting from 00_gain_analysis.py.')
    parser.add_argument('--make_plots', '-p', action='store_true', help='Produce plots besides .json files.')
    args = parser.parse_args()
    try:
        optimal_vreset_dict = pulsing_analysis(args)
        with open(os.path.join(args.data_path, "optimal_smoothed_values.json"),'w') as file_handle:
            json.dump(optimal_vreset_dict, file_handle, indent=4)
        final_vreset = find_optimal_vreset(optimal_vreset_dict, args)
        with open(os.path.join(args.data_path, "operation_point.json"),'w') as file_handle:
            json.dump(final_vreset, file_handle, indent=4)
    except KeyboardInterrupt:
        logging.info('User stopped.')
    except Exception as e:
        logging.exception(e)
        logging.fatal('Terminating!')
