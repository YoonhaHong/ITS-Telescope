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

N_CROSSINGS_SAVED=20

def threshold_scan(args,verbose=True,daq=None,dpts=None,now=None):
    if not os.path.exists(args.outdir): os.makedirs(args.outdir)
    if not now: now=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    if 'fname' in args:
        fname = args.outdir+"/"+args.fname
    else:
        fname = args.outdir+"/"+args.prefix+now

    assert args.ninj>1, "This test is implemented only for >1 injections at each vh."

    if not dpts:
        dpts = DPTSDAQBoard(calibration=args.proximity,serial=args.serial)
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

    if not daq:
        daq = pico_daq.ScopeAcqPS6000a(trg_ch="AUX",trg_mV=50,npre=10,npost=200000,nsegments=args.ninj)
    if verbose: daq.print()
    
    # ensure the length of TRG assertion is as long as the scope capture in daqboard clock cycles
    trg_high = int((daq.npre+daq.npost)*daq.dt*1e9/10)

    t = np.linspace(-daq.npre*daq.dt,daq.npost*daq.dt,daq.npre+daq.npost,endpoint=False)

    # different vsteps shape if using scripts/dpts/toa_tot_parameter_scan.py
    if isinstance(args.vsteps[0], (list,tuple)):
        vsteps_len = len(args.vsteps[0][0])
    else:
        vsteps_len = len(args.vsteps)
    
    data = np.full(
        (len(args.cols),len(args.rows),vsteps_len,args.ninj,N_CROSSINGS_SAVED,2),
        np.nan,dtype=np.float32)

    try:
        for ir,r in enumerate(tqdm(args.rows, desc="Row", leave=verbose)):
            for ic,c in enumerate(tqdm(args.cols, desc="Col", leave=False)):
                for iv in tqdm(range(vsteps_len), desc=" VH", leave=False):
                    if isinstance(args.vsteps[0], (list,tuple)):
                        v = args.vsteps[r][c][iv]
                    else:
                        v = args.vsteps[iv]
                    dpts.set_vh(v)
                    dpts.write_shreg(rs=1<<r,mc=0xFFFFFFFF,md=0xFFFFFFFF,cs=1<<c,mr=(1<<r)^0xFFFFFFFF,readback=False)
                    daq.arm()
                    dpts.pulse(ncycles_high=trg_high,ncycles_low=10000,npulses=args.ninj,wait=False)
                    daq.wait()
                    d = daq.rdo()
                    for inj in range(args.ninj):
                        for iz,z in enumerate(decoder.zero_suppress(t,d[inj][0],d[inj][1],args.invert,args.only_pos,args.fix_thresh)[:N_CROSSINGS_SAVED]):
                            data[ic,ir,iv,inj,iz,:] = z
        dpts.write_shreg(rs=0,mc=0,md=0,cs=0,mr=0,readback=False)
        if verbose:
            logging.info("Done!")
    except KeyboardInterrupt:
        args.interrupted={"row":r,"col":c,"vh":v}
        logging.warning(f"Measurement interrupted at {args.interrupted}")

    with open(fname+".json", 'w') as f:
        json.dump(vars(args), f, indent=4)
    np.save(fname+".npy", data)


if __name__=="__main__":
    parser = argparse.ArgumentParser("DPTS threshold scan",formatter_class=argparse.ArgumentDefaultsHelpFormatter,add_help=False)
    thr_group = parser.add_argument_group('Threshold arguments', 'The arguments (and default values) unique to the threshold scan.')
    thr_group.add_argument("--ninj", type=int, default=25, help="Number of injections per pixel.")
    thr_group.add_argument("--vmax", type=int, default=600, help="Max VH in mV.")
    thr_group.add_argument("--vmin", type=int, default=10, help="Min VH in mV.")
    thr_group.add_argument("--vstep",type=int, default=10, help="VH step in mV.")
    thr_group.add_argument("--rows", type=int, default=[], nargs="*", help="Rows to scan.")
    thr_group.add_argument("--cols", type=int, default=[], nargs="*", help="Rows to scan.")
    helpers.add_common_scan_args(parser)
    helpers.add_common_args(parser)
    args = parser.parse_args()
    
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    if args.config_json is not None:   
        helpers.load_json_args(parser, args)

    helpers.setup_logging(args,now)
    args.vh = "variable"
    helpers.finalise_args(args)

    if not args.rows: args.rows = list(range(32))
    if not args.cols: args.cols = list(range(32))
    
    args.vsteps = list(range(args.vmin, args.vmax+args.vstep, args.vstep))

    threshold_scan(args,now=now)
