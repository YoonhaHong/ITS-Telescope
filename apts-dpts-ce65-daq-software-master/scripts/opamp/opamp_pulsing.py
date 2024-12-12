#!/usr/bin/env python3

__author__ = "Roberto Russo"
__maintainer__ = "Roberto Russo"
__email__ = "r.russo@cern.ch"
__status__ = "Development"
__version__ = "1.10.0"

from mlr1daqboard import APTSDAQBoard
from labequipment import HAMEG
import logging
import argparse
import os, json
import pickle
import numpy as np
from tqdm import tqdm
from time import sleep
import sys
sys.path.append(os.path.join(os.path.dirname(__file__),'../../opamp/'))
import opamp_helpers as helpers


def acquire(args, oscilloscope, gain_calibration_dict, daq):
    if not args.fixed_vreset_measurement:
        vres_min, vres_max = get_vres_range_extr(gain_calibration_dict, args.vbb)
        args.vres_range = list(range(vres_min, vres_max+1, 10))
    else:
        args.vres_range = [args.vreset]
    # prepare dictionary with vreset values to be measured with related baseline and gain and print it for logging purposes
    with open(os.path.join(args.output_dir, "measured_settings.json"),'w') as measurement_dict:
        vbb_dict = get_measurement_dict(args.vres_range, gain_calibration_dict, args.vbb, args.fixed_vreset_measurement)
        json.dump(vbb_dict, measurement_dict, indent=4)
    with open(os.path.join(args.output_dir, args.fname+".json"),'w') as file_handle:
        json.dump(vars(args), file_handle, indent=4)

    # setting the OPAMP configuration
    helpers.set_dacs(daq, args)
    daq.set_pulse_sel(sel0=True,sel1=True)  # pulse the entire matrix
    daq.configure_readout(pulse=True, n_frames_before=args.n_frames_before, n_frames_after=args.n_frames_after,sampling_period=args.sampling_period)

    logging.info('Starting readout')
    raw_data_dict = {}
    adc_bytearray = bytearray()
    scope_bytearray = bytearray()
    for vres in args.vres_range:
        daq.set_vdac('AP_VRESET', vres)
        sleep(0.4)
        baselines, scope_max_voltage = find_max_baseline(vbb_dict, vres)  # in mV
        baselinedict = helpers.get_baseline_for_trigger(args.inner_pixel_connections, baselines)
        offset = scope_max_voltage + args.voltage_division - (args.voltage_division*oscilloscope.VOLTAGE_DIVISION)/2  # adjust the scope offset
        oscilloscope.set_offset(search=False, channels_offset=(offset, offset, offset, offset))
        oscilloscope.set_trigger(baseline=(baselinedict["baseline1"], baselinedict["baseline2"], baselinedict["baseline3"], baselinedict["baseline4"]), relative_trigger_level_volt=args.scope_relative_trigger_level_volt)
        sleep(1.0)
        for itrg in tqdm(range(args.ntrg),desc=f'Vreset {vres} - Trigger'):
            oscilloscope.arm_trigger()
            sleep(0.1)
            adc_data=daq.read_event()  # pulse matrix + get outer pixels data (read out via ADC)
            while not oscilloscope.is_ready():
                sleep(0.001)
            osc_data = oscilloscope.readout()  # inner pixels (read out via oscilloscope)
            osc_binary_data = bytearray()
            for ch in osc_data:
                osc_binary_data.extend(ch)
            osc_data = osc_binary_data
            if itrg == 0:
                scope_adc_dict = helpers.get_wf_conversion_factors(oscilloscope, args.scope_channels)  # only after first trigger, read the time and voltage origin and sampling increment to be saved in a .json file
            adc_bytearray.extend(adc_data)
            scope_bytearray.extend(osc_data)
    raw_data_dict['ADC'] = adc_bytearray
    raw_data_dict['scope'] = scope_bytearray
    with open(os.path.join(args.output_dir, f"{args.fname}.raw"),'wb') as raw_file, \
         open(os.path.join(args.output_dir, "scope_channel_settings.json"), "w") as conversion_factors_file:
        pickle.dump(raw_data_dict, raw_file, protocol=pickle.HIGHEST_PROTOCOL)
        json.dump(scope_adc_dict, conversion_factors_file, indent=4)
    oscilloscope.clear_waveform_axis_variables()
    logging.info('Done')


def get_vres_range_extr(baseline_dict, vbb):
    vres_min = []
    vres_max = []
    for p in baseline_dict[str(vbb)].keys():
        vres_min.append(baseline_dict[str(vbb)][p]['vreset'][0])
        vres_max.append(baseline_dict[str(vbb)][p]['vreset'][-1])
    vres_extr_min = np.max(vres_min)
    vres_extr_max = np.min(vres_max)
    return vres_extr_min,vres_extr_max


def get_measurement_dict(vreset_range, baseline_dict, vbb, single_vreset):
    vbb_dict = {}
    pixels_dict = {}
    if single_vreset:
        for p in baseline_dict[str(vbb)]['pixels'].keys():
            pixel_dict = {}
            pixel_dict['baseline'] = [baseline_dict[str(vbb)]['pixels'][p]['baseline']]
            pixel_dict['baseline_rms'] = [baseline_dict[str(vbb)]['pixels'][p]['baseline_rms']]
            pixels_dict[p] = pixel_dict
    else:
        for p in baseline_dict[str(vbb)].keys():
            pixel_dict = {}
            p_baseline = []
            p_baseline_rms = []
            p_gain = []
            p_gain_rms = []
            for vres in vreset_range:
                index = baseline_dict[str(vbb)][p]['vreset'].index(vres)
                p_baseline.append(baseline_dict[str(vbb)][p]['baseline'][index])
                p_baseline_rms.append(baseline_dict[str(vbb)][p]['baseline_rms'][index])
                p_gain.append(baseline_dict[str(vbb)][p]['gain'][index])
                p_gain_rms.append(baseline_dict[str(vbb)][p]['gain_rms'][index])
            pixel_dict['baseline'] = p_baseline
            pixel_dict['baseline_rms'] = p_baseline_rms
            pixel_dict['gain'] = p_gain
            pixel_dict['gain_rms'] = p_gain_rms
            pixels_dict[p] = pixel_dict
    vbb_dict['vreset_range'] = vreset_range
    vbb_dict['pixels'] = pixels_dict
    return vbb_dict


def find_max_baseline(measurement_dict, vreset):
    index = measurement_dict['vreset_range'].index(vreset)
    baseline_list = []
    baseline_rms_list = []
    for p in measurement_dict['pixels'].keys():
        baseline_list.append(measurement_dict['pixels'][p]['baseline'][index])
        baseline_rms_list.append(measurement_dict['pixels'][p]['baseline_rms'][index])
    scope_voltage_range = np.max(baseline_list+baseline_rms_list)*1E-3  # in V
    return baseline_list, scope_voltage_range


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OPAMP measurement of pulsed pixels at varying Vreset",formatter_class=argparse.ArgumentDefaultsHelpFormatter,add_help=False)
    helpers.add_common_args(parser)
    parser.add_argument('gain_calibration_file',metavar="GAIN_FILE", help='.json file with data resulting from gain calibration.')
    helpers.add_daq_args(parser)
    parser.add_argument('--scope_relative_trigger_level_volt',type=float,default=-10E-3,help='Oscilloscope trigger level with respect to pixel baseline (in V).')
    helpers.add_common_output_args(parser)
    args = parser.parse_args()
    helpers.finalise_args(args)
    helpers.setup_output_files(args, args.prefix[6:-1])
    with open(args.gain_calibration_file, 'r') as j:
        data_json = json.load(j)
    try:
        logging.info('Configuring DAQ')
        mlr1 = APTSDAQBoard(serial=args.serial,calibration=args.proximity)
        if mlr1.is_chip_powered() is False:
            logging.info("APTS was off --> turning ON")
            mlr1.power_on()
        assert mlr1.chip_type == 'OPAMP', f'Expected OPAMP calibration file, not {mlr1.chip_type}.'

        logging.info('Configuring Scope')
        scope = None
        scope = args.scope(address=args.ip_address, timeout_sec=25, active_channels=args.scope_channels)
        assert scope != None, f"Cannot connect to {args.scope.__name__}"
        scope.clear()
        args.scope = args.scope.__name__  # store the instantiated scope class as a string such that the information can be later saved in a .json file
        logging.info('Scope configured')
        h=HAMEG(args.hameg_path)
        assert args.daq_channel != args.vbb_channel, "The DAQ power channel and the vbb channel must be different"
        if args.vbb_scan:
            base_directory = args.output_dir
            assert args.vbb_channel in np.arange(1,h.n_ch+1), "The vbb channel number should be consistent with the power supply connections"
            for vbb in args.vbb_array:
                h.set_volt(args.vbb_channel,vbb)
                sleep(1)
                args.output_dir = os.path.join(base_directory,f"vbb_{vbb:.1f}")
                os.makedirs(args.output_dir, exist_ok=True)
                args.vbb = vbb
                scope.configure(vdiv=(args.voltage_division, args.voltage_division, args.voltage_division, args.voltage_division), tdiv=args.time_division, sampling_period_s=args.scope_sampling_period)
                args.scope_memory_depth = int(np.rint(scope.number_of_points))  # number of acquired points per saved waveform
                acquire(args, scope, data_json, mlr1)
                scope.clear()
        else:
            args.vbb = h.status()[3][args.vbb_channel-1]
            args.output_dir = os.path.join(base_directory,f"vbb_{args.vbb:.1f}")
            os.makedirs(args.output_dir, exist_ok=True)
            scope.configure(vdiv=(args.voltage_division, args.voltage_division, args.voltage_division, args.voltage_division), tdiv=args.time_division, sampling_period_s=args.scope_sampling_period)
            args.scope_memory_depth = int(np.rint(scope.number_of_points))  # number of acquired points per saved waveform
            acquire(args, scope, data_json, mlr1)
            scope.clear()
        h.set_volt(args.vbb_channel,0)
        del scope
    except KeyboardInterrupt:
        logging.info('User stopped.')
    except OSError as ose:
        logging.exception(ose)
        logging.info("Didn't find the instrument. Check the connection string.")
        logging.fatal('Terminating!')
    except Exception as e:
        logging.exception(e)
        logging.fatal('Terminating!')

