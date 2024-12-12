#!/usr/bin/env python3

__author__ = "Roberto Russo"
__maintainer__ = "Roberto Russo"
__email__ = "r.russo@cern.ch"
__status__ = "Development"

import logging, argparse, os, re
import json
import numpy as np
import pandas as pd
from tqdm import tqdm
from glob import glob
from itertools import combinations
import analysis_utils as au


def jitter_processing(args):
    scanned_vbb = au.list_vbb_dir(args.data_path)
    scanned_vbb.sort()
    for vbbpath in tqdm(scanned_vbb, desc="Vbb"):
        root_output_dir = os.path.join(vbbpath, f"time_jitter{args.file_suffix}")
        os.makedirs(root_output_dir, exist_ok=True)
        data = pd.read_csv(f"{vbbpath}/waveforms{args.file_suffix}.csv", sep="|")
        data_json_file = glob(f"{vbbpath}/opamp_vh_scan_*.json")[0]
        with open(data_json_file, 'r') as j:
            data_json = json.load(j)
        measured_vh = data_json["vh_array"]
        inner_pixel_connections = data_json["inner_pixel_connections"]
        pixel_couple_combinations = list(combinations(list(inner_pixel_connections.keys()), 2))
        for vh in tqdm(measured_vh, desc="Vh", leave=False):
            df = data.query(f"vh == {vh}")
            for pxs in tqdm(pixel_couple_combinations, desc="Pixel couples", leave=False):
                output_dir = os.path.join(root_output_dir, f"{inner_pixel_connections[pxs[0]]}-{inner_pixel_connections[pxs[1]]}")
                os.makedirs(output_dir, exist_ok=True)
                df_couple = df.query(f"ch == {float(pxs[0])} or ch == {float(pxs[1])}")
                df_couple = df_couple.groupby(['trg']).filter(lambda dataframe: dataframe['trg'].shape[0]==2)  # filter by only accepting triggers successfully processed for both pixels
                time_diff = np.zeros((9, int(df_couple.shape[0]/2)))  # generate ndarray to be filled with time differences
                trgs = df_couple['trg'].drop_duplicates().to_numpy()
                for i, CFD in enumerate(["t10", "t20", "t30", "t40", "t50", "t60", "t70", "t80", "t90"]):
                    df_CFD = df_couple[["ch", "trg", f"{CFD}"]]
                    for j, trg in enumerate(trgs):
                        time1 = df_CFD[(df_CFD['ch'] == float(pxs[0])) & (df_CFD['trg'] == trg)].iloc[0][f'{CFD}']
                        time2 = df_CFD[(df_CFD['ch'] == float(pxs[1])) & (df_CFD['trg'] == trg)].iloc[0][f'{CFD}']
                        time_diff[i, j] = time1 - time2  # [ps]
                np.save(f"{output_dir}/vh{vh}{args.file_suffix}.npy", time_diff)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APTS OPAMP routine to measure time residuals of pixel couples pulsed at varying Vh.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--data_path', '-d', help='Directory for input files.')
    parser.add_argument('--gain_calibration', '-g', action="store_true", help='Analyze gain calibrated data.')
    args = parser.parse_args()
    try:
        args.file_suffix = ""
        if args.gain_calibration:
            args.file_suffix = "_calibrated"
        jitter_processing(args)
    except KeyboardInterrupt:
        logging.info('User stopped.')
    except Exception as e:
        logging.exception(e)
        logging.fatal('Terminating!')
