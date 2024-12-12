import os
import re
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.artist import Artist
from matplotlib.ticker import MultipleLocator
from scipy.interpolate import interp1d
from scipy.stats import moment
from math import ceil, sqrt
from tqdm import tqdm
import sys
sys.path.append(os.path.join(os.path.dirname(__file__),'./waveform_analysis/'))
from common import *


mpl.rc('xtick', labelsize=15)
mpl.rc('ytick', labelsize=15)


def list_vbb_dir(dir):
    subfolders = [ f.path for f in os.scandir(dir) if f.is_dir() ]
    regex = re.compile(r'.*/vbb_\d.\d')
    filtered = [i for i in subfolders if regex.match(i)]
    return filtered


def make_waveforms_dataframe(script_name):
    if script_name == "01_pulsing_processing.py":
        dataframe = pd.DataFrame(
            {
                'vreset': pd.Series([], dtype='int'),             # Vreset (mV) 
                'ch': pd.Series([], dtype='int'),                 # scope channel
                'trg': pd.Series([], dtype='int'),                # trigger number
                'baseline': pd.Series([], dtype='float'),         # mean of the points considered as baseline (mV)
                'baseline_rms': pd.Series([], dtype='float'),     # rms of the points considered as baseline (mV)
                'baseline_noise': pd.Series([], dtype='float'),   # value of the sampled point used to evaluate the noise and selected among those used to measure the baseline from which the mean baseline value is subtracted (mV)
                'underline': pd.Series([], dtype='float'),        # mean of the points considered as underline (mV)
                'underline_rms': pd.Series([], dtype='float'),    # rms of the points considered as underline (mV)
                'underline_noise': pd.Series([], dtype='float'),  # value of the sampled point used to evaluate the noise and selected among those used to measure the underline from which the mean underline value is subtracted  (mV)
                'amplitude': pd.Series([], dtype='float'),        # pulse amplitude computed as difference between mean baseline and mean underline (mV)
                'amplitude_rms': pd.Series([], dtype='float'),    # quadratic sum of baseline rms and underline rms (mV)
                't10': pd.Series([], dtype='int'),                # time at 10% of amplitude (ps)
                't50': pd.Series([], dtype='int'),                # time at 50% of amplitude (ps)
                't90': pd.Series([], dtype='int'),                # time at 90% of amplitude (ps)
                'falltime1050': pd.Series([], dtype='int'),       # falltime 10%-50% (ps)
                'falltime1090': pd.Series([], dtype='int')        # falltime 10%-90% (ps)
            }
        )
    elif script_name == "03_vh_scan_processing.py":
        dataframe = pd.DataFrame(
            {
                'vh': pd.Series([], dtype='int'),                 # Vh (mV)
                'ch': pd.Series([], dtype='int'),                 # scope channel
                'trg': pd.Series([], dtype='int'),                # trigger number
                'baseline': pd.Series([], dtype='float'),         # mean of the points considered as baseline (mV)
                'baseline_rms': pd.Series([], dtype='float'),     # rms of the points considered as baseline (mV)
                'baseline_noise': pd.Series([], dtype='float'),   # value of the sampled point used to evaluate the noise and selected among those used to measure the baseline from which the mean baseline value is subtracted (mV)
                'underline': pd.Series([], dtype='float'),        # mean of the points considered as underline (mV)
                'underline_rms': pd.Series([], dtype='float'),    # rms of the points considered as underline (mV)
                'underline_noise': pd.Series([], dtype='float'),  # value of the sampled point used to evaluate the noise and selected among those used to measure the underline from which the mean underline value is subtracted  (mV)
                'amplitude': pd.Series([], dtype='float'),        # pulse amplitude computed as difference between mean baseline and mean underline (mV)
                'amplitude_rms': pd.Series([], dtype='float'),    # quadratic sum of baseline rms and underline rms (mV)
                't10': pd.Series([], dtype='int'),                # time at 10% of amplitude (ps)
                't20': pd.Series([], dtype='int'),                # time at 20% of amplitude (ps)
                't30': pd.Series([], dtype='int'),                # time at 30% of amplitude (ps)
                't40': pd.Series([], dtype='int'),                # time at 40% of amplitude (ps)
                't50': pd.Series([], dtype='int'),                # time at 50% of amplitude (ps)
                't60': pd.Series([], dtype='int'),                # time at 60% of amplitude (ps)
                't70': pd.Series([], dtype='int'),                # time at 70% of amplitude (ps)
                't80': pd.Series([], dtype='int'),                # time at 80% of amplitude (ps)
                't90': pd.Series([], dtype='int'),                # time at 90% of amplitude (ps)
                'falltime1050': pd.Series([], dtype='int'),       # falltime 10%-50% (ps)
                'falltime1090': pd.Series([], dtype='int'),       # falltime 10%-50% (ps)
            }
        )
    else:
        raise ValueError('This function is designed to be used by 01_pulsing_processing.py or 03_vh_scan_processing.py only.')
    return dataframe


def make_statistics_dataframe(script_name):
    if script_name == "01_pulsing_processing.py":
        dataframe = pd.DataFrame(
            {
                'vreset': pd.Series([], dtype='int'),                       # Vreset (mV)
                'ch': pd.Series([], dtype='int'),                           # scope channel
                'baseline_mean': pd.Series([], dtype='float'),              # mean of IQR of distribution of mean baseline level (mV)
                'baseline_rms': pd.Series([], dtype='float'),               # rms of IQR of distribution of mean baseline level (mV)
                'baseline_mean_error': pd.Series([], dtype='float'),        # standard mean error of IQR of distribution of mean baseline level (mV)
                'baseline_rms_mean': pd.Series([], dtype='float'),          # mean of IQR of distribution of the rms of the baseline level (mV)
                'baseline_rms_rms': pd.Series([], dtype='float'),           # rms of IQR of distribution of the rms of the baseline level (mV)
                'baseline_rms_mean_error': pd.Series([], dtype='float'),    # standard mean error of IQR of distribution of the rms of the baseline level (mV)
                'baseline_noise_mean': pd.Series([], dtype='float'),        # mean of IQR of distribution of the sample taken to evaluate the baseline noise (mV)
                'baseline_noise_rms': pd.Series([], dtype='float'),         # rms of IQR of distribution of the sample taken to evaluate the baseline noise (mV)
                'baseline_noise_mean_error': pd.Series([], dtype='float'),  # standard mean error of IQR of the sample taken to evaluate the baseline noise (mV)
                'baseline_noise_rms_error': pd.Series([], dtype='float'),   # standard error on the rms of IQR of the sample taken to evaluate the baseline noise (mV)
                'underline_mean': pd.Series([], dtype='float'),             # mean of IQR of distribution of mean underline level (mV)
                'underline_rms': pd.Series([], dtype='float'),              # rms of IQR of distribution of mean underline level (mV)
                'underline_mean_error': pd.Series([], dtype='float'),       # standard mean error of IQR of distribution of mean underline level (mV)
                'underline_rms_mean': pd.Series([], dtype='float'),         # mean of IQR of distribution of the rms of the underline level (mV)
                'underline_rms_rms': pd.Series([], dtype='float'),          # rms of IQR of distribution of the rms of the underline level (mV)
                'underline_rms_mean_error': pd.Series([], dtype='float'),   # standard mean error of IQR of distribution of the rms of the underline level (mV)
                'underline_noise_mean': pd.Series([], dtype='float'),       # mean of IQR of distribution of the sample taken to evaluate the underline noise (mV)
                'underline_noise_rms': pd.Series([], dtype='float'),        # rms of IQR of distribution of the sample taken to evaluate the underline noise (mV)
                'underline_noise_mean_error': pd.Series([], dtype='float'), # standard mean error of IQR of the sample taken to evaluate the underline noise (mV)
                'underline_noise_rms_error': pd.Series([], dtype='float'),  # standard error on the rms of IQR of the sample taken to evaluate the underline noise (mV)
                'amplitude_mean': pd.Series([], dtype='float'),             # mean of IQR of distribution of mean pulse amplitude (mV)
                'amplitude_rms': pd.Series([], dtype='float'),              # rms of IQR of distribution of mean pulse amplitude (mV)
                'amplitude_mean_error': pd.Series([], dtype='float'),       # standard mean error of IQR of distribution of mean pulse amplitude (mV)
                'amplitude_rms_mean': pd.Series([], dtype='float'),         # mean of IQR of distribution of rms pulse amplitude (mV)
                'amplitude_rms_rms': pd.Series([], dtype='float'),          # rms of IQR of distribution of rms pulse amplitude (mV)
                'amplitude_rms_mean_error': pd.Series([], dtype='float'),   # standard mean error of IQR of distribution of rms pulse amplitude (mV)
                'falltime1050_mean': pd.Series([], dtype='int'),            # mean of IQR of falltime 10%-50% distribution (ps)
                'falltime1050_rms': pd.Series([], dtype='int'),             # rms of IQR of falltime 10%-50% distribution (ps)
                'falltime1050_mean_error': pd.Series([], dtype='int'),      # standard mean error of IQR of falltime 10%-50% distribution (ps)
                'falltime1090_mean': pd.Series([], dtype='int'),            # mean of IQR of falltime 10%-90% distribution (ps)
                'falltime1090_rms': pd.Series([], dtype='int'),             # rms of IQR of falltime 10%-90% distribution (ps)
                'falltime1090_mean_error': pd.Series([], dtype='int')       # standard mean error of IQR of falltime 10%-90% distribution (ps)
            }
        )
    elif script_name == "03_vh_scan_processing.py":
        dataframe = pd.DataFrame(
            {
                'vh': pd.Series([], dtype='int'),                           # Vh (mV)
                'ch': pd.Series([], dtype='int'),                           # scope channel
                'baseline_mean': pd.Series([], dtype='float'),              # mean of IQR of distribution of mean baseline level (mV)
                'baseline_rms': pd.Series([], dtype='float'),               # rms of IQR of distribution of mean baseline level (mV)
                'baseline_mean_error': pd.Series([], dtype='float'),        # standard mean error of IQR of distribution of mean baseline level (mV)
                'baseline_rms_mean': pd.Series([], dtype='float'),          # mean of IQR of distribution of the rms of the baseline level (mV)
                'baseline_rms_rms': pd.Series([], dtype='float'),           # rms of IQR of distribution of the rms of the baseline level (mV)
                'baseline_rms_mean_error': pd.Series([], dtype='float'),    # standard mean error of IQR of distribution of the rms of the baseline level (mV)
                'baseline_noise_mean': pd.Series([], dtype='float'),        # mean of IQR of distribution of the sample taken to evaluate the baseline noise (mV)
                'baseline_noise_rms': pd.Series([], dtype='float'),         # rms of IQR of distribution of the sample taken to evaluate the baseline noise (mV)
                'baseline_noise_mean_error': pd.Series([], dtype='float'),  # standard mean error of IQR of the sample taken to evaluate the baseline noise (mV)
                'baseline_noise_rms_error': pd.Series([], dtype='float'),   # standard error on the rms of IQR of the sample taken to evaluate the baseline noise (mV)
                'underline_mean': pd.Series([], dtype='float'),             # mean of IQR of distribution of mean underline level (mV)
                'underline_rms': pd.Series([], dtype='float'),              # rms of IQR of distribution of mean underline level (mV)
                'underline_mean_error': pd.Series([], dtype='float'),       # standard mean error of IQR of distribution of mean underline level (mV)
                'underline_rms_mean': pd.Series([], dtype='float'),         # mean of IQR of distribution of the rms of the underline level (mV)
                'underline_rms_rms': pd.Series([], dtype='float'),          # rms of IQR of distribution of the rms of the underline level (mV)
                'underline_rms_mean_error': pd.Series([], dtype='float'),   # standard mean error of IQR of distribution of the rms of the underline level (mV)
                'underline_noise_mean': pd.Series([], dtype='float'),       # mean of IQR of distribution of the sample taken to evaluate the underline noise (mV)
                'underline_noise_rms': pd.Series([], dtype='float'),        # rms of IQR of distribution of the sample taken to evaluate the underline noise (mV)
                'underline_noise_mean_error': pd.Series([], dtype='float'), # standard mean error of IQR of the sample taken to evaluate the underline noise (mV)
                'underline_noise_rms_error': pd.Series([], dtype='float'),  # standard error on the rms of IQR of the sample taken to evaluate the underline noise (mV)
                'amplitude_mean': pd.Series([], dtype='float'),             # mean of IQR of distribution of mean pulse amplitude (mV)
                'amplitude_rms': pd.Series([], dtype='float'),              # rms of IQR of distribution of mean pulse amplitude (mV)
                'amplitude_mean_error': pd.Series([], dtype='float'),       # standard mean error of IQR of distribution of mean pulse amplitude (mV)
                'amplitude_rms_mean': pd.Series([], dtype='float'),         # mean of IQR of distribution of rms pulse amplitude (mV)
                'amplitude_rms_rms': pd.Series([], dtype='float'),          # rms of IQR of distribution of rms pulse amplitude (mV)
                'amplitude_rms_mean_error': pd.Series([], dtype='float'),   # standard mean error of IQR of distribution of rms pulse amplitude (mV)
                'falltime1050_mean': pd.Series([], dtype='int'),            # mean of IQR of falltime 10%-50% distribution (ps)
                'falltime1050_rms': pd.Series([], dtype='int'),             # rms of IQR of error falltime 10%-50% distribution (ps)
                'falltime1050_mean_error': pd.Series([], dtype='int'),      # standard mean error of IQR of falltime 10%-50% distribution (ps)
                'falltime1090_mean': pd.Series([], dtype='int'),            # mean of IQR of falltime 10%-90% distribution (ps)
                'falltime1090_rms': pd.Series([], dtype='int'),             # rms of IQR of falltime 10%-90% distribution (ps)
                'falltime1090_mean_error': pd.Series([], dtype='int')       # standard mean error of IQR of falltime 10%-90% distribution (ps)
            }
        )
    else:
        raise ValueError('This function is designed to be used by 01_pulsing_processing.py or 03_vh_scan_processing.py only.')
    return dataframe


def analyse_waveform(adc_signal, scope_channel, scope_axis_dict, channel_to_pixel_dict, baseline_and_underline_evaluation_points, script_name, signal_extraction_method="derivative",\
    resample_waveform=False, integration_time=None, gain_calibration_data=None):
    assert signal_extraction_method in ["threshold", "derivative"], "Only threshold-based and derivative-based t0 identification algorithms with related baseline and underline definitions are implemented"
    baseline = -999.
    underline = -999.
    CFD_times = [-999., -999., -999., -999., -999., -999., -999., -999., -999., -999.]  # t0 + CFD times from 10% to 90%
    time = (scope_axis_dict["t0"] + scope_axis_dict["dt"]*np.linspace(0, len(adc_signal), num=len(adc_signal)))*1e9         # in ns
    voltage_signal = (scope_axis_dict[f"v0_ch{scope_channel}"] + scope_axis_dict[f"dv_ch{scope_channel}"]*adc_signal)*1000  # in mV
    resampled_graph = None
    if gain_calibration_data is not None:
        pixel = int(re.findall(r'J(\d+)', channel_to_pixel_dict[scope_channel])[0])
        interp = interp1d(gain_calibration_data["baseline_all"][pixel, :],gain_calibration_data["vres_range"],kind='cubic',fill_value='extrapolate')
        voltage_signal = interp(voltage_signal)
    graph = [time, voltage_signal]
    if signal_extraction_method == "threshold":
        t0_bin = FindLeftNearBaseline(graph, cut=7, pointsWithinCut=1, totalStep=2)
    else:
        assert integration_time is not None, "Provide an integration time to find the t0 with the derivative-based algorithm"
        t0_bin = find_edge(graph, dt_ns=scope_axis_dict["dt"]*1e9, t_int=integration_time, thr=1)
    if (t0_bin < 0): return graph, resampled_graph, baseline, None, None, underline, None, None, t0_bin, None, CFD_times
    if resample_waveform:
        resample_range = [np.argmin(np.abs(graph[0]-(graph[0][t0_bin]-baseline_and_underline_evaluation_points[1]))), np.argmin(np.abs(graph[0]-(graph[0][t0_bin]+baseline_and_underline_evaluation_points[3])))]
        if resample_range[0] < 0: return graph, resampled_graph, baseline, None, None, underline, None, None, t0_bin, None, CFD_times
        resampled_graph = ResampleGraph(graph, findRange=resample_range, softwareScaleFactorX=12.5e-3)  # resample the waveform in CFD range with sampling period 12.5 ps
    if signal_extraction_method == "threshold":        
        baseline, baseline_RMS, baseline_noise_point = GetDefaultBaseline(graph, t0_bin=t0_bin, dt_ns=scope_axis_dict["dt"]*1e9,\
            evaluation_time_ns=baseline_and_underline_evaluation_points[0], start_time_before_t0_ns=baseline_and_underline_evaluation_points[0]+baseline_and_underline_evaluation_points[1])
        underline, underline_RMS, underline_noise_point = GetDefaultUnderline(graph, t0_bin=t0_bin, dt_ns=scope_axis_dict["dt"]*1e9,\
            evaluation_time_ns=baseline_and_underline_evaluation_points[2], start_time_after_t0_ns=baseline_and_underline_evaluation_points[3])
    else:
        baseline, baseline_RMS, baseline_noise_point, underline, underline_RMS, underline_noise_point, _ = GetAmp(graph, t0_bin=t0_bin, dt_ns=scope_axis_dict["dt"]*1e9,\
            int1=baseline_and_underline_evaluation_points[0]+baseline_and_underline_evaluation_points[1], int2=baseline_and_underline_evaluation_points[0])
    CFD_range = [(t0_bin*scope_axis_dict["dt"]+scope_axis_dict["t0"])*1e9-baseline_and_underline_evaluation_points[1],\
        (t0_bin*scope_axis_dict["dt"]+scope_axis_dict["t0"])*1e9+baseline_and_underline_evaluation_points[3]]
    CFD_times[0] = (t0_bin*scope_axis_dict["dt"]+scope_axis_dict["t0"])*1e9
    for elem in range(1,10):
        backward_flag = True
        if elem>5:
            backward_flag = False
        if resample_waveform:
            CFD_times[elem] = FindOnGraph(resampled_graph,baseline-(elem/10)*(baseline-underline),CFD_range[0],CFD_range[1],interpolate=1,backw=backward_flag)
        else:
            CFD_times[elem] = FindOnGraph(graph,baseline-(elem/10)*(baseline-underline),CFD_range[0],CFD_range[1],interpolate=1,backw=backward_flag)
        if elem>1 and (CFD_times[elem]<CFD_times[elem-1]):  # if mistake in measuring CFD time because of noise, assign measurement to first point after previous CFD measurement
            if resample_waveform:
                index = (np.abs(resampled_graph[0] - CFD_times[elem-1])).argmin() + 1 if ((np.abs(resampled_graph[0] - CFD_times[elem-1])).argmin() + 1) < len(resampled_graph[0]) else (np.abs(resampled_graph[0] - CFD_times[elem-1])).argmin()
                CFD_times[elem] = resampled_graph[0][index]
            else:
                index = (np.abs(graph[0] - CFD_times[elem-1])).argmin() + 1 if ((np.abs(graph[0] - CFD_times[elem-1])).argmin() + 1) < len(graph[0]) else (np.abs(graph[0] - CFD_times[elem-1])).argmin()
                CFD_times[elem] = graph[0][index]
    return graph, resampled_graph, baseline, baseline_RMS, baseline_noise_point, underline, underline_RMS, underline_noise_point, t0_bin, CFD_range, CFD_times


def plot_waveform(graph, baseline, underline, t0_bin, scope_axis_dict, CFD_times, CFD_search_limit, scope_channel, resampled_graph=None, vbb=None, vreset=None, vh=None, trigger=None):
    figd, axd = plt.subplots(figsize=(21,10))
    y_plot_array = np.arange(start=underline-1., stop=baseline+1., step=0.1)
    x_plot_array = np.ones(len(y_plot_array))
    axd.plot(graph[0], graph[1], '.', label=f'CH{scope_channel}')
    if resampled_graph is not None:
        axd.plot(resampled_graph[0], resampled_graph[1], '.c', label=f'Resampled CH{scope_channel}')
    axd.plot(graph[0][0:t0_bin], baseline*np.ones(len(graph[0][0:t0_bin])), '--r', label='Baseline')
    axd.plot(graph[0][t0_bin:], underline*np.ones(len(graph[0][t0_bin:])), '-.r', label='Underline')
    axd.plot(x_plot_array*(t0_bin*scope_axis_dict["dt"]+scope_axis_dict["t0"])*1e9, y_plot_array, '-k', label='t$_0$')
    axd.plot(x_plot_array*CFD_times[1], y_plot_array, '-y', label='CFD t$_{10\%}$')
    axd.plot(x_plot_array*CFD_times[5], y_plot_array, '-g', label='CFD t$_{50\%}$')
    axd.plot(x_plot_array*CFD_times[9], y_plot_array, '-m', label='CFD t$_{90\%}$')
    axd.plot(x_plot_array*CFD_search_limit, y_plot_array, '-b', label='CFD search limit')
    axd.set_xlim(-10.1, 10.1)
    axd.set_xlabel('Time (ns)', fontsize = 15)
    axd.set_ylabel('Amplitude (mV)', fontsize = 15)
    axd.xaxis.set_major_locator(MultipleLocator(1))
    axd.xaxis.set_minor_locator(MultipleLocator(0.1))
    axd.legend()
    if (vbb is not None) and (vreset is not None) and (trigger is not None):
        axd.set_title("V$_{sub}$ = %s V, V$_{reset}$ = %s mV - n$_{trg}$ = %s" % (vbb, vreset, trigger), fontsize=24)
    if (vbb is not None) and (vh is not None) and (trigger is not None):
        axd.set_title("V$_{sub}$ = %s V, V$_h$ = %s mV - n$_{trg}$ = %s" % (vbb, vh, trigger), fontsize=24)
    plt.show()


def write_waveforms_dataframe(dataframe, script_name, parameter, scope_channel, trigger, baseline_estimators, underline_estimators, CFD_times):
    if script_name == "01_pulsing_processing.py":
        dataframe = pd.concat([dataframe,
            pd.Series({
                'vreset': parameter,
                'ch': scope_channel,
                'trg': trigger,
                'baseline': round(baseline_estimators[0],2),
                'baseline_rms': round(baseline_estimators[1],2),
                'baseline_noise': round(baseline_estimators[2]-baseline_estimators[0],2),
                'underline': round(underline_estimators[0],2),
                'underline_rms': round(underline_estimators[1],2),
                'underline_noise': round(underline_estimators[2]-underline_estimators[0],2),
                'amplitude': round(baseline_estimators[0]-underline_estimators[0],2),
                'amplitude_rms': round(sqrt(baseline_estimators[1]**2+underline_estimators[1]**2),2),
                't0': round(CFD_times[0]*1000),
                't10': round(CFD_times[1]*1000),
                't50': round(CFD_times[5]*1000),
                't90': round(CFD_times[9]*1000),
                'falltime1050': round((CFD_times[5]-CFD_times[1])*1000),
                'falltime1090': round((CFD_times[9]-CFD_times[1])*1000)
            }).to_frame().T],
            ignore_index=True
        )
    elif script_name == "03_vh_scan_processing.py":
        dataframe = pd.concat([dataframe,
            pd.Series({
                'vh': parameter,
                'ch': scope_channel,
                'trg': trigger,
                'baseline': round(baseline_estimators[0],2),
                'baseline_rms': round(baseline_estimators[1],2),
                'baseline_noise': round(baseline_estimators[2]-baseline_estimators[0],2),
                'underline': round(underline_estimators[0],2),
                'underline_rms': round(underline_estimators[1],2),
                'underline_noise': round(underline_estimators[2]-underline_estimators[0],2),
                'amplitude': round(baseline_estimators[0]-underline_estimators[0],2),
                'amplitude_rms': round(sqrt(baseline_estimators[1]**2+underline_estimators[1]**2),2),
                't0': round(CFD_times[0]*1000),
                't10': round(CFD_times[1]*1000),
                't20': round(CFD_times[2]*1000),
                't30': round(CFD_times[3]*1000),
                't40': round(CFD_times[4]*1000),
                't50': round(CFD_times[5]*1000),
                't60': round(CFD_times[6]*1000),
                't70': round(CFD_times[7]*1000),
                't80': round(CFD_times[8]*1000),
                't90': round(CFD_times[9]*1000),
                'falltime1050': round((CFD_times[5]-CFD_times[1])*1000),
                'falltime1090': round((CFD_times[9]-CFD_times[1])*1000),
            }).to_frame().T],
            ignore_index=True
        )
    else:
        raise ValueError('This function is designed to be used by 01_pulsing_processing.py or 03_vh_scan_processing.py only.')
    return dataframe


def write_statistics_dataframe(dataframe, script_name, parameter, scope_channel, record):
    if script_name == "01_pulsing_processing.py":
        dataframe = pd.concat([dataframe,
            pd.Series({
                'vreset': parameter,
                'ch': scope_channel,
                'baseline_mean': round(record["baseline"][f"{scope_channel}"]["mean"],2),
                'baseline_rms': round(record["baseline"][f"{scope_channel}"]["rms"],2),
                'baseline_mean_error': round(record["baseline"][f"{scope_channel}"]["mean_error"],4),
                'baseline_rms_mean': round(record["baseline_rms"][f"{scope_channel}"]["mean"],2),
                'baseline_rms_rms': round(record["baseline_rms"][f"{scope_channel}"]["rms"],2),
                'baseline_rms_mean_error': round(record["baseline_rms"][f"{scope_channel}"]["mean_error"],4),
                'baseline_noise_mean': round(record["baseline_noise"][f"{scope_channel}"]["mean"],2),
                'baseline_noise_rms': round(record["baseline_noise"][f"{scope_channel}"]["rms"],2),
                'baseline_noise_mean_error': round(record["baseline_noise"][f"{scope_channel}"]["mean_error"],4),
                'baseline_noise_rms_error': round(record["baseline_noise"][f"{scope_channel}"]["rms_error"],4),
                'underline_mean': round(record["underline"][f"{scope_channel}"]["mean"],2),
                'underline_rms': round(record["underline"][f"{scope_channel}"]["rms"],2),
                'underline_mean_error': round(record["underline"][f"{scope_channel}"]["mean_error"],4),
                'underline_rms_mean': round(record["underline_rms"][f"{scope_channel}"]["mean"],2),
                'underline_rms_rms': round(record["underline_rms"][f"{scope_channel}"]["rms"],2),
                'underline_rms_mean_error': round(record["underline_rms"][f"{scope_channel}"]["mean_error"],4),
                'underline_noise_mean': round(record["underline_noise"][f"{scope_channel}"]["mean"],2),
                'underline_noise_rms': round(record["underline_noise"][f"{scope_channel}"]["rms"],2),
                'underline_noise_mean_error': round(record["underline_noise"][f"{scope_channel}"]["mean_error"],4),
                'underline_noise_rms_error': round(record["underline_noise"][f"{scope_channel}"]["rms_error"],4),
                'amplitude_mean': round(record["amplitude"][f"{scope_channel}"]["mean"],2),
                'amplitude_rms': round(record["amplitude"][f"{scope_channel}"]["rms"],2),
                'amplitude_mean_error': round(record["amplitude"][f"{scope_channel}"]["mean_error"],4),
                'amplitude_rms_mean': round(record["amplitude_rms"][f"{scope_channel}"]["mean"],2),
                'amplitude_rms_rms': round(record["amplitude_rms"][f"{scope_channel}"]["rms"],2),
                'amplitude_rms_mean_error': round(record["amplitude_rms"][f"{scope_channel}"]["mean_error"],4),
                'falltime1050_mean': round(record["falltime1050"][f"{scope_channel}"]["mean"]),
                'falltime1050_rms': round(record["falltime1050"][f"{scope_channel}"]["rms"]),
                'falltime1050_mean_error': round(record["falltime1050"][f"{scope_channel}"]["mean_error"]),
                'falltime1090_mean': round(record["falltime1090"][f"{scope_channel}"]["mean"]),
                'falltime1090_rms': round(record["falltime1090"][f"{scope_channel}"]["rms"]),
                'falltime1090_mean_error': round(record["falltime1090"][f"{scope_channel}"]["mean_error"])
            }).to_frame().T],
            ignore_index=True
        )
    elif script_name == "03_vh_scan_processing.py":
        dataframe = pd.concat([dataframe,
            pd.Series({
                'vh': parameter,
                'ch': scope_channel,
                'baseline_mean': round(record["baseline"][f"{scope_channel}"]["mean"],2),
                'baseline_rms': round(record["baseline"][f"{scope_channel}"]["rms"],2),
                'baseline_mean_error': round(record["baseline"][f"{scope_channel}"]["mean_error"],4),
                'baseline_rms_mean': round(record["baseline_rms"][f"{scope_channel}"]["mean"],2),
                'baseline_rms_rms': round(record["baseline_rms"][f"{scope_channel}"]["rms"],2),
                'baseline_rms_mean_error': round(record["baseline_rms"][f"{scope_channel}"]["mean_error"],4),
                'baseline_noise_mean': round(record["baseline_noise"][f"{scope_channel}"]["mean"],2),
                'baseline_noise_rms': round(record["baseline_noise"][f"{scope_channel}"]["rms"],2),
                'baseline_noise_mean_error': round(record["baseline_noise"][f"{scope_channel}"]["mean_error"],4),
                'baseline_noise_rms_error': round(record["baseline_noise"][f"{scope_channel}"]["rms_error"],4),
                'underline_mean': round(record["underline"][f"{scope_channel}"]["mean"],2),
                'underline_rms': round(record["underline"][f"{scope_channel}"]["rms"],2),
                'underline_mean_error': round(record["underline"][f"{scope_channel}"]["mean_error"],4),
                'underline_rms_mean': round(record["underline_rms"][f"{scope_channel}"]["mean"],2),
                'underline_rms_rms': round(record["underline_rms"][f"{scope_channel}"]["rms"],2),
                'underline_rms_mean_error': round(record["underline_rms"][f"{scope_channel}"]["mean_error"],4),
                'underline_noise_mean': round(record["underline_noise"][f"{scope_channel}"]["mean"],2),
                'underline_noise_rms': round(record["underline_noise"][f"{scope_channel}"]["rms"],2),
                'underline_noise_mean_error': round(record["underline_noise"][f"{scope_channel}"]["mean_error"],4),
                'underline_noise_rms_error': round(record["underline_noise"][f"{scope_channel}"]["rms_error"],4),
                'amplitude_mean': round(record["amplitude"][f"{scope_channel}"]["mean"],2),
                'amplitude_rms': round(record["amplitude"][f"{scope_channel}"]["rms"],2),
                'amplitude_mean_error': round(record["amplitude"][f"{scope_channel}"]["mean_error"],4),
                'amplitude_rms_mean': round(record["amplitude_rms"][f"{scope_channel}"]["mean"],2),
                'amplitude_rms_rms': round(record["amplitude_rms"][f"{scope_channel}"]["rms"],2),
                'amplitude_rms_mean_error': round(record["amplitude_rms"][f"{scope_channel}"]["mean_error"],4),
                'falltime1050_mean': round(record["falltime1050"][f"{scope_channel}"]["mean"]),
                'falltime1050_rms': round(record["falltime1050"][f"{scope_channel}"]["rms"]),
                'falltime1050_mean_error': round(record["falltime1050"][f"{scope_channel}"]["mean_error"]),
                'falltime1090_mean': round(record["falltime1090"][f"{scope_channel}"]["mean"]),
                'falltime1090_rms': round(record["falltime1090"][f"{scope_channel}"]["rms"]),
                'falltime1090_mean_error': round(record["falltime1090"][f"{scope_channel}"]["mean_error"])
            }).to_frame().T],
            ignore_index=True
        )    
    else:
        raise ValueError('This function is designed to be used by 01_pulsing_processing.py or 03_vh_scan_processing.py only.')
    return dataframe


def hist_plot(ax, data, cleaned_data, bin_width, unit_of_measure):
    nbins = ceil((np.max(data) - np.min(data)) / bin_width)
    if nbins > 0:
        ax.hist(data, bins=nbins, color='navy', alpha=0.7, density=False)
    props = dict(boxstyle='square', facecolor='white', alpha=1.0, edgecolor='black', zorder=10)
    textstr = '\n'.join((
        'entries = %d' % (data.shape[0]),
        'mean = %.2f %s' % (round(np.mean(data),2), unit_of_measure, ),
        'RMS = %.2f %s' % (round(np.std(data),2), unit_of_measure, ),
        'entries$_{IQR}$ = %d' % (cleaned_data.shape[0]),
        'mean$_{IQR}$ = %.2f %s' % (round(np.mean(cleaned_data),2), unit_of_measure, ),
        'RMS$_{IQR}$ = %.2f %s' % (round(np.std(cleaned_data),2), unit_of_measure, ),
    ))
    ax.text(0.015, 0.925, textstr, transform=ax.transAxes, fontsize=12, verticalalignment='top', bbox=props, backgroundcolor='white')
    ax.grid()


def control_plots(channel, axis, quantity, array, cleaned_array, bin_width, channel_to_pixel_dictionary):
    x = int(int(channel-1)/2)
    y = int(int(channel-1)%2)
    axis[x,y].set_title(f"{channel_to_pixel_dictionary[str(channel)]}")
    if quantity in ["falltime1050", "falltime1090"]:
        uom = "ps"
    else:
        uom = "mV"
    if len(array) > 0:
        hist_plot(ax=axis[x,y], data=array, cleaned_data=cleaned_array, bin_width=bin_width, unit_of_measure=uom)
    else:
        axis[x,y].text(0.5, 0.5, "No good data available", fontsize=12)


def process_waveforms_dataframe(waveforms_dataframe, statistics_dataframe, script_name, value_range, channel_to_pixel_dictionary, make_control_plots, baseline_and_underline_evaluation_points,\
    output_plot_dir, output_file_suffix=""):
    parameter_dict = {
        "baseline": {"bin_width": 0.5, "unit_of_measure": "mV", "axis_label": "Baseline mean", "control_plot_suptitle": f"Baseline mean evaluated on {baseline_and_underline_evaluation_points[0]} ns interval", "control_plot_fig_name": "Baseline_mean", "plot_dir": "baseline"},
        "baseline_rms": {"bin_width": 0.25, "unit_of_measure": "mV", "axis_label": "Baseline rms", "control_plot_suptitle": f"Baseline RMS evaluated on {baseline_and_underline_evaluation_points[0]} ns interval", "control_plot_fig_name": "Baseline_rms", "plot_dir": "baseline"},
        "baseline_noise": {"bin_width": 0.25, "unit_of_measure": "mV", "axis_label": "Baseline noise sample", "control_plot_suptitle": f"Baseline noise sample measured {baseline_and_underline_evaluation_points[1]} ns before t$_0$ \u2212 Baseline mean", "control_plot_fig_name": "Baseline_noise", "plot_dir": "baseline"},        
        "underline": {"bin_width": 0.5, "unit_of_measure": "mV", "axis_label": "Underline mean", "control_plot_suptitle": f"Underline mean evaluated on {baseline_and_underline_evaluation_points[2]} ns interval", "control_plot_fig_name": "Underline_mean", "plot_dir": "underline"},
        "underline_rms": {"bin_width": 0.25, "unit_of_measure": "mV", "axis_label": "Underline rms", "control_plot_suptitle": f"Underline RMS evaluated on {baseline_and_underline_evaluation_points[2]} ns interval", "control_plot_fig_name": "Underline_rms", "plot_dir": "underline"},
        "underline_noise": {"bin_width": 0.25, "unit_of_measure": "mV", "axis_label": "Underline noise sample", "control_plot_suptitle": f"Underline noise sample measured {baseline_and_underline_evaluation_points[3]} ns after t$_0$ \u2212 Underline mean", "control_plot_fig_name": "Underline_noise", "plot_dir": "underline"},
        "amplitude": {"bin_width": 0.5, "unit_of_measure": "mV", "axis_label": "Signal amplitude mean", "control_plot_suptitle": "Signal amplitude mean", "control_plot_fig_name": "Signal_amplitude_mean", "plot_dir": "amplitude"},
        "amplitude_rms": {"bin_width": 0.25, "unit_of_measure": "mV", "axis_label": "Signal amplitude rms", "control_plot_suptitle": "Signal amplitude rms", "control_plot_fig_name": "Signal_amplitude_rms", "plot_dir": "amplitude"},
        "falltime1050": {"bin_width": 5, "unit_of_measure": "ps", "axis_label": r"Signal falltime 10%-50%", "control_plot_suptitle": r"Falltime 10%-50%", "control_plot_fig_name": "Falltime_10_50", "plot_dir": "falltime"},
        "falltime1090": {"bin_width": 10, "unit_of_measure": "ps", "axis_label": r"Signal falltime 10%-90%", "control_plot_suptitle": r"Falltime 10%-90%", "control_plot_fig_name": "Falltime_10_90", "plot_dir": "falltime"}
                      }
    if make_control_plots:
        root_plot_dir = os.path.join(output_plot_dir, f"control_plots{output_file_suffix}")
        os.makedirs(root_plot_dir, exist_ok=True)
        for parameter in parameter_dict.keys():
            os.makedirs(os.path.join(root_plot_dir, parameter_dict[parameter]["plot_dir"]), exist_ok=True)
        fig, ax = plt.subplots(ncols=2, nrows=2, sharex=True, sharey=True, figsize=(21,10))
        plt.subplots_adjust(hspace=.1, wspace=.05)  # adjust vertical space between subplots
    if script_name == "01_pulsing_processing.py":
        query_parameter = "vreset"
    elif script_name == "03_vh_scan_processing.py":
        query_parameter = "vh"
    else:
        raise ValueError('This function is designed to be used by 01_pulsing_processing.py or 03_vh_scan_processing.py only.')
    for value in tqdm(value_range):
        df = waveforms_dataframe.query(f"{query_parameter}=={value}")
        dataframe_record = {}
        for parameter in parameter_dict.keys():
            dataframe_record[f"{parameter}"] = {}
            ch_record = {}
            for ch in channel_to_pixel_dictionary.keys():
                channel = int(ch)
                df_ch = df.query(f"ch=={channel}")
                data = df_ch[f"{parameter}"].values.astype(float)
                # InterQuartile Range (IQR) technique to discard outliers
                q1 = np.quantile(data, 0.25)
                q3 = np.quantile(data, 0.75)
                iqr = q3 - q1
                mask = np.where((data > q1 - 6*iqr) & (data < q3 + 6*iqr))  # create a mask to filter data outside the IQR
                cleaned_data = data[mask]
                ch_record[ch] = {}
                ch_record[ch]["mean"] = np.mean(cleaned_data)
                ch_record[ch]["mean_error"] = np.std(cleaned_data)/np.sqrt(len(cleaned_data))  # standard mean error
                ch_record[ch]["rms"] = np.std(cleaned_data)
                ch_record[ch]["rms_error"] = compute_standard_error_of_standard_deviation(cleaned_data)
                if make_control_plots:
                    control_plots(channel, ax, parameter, data, cleaned_data, parameter_dict[parameter]["bin_width"], channel_to_pixel_dictionary)
            if make_control_plots:
                textx = fig.text(0.5, 0.05, f'{parameter_dict[parameter]["axis_label"]} ({parameter_dict[parameter]["unit_of_measure"]})', ha='center', va='center', rotation='horizontal', fontsize=15)
                texty = fig.text(0.09, 0.5, f'Occurrencies (per {parameter_dict[parameter]["bin_width"]} {parameter_dict[parameter]["unit_of_measure"]})', ha='center', va='center', rotation='vertical', fontsize=15)
                fig.suptitle(parameter_dict[parameter]["control_plot_suptitle"], fontsize=16)
                fig.savefig(os.path.join(f"{root_plot_dir}/{parameter_dict[parameter]['plot_dir']}", f"{query_parameter}{value}_{parameter_dict[parameter]['control_plot_fig_name']}.png"), bbox_inches='tight', pad_inches=0.1)
                ax[0,0].clear()
                ax[0,1].clear()
                ax[1,0].clear()
                ax[1,1].clear()
                Artist.remove(textx)
                Artist.remove(texty)
            dataframe_record[f"{parameter}"] = ch_record
        for ch in channel_to_pixel_dictionary.keys():
            statistics_dataframe = write_statistics_dataframe(dataframe=statistics_dataframe, script_name=script_name, parameter=value, scope_channel=int(ch), record=dataframe_record)
    return statistics_dataframe


def define_figures():
    f1, a1 = plt.subplots(ncols=2, nrows=2, sharex=True, sharey=True, figsize=(21,10))
    plt.subplots_adjust(hspace=.1, wspace=.05)  # adjust vertical space between subplots
    f2, a2 = plt.subplots(ncols=2, nrows=2, sharex=True, sharey=True, figsize=(21,10))
    plt.subplots_adjust(hspace=.1, wspace=.05)  # adjust vertical space between subplots
    f3, a3 = plt.subplots(ncols=2, nrows=2, sharex=True, sharey=True, figsize=(21,10))
    plt.subplots_adjust(hspace=.1, wspace=.05)  # adjust vertical space between subplots
    f4, a4 = plt.subplots(ncols=2, nrows=2, sharex=True, sharey=True, figsize=(21,10))
    plt.subplots_adjust(hspace=.1, wspace=.05)  # adjust vertical space between subplots
    f5, a5 = plt.subplots(ncols=2, nrows=2, sharex=True, sharey=True, figsize=(21,10))
    plt.subplots_adjust(hspace=.1, wspace=.05)  # adjust vertical space between subplots
    f6, a6 = plt.subplots(ncols=2, nrows=2, sharex=True, sharey=True, figsize=(21,10))
    plt.subplots_adjust(hspace=.1, wspace=.05)  # adjust vertical space between subplots
    f7, a7 = plt.subplots(ncols=2, nrows=2, sharex=True, sharey=True, figsize=(21,10))
    plt.subplots_adjust(hspace=.1, wspace=.05)  # adjust vertical space between subplots
    f8, a8 = plt.subplots(ncols=2, nrows=2, sharex=True, sharey=True, figsize=(21,10))
    plt.subplots_adjust(hspace=.1, wspace=.05)  # adjust vertical space between subplots
    f9, a9 = plt.subplots(ncols=2, nrows=2, sharex=True, sharey=True, figsize=(21,10))
    plt.subplots_adjust(hspace=.1, wspace=.05)  # adjust vertical space between subplots
    f10, a10 = plt.subplots(ncols=2, nrows=2, sharex=True, sharey=True, figsize=(21,10))
    plt.subplots_adjust(hspace=.1, wspace=.05)  # adjust vertical space between subplots
    f11, a11 = plt.subplots(ncols=2, nrows=2, sharex=True, sharey=True, figsize=(21,10))
    plt.subplots_adjust(hspace=.1, wspace=.05)  # adjust vertical space between subplots
    f12, a12 = plt.subplots(ncols=2, nrows=2, sharex=True, sharey=True, figsize=(21,10))
    plt.subplots_adjust(hspace=.1, wspace=.05)  # adjust vertical space between subplots
    return f1, a1, f2, a2, f3, a3, f4, a4, f5, a5, f6, a6, f7, a7, f8, a8, f9, a9, f10, a10, f11, a11, f12, a12


def compute_standard_mean_error(data):
    return np.std(data)/sqrt(data.shape[0])


def compute_standard_error_of_standard_deviation(data):
    # https://stats.stackexchange.com/questions/156518/what-is-the-standard-error-of-the-sample-standard-deviation
    return (1/(2*np.std(data)))*sqrt((1/data.shape[0])*(moment(data,moment=4)-((np.std(data))**4)*(data.shape[0]-3)/(data.shape[0]-1)))


def three_sigma_quantiles_dataset(data):
    # filter dataset to central 0.997 quantiles
    ql = np.quantile(data, 0.0015)
    qu = np.quantile(data, 0.9985)
    mask = np.where((data > ql) & (data < qu))
    central_data = data[mask]
    return central_data
