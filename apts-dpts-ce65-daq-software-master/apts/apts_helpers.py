import pathlib
import json
import sys,os,re
import copy

def add_common_args(parser):
    default_data_dir = os.path.realpath(os.path.join(os.path.dirname(__file__),"../Data"))
    parser.add_argument('proximity',metavar="PROXIMITY",help='Proximity card name (e.g. APTS-003). The name must be in the same format as the corresponding calibration file.')
    parser.add_argument('chip_ID',metavar="CHIP_ID", help='Chip ID (e.g. AF15_W22B5). The name should be the same as in the the TWiki inventory.')
    parser.add_argument('--serial' ,'-s',help='serial number of the DAQ board')
    parser.add_argument('--pulse','-p',default=None,help='PULSE: s(first pixel), out(outer), in(inner), f(full)',type=lambda t: {'s':0,'out':1,'in':2,'f':3}[t] )
    parser.add_argument('--mux', default=-1, type=int, help='Select different sensor variants in multiplexing chip. 0 = Left top:  Larger nwell collection electrode, 1 = Left bottom: Reference, 2 = Right top: Finger-shape pwell enclusure, 3 = Right bottom: Smaller pwell enclosure, -1 for not multiplexer')
    parser.add_argument('--trg_pixels','--trg-pixels','-tp',nargs='+',type=lambda px: px if px=='inner' else tuple(map(int,px.split(','))),help='Pixels to use as internal trigger source, e.g. "-tp inner" to use only central pixels", or "-tp 0,0 2,1" to enable individual pixels addressing them by (col,row)')
    parser.add_argument('--n_frames_before','--n-frames-before','-nfb', default=100, type=int, help='Number of frame before trigger/signal 1-100')
    parser.add_argument('--n_frames_after','--n-frames-after','-nfa', default=100, type=int, help='Number of frame after trigger/signal 1-700')
    parser.add_argument('--sampling_period','--sampling-period','-sp',default=40, type=int, help='Sampling period 1-40 (unit of 6.25 ns)')
    parser.add_argument('--vh','-vh',       default=1200,type=float,help='VH DAC setting in mV')
    parser.add_argument('--ireset','-ir',  default=1,   type=float,help='IRESET DAC setting in uA ')    
    parser.add_argument('--expert_wait','-exw', default=9, type=int,help='Only for expert (seconds unit)')
    parser.add_argument('--output_dir','-o',default=default_data_dir,help='Directory for output files.')
    parser.add_argument('--suffix',default='',help='Output file suffix')

    args = parser.parse_args()
    
    if args.proximity.split('-')[0]=='APTS':
        parser.add_argument('--vreset','-vr',  default=500, type=float,help='VRESET DAC setting in mV')
        parser.add_argument('--ibiasn','-ibn', default=20,  type=float,help='IBIASN DAC setting in uA ')
        parser.add_argument('--ibiasp','-ibp', default=2,   type=float,help='IBIASP DAC setting in uA ')
        parser.add_argument('--ibias4','-ib4', default=150, type=float,help='IBIAS4SF DAC setting in uA ')
        parser.add_argument('--ibias3','-ib3', default=200, type=float,help='IBIAS3 DAC setting in uA ')
    elif args.proximity.split('-')[0]=='OPAMP':
        parser.add_argument('--vreset','-vr',  default=400, type=float,help='VRESET DAC setting in mV')
        parser.add_argument('--ibiasn','-ibn', default=500,  type=float,help='IBIASN DAC setting in uA ')
        parser.add_argument('--ibiasp','-ibp', default=45,   type=float,help='IBIASP DAC setting in uA ')
        parser.add_argument('--ibias4','-ib4', default=2600, type=float,help='IBIAS4SF DAC setting in uA ')
        parser.add_argument('--ibias3','-ib3', default=850, type=float,help='IBIAS3 DAC setting in uA ')
        parser.add_argument('--vcasp','-vcp', default=270, type=float,help='IBIAS4SF DAC setting in uA ')
        parser.add_argument('--vcasn','-vcn', default=900, type=float,help='IBIAS3 DAC setting in uA ')
        
def finalise_args(args):
    args.pwell = args.sub = args.vbb_array
    try:
        if args.proximity.split('-')[0]=='APTS':
            args.pitch, args.version, args.wafer, args.chip = re.findall('[E]?[R]?[1]?A[AF]([0-9]+)([PB]?[M]?)_W([0-9]+)B([0-9]+$)', args.chip_ID)[0]
        else:
            args.wafer, args.version, args.chip = re.findall('W([0-9]+)AO10([PB]?)b([0-9]+$)', args.chip_ID)[0]
    except IndexError:
        raise ValueError(f"Unexpected format for chip ID, expected 'AF'or'AA' +pitch+variant+_+'W'+wafer_number+'B'+chip_number")
    if args.wafer=="22": args.split = "4 (opt.)"
    elif args.wafer=="13": args.split = "1 (opt.)"
    elif args.wafer=="16": args.split = "2 (opt.)"
    elif args.wafer=="19": args.split = "3 (opt.)"
    elif args.wafer=="24": args.split = "2 (opt.)"#ER1

    else: raise ValueError(f"Unrecognised wafer: {args.wafer}, shoulde be '13', '16', '19', '22' for MLR1 or '24' for ER1")
