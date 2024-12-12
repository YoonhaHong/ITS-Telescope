#!/usr/bin/env python3

__author__ = "Roberto Russo, Umberto Savino"
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


def acquire(args, oscilloscope,daq):
    with open(os.path.join(args.output_dir, args.fname+".json"),'w') as file_handle:
        json.dump(vars(args), file_handle, indent=4)
    
    # setting the OPAMP configuration
    helpers.set_dacs(daq, args)
    if args.pulse!=None: daq.set_pulse_sel(sel0=(args.pulse&1),sel1=((args.pulse>>1)&1))
    daq.configure_readout(trg_type=args.trg_type,trg_thr=args.trg_thr,pulse=(args.pulse!=None),n_frames_before=args.n_frames_before, n_frames_after=args.n_frames_after,sampling_period=args.sampling_period)
    if args.trg_pixels!=None: daq.set_internal_trigger_mask(trg_pixels=args.trg_pixels)

    logging.info('Starting readout')
    raw_data_dict = {}
    adc_bytearray = bytearray()
    scope_bytearray = bytearray()

    for itrg in tqdm(range(args.ntrg),desc=f'Trigger'):
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OPAMP measurement of pulsed pixels",formatter_class=argparse.ArgumentDefaultsHelpFormatter,add_help=False)
    parser.add_argument('--pulse','-p',default=None,help='PULSE: s(first pixel), out(outer), in(inner), f(full)',type=lambda t: {'s':0,'out':1,'in':2,'f':3}[t] )
    parser.add_argument('--trg_pixels','--trg-pixels','-tp',nargs='+',type=lambda px: px if px=='inner' else tuple(map(int,px.split(','))),help='Pixels to use as internal trigger source, e.g. "-tp inner" to use only central pixels", or "-tp 0,0 2,1" to enable individual pixels addressing them by (col,row)')
    parser.add_argument('--trg_type','-ty',default=1, help='trigger: ext, int',type=lambda t: {'ext':0,'int':1}[t])
    parser.add_argument('--trg_thr','-tt',type=int,help='auto trigger threshold in ADC counts (default=20)',default=20)
    
    helpers.add_common_args(parser)
    helpers.add_daq_args(parser)
    parser.add_argument('--scope_relative_trigger_level_volt',type=float,default=-10E-3,help='Oscilloscope trigger level with respect to pixel baseline (in V).')
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
                scope.set_offset(search=True)
                scope.set_trigger(relative_trigger_level_volt=args.scope_relative_trigger_level_volt)
                logging.info('Scope configured')
                acquire(args, scope, mlr1)
                scope.clear()
        else:
            args.vbb = h.status()[3][args.vbb_channel-1]
            scope.configure(vdiv=(args.voltage_division, args.voltage_division, args.voltage_division, args.voltage_division), tdiv=args.time_division, sampling_period_s=args.scope_sampling_period)
            args.scope_memory_depth = int(np.rint(scope.number_of_points))  # number of acquired points per saved waveform
            scope.set_offset(search=True)
            scope.set_trigger(relative_trigger_level_volt=args.scope_relative_trigger_level_volt)
            logging.info('Scope configured')
            acquire(args, scope, mlr1)
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

