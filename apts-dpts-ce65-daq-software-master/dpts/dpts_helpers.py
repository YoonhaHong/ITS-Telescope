import logging
import pathlib
import json
import sys,os,re
import copy

def mask_pattern(pxl_list=[], mask=True): 
    ''' mask=False -> umask pxl_list, mask others /
        mask=True -> mask pxl_list, unmask others '''
    mc=mr=md=0x0
    for col,row in pxl_list:
        mr |= 1<<row
        mc |= 1<<col
        md |= 1<<((row-col) if row>=col else (32+row-col))
    if not mask:
        mr ^= 0xFFFFFFFF
        mc ^= 0xFFFFFFFF
        md ^= 0xFFFFFFFF
    if md&1==0: logging.warning("MD[0]=0 activates the monitoring pixel which should be off during normal operation!")
    return mc,md,mr

def pulse_pattern(pxl_list=[]):
    ''' select pxl_list for pulsing '''
    cs=rs=0x0
    for col,row in pxl_list:
        cs |= 1<<col
        rs |= 1<<row
    return cs,rs

def setup_logging(args,now):
    gitrepo = "apts-dpts-ce65-daq-software"
    default_log_dir = os.path.realpath(os.path.join(os.getcwd().split(gitrepo)[0]+gitrepo,"./Logs"))

    if args.serial:
        log_fname = f"{args.prefix}{args.serial}_{now}"
    else:
        log_fname = f"{args.prefix}{now}"
    
    logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                       filename=os.path.join(default_log_dir,log_fname+".log"),filemode='w')
    log_term = logging.StreamHandler()
    log_term.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    log_term.setLevel(logging.getLevelName(args.log_level.upper()))
    logging.getLogger().addHandler(log_term)
    
# add the common arguments across all the dpts scipts
def add_common_args(parser):
    parser.add_argument('proximity',metavar="PROXIMITY",help='Proximity card name (e.g. DPTS-001). The name must be in the same format as the corresponding calibration file.')
    chip_info = parser.add_argument_group('Chip arguments', 'The chip ID and the chip biases with their values that are set by the script at the start.')
    chip_info.add_argument('--vcasb',  '-vb',  default=300, type=float, help='VCASB in mV')
    chip_info.add_argument('--vcasn',  '-vn',  default=300, type=float, help='VCASN in mV')
    chip_info.add_argument('--ireset', '-ir',  default=10,  type=float, help='IRESET in pA')
    chip_info.add_argument('--idb',    '-id',  default=100, type=float, help='IDB in nA')
    chip_info.add_argument('--ibias',  '-ib',  default=100, type=float, help='IBIAS in nA')
    chip_info.add_argument('--ibiasn', '-ibn', default=10,  type=float, help='IBIASN in nA')
    chip_info.add_argument('--ibiasf', '-ibf', default=0,   type=float, help='IBIASF in mA')
    chip_info.add_argument('--vbb', default=-1.2, type=float, help='For logging purposes, the VBB value in V already set by the user (Vsub and Vpwell)')
    chip_info.add_argument('--temperature', type=float, help='For logging purposes, the temperature in °C, will not be measured or set automatically.')
    chip_info.add_argument('--id', default="DPTS", help='The ID of the chip being tested, e.g. DPTSXW22B1 (X variant, wafer 22, chip 1).')
    misc_group = parser.add_argument_group('Miscellaneous arguments')
    misc_group.add_argument('--config-json',metavar="JSON_FILE",help='Configuration file to be loaded. Order of priority: Command line argument -> Argument from JSON -> Default value')
    misc_group.add_argument('--comments','-c', help='Just any comments regarding this measurement.')
    misc_group.add_argument('--prefix',default=pathlib.Path(sys.argv[0]).stem+"_",help='Output file prefix')
    misc_group.add_argument("--serial" ,"-s", help="Serial number of the DAQ board.")
    misc_group.add_argument("--log-level", default="INFO", help="Logging level.")
    misc_group.add_argument("-h", "--help", action="help", help="show this help message and exit")

# add the common arguments for the scan scipts
def add_common_scan_args(parser):
    default_data_dir = os.path.realpath(os.path.join(os.path.dirname(__file__),"../Data"))
    scan_group = parser.add_argument_group('Common scan arguments', 'The arguments common across all scan scripts (thr, fhr, source, decoding).')
    scan_group.add_argument("--outdir" , default = default_data_dir, help = "Directory with output files")
    scan_group.add_argument("--only-pos", action='store_true', help="Decode only positive waveform.")
    scan_group.add_argument("--invert", action='store_true', help="Invert pos and neg waveforms for decoding.")
    scan_group.add_argument('--fix-thresh', type=int, default=-1, help="Look at pos waveform crossing a fixed threshold instead of neg waveform.")

# load additional arguments from the JSON file specified in arguments
def load_json_args(parser, args):
    nodef_parser = copy.deepcopy(parser) #deepcopy the parser, set all defaults to None and parse again
    nodef_parser.set_defaults(**{arg: None for arg in vars(args)})
    nodef_args_dict = vars(nodef_parser.parse_args())
    with open(args.config_json, 'r') as file_json:
        json_config = json.load(file_json)
        for json_arg in json_config: #loop over all json arguments
            if json_arg in args: #check if json argument is also one of the program arguments
                if nodef_args_dict[json_arg] == None: #check that the command line argument was not typed by hand 
                    setattr(args, json_arg, json_config[json_arg])

# add the finishing touches to args, then dump to log file
def finalise_args(args):
    args.pwell = args.sub = args.vbb
    if args.id!="DPTS":
        try:
            args.version, args.wafer, args.chip = re.findall('DPTS([OXS])W([0-9]+)B([0-9]+$)', args.id)[0]
        except IndexError:
            raise ValueError(f"Unexpected format for chip ID, expected 'DPTS'+variant+'W'+wafer_number+'B'+chip_number")
        if args.wafer=="22": args.split = "4 (opt.)"
        elif args.wafer=="13": args.split = "1 (opt.)"
        else: raise ValueError(f"Unrecognised wafer: {args.wafer}, shoulde be either '13' or '22'")
    else:
        logging.warning("Non specific chip ID 'DPTS' kept")

    logging.debug(f"Running {os.path.basename(__file__)} with arguments:\n{json.dumps(vars(args),indent=4)}")

# check if given pixel would be masked by given mask
def is_pixel_activated_in_mask(c, r, mc, md, mr):
    cmc = cmr = cmd = 0x0
    cmr |= 1<<r
    cmc |= 1<<c
    cmd |= 1<<((r-c) if r>=c else (32+r-c))
    if cmc & mc and cmr & mr and cmd & md:
        return False
    return True

# get all pixels that are not in pxl_list but would be deactivated by applying a mask of all pxl_list pixels
def get_masking_ghosts(pxl_list, mc, md, mr):
    ghosts = []
    for r in range(32):
        for c in range(32):
            is_active = is_pixel_activated_in_mask(c, r, mc, md, mr)
            if not is_active and [c,r] not in pxl_list: ghosts.append([c, r])
    return ghosts