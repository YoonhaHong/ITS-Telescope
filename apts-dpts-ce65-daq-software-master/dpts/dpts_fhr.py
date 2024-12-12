#!/usr/bin/env python3

import logging
import argparse
from tqdm import tqdm
from time import sleep
import os, datetime
import numpy as np
import json
from mlr1daqboard import DPTSDAQBoard 
from mlr1daqboard import pico_daq
from mlr1daqboard import dpts_decoder as decoder
import dpts_helpers as helpers

N_CROSSINGS_SAVED=32
MAX_CROSSINGS=1000

def fhr_scan(args,verbose=True,daq=None,dpts=None,now=None):
    if not os.path.exists(args.outdir): os.makedirs(args.outdir)
    if not now: now=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    if 'fname' in args:
        fname = args.outdir+"/"+args.fname
    else:
        fname = args.outdir+"/"+args.prefix+now
    
    assert args.nseg>1, "This test is implemnted only for >1 segments."

    if not dpts:
        dpts = DPTSDAQBoard(calibration=args.proximity,serial=args.serial)
        if not dpts.is_chip_powered():
            logging.warning(f"Is chip powered? Current seems low: {dpts.read_chip_currents()}")

    # set the chip biases
    if verbose:
        logging.info(f"Setting DACs")
        dpts.set_dacs(args)
    else:
        dpts.set_dacs(args,level=logging.DEBUG)
    
    if not daq:
        daq = pico_daq.ScopeAcqPS6000a(trg_ch=args.trg_ch,trg_mV=50,npre=10,npost=200000, \
            auto_trigger_us=args.trg_wait, nsegments=args.nseg)
    if verbose: daq.print()
    
    # ensure the length of TRG assertion is as long as the scope capture in daqboard clock cycles
    trg_high = int((daq.npre+daq.npost)*daq.dt*1e9/10)
    
    if args.ntrg%args.nseg!=0:
        args.ntrg=round(args.ntrg/args.nseg)*args.nseg
        logging.info(f"Setting number of triggers to {args.ntrg}")

    t = np.linspace(-daq.npre*daq.dt,daq.npost*daq.dt,daq.npre+daq.npost,endpoint=False)

    data = np.full((args.ntrg,N_CROSSINGS_SAVED,2), np.nan, dtype=np.float32)

    if hasattr(args, "mask_pixel") and args.mask_pixel:
        logging.info(f"Masking following pixel: {args.mask_pixel}")
        mc,md,mr=helpers.mask_pattern(args.mask_pixel)
        masking_ghosts=helpers.get_masking_ghosts(args.mask_pixel, mc, md, mr)
        if masking_ghosts:
            logging.warning(f"Following pixel will be masked additionally by ghosting: {masking_ghosts}")
    else:
        mc=md=mr=0
    dpts.write_shreg(rs=0,mc=mc,md=md,cs=0,mr=mr,readback=False)

    too_high_fhr=False
    try:
        for itrg,trg in enumerate(tqdm(range(0,args.ntrg,args.nseg),desc="Triggers/nseg",leave=verbose)):
            daq.arm()
            sleep(0.001) # needed for picoscope!
            if args.trg_ch=="AUX":
                dpts.pulse(ncycles_high=trg_high,ncycles_low=10000,npulses=args.nseg,wait=False)
            daq.wait()
            d = daq.rdo()
            for iseg in range(args.nseg):
                zs = decoder.zero_suppress(t,d[iseg][0],d[iseg][1],args.invert,args.only_pos,args.fix_thresh)
                if len(zs)>MAX_CROSSINGS: too_high_fhr=True
                for iz,z in enumerate(zs[:N_CROSSINGS_SAVED]):
                    data[trg + iseg,iz,:] = z
            if too_high_fhr:
                args.interrupted={"itrg":itrg,"too_high_fhr":True}
                break
        if verbose:
            if too_high_fhr:
                logging.warning(f"Interrupted the measurement because too high FHR (>{MAX_CROSSINGS} crossings per trigger)")
            else:
                logging.info("Done!")
    except KeyboardInterrupt:
        args.interrupted={"itrg":itrg}
        logging.warning(f"Measurement interrupted at {args.interrupted}")

    with open(fname+".json", 'w') as f:
        json.dump(vars(args), f, indent=4)
    np.save(fname+".npy", data)


if __name__=="__main__":
    parser = argparse.ArgumentParser("DPTS fake hit-rate scan", formatter_class=argparse.ArgumentDefaultsHelpFormatter,add_help=False)
    fhr_group = parser.add_argument_group('Fake hit-rate arguments', 'The arguments (and default values) unique to the fake hit-rate scan.')
    fhr_group.add_argument("--ntrg", type=int, default=10000, help="Total number of triggers.")
    fhr_group.add_argument("--trg_ch", "--ch", default="AUX", help="Trigger channel. Hint: trigger on signal (CML output) biases the data.")
    fhr_group.add_argument("--trg_wait", type=int, default=0, help="Time in us before auto trigger fires (0=inf).")
    fhr_group.add_argument("--nseg", type=int, default=100, help="Number of picoscope segments (ntrg is divided in trains of nseg triggers)")
    fhr_group.add_argument('--mask_pixel', '-m', nargs=2, type=int, default=[], action='append', help='Pixel (col and row) to mask out. Can be used multiple times.')
    helpers.add_common_scan_args(parser)
    helpers.add_common_args(parser)
    args = parser.parse_args()

    if args.config_json is not None:   
        helpers.load_json_args(parser, args)
    
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    helpers.setup_logging(args,now)
    helpers.finalise_args(args)

    fhr_scan(args,now=now)

