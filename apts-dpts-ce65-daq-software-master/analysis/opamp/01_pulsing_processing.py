#!/usr/bin/env python3

__author__ = "Roberto Russo"
__maintainer__ = "Roberto Russo"
__email__ = "r.russo@cern.ch"
__status__ = "Development"

from opamp_decode import raw_to_npz
import logging, argparse, os, re, json
import numpy as np
from glob import glob
from tqdm import tqdm
import analysis_utils as au


def pulsing_processing(args):
    scanned_vbb = au.list_vbb_dir(args.data_path)
    for vbb_dir in tqdm(scanned_vbb, desc="Vbb"):
        vbb = vbb_dir.split("/")[-1]
        data_json_file = glob(f"{vbb_dir}/opamp_pulsing_*.json")[0]
        with open(data_json_file, 'r') as j:
            data_json = json.load(j)
        pixel_dict = data_json['inner_pixel_connections']
        scope_measured_pixels = []
        for p in pixel_dict.keys():
            scope_measured_pixels.append(int(re.findall(r'J(\d+)', pixel_dict[p])[0]))
        vres_range = data_json['vres_range']
        ntrg = data_json['ntrg']  # number of triggers acquired per measured configuration
        with open(os.path.join(vbb_dir, "scope_channel_settings.json"), 'r') as j:
            scope_ADC_to_mV_json = json.load(j)
        raw_data_file = glob(f"{vbb_dir}/opamp_pulsing_*.raw")[0]
        if not os.path.exists(raw_data_file.replace('.raw','_decoded.npz')):
            raw_to_npz(raw_data_file, raw_data_file.replace('.raw','_decoded.npz'), len(scope_measured_pixels), data_json['scope_memory_depth'], args.scope_data_precision, header=args.header)
        waveforms = np.load(raw_data_file.replace('.raw','_decoded.npz'))
        waveforms = waveforms['scope'] # scope waveforms processed only
        df_waveforms = au.make_waveforms_dataframe(script_name=os.path.basename(__file__))
        for i in tqdm(range(waveforms.shape[0]), leave=False, desc="Waveform"):
            vres = vres_range[i//ntrg]
            for p in range(waveforms.shape[1]):
                scope_channel = list(pixel_dict.keys())[p]
                adc_waveform = waveforms[i, p, :]
                graph, resampled_graph, baseline, baseline_rms, baseline_noise_point, underline, underline_rms, underline_noise_point, t0_bin, CFD_range, CFD_times = au.analyse_waveform(adc_signal=adc_waveform,\
                    scope_channel=scope_channel, scope_axis_dict=scope_ADC_to_mV_json, channel_to_pixel_dict=pixel_dict, baseline_and_underline_evaluation_points=\
                    (args.baseline_evaluation_interval,args.baseline_first_time_before_t0,args.underline_evaluation_interval,args.underline_first_time_after_t0), script_name=os.path.basename(__file__),\
                    signal_extraction_method=args.signal_extraction_method, resample_waveform=args.resample_waveform, integration_time=args.integration_time)
                if (baseline-underline > 1.5) and (CFD_times[0] != -999.) and (CFD_times[1] != -999.) and (CFD_times[5] != -999.) and (CFD_times[9] != -999.):
                    if args.debug_plot:
                        au.plot_waveform(graph=graph, baseline=baseline, underline=underline, t0_bin=t0_bin, scope_axis_dict=scope_ADC_to_mV_json, CFD_times=CFD_times, CFD_search_limit=CFD_range[1],\
                            scope_channel=scope_channel, resampled_graph=resampled_graph, vbb=vbb[-3:], vreset=vres, trigger=int(i%ntrg))
                    df_waveforms = au.write_waveforms_dataframe(dataframe=df_waveforms, script_name=os.path.basename(__file__), parameter=vres, scope_channel=int(scope_channel), trigger=int(i%ntrg),\
                        baseline_estimators=(baseline, baseline_rms, baseline_noise_point), underline_estimators=(underline, underline_rms, underline_noise_point), CFD_times=CFD_times)
        df_waveforms.to_csv(os.path.join(vbb_dir, "waveforms.csv"), sep='|', index=False)  # save file
        df_statistics = au.make_statistics_dataframe(script_name=os.path.basename(__file__))
        df_statistics = au.process_waveforms_dataframe(waveforms_dataframe=df_waveforms, statistics_dataframe=df_statistics, script_name=os.path.basename(__file__), value_range=vres_range,\
            channel_to_pixel_dictionary=pixel_dict, make_control_plots=args.control_plots, baseline_and_underline_evaluation_points=\
            (args.baseline_evaluation_interval,args.baseline_first_time_before_t0,args.underline_evaluation_interval,args.underline_first_time_after_t0), output_plot_dir=vbb_dir)
        df_statistics.to_csv(os.path.join(vbb_dir, "pulsing_statistics.csv"), sep='|', index=False)  # save file
        with open(os.path.join(vbb_dir, "pulsing_processing_arguments.json"),'w') as file_handle:
            json.dump(vars(args), file_handle, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APTS OPAMP routine to process data of pulsed pixels at varying vreset.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--data_path', '-d', help='Directory for input files.')
    parser.add_argument('--scope_data_precision', '-s', type=int, choices=[1, 2, 4], default=1, const=1, nargs='?', help='Number of bytes used to store scope waveform data.')
    parser.add_argument('--header', '-hd', nargs='+', default=None, help='Remove the header by giving: byte in header  byte in footer  num pulses  num points scanned  num channels .')
    parser.add_argument('--signal_extraction_method','-sem',type=str, choices=['threshold','derivative'],default='derivative',const='derivative',nargs='?',help='t0 finder algorithm and related methods to extract baseline, underline and amplitude.')
    parser.add_argument('--resample_waveform', action='store_true', help='Software resampling of oscilloscope acquired waveforms with sampling interval of 12.5 ps.')
    parser.add_argument('--control_plots', action='store_true', help='Produce signal amplitude and falltime histograms for each vreset.')
    parser.add_argument('--debug_plot', action='store_true', help='Show plot of the analyzed waveform.')
    args = parser.parse_args()
    try:
        if args.signal_extraction_method == "threshold":
            args.baseline_evaluation_interval = 2.5  # in ns
            args.baseline_first_time_before_t0 = 15  # first time before t0 in ns
            args.underline_evaluation_interval = 1.25  # in ns
            args.underline_first_time_after_t0 = 21.5  # first time after t0 in ns
            args.integration_time = None  # no integration time is needed for the threshold-based t0 identifier
        else:
            args.baseline_evaluation_interval = 2.5  # in ns
            args.baseline_first_time_before_t0 = 15  # first time before t0 in ns
            args.underline_evaluation_interval = 2.5  # in ns
            args.underline_first_time_after_t0 = 15  # first time after t0 in ns
            args.integration_time = 17.5  # integration time to find t0 in ns
        pulsing_processing(args)
    except KeyboardInterrupt:
        logging.info('User stopped.')
    except Exception as e:
        logging.exception(e)
        logging.fatal('Terminating!')
