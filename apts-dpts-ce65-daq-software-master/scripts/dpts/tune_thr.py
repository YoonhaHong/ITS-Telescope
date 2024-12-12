#!/usr/bin/env python3

import datetime
import logging
import argparse
import sys, os, json, glob, re
import copy
import numpy as np
from tqdm import tqdm
from time import sleep
from labequipment import HAMEG
from mlr1daqboard import DPTSDAQBoard
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__),"../../dpts")))
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__),"../../analysis/dpts")))
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


def measure_thresholds(config, dpts, param_range):
    import dpts_threshold as threshold
    from mlr1daqboard import pico_daq

    logging.info("Starting measurement of thresholds.")

    daq = pico_daq.ScopeAcqPS6000a(trg_ch=config.trg_ch,trg_mV=50,npre=10,npost=200000,nsegments=config.ninj)

    config.outdir = config.basedir + "tuning/"

    for param_value in tqdm(param_range,desc=f"{config.param}",leave=False):
        
        set_dac(dpts,config.param,param_value,config)
        sleep(0.5)
        
        thr_fname = f"thr_VBB{config.pwell}V_VCASB{config.vcasb}mV_IBIAS{config.ibias}nA_IDB{config.idb}nA_IRESET{config.ireset}pA_VCASN{config.vcasn}mV"
        config.fname = thr_fname
        threshold.threshold_scan(copy.deepcopy(config),verbose=False,daq=daq,dpts=dpts)


def analyse_thresholds(config, plotdir):
    import thresholdana
    
    logging.info("Starting threshold analysis.")

    plotdir = config.basedir + plotdir
    fname  = plotdir + "/thr*.npy" 

    logging.info(f"Processing all file matching pattern {fname}")
    for f in tqdm(glob.glob(fname),desc="Processing file",leave=False):
        if '.npy' in f:
            thresholdana.analyse_threshold_scan(f, f.replace('.npy','.json'),None,plotdir,0,None,verbose=False)

        if plotdir=="tuned":
            npz = np.load(f.replace('.npy','*.npz'))
            thresholds = npz['thresholds']
            thresholds[thresholds==0]=np.nan
            logging.info(f"Measured threshold at tuned parameter value = {np.nanmean(thresholds)} e-.")

def interpolate(config, data, data_tuned, it):
    x1,y1=data[it-1]
    x2,y2=data[it]
    config.tuned_param=round(x1+(config.target-y1)*(x2-x1)/(y2-y1))
    thr=(y1+(config.tuned_param-x1)*(y2-y1)/(x2-x1))
    data_tuned={
        f"{config.param}": config.tuned_param,
        "Threshold": thr
    }
    return data_tuned

def tune_thresholds(config):
    from matplotlib import pyplot as plt
    
    logging.info("Starting threshold tuning.")
    
    plotdir = config.basedir + "tuning/"
    
    plt.figure(f"Threshold vs {config.param}")
    x = []
    y = []

    data = {}
    for f in sorted(glob.glob(os.path.join(plotdir,"thr*.npz"))):
        npz = np.load(f)
        param_value = float(re.split('(\d+)',f.split("tuning")[1].split(f"_{config.param}")[1])[1])
        thresholds = npz['thresholds']
        thresholds[thresholds==0]=np.nan
        data[param_value] = np.nanmean(thresholds)
        x.append(param_value)
        y.append(data[param_value])

    assert data, f"Could not find any .npz files in {plotdir}." 

    sorted_xy = sorted(zip(x,y))
    sorted_xy = np.array(sorted_xy)
    plt.plot(sorted_xy[:,0],sorted_xy[:,1],marker='o')

    data_tuned = {}
    data = sorted(data.items())
    it=next((i for i,d in enumerate(data) if d[1]<config.target),0)
    if it==0:
        # take into account the different param vs threshold relations
        it=next((i for i,d in enumerate(data) if d[1]>config.target),0)
        if it==0:
            raise ValueError(f"Could not find target threshold in given param range.\n" \
                    f"Target             = {config.target}\n"\
                    f"Measured values    = {data}")
        else:
            data_tuned = interpolate(config, data, data_tuned, it)
    else:
        data_tuned = interpolate(config, data, data_tuned, it)
    
    plt.axvline(config.tuned_param,linestyle='dashed',color='red',label=f"Tuned {config.param} = {config.tuned_param}")
    plt.axhline(config.target,linestyle='dashed',color='grey',label=f"Target = {config.target}")
    plt.xlabel(f"{config.param} ({config.units})")
    plt.ylabel("Threshold ($\it{e^{-}}$)")
    plt.legend(loc='best')
    plt.savefig(os.path.join(config.basedir,"threshold_tuning.png"))

    logging.info(f"At VBB = {config.pwell} V: {config.param} tuned to {config.target} e- = {config.tuned_param} {config.units}")

    with open(os.path.join(config.basedir,"threshold_tuning.json"),'w') as jf:
        json.dump(data_tuned,jf,indent=4)


def measure_tuned_thresholds(config, dpts):
    import dpts_threshold as threshold
    from mlr1daqboard import pico_daq
    
    logging.info("Starting measurement of tuned thresholds.")
    
    with open(os.path.join(config.basedir,"threshold_tuning.json")) as jf:
        tuning = json.load(jf)
    assert tuning['Threshold'] is not None, "Threshold tuning bad"
    config.tuned_param = tuning[config.param]

    daq = pico_daq.ScopeAcqPS6000a(trg_ch=config.trg_ch,trg_mV=50,npre=10,npost=200000,nsegments=config.ninj)
    
    config.outdir = config.basedir + "tuned/"
    
    set_dac(dpts,config.param,config.tuned_param,config)
    sleep(0.5)
    
    thr_fname = f"thr_tuned_VBB{config.pwell}V_VCASB{config.vcasb}mV_IBIAS{config.ibias}nA_IDB{config.idb}nA_IRESET{config.ireset}pA_VCASN{config.vcasn}mV"
    config.fname = thr_fname
    threshold.threshold_scan(copy.deepcopy(config),verbose=False,daq=daq,dpts=dpts)


if __name__=="__main__":
    default_data_dir = os.path.realpath(os.path.join(os.path.dirname(__file__),"../../Data"))
    parser = argparse.ArgumentParser("Behold! A crude imitation of the ultimate threshold tuning script.")
    parser.add_argument("config", help="JSON file containing the configuration of this script.")
    parser.add_argument('--outdir', default=default_data_dir, help="Output base directory.")
    args = parser.parse_args()

    with open(args.config) as jf:
        config = json.load(jf)
        config = argparse.Namespace(**config)
    
    prefix = f'{config.id}_tune_thr_{config.param}'
    config.prefix = prefix+"_"
    now=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    helpers.setup_logging(config,now)
    logging.debug(f"Running {os.path.basename(__file__)} with arguments:\n{json.dumps(vars(config),indent=4)}")

    # do some checks before launching the scans
    assert config.param in ["VCASB", "VCASN", "IDB", "IRESET", "IBIAS"], f"{config.param} is not a valid chip parameter. Please choose from VCASB, VCASN, IDB, IRESET or IBIAS."
    assert set(i for i in config.VBB_Settings.keys()) == set(i for i in config.VBB_RANGE.keys()), "VBB_PARAM and VBB_Settings do not have the same VBB values, please check."
    assert config.command in ["FULL","MEASURE","ANALYSE","TUNE","MEASURE_TUNED","ANALYSE_TUNED"], f"{config.command} is not a valid config.command, please choose from FULL, MEASURE, ANALYSE, TUNE, MEASURE_TUNED, ANALYSE_TUNED"
    if "FULL" in config.command:
        config.command = ["MEASURE","ANALYSE","TUNE","MEASURE_TUNED","ANALYSE_TUNED"]
        logging.info("FULL has been chosen, this may take a while.")
    else:
        config.command = [config.command]

    # set up units
    units = {'IRESET':'pA', 'IDB':'nA', 'IBIAS':'nA', 'VCASB':'mV', 'VCASN':'mV', 'VBB':'V'}
    config.units = units[config.param]

    if args.outdir == default_data_dir: config.basedir=os.path.join(args.outdir,f"{prefix}_{now}/")
    else: config.basedir = args.outdir
    if not os.path.exists(config.basedir): os.makedirs(config.basedir)

    if "MEASURE" in config.command or "MEASURE_TUNED" in config.command:
        ps = HAMEG(config.hameg_path)
        dpts = DPTSDAQBoard(calibration=config.proximity,serial=config.serial)
        if not dpts.is_chip_powered():
            logging.warning(f"Is chip powered? Current seems low: {dpts.read_chip_currents()}")
    
    config.vsteps = list(range(config.vmin, config.vmax+config.vstep, config.vstep))

    logging.info(f"Starting {config.param} VBB tune!")
    for vbb in tqdm(config.VBB_RANGE.keys(),desc="VBB"):
        if "MEASURE" in config.command or "MEASURE_TUNED" in config.command:
            ps.set_volt(config.VBB_CH,abs(float(vbb)))
            sleep(2)
        config.pwell = vbb
        config.sub = vbb
        config.basedir = f"{config.basedir}vbb{abs(float(vbb))}/"
        if not os.path.exists(config.basedir): os.makedirs(config.basedir)

        param_range = range(config.VBB_RANGE[vbb]['start'], config.VBB_RANGE[vbb]['end'] + config.VBB_RANGE[vbb]['step'], config.VBB_RANGE[vbb]['step'])

        # make sure that before the scan chip is at nominal settings for this VBB
        if "MEASURE" in config.command or "MEASURE_TUNED" in config.command:
            logging.info(f"Setting nominal chip parameters from config file for VBB = {vbb} V")
            for dac in config.VBB_Settings[vbb].keys():
                setattr(config, dac, config.VBB_Settings[vbb][dac])
            dpts.set_dacs(config)
            sleep(0.5)
        
        if "MEASURE"       in config.command: measure_thresholds(config, dpts, param_range)
        if "ANALYSE"       in config.command: analyse_thresholds(config, "tuning")
        if "TUNE"          in config.command: tune_thresholds(config)
        if "MEASURE_TUNED" in config.command: measure_tuned_thresholds(config, dpts)
        if "ANALYSE_TUNED" in config.command: analyse_thresholds(config, "tuned")

        config.basedir = config.basedir.split("vbb")[0]
    
    logging.info(f"Done with {config.param} VBB tune!")
    sleep(1)

