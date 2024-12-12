#!/usr/bin/env python3

import logging
import argparse
from time import sleep
import os, datetime
import json
from mlr1daqboard import DPTSDAQBoard 
from labequipment import HAMEG
from labequipment import RTD23
from labequipment import PTH
import dpts_helpers as helpers

def create_print_line(ia, id, ib, ivbb=None, t=None, p=None, h=None, tr=None):
    out = f"Ia = {ia:0.2f}mA, Id = {id:0.2f}mA, Ib = {ib:0.2f}mA"
    if ivbb is not None:
        out+=f", Ivbb = {ivbb:0.1f}mA"
    if t and p and h:
        out+=f", T = {t:0.2f}°C, P = {p:0.2f}hPa, H = {h:0.2f}%RH"
    if tr is not None:
        out+=f", Tjig = {tr:0.2f}°C"
    return out

def create_log_line(readnow, ia, id, ib, ivbb=None, t=None, p=None, h=None, tr=None):
    out = f"{readnow},{ia},{id},{ib}"
    if ivbb is not None:
        out+=f",{ivbb}"
    if t and p and h:
        out+=f",{t},{p},{h}"
    if tr is not None:
        out+=f",{tr}"
    return out+"\n"

def current_logger(args,verbose=True,dpts=None,now=None,hameg=None,pth=None,rtd23=None):
    if not os.path.exists(args.outdir): os.makedirs(args.outdir)
    if not now: now=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    if 'fname' in args:
        fname = args.outdir+"/"+args.fname
    else:
        fname = args.outdir+"/"+args.prefix+now

    if not dpts:
        dpts = DPTSDAQBoard(calibration=args.proximity,serial=args.serial)
        dpts.power_on()
        if not dpts.is_chip_powered():
            logging.warning(f"Is chip powered? Current seems low: {dpts.read_chip_currents()}")
    
    # set the chip biases
    if verbose:
        logging.info(f"Setting DACs")
        if args.vh!="variable": dpts.set_dacs(args,vh=True)
        else: dpts.set_dacs(args)
    else:
        if args.vh!="variable": dpts.set_dacs(args,vh=True,level=logging.DEBUG)
        else: dpts.set_dacs(args,level=logging.DEBUG)

    # set vbb
    if args.hameg_path is not None and args.hameg_vbb_ch is not None:
        if not hameg:
            hameg = HAMEG(args.hameg_path)
        hameg.set_curr(args.hameg_vbb_ch, 0.0001)
        assert abs(args.vbb) <= 3, "VBB has to be smaller or equal 3V."
        hameg.set_volt(args.hameg_vbb_ch, abs(args.vbb))

    # flush shreg
    dpts.write_shreg(rs=0,mc=0,md=0,cs=0,mr=0,readback=False)
    
    init=f"time,ia_ma,id_ma,ib_ma"
    if hameg:
        init+=",ivbb_ma"
    if pth:
        init+=",t_degc,p_hpa,h_prh"
    if rtd23:
        init+=",tjig_degc"
    fout=open((fname+".csv"),'w')
    fout.write(init+"\n")

    try:
        while True:
            readnow = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            ia = dpts.read_isenseA()
            id = dpts.read_isenseD()
            ib = dpts.read_isenseB()
            ivbb = None
            t = None
            p = None
            h = None
            tr = None
            if hameg:
                ivbb = hameg.status()[4][args.hameg_vbb_ch-1]*1000
            if pth:
                t = pth.getT()
                p = pth.getP()
                h = pth.getH()
            if rtd23:
                tr = rtd23.get_temperature()
            logging.info(create_print_line(ia, id, ib, ivbb, t, p, h, tr))
            fout.write(create_log_line(readnow, ia, id, ib, ivbb, t, p, h, tr))
            sleep(args.log_interval)
    except KeyboardInterrupt:
        print('interrupted!')
        fout.close()
        with open(fname+".json", 'w') as f:
            json.dump(vars(args), f, indent=4)

if __name__=="__main__":
    parser = argparse.ArgumentParser("DPTS current monitor and logger",formatter_class=argparse.ArgumentDefaultsHelpFormatter,add_help=False)
    current_log_group = parser.add_argument_group('Current monitor arguments', 'The arguments (and default values) unique to current logs.')
    current_log_group.add_argument("--hameg-path", help="Path to the HAMEG. If proper path and channel are given, VBB is actually set to the chip.")
    current_log_group.add_argument("--hameg-vbb-ch", type=int, choices=[1,2,3,4], default=2, help="Path to the HAMEG VBB channel.")
    current_log_group.add_argument("--pth", action="store_true", help="Use the PTH for temperature logging.")
    current_log_group.add_argument("--rtd23", action="store_true", help="Use the RTD23 for temperature logging.")
    current_log_group.add_argument("--log-interval", default=2, type=float, help="Time in s between two current readings.")
    current_log_group.add_argument('--vh', default=600, type=float, help='VH in mV')
    default_data_dir = os.path.realpath(os.path.join(os.path.dirname(__file__),"../Data"))
    current_log_group.add_argument("--outdir" , default = default_data_dir, help = "Directory with output files")
    helpers.add_common_args(parser)
    args = parser.parse_args()
    
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    if args.config_json is not None:   
        helpers.load_json_args(parser, args)

    helpers.setup_logging(args,now)
    helpers.finalise_args(args)
    
    if args.hameg_path is not None and args.hameg_vbb_ch is not None:
        hameg = HAMEG(args.hameg_path)
    else:
        hameg = None


    if args.pth:
        pth = PTH()
    else:
        pth = None

    if args.rtd23:
        rtd23 = RTD23()
    else:
        rtd23 = None

    current_logger(args,hameg=hameg,now=now,pth=pth,rtd23=rtd23)
