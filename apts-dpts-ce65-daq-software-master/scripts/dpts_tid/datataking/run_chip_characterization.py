#!/usr/bin/env python3

import datetime
import logging
import argparse
import sys, os, json
import glob
import shutil
import re
import subprocess
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__),"../../dpts")))

if __name__=="__main__":
    default_data_dir = os.path.realpath(os.path.join(os.path.dirname(__file__),"../../Data"))
    parser = argparse.ArgumentParser("This script is a wrapper to run all known analyses od the DPTS automatically. In particular\
                                        these are a FHR scan, a threshold scan, a decoding calibration, a non-linear calibration\
                                        and a source scan. For the source scan, the source will be shuttered with a Thorlabs FW102C\
                                        filterwheel. All parameters are read from a single config. See the example config for further\
                                        reference.")
    parser.add_argument("config", help="JSON file containing the configuration of this script.")
    parser.add_argument('--outdir', default=default_data_dir, help="Output base directory.")
    args = parser.parse_args()        
    
    with open(args.config) as jf:
        config = json.load(jf)

    config["VBB_PARAM"] = [[config["vbb"], [config["vcasb"]]]]
    config["VBB_Settings"] = {str(config["vbb"]): {key: config[key] for key in ["vcasb", "vcasn", "ireset", "ibias", "ibiasn", "idb"]}}
    config["param"] = "VCASB"

    prefix = f'{config["id"]}_fullchar'
    now=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')  

    gitrepo = "apts-dpts-ce65-daq-software"
    default_log_dir = os.path.realpath(os.path.join(os.getcwd().split(gitrepo)[0]+gitrepo,"./Logs"))

    if config["serial"]:
        log_fname = f"{prefix}_{config['serial']}_{now}"
    else:
        log_fname = f"{prefix}_{now}"

    logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                       filename=os.path.join(default_log_dir,log_fname+".log"),filemode='w')
    log_term = logging.StreamHandler()
    log_term.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    log_term.setLevel(logging.getLevelName(config['log_level'].upper()))
    logging.getLogger().addHandler(log_term)    
    logging.debug(f"Running {os.path.basename(__file__)} with arguments:\n{json.dumps(config,indent=4)}")


    if config["id"]!="DPTS":
        try:
            config["version"], config["wafer"], config["chip"] = re.findall('DPTS([OXS])W([0-9]+)B([0-9]+$)', config["id"])[0]
        except IndexError:
            raise ValueError(f"Unexpected format for chip ID, expected 'DPTS'+variant+'W'+wafer_number+'B'+chip_number")
        if config["wafer"]=="22": config["split"] = "4 (opt.)"
        elif config["wafer"]=="13": config["wafer"] = "1 (opt.)"
        else: raise ValueError(f"Unrecognised wafer: {config['wafer']}, shoulde be either '13' or '22'")
    else:
        logging.warning("Non specific chip ID 'DPTS' kept")
    logging.debug(f"Running {os.path.basename(__file__)} with arguments:\n{json.dumps(vars(args),indent=4)}")

    args.outdir_full=os.path.join(args.outdir,f"{prefix}_{now}/")
    if not os.path.exists(args.outdir_full): os.makedirs(args.outdir_full)
    config_dir = os.path.join(args.outdir_full, "config")
    os.makedirs(config_dir)

    if config["DO_THR"] or config["DO_FHR"]:
        # create config for fhr thr
        logging.info("Creating config for THR and/or FHR scan")

        with open("config_thr_fhr_template.json") as jf:
            config_thr = json.load(jf)
        for key in config_thr:
            if key in config.keys():
                config_thr[key] = config[key]
        # config_thr["ninj"] = config.get("thr_ninj", None)
        # config_thr["ntrg"] = config.get("fhr_ntrg", None)
        for key in config:
            if key.startswith("thr_"):
                config_thr[key.removeprefix("thr_")] = config[key]
            if key.startswith("fhr_"):
                config_thr[key.removeprefix("fhr_")] = config[key]
        config_path_thr_fhr = os.path.join(config_dir, f"config_{prefix}_thr_fhr_char.json")
        with open(config_path_thr_fhr, "w") as jf:
            json.dump(config_thr, jf, indent=4)

        logging.info(f"Starting THR/FHR scan with {os.path.basename(config_path_thr_fhr)}...")
        subprocess.run(f"./thr_fhr_parameter_scan.py {config_path_thr_fhr} --outdir {args.outdir_full}", shell=True, check=True)
        
        # cretae runlist
        # print(glob.glob(f"{args.outdir_full}/thr*.json"))
        list_of_files = glob.glob(args.outdir_full+"/*")
        latest_dir = max(list_of_files, key=os.path.getctime)
        if config["DO_THR"]:
            latest_thr = glob.glob(f"{latest_dir}/thr*.json")[0].removesuffix(".json")
        if config["DO_FHR"]:
            latest_fhr = glob.glob(f"{latest_dir}/fhr*.json")[0].removesuffix(".json")
        with open((args.outdir_full+"runlist.csv"),'w') as runlist:
            if config["DO_THR"]:
                runlist.write(f"thr,{os.path.relpath(latest_thr,args.outdir_full)}\n")
            if config["DO_FHR"]:
                runlist.write(f"fhr,{os.path.relpath(latest_fhr,args.outdir_full)}\n")

    if config["DO_TOA"]:
        # analzyse threshold scan
        logging.info("Analyzing THR scan")
        subprocess.run(f"../../analysis/dpts/thresholdana.py {latest_thr+'.json'} --outdir {os.path.dirname(latest_thr)} --quiet --energy-factor 1", shell=True, check=True)
        
        # create toa config
        logging.info("Creating config for TOA scan")
        with open("config_toa_tot_template.json") as jf:
            config_toa = json.load(jf)
        for key in config_toa:
            if key in config.keys():
                config_toa[key] = config[key]
        config_toa["thrmap_dir"] = os.path.abspath(os.path.dirname(latest_thr))+"/"
        for key in config:
            if key.startswith("toa_"):
                config_thr[key.removeprefix("toa_")] = config[key]
        config_path_toa = os.path.join(config_dir, f"config_{prefix}_toa_tot_char.json")
        with open(config_path_toa, "w") as jf:
            json.dump(config_toa, jf, indent=4)

        logging.info(f"Starting TOA/TOT scan with {os.path.basename(config_path_toa)}...")
        subprocess.run(f"./toa_tot_parameter_scan.py {config_path_toa} --outdir {args.outdir_full}", shell=True, check=True)
        
        list_of_files = glob.glob(args.outdir_full+"/*")
        latest_dir = max(list_of_files, key=os.path.getctime)
        latest_toa = glob.glob(f"{latest_dir}/toa*.json")[-1].removesuffix(".json")
        with open((args.outdir_full+"runlist.csv"),'a') as runlist:
            runlist.write(f"toa,{os.path.relpath(latest_toa,args.outdir_full)}\n")

    if config["DO_DECODING"]:
        # create decoding config
        logging.info("Creating config for decoding calibration")
        with open("config_decoding_template.json") as jf:
            config_decoding = json.load(jf)
        for key in config_decoding:
            if key in config.keys():
                config_decoding[key] = config[key]
        # if value := config.get("decoding_ninj"):
        #     config_decoding["ninj"] = value
        # if value := config.get("decoding_vcasb"):
        #     config_decoding["vcasb"] = value
        for key in config:
            if key.startswith("decoding_"):
                config_decoding[key.removeprefix("decoding_")] = config[key]
        # config_decoding["rows"] = []
        # config_decoding["cols"] = []
        config_path_decoding = os.path.join(config_dir, f"config_{prefix}_decoding_char.json")
        with open(config_path_decoding, "w") as jf:
            json.dump(config_decoding, jf, indent=4)

        logging.info(f"Starting decoding calibration with {os.path.basename(config_path_decoding)}...")
        subprocess.run(f"../../dpts/dpts_decoding_calib.py {config['proximity']} --config-json {config_path_decoding} --outdir {args.outdir_full}", shell=True, check=True)
        
        # cretae runlist
        latest_decoding = glob.glob(f"{args.outdir_full}/dpts_decoding_*.json")[-1].removesuffix(".json")
        with open((args.outdir_full+"runlist.csv"),'a') as runlist:
            runlist.write(f"decoding,{os.path.relpath(latest_decoding,args.outdir_full)}\n")

    if config["DO_SOURCE"]:
        # create source config
        logging.info("Creating config for source scan")
        with open("config_source_template.json") as jf:
            config_source = json.load(jf)
        for key in config_source:
            if key in config.keys():
                config_source[key] = config[key]
        # config_source["ntrg"] = config["source_ntrg"]
        # config_source["trg_ch"] = config["source_trg_ch"]
        for key in config:
            if key.startswith("source_"):
                config_source[key.removeprefix("source_")] = config[key]
        # if value := config.get("source_pixel"):
        #     config_source["pixel"] = value
        config_path_source = os.path.join(config_dir, f"config_{prefix}_source_char.json")
        with open(config_path_source, "w") as jf:
            json.dump(config_source, jf, indent=4)

        # open source
        logging.info("Source will be opened now...")
        subprocess.run(f"FW102C {config['FW102C_open']}", shell=True, check=True)

        logging.info(f"Starting source scan with {os.path.basename(config_path_source)}...")
        subprocess.run(f"../../dpts/dpts_source.py {config['proximity']} --config-json {config_path_source} --outdir {args.outdir_full}", shell=True, check=True)

        # close source
        logging.info("Source will be closed now...")
        subprocess.run(f"FW102C {config['FW102C_close']}", shell=True, check=True)

        # create runlist
        latest_source = glob.glob(f"{args.outdir_full}/dpts_source_*.json")[-1].removesuffix(".json")
        with open((args.outdir_full+"runlist.csv"),'a') as runlist:
            runlist.write(f"source,{os.path.relpath(latest_source,args.outdir_full)}\n")


    
