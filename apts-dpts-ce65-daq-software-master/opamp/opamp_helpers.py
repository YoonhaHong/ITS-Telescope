from mlr1daqboard.opamp_scope import OPAMPscope
import logging
import os,re, sys
from datetime import datetime
from pathlib import Path
from time import sleep


def add_common_args(parser):
    parser.add_argument('proximity',metavar="PROXIMITY",help='Proximity card name (e.g. OPAMP-010). The name must be in the same format as the corresponding calibration file.')
    parser.add_argument('chip_ID',metavar="CHIP",help='Chip name (e.g. W22AO10Pb14)')
    chip_operation = parser.add_argument_group('Chip operation arguments', 'Chip biases and operation settings.')
    chip_operation.add_argument('--ntrg',type=int,help='Number of triggers per measured configuration',default=100)
    chip_operation.add_argument('--n_frames_before','--n-frames-before','-nfb',default=100, type=int, help='Number of ADC frames before trigger/signal 1-100.')
    chip_operation.add_argument('--n_frames_after','--n-frames-after','-nfa',default=100, type=int, help='Number of ADC frames after trigger/signal 1-700.')
    chip_operation.add_argument('--sampling_period','--sampling-period','-sp',default=40, type=int, help='ADC sampling period: 1 unit = 6.25 ns, minimum value = 40.')
    chip_operation.add_argument('--ibias4','-ib4',default=2600, type=float,help='IBIAS4 DAC setting in uA.')
    chip_operation.add_argument('--vcasp','-vcp',default=270, type=float,help='VCASP DAC setting in mV.')
    chip_operation.add_argument('--vcasn','-vcn',default=900, type=float,help='VCASN DAC setting in mV.')
    chip_operation.add_argument('--ibiasn','-ibn',default=500, type=float,help='IBIASN DAC setting in uA.')
    chip_operation.add_argument('--ireset','-ir',default=1, type=float,help='IRESET DAC setting in uA.')
    chip_operation.add_argument('--ibiasp','-ibp',default=45, type=float,help='IBIASP DAC setting in uA.')
    chip_operation.add_argument('--ibias3','-ib3',default=850, type=float,help='IBIAS3 DAC setting in uA.')
    chip_operation.add_argument('--vh','-v',default=1200, type=float,help='VH DAC setting in mV.')
    chip_operation.add_argument('--vreset','-vr',default=400, type=float,help='VRESET DAC setting in mV.')
    chip_operation.add_argument('--expert_wait','-exw',default=9,type=int,help='Only for expert (seconds unit).')
    chip_operation.add_argument('--fixed_vreset_measurement',action='store_true',help='Perform the measurement without vreset scan. The chip will be operated with the value passed by the argument vreset.')
    misc_group = parser.add_argument_group('Miscellaneous arguments')
    misc_group.add_argument('--serial','-s',help='serial number of the DAQ board')
    misc_group.add_argument("--log-level", default="INFO", help="Logging level.")
    misc_group.add_argument('--help','-h',action="help",help='show this help message and exit')


def add_daq_args(parser):
    parser.add_argument('scope',metavar="OSCILLOSCOPE",choices=[s for s in OPAMPscope.__subclasses__()],
                           type=lambda n: next((s for s in OPAMPscope.__subclasses__() if len(n) >= 3 and n.lower() in s.__name__.lower()), n),
                           help='Scope used, i.e. at least first three letters of the scope name. '+
                           'Available scopes: '+str([s.__name__ for s in OPAMPscope.__subclasses__()]))
    oscilloscope = parser.add_argument_group('Oscilloscope related arguments', 'Oscilloscope settings.')
    oscilloscope.add_argument('--ip_address','-ip',type=str,required=True, help='IP address of the scope.')
    oscilloscope.add_argument('--scope_channels','-sc',type=int,choices=[1,2,3,4],nargs='+',default=[1,2,3,4],help='scope channels to be acquired.')
    oscilloscope.add_argument('--time_division','-td',type=float,default=5E-9,help='Horizontal division scale in seconds.')
    oscilloscope.add_argument('--scope_sampling_period','-ssp',type=float,required=True,help='Oscilloscope sampling period in seconds (ex: 0.0625E-9).')
    oscilloscope.add_argument('--voltage_division','-vd',type=float,default=20E-3,help='Vertical division scale of the selected channel in volts.')
    oscilloscope.add_argument('--voltage_offset','-vo',type=float,default=300E-3,help='Voltage offset on the scope display of the selected channel in volts.')
    oscilloscope.add_argument('--inner_pixel_connections','-ipc',type=dict,default={'1':'J5','2':'J6','3':'J9','4':'J10',},help='Scope channel with the corresponding pixel of the matrix.')
    rev_bias_scan = parser.add_argument_group('Reverse bias scan arguments', 'Vbb scan and list of reverse biases to be measured.')
    rev_bias_scan.add_argument('--vbb_scan',action='store_true',help='Perform a scan of VBB')
    rev_bias_scan.add_argument('--vbb_array','-vbb', nargs='+',type=float, default=[0.0, 0.6, 1.2, 1.8, 2.4, 3.0, 3.6, 4.8], help='Array of Vbb values (example: -vbb 0. 1.4 2.).')
    power_supply = parser.add_argument_group('Power supply related arguments', 'Power supply device link and used channel to provide reverse bias voltage.')
    power_supply.add_argument('--hameg-path','-hpath',type=str,required=True,help='Path to the HAMEG device.')
    power_supply.add_argument('--daq_channel','-daqc',type=int,required=True,help='Channel of the power supply connected to the DAQ (5V)')
    power_supply.add_argument('--vbb_channel','-vbbc',type=int,required=True,help='Channel of the power supply connected to the VBB')


def add_common_output_args(parser):
    default_data_dir = os.path.realpath(os.path.join(os.path.dirname(__file__),"../Data"))
    output_group = parser.add_argument_group('Common output files arguments', 'The arguments common to the output files produced by the scripts.')
    output_group.add_argument('--prefix',default=Path(sys.argv[0]).stem+"_",help='Output file prefix')
    output_group.add_argument('--suffix',default='',help='Output file suffix')
    output_group.add_argument('--output-dir','-o',default=default_data_dir,help='Directory for output files.')


def finalise_args(args):
    args.pwell = args.sub = args.vbb_array
    try:
        args.wafer, args.version, args.chip = re.findall('W([0-9]+)AO10([PB]?)[ab]([0-9]+$)', args.chip_ID)[0]
    except IndexError:
        raise ValueError(f"Unexpected format for chip ID, expected 'W'+wafer_number+'AO10'+flavour+board_label+chip_number")
    if args.wafer=="22": args.split = "4 (opt.)"
    elif args.wafer=="13": args.split = "1 (opt.)"
    else: raise ValueError(f"Unrecognised wafer: {args.wafer}, shoulde be either '13' or '22'")


def make_output_dir(root_output_path,chipID,calibration):
    path = os.path.join(root_output_path, f"{chipID}/{calibration}_calibration/{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    if not os.path.exists(path): os.makedirs(path)
    return path


def setup_output_files(args,procedure):
    if args.serial:
        args.fname = f"{args.prefix}{args.serial}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{args.suffix}"
    else:
        args.fname = f"{args.prefix}{datetime.now().strftime('%Y%m%d_%H%M%S')}{args.suffix}"
    if not args.output_dir:
        args.output_dir = f"../../Data/{args.prefix}{datetime.now().strftime('%Y%m%d_%H%M%S')}{args.suffix}"
    else:
        args.output_dir = make_output_dir(args.output_dir, args.chip_ID, procedure)
    logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                       filename=os.path.join(args.output_dir,args.fname+".log"),filemode='w')
    log_term = logging.StreamHandler()
    log_term.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    log_term.setLevel(logging.getLevelName(args.log_level.upper()))
    logging.getLogger('pyvisa').setLevel(logging.INFO)
    logging.getLogger().addHandler(log_term)


def set_dacs(daqboard, args):
    daqboard.set_idac('AP_IBIAS4OPA_DP_IBIASN',  args.ibias4) # unit uA
    daqboard.set_idac('CE_COL_AP_IBIASN',        args.ibiasn)
    daqboard.set_idac('CE_PMOS_AP_DP_IRESET',    args.ireset)
    daqboard.set_idac('AP_IBIASP_DP_IDB',        args.ibiasp)
    daqboard.set_idac('AP_IBIAS3_DP_IBIAS',      args.ibias3)
    daqboard.set_vdac('AP_VCASP_MUX0_DP_VCASB',  args.vcasp)  # unit mV
    daqboard.set_vdac('AP_VCASN_MUX1_DP_VCASN',  args.vcasn)
    daqboard.set_vdac('AP_VRESET',               args.vreset)
    daqboard.set_vdac('CE_VOFFSET_AP_DP_VH',     args.vh)
    
    logging.info(f"DAC values setting, waiting {args.expert_wait} seconds for Ia current to stabilize...")
    for _ in range(args.expert_wait):
        logging.info(f"   Ia = {daqboard.read_isenseA():0.2f} mA")
        sleep(1)


def get_wf_conversion_factors(oscilloscope, active_channels):
    dt,t0,dvs,v0s = oscilloscope.get_waveform_axis_variables()
    chs_dict = {}
    chs_dict['dt'] = float(dt)
    chs_dict['t0'] = float(t0)
    for pos, c in enumerate(active_channels):
        chs_dict[f'dv_ch{c}'] = dvs[pos]
        chs_dict[f'v0_ch{c}'] = v0s[pos]
    return chs_dict


def get_baseline_for_trigger(connection_dict, baseline_list):
    baselineDict = {}
    baselineDict["baseline1"] = None
    baselineDict["baseline2"] = None
    baselineDict["baseline3"] = None
    baselineDict["baseline4"] = None
    for c in connection_dict.keys():
        baselineDict[f"baseline{c}"] = float(baseline_list[list(connection_dict.keys()).index(c)])*1E-3  # in V
    return baselineDict

