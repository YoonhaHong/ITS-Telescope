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
import opamp_helpers as helpers


def apts_opamp_gain(args, oscilloscope, daq):
    vres_range = np.arange(20, 901, 10)
    if args.fixed_vreset_measurement:
        vres_range = np.array([args.vreset])
    with open(os.path.join(args.output_dir, args.fname+".json"),'w') as file_handle:
        json.dump(vars(args), file_handle, indent=4)
    
    # setting the OPAMP configuration
    helpers.set_dacs(daq, args)
    daq.configure_readout(n_frames_before=args.n_frames_before, n_frames_after=args.n_frames_after,sampling_period=args.sampling_period)
    
    logging.info('Starting readout')
    raw_data_dict = {}
    adc_bytearray = bytearray()
    scope_bytearray = bytearray()
    for vres in vres_range:
        daq.set_vdac('AP_VRESET', vres)
        sleep(1.0)
        for itrg in tqdm(range(args.ntrg),desc=f'Vreset {vres} - Trigger'):
            oscilloscope.arm_trigger(force=True)
            adc_data=daq.read_event()  # outer pixels (read out via ADC)
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OPAMP gain measurement",formatter_class=argparse.ArgumentDefaultsHelpFormatter,add_help=False)
    helpers.add_common_args(parser)
    helpers.add_daq_args(parser)
    helpers.add_common_output_args(parser)
    args = parser.parse_args()
    helpers.finalise_args(args)
    helpers.setup_output_files(args, args.prefix[6:-1])
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
        args.voltage_division = 75E-3  # set 75 mV per division
        args.voltage_offset = 300E-3  # set 300 mV of voltage offset
        args.time_division = np.round((6.25E-9 * args.sampling_period * (args.n_frames_before + args.n_frames_after))/scope.TIME_DIVISION, 9)  # round to the 9th digit (ns) to prevent floating point error
        args.scope_sampling_period = 6.25E-9 * args.sampling_period
        scope.configure(vdiv=(args.voltage_division, args.voltage_division, args.voltage_division, args.voltage_division), tdiv=args.time_division, sampling_period_s=args.scope_sampling_period)
        args.scope_memory_depth = int(np.rint(scope.number_of_points))  # number of acquired points per saved waveform
        scope.set_offset(search=False, channels_offset=(args.voltage_offset, args.voltage_offset, args.voltage_offset, args.voltage_offset))
        scope.set_trigger_sweep(mode="AUTO")  # set the scope trigger sweep in AUTO mode
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
                os.makedirs(args.output_dir,exist_ok=True)
                args.vbb = vbb
                apts_opamp_gain(args,scope,mlr1)
        else:
            args.vbb = h.status()[3][args.vbb_channel-1]
            apts_opamp_gain(args,scope,mlr1)
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
