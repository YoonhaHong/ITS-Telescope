#!/usr/bin/env python3

import datetime
import logging
import argparse
import sys, os, json, csv
import copy
from tqdm import tqdm
from time import sleep
import numpy as np
from labequipment import HAMEG
from mlr1daqboard import DPTSDAQBoard
from mlr1daqboard import pico_daq
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__),"../../dpts")))
import dpts_threshold as threshold
import dpts_helpers as helpers

# tune the Vh values for each pixel based on its threshold
def create_vsteps_map(config,thrmap):
    vsteps_map =  np.zeros((32,32,55))
    for r in config.rows:
        for c in config.cols:
            threshold = thrmap[r][c]
            # catch if pixel has too low or too high a threshold (basically a bad measurement)
            if thrmap[r][c]<30 or  thrmap[r][c]>1000 or np.isnan(thrmap[r][c]): threshold = 100
            vsteps  = np.linspace(threshold-20,threshold+20,20,endpoint=False)
            vsteps  = np.append(vsteps,np.linspace(vsteps[19]+2,vsteps[19]+202,20,endpoint=False))
            # put 10 points between non-linear part and 1100 mV
            midstep = (1100 - vsteps[39])/10
            vsteps  = np.append(vsteps,np.linspace(vsteps[39]+midstep,1100,10,endpoint=False))
            vsteps  = np.append(vsteps,np.linspace(1100,1200,5))
            vsteps  = vsteps.tolist()
            
            assert any(t < 1201 for t in vsteps)

            vsteps_map[r][c] = vsteps

    return vsteps_map

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
        raise ValueError(f"{config.param} is not a valid chip parameter. Please choose from VCASB, VCASN, IDB, IRESET or IBIAS")

# loop over the parameter list fot the vbb and run the scans
def param_loop(config, dpts, daq, vbb, param_list, fout, thrmap):
    for param_value in tqdm(param_list,desc=f"{config.param}",leave=False):
        config.pwell = vbb
        config.sub = vbb
        set_dac(dpts,config.param,param_value,config)
        sleep(0.5)
        
        # create the vsteps using the measured thresholds
        if config.thrmap_dir is None:
            config.vsteps = create_vsteps_map(config,thrmap)
        else:
            config.vsteps = create_vsteps_map(config,thrmap[vbb][param_value])
        config.vsteps = config.vsteps.tolist()
        
        fname = f"toatot_VBB{vbb}V_VCASB{config.vcasb}mV_IBIAS{config.ibias}nA_IDB{config.idb}nA_IRESET{config.ireset}pA_VCASN{config.vcasn}mV"
        config.fname = fname
        threshold.threshold_scan(copy.deepcopy(config),verbose=False,daq=daq,dpts=dpts)
        fout.write(f"{vbb},{config.vcasb},{config.vcasn},{config.ireset},{config.idb},{config.ibias},{config.ibiasn},{fname}\n")

if __name__=="__main__":
    default_data_dir = os.path.realpath(os.path.join(os.path.dirname(__file__),"../../Data"))
    parser = argparse.ArgumentParser("ToA and ToT scan loop over VBB and chosen chip parameter.\n"\
            "       Loads the all the scan arguments from the config file.\n"\
            "       Controls the VBB using a R&S HAMEG power supply.\n"\
            "       Uses 'VBB_PARAM' to loop over the chosen parameter for each VBB.\n"\
            "       Can set unique chip bias settings for each VBB with 'VBB_Settings'\n")
    parser.add_argument("config", help="JSON file containing the configuration of this script.")
    parser.add_argument('--outdir' , default=default_data_dir, help="Output base directory.")
    args = parser.parse_args()    

    with open(args.config) as jf:
        config = json.load(jf)
        config = argparse.Namespace(**config)

    config.prefix = f"{config.id}_toatot_{config.param}_vbb_"
    now=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    helpers.setup_logging(config,now)
    logging.debug(f"Running {os.path.basename(__file__)} with arguments:\n{json.dumps(vars(config),indent=4)}")
    
    # do some checks before launching the scans
    assert config.param in ["VCASB", "VCASN", "IDB", "IRESET", "IBIAS"], f"{config.param} is not a valid chip parameter. Please choose from VCASB, VCASN, IDB, IRESET or IBIAS."
    assert set(float(i) for i in config.VBB_Settings.keys()) == set(i[0] for i in config.VBB_PARAM), "VBB_PARAM and VBB_Settings do not have the same VBB values, please check."
    
    logging.info(f"Doing ToA and ToT Scan with {config.ninj} injections")

    config.outdir=os.path.join(args.outdir,f"{config.prefix}{now}/")
    if not os.path.exists(config.outdir): os.makedirs(config.outdir)
    
    fout=open(os.path.join(config.outdir,"flist.csv"),'w')
    fout.write(f"vbb,vcasb,vcasn,ireset,idb,ibias,ibiasn,fname\n")

    ps = HAMEG(config.hameg_path)
    daq = pico_daq.ScopeAcqPS6000a(trg_ch=config.trg_ch,trg_mV=50,npre=10,npost=200000,nsegments=config.ninj)
    dpts = DPTSDAQBoard(calibration=config.proximity,serial=config.serial)
    if not dpts.is_chip_powered():
        logging.warning(f"Is chip powered? Current seems low: {dpts.read_chip_currents()}")

    # load a threshold map to get the vsteps for each pixel
    if config.thrmap_dir is None:
        thrmap = np.full((32,32),100)
        logging.warning("No threshold map used. Using a default value of 100 e- for the threshold of all pixels")
    else:
        thrmap = {}
        with open(config.thrmap_dir+"flist.csv") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if '#' in row['vbb']: continue
                vbb=float(row['vbb'])
                param_value=float(row[f'{config.param.lower()}'])
                fname=row['fname'] if 'fname' in row else row['thr']
                if vbb not in thrmap: thrmap[vbb]={}
                npz = np.load(config.thrmap_dir+"/"+fname+'_analyzed.npz')
                thrmap[vbb][param_value] = npz['thresholds']

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
        param_loop(config, dpts, daq, vbb, param_list, fout, thrmap)
        
    fout.close()
    logging.info(f"Done with {config.param} VBB scan!")
    sleep(1)
