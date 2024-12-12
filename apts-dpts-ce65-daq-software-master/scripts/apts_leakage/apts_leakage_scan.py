# this is a python script

#=======================================================================
#   Copyright (C) 2023 Univ. of Bham  All rights reserved.
#   
#   		FileName：		apts_leakage_scan.py
#   	 	Author：		LongLI <long.l@cern.ch>
#   		Time：			2023.10.31
#   		Description：
#
#======================================================================

import datetime
import logging
from pathlib import Path
import argparse
import os
from time import sleep
import sys
import leakage_data_taking
from labequipment import HAMEG
sys.path.append('../../apts/')
sys.path.append('../../analysis/apts')
import apts_readout
import apts_gain
import apts_helpers as helpers

def apts_leakage_scan(args):

    # power on the DAQ board and sensor 
    h = HAMEG(args.hameg_path)
    
    base_folder = args.output_dir
    
    h.set_volt(args.vbb_channel, 0)
    h.set_volt(args.daq_channel, 5)
    h.power(True, args.daq_channel)
    h.power(True, args.vbb_channel)
    print('Daq and carried board powered on')
    sleep(4)
    # flash the bit file to DAQ board
    os.system(f'../../tools/mlr1-daq-program --fx3 ../../tools/fx3.img --fpga ../../tools/{args.firmware}')
    for temp in args.temp_range:  # temperature control, not available at Bham, to be completed
        for vbb in args.vbb_array:
            h.set_volt(args.vbb_channel, vbb) 
            for ir in args.ireset_array:
                print(f'Start data taking at Vbb {vbb}V, ir {ir}...')

                gain_path = base_folder+f'/{args.proximity}/{args.chip_ID}/calib/temp{temp}/vbb_{vbb}/ir_{ir}/'
                if not os.path.exists(gain_path): os.makedirs(gain_path)
                # do apts_gain first
                cmd = f'python3 ../../apts/apts_gain.py {args.proximity} {args.chip_ID} -ir {ir} --ntrg_vres {args.ntrg_vres} -exw 2 -o {gain_path}'
                os.system(cmd)
                gain_path=''
                # do leakage_data_taking
                data_path = base_folder+f'/{args.proximity}/{args.chip_ID}/data'
                if not os.path.exists(data_path): os.makedirs(data_path)
                args.output_dir = data_path
                args.vbb = vbb
                args.ireset = ir
                args.Temp = temp
                leakage_data_taking.data_taking(args)
                data_path = ''
    
    h.power(False, args.daq_channel)
    h.power(False, args.vbb_channel)


if __name__ == '__main__':
    default_data_dir = os.path.relpath(os.path.join(os.path.dirname(__file__), '../../Data'))

    parser = argparse.ArgumentParser(description='All scripts for vbb and ireset scan')
    parser.add_argument('--firmware', '-fw', default='0x107E7316.bit', help='Version of FPGA firmware file.')
    parser.add_argument('--hameg_path', '-hpath', default='/dev/serial/by-id/usb-HAMEG_HAMEG_HO720_000148344-if00-port0', help='Path to the HAMEG device.')
    parser.add_argument('--daq_channel', '-daqc', type=int, default=1, help='Channel of the power supply connected to the DAQ (5V)')
    parser.add_argument('--vbb_channel', '-vbbc', type=int, default=2, help='Channel of the power supply connected to the VBB')
    parser.add_argument('--ntrg', '-n', type=int, help='number of triggers', default=1000)
    parser.add_argument('--ntrg_vres', '-nvres', type=int, help='number of triggers per vreset step', default=50)
    parser.add_argument('--trg_type', '-ty', default=1, help='trigger: ext, int', type=lambda t:{'ext':0, 'int':1}[t])
    parser.add_argument('--trg_thr', '-tt', type=int, help='auto trigger threshold in ADC unit', default = 20)
    parser.add_argument('--vbb_array', '-vbbr', nargs='+', type=float, default= [0.0, 1.2, 2.4, 3.6, 4.8], help='Only for book keeping (no effect): Array of Vbb values (ex.: -vbbr 0. 1.4 2 ).')
    parser.add_argument('--ireset_array', '-irr', nargs='+', type=float, default= [0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6], help='Reset current array for leakage data taking')
    parser.add_argument('--temp_range', '-tr', nargs='+', type=float, default= [20], help='Temperature array for leakage data taking')
    parser.add_argument('--prefix', default='apts_', help='Output file prefix')
    parser.add_argument('--Temp', default=20, type=float, help='Temperature of the sensor in degree Celsius')
    parser.add_argument('--vbb', type=float, help='Only for bookkeeping (no effect): Bias voltage applied in unit of V (e.g. 0 , 1.2 ,...).')
    helpers.add_common_args(parser)
    args = parser.parse_args()
    helpers.finalise_args(args)
    apts_leakage_scan(args)
