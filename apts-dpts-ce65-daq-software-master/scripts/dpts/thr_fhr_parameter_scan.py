#!/usr/bin/env python3

import datetime
import logging
import argparse
import sys, os, json
import copy
from tqdm import tqdm
from time import sleep
from labequipment import HAMEG
from mlr1daqboard import DPTSDAQBoard
from mlr1daqboard import pico_daq
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__),"../../dpts")))
import dpts_threshold as threshold
import dpts_fhr as fhr
import dpts_helpers as helpers

def set_dac(dpts, dac, value, config):
    if dac=="IRESET":
        config.ireset = value
        dpts.set_ireset(value) # unit uA
    elif dac=="IDB":
        config.idb = value
        dpts.set_idb(value/10) # unit uA
    elif dac=="IBIAS":
        # here always keep IBIASN=IBIAS/10
        config.ibias = value
        config.ibiasn = value/10
        dpts.set_ibias(value/10) # unit uA
        dpts.set_ibiasn(value/10) # unit uA
    elif dac=="VCASB":
        config.vcasb = value
        dpts.set_vcasb(value) # unit mv
    elif dac=="VCASN":
        config.vcasn = value
        dpts.set_vcasn(value) # unit mV
    else:
        raise ValueError(f"{dac} is not a valid chip parameter. Please choose from VCASB, VCASN, IDB, IRESET or IBIAS")

# loop over the parameter list fot the vbb and run the scans
def param_loop(config, dpts, daq, vbb, param_list, fout):
    for param_value in tqdm(param_list,desc=f"{config.param}",leave=False):
        config.pwell = vbb
        config.sub = vbb
        set_dac(dpts,config.param,param_value,config)
        sleep(0.5)
        suffix = f"_VBB{vbb}V_VCASB{config.vcasb}mV_IBIAS{config.ibias}nA_IDB{config.idb}nA_IRESET{config.ireset}pA_VCASN{config.vcasn}mV"
        thr_fname = "thr"+suffix if config.DO_THR else ""
        fhr_fname = "fhr"+suffix if config.DO_FHR else ""
        if config.DO_THR:
            config.fname = thr_fname
            threshold.threshold_scan(copy.deepcopy(config),verbose=False,daq=daq,dpts=dpts)
        if config.DO_FHR:
            config.fname = fhr_fname
            fhr.fhr_scan(copy.deepcopy(config),verbose=False,daq=daq,dpts=dpts)
        fout.write(f"{vbb},{config.vcasb},{config.vcasn},{config.ireset},{config.idb},{config.ibias},{config.ibiasn},{thr_fname},{fhr_fname}\n")

if __name__=="__main__":
    default_data_dir = os.path.realpath(os.path.join(os.path.dirname(__file__),"../../Data"))
    parser = argparse.ArgumentParser("Threshold scan and FHR scan loop over VBB and chosen chip parameter.\n"\
            "       Loads the all the scan arguments from the config file.\n"\
            "       Controls the VBB using a R&S HAMEG power supply.\n"\
            "       Uses 'VBB_PARAM' to loop over the chosen parameter for each VBB.\n"\
            "       Can set unique chip bias settings for each VBB with 'VBB_Settings'\n")
    parser.add_argument("config", help="JSON file containing the configuration of this script.")
    parser.add_argument('--outdir', default=default_data_dir, help="Output base directory.")
    args = parser.parse_args()    

    with open(args.config) as jf:
        config = json.load(jf)
        config = argparse.Namespace(**config)
    
    prefix = f'{config.id}{"_thr" if config.DO_THR else ""}{"_fhr" if config.DO_FHR else ""}_{config.param}_vbb'
    config.prefix = prefix+"_"
    now=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    helpers.setup_logging(config,now)
    logging.debug(f"Running {os.path.basename(__file__)} with arguments:\n{json.dumps(vars(config),indent=4)}")

    # do some checks before launching the scans
    assert config.param in ["VCASB", "VCASN", "IDB", "IRESET", "IBIAS"], f"{config.param} is not a valid chip parameter. Please choose from VCASB, VCASN, IDB, IRESET or IBIAS."
    assert set(float(i) for i in config.VBB_Settings.keys()) == set(i[0] for i in config.VBB_PARAM), "VBB_PARAM and VBB_Settings do not have the same VBB values, please check."
    assert config.DO_THR or config.DO_FHR

    if config.DO_THR:
        logging.info(f"Doing Threshold Scan with VH from {config.vmin} to {config.vmax} with {config.vstep} mV step and {config.ninj} injections")
        if config.ninj!=config.nseg:
            config.nseg=config.ninj
            logging.info(f"Setting nseg = ninj = {config.nseg}")
        config.nseg=config.ninj
        if config.trg_ch!="AUX":
            logging.warning("Triggering in threshold scan should be on AUX!")
    if config.DO_FHR:
        logging.info(f"Doing Fake Hit Rate with {config.ntrg} triggers and {config.nseg} segments")
        if config.ninj!=config.nseg:
            config.ninj=config.nseg
            logging.info(f"Setting nseg = ninj = {config.nseg}")

    config.outdir=os.path.join(args.outdir,f"{prefix}_{now}/")
    if not os.path.exists(config.outdir): os.makedirs(config.outdir)
    
    fout=open(os.path.join(config.outdir,"flist.csv"),'w')
    fout.write(f"vbb,vcasb,vcasn,ireset,idb,ibias,ibiasn,thr,fhr\n")
    
    ps = HAMEG(config.hameg_path)
    daq = pico_daq.ScopeAcqPS6000a(trg_ch=config.trg_ch,trg_mV=50,npre=10,npost=200000,nsegments=config.ninj)
    dpts = DPTSDAQBoard(calibration=config.proximity,serial=config.serial)
    if not dpts.is_chip_powered():
        logging.warning(f"Is chip powered? Current seems low: {dpts.read_chip_currents()}")
    
    config.vsteps = list(range(config.vmin, config.vmax+config.vstep, config.vstep))

    logging.info(f"Starting {config.param} VBB scan!")
    for vbb,param_list in tqdm(config.VBB_PARAM,desc="VBB"):
        ps.set_volt(config.VBB_CH,abs(vbb))
        sleep(2)
        # make sure that before the scan chip is at nominal settings for this VBB
        logging.info(f"Setting nominal chip parameters from config file for VBB = {vbb} V")
        for dac in config.VBB_Settings[str(vbb)].keys():
            setattr(config, dac, config.VBB_Settings[str(vbb)][dac])
        dpts.set_dacs(config)
        sleep(0.5)
        param_loop(config, dpts, daq, vbb, param_list, fout)
    
    fout.close()
    logging.info(f"Done with {config.param} VBB scan!")
    sleep(1)
